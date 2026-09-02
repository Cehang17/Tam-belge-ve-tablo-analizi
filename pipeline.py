import os
import json
import torch
from PIL import Image
import fitz  # PyMuPDF
from huggingface_hub import hf_hub_download

# --- IMPORTS ---
from doclayout_yolo import YOLOv10
from transformers import TableTransformerForObjectDetection, AutoImageProcessor
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# --- GLOBAL MODEL DEĞİŞKENLERİ ---
layout_model = None
table_processor = None
table_model = None
det_model = None
det_processor = None
rec_model = None
rec_processor = None
_models_loaded = False


def load_models(status_callback=None):
    """Tüm modelleri bir kere yükler. status_callback(mesaj) ile ilerleme bildirimi yapılabilir."""
    global layout_model, table_processor, table_model
    global det_model, det_processor, rec_model, rec_processor
    global _models_loaded

    if _models_loaded:
        return

    def _status(msg):
        print(msg)
        if status_callback:
            status_callback(msg)

    # 1. DocLayout-YOLO
    _status("DocLayout-YOLO yükleniyor...")
    yolo_weight_path = hf_hub_download(
        repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
        filename="doclayout_yolo_docstructbench_imgsz1024.pt"
    )
    layout_model = YOLOv10(yolo_weight_path)

    # 2. Table Transformer
    _status("Table Transformer yükleniyor...")
    table_processor = AutoImageProcessor.from_pretrained("microsoft/table-transformer-structure-recognition")
    table_model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-structure-recognition")

    # 3. Surya OCR
    _status("Surya OCR yükleniyor...")
    det_model = load_det_model()
    det_processor = load_det_processor()
    rec_model = load_rec_model()
    rec_processor = load_rec_processor()

    _models_loaded = True
    _status("Tüm modeller başarıyla yüklendi.")


def pipeline_pdf_to_json(pdf_path, progress_callback=None):
    """
    PDF'i analiz edip tüm metinler, layout blokları (başlık, düz metin, şekil vb.) 
    ve tablolar (hücre bazlı) için yapılandırılmış JSON döndürür.
    """
    # Modeller yüklü değilse yükle
    if not _models_loaded:
        load_models()

    def _progress(page, total, msg):
        print(msg)
        if progress_callback:
            progress_callback(page, total, msg)

    _progress(0, 0, f"[Başladı] {os.path.basename(pdf_path)} işleniyor...")

    # PDF sayfalarını bellekte PIL Görsellerine dönüştür (PyMuPDF)
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)
    doc.close()

    final_output = []
    total_pages = len(pages)

    for page_idx, page_img in enumerate(pages):
        _progress(page_idx + 1, total_pages, f"Sayfa {page_idx + 1} / {total_pages} analiz ediliyor...")

        # 1. ADIM: TÜM SAYFADA SURYA OCR (Tüm metinleri ve satır koordinatlarını eksiksiz çıkar)
        _progress(page_idx + 1, total_pages, f"Sayfa {page_idx + 1}: Belge geneli Surya OCR okuması yapılıyor...")
        try:
            ocr_results = run_ocr([page_img], [["tr", "en"]], det_model, det_processor, rec_model, rec_processor)
            page_ocr_lines = ocr_results[0].text_lines if ocr_results else []
        except Exception as e:
            print(f"Sayfa {page_idx + 1} OCR hatası: {e}")
            page_ocr_lines = []

        full_page_text = "\n".join([line.text for line in page_ocr_lines]).strip()

        # 2. ADIM: DocLayout-YOLO ile Düzen (Layout) Analizi (imgsz=1024 ve hassas conf)
        _progress(page_idx + 1, total_pages, f"Sayfa {page_idx + 1}: DocLayout-YOLO ile düzen analizi yapılıyor...")
        try:
            layout_results = layout_model(page_img, imgsz=1024, conf=0.15, verbose=False)[0]
            boxes = layout_results.boxes
        except Exception as e:
            print(f"Sayfa {page_idx + 1} DocLayout-YOLO hatası: {e}")
            boxes = []

        page_data = {
            "page": page_idx + 1,
            "full_text": full_page_text,
            "elements": []
        }

        # Kullanılan OCR satırlarının indekslerini takip et
        matched_ocr_line_indices = set()

        # Tespit edilen layout bölgelerini dön
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            score = float(box.conf[0].item())
            label = layout_model.names[int(box.cls[0].item())]

            # Bu layout kutusunun içine düşen OCR satırlarını bul
            region_lines = []
            for l_idx, line in enumerate(page_ocr_lines):
                lx1, ly1, lx2, ly2 = line.bbox
                l_center_x = (lx1 + lx2) / 2
                l_center_y = (ly1 + ly2) / 2
                # Merkez koordinatı veya toleranslı örtüşme
                if (x1 - 10) <= l_center_x <= (x2 + 10) and (y1 - 10) <= l_center_y <= (y2 + 10):
                    region_lines.append((l_idx, line))
                    matched_ocr_line_indices.add(l_idx)

            region_ocr_lines = [l for _, l in region_lines]
            region_text = "\n".join([l.text for l in region_ocr_lines]).strip()

            # Bölge bir TABLO ise Table Transformer ile Satır/Sütun ve Hücre Ayrıştırması
            if label == "table":
                _progress(page_idx + 1, total_pages, f"Sayfa {page_idx + 1}: Tablo tespit edildi, hücre ızgarası ayrıştırılıyor...")
                cropped_region = page_img.crop((x1, y1, x2, y2))
                
                table_rows = []
                table_cols = []
                try:
                    inputs = table_processor(images=cropped_region, return_tensors="pt")
                    with torch.no_grad():
                        outputs = table_model(**inputs)

                    target_sizes = torch.tensor([cropped_region.size[::-1]])
                    results = table_processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]

                    for score_val, label_idx, box_val in zip(results["scores"], results["labels"], results["boxes"]):
                        cell_label = table_model.config.id2label[label_idx.item()]
                        bx1, by1, bx2, by2 = map(int, box_val.tolist())

                        if cell_label in ["table row", "table column header", "table projected row header"]:
                            table_rows.append({"coords": [bx1, by1, bx2, by2], "is_header": "header" in cell_label})
                        elif cell_label == "table column":
                            table_cols.append({"coords": [bx1, by1, bx2, by2]})

                    table_rows.sort(key=lambda r: r["coords"][1])
                    table_cols.sort(key=lambda c: c["coords"][0])
                except Exception as e:
                    print(f"Table Transformer hatası: {e}")

                # Tablo içi OCR satırları: Eğer bölge OCR'ı boşsa kırpıntı üzerinde ek OCR çalıştır
                if not region_ocr_lines:
                    try:
                        sub_ocr = run_ocr([cropped_region], [["tr", "en"]], det_model, det_processor, rec_model, rec_processor)
                        region_ocr_lines = sub_ocr[0].text_lines if sub_ocr else []
                        region_text = "\n".join([l.text for l in region_ocr_lines]).strip()
                    except Exception:
                        pass

                table_cells = []

                if table_rows and table_cols:
                    # Satır ve Sütun kesişimlerinden hücre ızgarası oluştur
                    for r_idx, row in enumerate(table_rows):
                        ry1, ry2 = row["coords"][1], row["coords"][3]
                        for c_idx, col in enumerate(table_cols):
                            cx1, cx2 = col["coords"][0], col["coords"][2]

                            # Göreceli ve Mutlak Hücre sınırları
                            cell_bbox = [cx1, ry1, cx2, ry2]
                            abs_bbox = [x1 + cx1, y1 + ry1, x1 + cx2, y1 + ry2]

                            # Bu hücrenin içine düşen OCR metinlerini eşleştir
                            matching_texts = []
                            for line in region_ocr_lines:
                                lx1, ly1, lx2, ly2 = line.bbox
                                l_center_x = (lx1 + lx2) / 2
                                l_center_y = (ly1 + ly2) / 2
                                
                                # Satır mutlak koordinatta mı göreceli mi kontrol et
                                in_abs = (abs_bbox[0] - 8) <= l_center_x <= (abs_bbox[2] + 8) and (abs_bbox[1] - 8) <= l_center_y <= (abs_bbox[3] + 8)
                                in_rel = (cx1 - 8) <= l_center_x <= (cx2 + 8) and (ry1 - 8) <= l_center_y <= (ry2 + 8)
                                
                                if in_abs or in_rel:
                                    matching_texts.append(line.text.strip())

                            cell_text = " ".join(matching_texts).strip()

                            table_cells.append({
                                "row": r_idx,
                                "col": c_idx,
                                "is_header": row["is_header"],
                                "cell_coords": cell_bbox,
                                "abs_coords": abs_bbox,
                                "text": cell_text
                            })
                else:
                    # Satır/sütun tespit edilemediyse doğrudan OCR satırlarını hücre olarak ekle
                    for l_idx, line in enumerate(region_ocr_lines):
                        lx1, ly1, lx2, ly2 = map(int, line.bbox)
                        table_cells.append({
                            "row": l_idx,
                            "col": 0,
                            "is_header": False,
                            "cell_coords": [lx1 - x1 if lx1 >= x1 else lx1, ly1 - y1 if ly1 >= y1 else ly1, lx2 - x1 if lx2 >= x1 else lx2, ly2 - y1 if ly2 >= y1 else ly2],
                            "abs_coords": [lx1 if lx1 >= x1 else x1 + lx1, ly1 if ly1 >= y1 else y1 + ly1, lx2 if lx2 >= x1 else x1 + lx2, ly2 if ly2 >= y1 else y1 + ly2],
                            "text": line.text.strip()
                        })

                page_data["elements"].append({
                    "type": "table",
                    "coords": [x1, y1, x2, y2],
                    "confidence": score,
                    "num_rows": len(table_rows) if table_rows else len(table_cells),
                    "num_cols": len(table_cols) if table_cols else 1,
                    "cells": table_cells,
                    "raw_text": region_text
                })

            # DİĞER TÜM LAYOUT ALANLARI (title, plain text, figure, figure_caption, table_caption, header, footer vb.)
            else:
                page_data["elements"].append({
                    "type": label,
                    "coords": [x1, y1, x2, y2],
                    "confidence": score,
                    "text": region_text
                })

        # 3. ADIM: DocLayout-YOLO'nun kaçırdığı herhangi bir OCR satırı varsa fallback olarak layout'a ekle (Sıfır Veri Kaybı)
        unmatched_lines = [page_ocr_lines[i] for i in range(len(page_ocr_lines)) if i not in matched_ocr_line_indices]
        if unmatched_lines:
            # Komşu eşleşmemiş satırları birleştirip text bloğu yap
            current_block = []
            for u_line in unmatched_lines:
                if not current_block:
                    current_block.append(u_line)
                else:
                    prev_y2 = current_block[-1].bbox[3]
                    curr_y1 = u_line.bbox[1]
                    if abs(curr_y1 - prev_y2) < 40:  # Aynı blok mesafesi
                        current_block.append(u_line)
                    else:
                        bx1 = min(l.bbox[0] for l in current_block)
                        by1 = min(l.bbox[1] for l in current_block)
                        bx2 = max(l.bbox[2] for l in current_block)
                        by2 = max(l.bbox[3] for l in current_block)
                        b_text = "\n".join(l.text for l in current_block).strip()
                        if b_text:
                            page_data["elements"].append({
                                "type": "plain text",
                                "coords": [int(bx1), int(by1), int(bx2), int(by2)],
                                "confidence": 0.90,
                                "text": b_text
                            })
                        current_block = [u_line]

            if current_block:
                bx1 = min(l.bbox[0] for l in current_block)
                by1 = min(l.bbox[1] for l in current_block)
                bx2 = max(l.bbox[2] for l in current_block)
                by2 = max(l.bbox[3] for l in current_block)
                b_text = "\n".join(l.text for l in current_block).strip()
                if b_text:
                    page_data["elements"].append({
                        "type": "plain text",
                        "coords": [int(bx1), int(by1), int(bx2), int(by2)],
                        "confidence": 0.90,
                        "text": b_text
                    })

        # Sayfa içi elemanları dikey konuma (y koordinatına) göre doğal okuma sırasına diz
        page_data["elements"].sort(key=lambda elem: elem["coords"][1])
        final_output.append(page_data)

    return final_output


# --- CLI ÇALIŞTIRMA ---
if __name__ == "__main__":
    load_models()

    pdf_file = "ornek_dokuman.pdf"

    if not os.path.exists(pdf_file):
        print(f"\nHATA: Lütfen kodun yanına '{pdf_file}' adında bir PDF koyun veya yolu güncelleyin.")
    else:
        result_json = pipeline_pdf_to_json(pdf_file)

        output_json_path = "output_structure.json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=4)

        print(f"\n[Başarılı] İşlem tamamlandı. Yapılandırılmış çıktı '{output_json_path}' dosyasına kaydedildi.")