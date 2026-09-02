# 🚀 SUNUCUYU BAŞLATMA REHBERİ

## Sorunlar ve Çözümleri

### Sorun 1: Python Terminali Açılmıyor
**Çözüm:** PyTorch ve model paketleri yüklenmesi gerekiyor.

### Sorun 2: "No module named 'torch'"
**Çözüm:** PyTorch kurulması gerekiyor (2-10 dakika alabilir).

### Sorun 3: "No module named 'doclayout_yolo'"
**Çözüm:** Model paketleri kurulması gerekiyor (biraz zaman alabilir).

---

## ✅ ÇÖZÜM (3 SEÇENEĞİ DENE)

### SEÇENEK 1: Batch Dosyası (En Kolay) ⭐ ÖNERILEN
1. Dosya yöneticisinde projeye git
2. **`start_server.bat`** dosyasını **çift tıkla**
3. Otomatik olarak:
   - Flask yüklenir
   - Werkzeug yüklenir  
   - Flask-CORS yüklenir
   - **PyTorch yüklenir** (2-10 dakika) ⏳
   - Model paketleri yüklenir
   - Sunucu başlar

✅ Başarılı olursa göreceksin:
```
Tarayıcınızda oturun:
  http://127.0.0.1:5000
```

**⚠️ ÖNEMLİ:** PyTorch yüklenmesi 2-10 dakika alabilir. SABIR EDEN BEKLEME!

---

### SEÇENEK 2: VS Code Terminal (Alternatif)
1. VS Code'da **Ctrl + `` ** tuşuna bas (terminal aç)
2. Aşağıdaki komutu **kopyala ve yapıştır**:

```powershell
python -m pip install flask werkzeug flask-cors; python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; python -m pip install -r requirements.txt; python app.py
```

PowerShell ve Bash'ta `;` ile ayırman lazım (Windows CMD'de `&&` kullanılır).

Eğer PowerShell'de sorun yaşarsan:
```powershell
python -m pip install -r requirements.txt; python app.py
```

3. **Enter** tuşuna bas
4. Bekle (PyTorch yüklenmesi zaman alacak)
5. Tarayıcıda **http://127.0.0.1:5000** aç

---

### SEÇENEK 3: Python Script (Alternatif)
1. VS Code'da terminal aç (Ctrl + ``)
2. Şu komutu yaz:

```powershell
python start_server.py
```

3. **Enter** tuşuna bas
4. Bekle (PyTorch yüklenmesi 2-10 dakika)

---

## 📦 Kurulan Paketler

### Web Sunucusu
- Flask
- Werkzeug
- Flask-CORS

### Makine Öğrenmesi (Zaman Alır) ⏳
- **PyTorch** (2-10 dakika!) - AI modelleri için
- torchvision - Görüntü işleme
- transformers - Dönüştürücü modelleri
- huggingface-hub - Model indirme

### Görüntü ve Metin
- Pillow - Görüntü işleme
- PyMuPDF - PDF okuma

### Doküman Analiz Modelleri
- **doclayout-yolo** - Layout detection
- **surya-ocr** - Metin tanıma (OCR)

---

## 🔍 SORUN GİDERME

### "HATA: Paketler yuklenemedi!"
1. Antivirus'u kurulum sırasında geçici olarak kapat
2. Seçenek 1 (batch dosyası) yeniden dene
3. Terminal çıktısını ekran görüntüsü olarak göster

### "Bağlantı reddedildi" veya "Failed to fetch"
**Çözüm:** Sunucu çalışmıyor
1. Terminal penceresinde Flask başlangıç mesajı var mı kontrol et
2. `Ctrl+C` ile kapatıp yeniden başlat
3. http://127.0.0.1:5000 tarayıcıda aç

### "Port 5000 zaten kullanımda"
**Çözüm:** 
- Başka bir Flask sunucusu veya uygulaması çalışıyor
- Task Manager'da Python'ı bul ve kapat
- Ya da app.py'de port numarasını değiştir

### "PyTorch kurulumu başarısız oldu"
Bu sorun:
1. İnternet bağlantısı koptuğunda olur
2. Disk alanı yetersizse olur (minimum 5 GB)
3. Antivirus engelliyorsa olur

Çözüm:
- İnternet bağlantısı kontrol et
- Disk alanını boşalt (en az 5 GB)
- Antivirus'u geçici olarak kapat
- Tekrar dene

---

## ✔️ BAŞARILI İŞE YARADI MI?

✅ Tarayıcıda http://127.0.0.1:5000 açılıyorsa TAMAMDIR!

Görmek gerekli:
- 🟢 Yeşil "Hazır" yazısı ← Modeller yüklendi
- 🟡 Sarı "Yükleniyor" yazısı ← Bekle biraz daha
- PDF yükleme alanı

---

## 📝 DOSYALAR

- **start_server.bat** - Windows çift tıklamak için (ÖNERILEN)
- **start_server.py** - Python ile çalıştırmak için
- **requirements.txt** - Tüm Python paketleri
- **app.py** - Flask uygulaması (ana dosya)
- **pipeline.py** - Model yükleme ve işleme

---

## ⏳ BEKLEME SÜRELERİ

İlk kez çalıştırırken:
- Flask paketleri: 30 saniye
- PyTorch: 2-10 dakika 🐌
- Model paketleri: 2-5 dakika
- **TOPLAM: 5-20 dakika** ⏱️

Sonraki açılışlarda paketler tekrar yüklenmez, çok hızlı açılır!

---

**Hala sorun mu var? Terminal çıktısını ve hata mesajını paylaş!** 📸
