@echo off
REM Startup script for Flask server on Windows
REM Flask ve diger paketleri yukleyip sunucuyu baslatir

echo.
echo ====================================================================
echo   DocLayout Analiz Sunucusu Baslatiliyor...
echo ====================================================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Use full Python path
set PYTHON_PATH=C:\Users\HASAN_WIN11\AppData\Local\Programs\Python\Python310\python.exe

REM Check if Python exists
if not exist "%PYTHON_PATH%" (
    echo HATA: Python kurulu degil!
    echo Yukleyin: https://www.python.org
    pause
    exit /b 1
)

echo Python bulundu: %PYTHON_PATH%
echo.
echo ====================================================================
echo  ADIM 1: Flask ve temel paketler yükleniyor...
echo ====================================================================
echo.

REM Install base packages first
"%PYTHON_PATH%" -m pip install --upgrade pip setuptools wheel
"%PYTHON_PATH%" -m pip install flask werkzeug flask-cors

if errorlevel 1 (
    echo.
    echo HATA: Temel paketler yuklenemedi!
    pause
    exit /b 1
)

echo ====================================================================
echo  ADIM 2: PyTorch yükleniyor (Bu biraz surebilir...)
echo ====================================================================
echo.
echo PyTorch indirilip kurulması 2-10 dakika alabilir.
echo Lütfen bekleyin...
echo.

REM Install PyTorch and other ML dependencies
"%PYTHON_PATH%" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

if errorlevel 1 (
    echo.
    echo HATA: PyTorch yuklenemedi!
    echo El ile yoklemeyi dene:
    echo "%PYTHON_PATH%" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo  ADIM 3: Model ve OCR paketleri yükleniyor...
echo ====================================================================
echo.

REM Install remaining packages from requirements.txt
if exist "requirements.txt" (
    echo requirements.txt bulundu, paketler yükleniyor...
    "%PYTHON_PATH%" -m pip install -r requirements.txt
) else (
    echo requirements.txt bulunamadi, manual kurulum yapiliyor...
    "%PYTHON_PATH%" -m pip install transformers huggingface-hub Pillow PyMuPDF doclayout-yolo surya-ocr
)

if errorlevel 1 (
    echo.
    echo HATA: Model paketleri yuklenemedi!
    echo Bu sorun sonra model yukleme sirasinda ortaya cikabilir.
    echo.
)

echo.
echo ====================================================================
echo  ADIM 4: Sunucu baslatiliyor...
echo ====================================================================
echo.
echo Tarayicinizda oturun:
echo   http://127.0.0.1:5000
echo.
echo Kapatmak icin Ctrl+C tusuna basin.
echo.

REM Run the Flask app
"%PYTHON_PATH%" app.py

pause
