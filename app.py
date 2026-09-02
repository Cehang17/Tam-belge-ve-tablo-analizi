import os
import json
import uuid
import threading
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
app.config['JSON_AS_ASCII'] = False  # Support Turkish characters

# Enable CORS for frontend requests
try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    logger.warning("flask-cors not installed. Install with: pip install flask-cors")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# --- Analiz durumu takibi ---
analysis_status = {}  # job_id -> { status, message, progress, result_file }

# --- Model yükleme ---
models_ready = False
models_loading = False
model_load_error = None


def ensure_models():
    """Modelleri arka planda bir kere yükle."""
    global models_ready, models_loading, model_load_error
    if models_ready or models_loading:
        return
    models_loading = True

    def _load():
        global models_ready, models_loading, model_load_error
        try:
            from pipeline import load_models
            load_models()
            models_ready = True
        except ModuleNotFoundError as e:
            missing_module = str(e).split("'")[1] if "'" in str(e) else str(e)
            model_load_error = (
                f"Paket eksik: '{missing_module}'\n\n"
                f"Çözüm:\n"
                f"1. Terminal'de şunu çalıştır:\n"
                f"   python -m pip install -r requirements.txt\n"
                f"2. Sonra uygulamayı yeniden başlat\n\n"
                f"PyTorch kurulması 2-10 dakika alabilir."
            )
            logger.error(f"Model loading error: {model_load_error}")
        except Exception as e:
            model_load_error = str(e)
            logger.error(f"Model loading error: {e}")
        finally:
            models_loading = False

    t = threading.Thread(target=_load, daemon=True)
    t.start()


# Sunucu başlarken modelleri yüklemeye başla
ensure_models()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def get_model_status():
    """Model yükleme durumunu döndür."""
    logger.info(f"Status check: models_ready={models_ready}, models_loading={models_loading}")
    return jsonify({
        'models_ready': models_ready,
        'models_loading': models_loading,
        'error': model_load_error
    })


@app.route('/api/upload', methods=['POST'])
def upload_and_analyze():
    """PDF yükle ve analiz işini başlat."""
    logger.info("Upload request received")
    if not models_ready:
        logger.warning("Upload attempted but models not ready")
        return jsonify({'error': 'Modeller henüz yükleniyor, lütfen bekleyin...'}), 503

    if 'file' not in request.files:
        return jsonify({'error': 'Dosya seçilmedi.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi.'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Sadece PDF dosyaları desteklenir.'}), 400

    # Benzersiz iş kimliği oluştur
    job_id = str(uuid.uuid4())[:8]
    filename = secure_filename(file.filename)
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{filename}")
    file.save(pdf_path)

    # Analiz durumunu başlat
    analysis_status[job_id] = {
        'status': 'running',
        'message': 'PDF yüklendi, analiz başlatılıyor...',
        'progress': 0,
        'total_pages': 0,
        'result_file': None,
        'original_name': filename
    }

    # Arka planda analiz başlat
    t = threading.Thread(target=_run_analysis, args=(job_id, pdf_path, filename), daemon=True)
    t.start()

    return jsonify({'job_id': job_id})


def _run_analysis(job_id, pdf_path, original_filename):
    """Arka planda pipeline çalıştır."""
    try:
        from pipeline import pipeline_pdf_to_json

        def progress_cb(page, total, msg):
            analysis_status[job_id]['progress'] = page
            analysis_status[job_id]['total_pages'] = total
            analysis_status[job_id]['message'] = msg

        result = pipeline_pdf_to_json(pdf_path, progress_callback=progress_cb)

        # Sonucu JSON olarak kaydet
        base_name = os.path.splitext(original_filename)[0]
        result_filename = f"{job_id}_{base_name}_layout.json"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        analysis_status[job_id]['status'] = 'done'
        analysis_status[job_id]['message'] = 'Analiz tamamlandı!'
        analysis_status[job_id]['result_file'] = result_filename
        analysis_status[job_id]['data'] = result

    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_status[job_id]['status'] = 'error'
        analysis_status[job_id]['message'] = f'Hata: {str(e)}'

    finally:
        # Yüklenen PDF'i temizle
        try:
            os.remove(pdf_path)
        except OSError:
            pass


@app.route('/api/job/<job_id>')
def job_status(job_id):
    """İş durumunu sorgula."""
    if job_id not in analysis_status:
        return jsonify({'error': 'Geçersiz iş kimliği.'}), 404
    return jsonify(analysis_status[job_id])


@app.route('/api/result/<job_id>')
def get_job_result(job_id):
    """Analiz sonucunun tam JSON verisini döndür."""
    if job_id not in analysis_status:
        return jsonify({'error': 'Geçersiz iş kimliği.'}), 404
    
    job = analysis_status[job_id]
    if job.get('status') != 'done':
        return jsonify({'error': 'Analiz henüz tamamlanmadı.', 'status': job.get('status')}), 400

    if 'data' in job and job['data'] is not None:
        return jsonify(job['data'])

    result_file = job.get('result_file')
    if result_file:
        filepath = os.path.join(RESULTS_FOLDER, secure_filename(result_file))
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))

    return jsonify({'error': 'Sonuç bulunamadı.'}), 404


@app.route('/api/download/<filename>')
def download_result(filename):
    """Sonuç JSON dosyasını indir."""
    filepath = os.path.join(RESULTS_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({'error': 'Dosya bulunamadı.'}), 404

    # İndirme adını güzelleştir (job_id'yi kaldır)
    parts = filename.split('_', 1)
    download_name = parts[1] if len(parts) > 1 else filename

    return send_file(filepath, as_attachment=True, download_name=download_name)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Layout Analiz Arayüzü Başlatılıyor...")
    print("  Tarayıcıda açın: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=False, port=5000)
