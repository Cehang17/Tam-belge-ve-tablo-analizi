#!/usr/bin/env python3
"""
DocLayout Flask Sunucusu Başlatıcı
Paketleri yükler ve sunucuyu başlatır
"""
import subprocess
import sys
import os

def install_packages():
    """Tüm gerekli paketleri yükler"""
    print("\n" + "=" * 60)
    print("ADIM 1: Flask ve temel paketler yükleniyor...")
    print("=" * 60 + "\n")
    
    # Step 1: Upgrade pip and install base packages
    base_packages = ['flask', 'werkzeug', 'flask-cors']
    
    print("  → pip güncelleniyor...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'],
                   capture_output=True)
    
    for pkg in base_packages:
        print(f"  → {pkg} yükleniyor...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ✗ HATA: {pkg} kurulamadı!")
            return False
    
    print("\n" + "=" * 60)
    print("ADIM 2: PyTorch yükleniyor (2-10 dakika alabilir)...")
    print("=" * 60 + "\n")
    print("  → PyTorch CPU versiyonu indirilip kuruluyor...")
    print("  → Lütfen bekleyin...\n")
    
    # Step 2: Install PyTorch
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'torch', 'torchvision', 'torchaudio',
         '--index-url', 'https://download.pytorch.org/whl/cpu'],
        timeout=600  # 10 minute timeout
    )
    
    if result.returncode != 0:
        print("\n  ✗ PyTorch kurulumu başarısız!")
        print("  → Model yükleme sırasında hata alabilirsiniz\n")
        return False
    
    print("  ✓ PyTorch kuruldu\n")
    
    print("=" * 60)
    print("ADIM 3: Model ve OCR paketleri yükleniyor...")
    print("=" * 60 + "\n")
    
    # Step 3: Install remaining packages
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    if os.path.exists(requirements_file):
        print(f"  → requirements.txt bulundu")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_file],
            capture_output=True, text=True,
            timeout=600
        )
    else:
        print(f"  → requirements.txt bulunamadı, manual kurulum yapiliyor...")
        ml_packages = ['transformers', 'huggingface-hub', 'Pillow', 'PyMuPDF',
                      'doclayout-yolo', 'surya-ocr']
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install'] + ml_packages,
            capture_output=True, text=True,
            timeout=600
        )
    
    if result.returncode != 0:
        print("  ⚠ Uyarı: Bazı model paketleri kurulamayabilir")
        if result.stderr:
            print(f"  Hata: {result.stderr[:200]}")
        print("  → Bu sorun model yükleme sırasında ortaya çıkabilir\n")
    
    return True

def main():
    print("\n" + "=" * 60)
    print("  DocLayout Analiz Sunucusu Başlatılıyor...")
    print("=" * 60)
    
    try:
        if not install_packages():
            print("\nHATA: Paket kurulumu tamamlanamadı!")
            return False
        
        print("\n" + "=" * 60)
        print("ADIM 4: Flask sunucusu başlatılıyor...")
        print("=" * 60)
        print("\nTarayıcınızda açın:")
        print("  → http://127.0.0.1:5000")
        print("\nKapatmak için Ctrl+C tuşuna basın.\n")
        
        # Run Flask app
        os.system(f'{sys.executable} app.py')
        
        return True
    
    except KeyboardInterrupt:
        print("\n\nSunucu kapatıldı.")
        return True
    except Exception as e:
        print(f"\nHATA: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)


