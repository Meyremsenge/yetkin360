@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Yetkin360 - Baslatici
cd /d "%~dp0"

echo ============================================================
echo   Yetkin360 - Otomatik Baslatma
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1) Docker Desktop kontrolu
REM ------------------------------------------------------------
echo [1/7] Docker kontrol ediliyor...
docker info >nul 2>&1
if errorlevel 1 (
    echo   Docker calismiyor, Docker Desktop baslatiliyor...
    set "DOCKER_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    if exist "!DOCKER_EXE!" (
        start "" "!DOCKER_EXE!"
    ) else (
        echo   HATA: Docker Desktop bulunamadi: "!DOCKER_EXE!"
        echo   Docker Desktop'i elle baslatip bu scripti tekrar calistir.
        pause
        exit /b 1
    )
    echo   Docker'in ayaga kalkmasi bekleniyor (bu 30-60 saniye surebilir)...
    set "DOCKER_READY="
    for /l %%i in (1,1,60) do (
        docker info >nul 2>&1
        if not errorlevel 1 (
            set "DOCKER_READY=1"
            goto docker_ready
        )
        timeout /t 2 /nobreak >nul
    )
    :docker_ready
    if not defined DOCKER_READY (
        echo   HATA: Docker 2 dakika icinde ayaga kalkmadi. Elle kontrol et.
        pause
        exit /b 1
    )
)
echo   Docker calisiyor.
echo.

REM ------------------------------------------------------------
REM 2) Dolu port kontrolu (5432 postgres, 9000/9001 minio, 8000 backend, 3000 frontend)
REM    Doluysa: sahibi bizim docker-compose container'imiz mi diye bakma yapmiyoruz,
REM    onun yerine "bu portu kullanan PID'i durdurmak ister misin" diye soruyoruz.
REM ------------------------------------------------------------
echo [2/7] Portlar kontrol ediliyor (5432, 9000, 9001, 8000, 3000)...
for %%P in (5432 9000 9001 8000 3000) do call :check_port %%P
echo.

REM ------------------------------------------------------------
REM 3) .env dosyasi kontrolu
REM ------------------------------------------------------------
echo [3/7] .env kontrol ediliyor...
if not exist ".env" (
    echo   .env bulunamadi, .env.example'dan kopyalaniyor...
    copy /y ".env.example" ".env" >nul
    echo   UYARI: .env icindeki DEGISTIR_ ile baslayan placeholder degerleri
    echo   gercek degerlerle degistirmen gerekebilir (uretim icin zorunlu,
    echo   yerel gelistirme icin genelde varsayilanlar calisir).
)
echo   .env hazir.
echo.

REM ------------------------------------------------------------
REM 4) PostgreSQL + MinIO container'lari
REM ------------------------------------------------------------
echo [4/7] PostgreSQL + MinIO baslatiliyor (docker compose up -d)...
docker compose up -d
if errorlevel 1 (
    echo   HATA: docker compose up -d basarisiz oldu.
    pause
    exit /b 1
)
echo   Container'lar ayakta. Veritabaninin hazir olmasi bekleniyor...
timeout /t 5 /nobreak >nul
echo.

REM ------------------------------------------------------------
REM 5) Backend: venv + bagimliliklar + migration + seed
REM ------------------------------------------------------------
echo [5/7] Backend hazirlaniyor...
cd backend

if not exist ".venv\Scripts\python.exe" (
    echo   Sanal ortam (.venv) bulunamadi, olusturuluyor...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo   Bagimliliklar kontrol ediliyor / kuruluyor...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

echo   Migration uygulaniyor (alembic upgrade head)...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    echo   HATA: Migration basarisiz oldu. Yukaridaki hatayi incele.
    cd ..
    pause
    exit /b 1
)

echo   Seed verisi yukleniyor (idempotent, tekrar calistirmak guvenli)...
".venv\Scripts\python.exe" -m scripts.seed

cd ..
echo   Backend hazir.
echo.

REM ------------------------------------------------------------
REM 6) Frontend: node_modules
REM ------------------------------------------------------------
echo [6/7] Frontend hazirlaniyor...
cd frontend
if not exist "node_modules" (
    echo   node_modules bulunamadi, npm install calistiriliyor...
    call npm install
)
cd ..
echo   Frontend hazir.
echo.

REM ------------------------------------------------------------
REM 7) Backend ve frontend'i ayri pencerelerde baslat, tarayiciyi ac
REM ------------------------------------------------------------
echo [7/7] Sunucular baslatiliyor...
start "Yetkin360 - Backend (8000)" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Yetkin360 - Frontend (3000)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo   Sunucularin ayaga kalkmasi bekleniyor (10 saniye)...
timeout /t 10 /nobreak >nul

echo   Tarayici aciliyor: http://localhost:3000
start "" "http://localhost:3000"

echo.
echo ============================================================
echo   Yetkin360 baslatildi.
echo   Frontend : http://localhost:3000
echo   Backend  : http://localhost:8000/docs  (FastAPI Swagger)
echo   MinIO    : http://localhost:9001       (konsol)
echo.
echo   Seed giris bilgileri (backend/scripts/seed.py, sabit test sifresi):
echo     Ogrenci      : ogrenci1@seed.local .. ogrenci20@seed.local
echo     Kurum admin  : kurum1-admin@seed.local .. kurum5-admin@seed.local
echo     Organizasyon : org1-admin@seed.local .. org5-admin@seed.local
echo     Sifre (hepsi): SeedTest123!
echo.
echo   Bu pencereyi kapatabilirsin, backend/frontend ayri pencerelerde
echo   calismaya devam eder. Durdurmak icin o pencereleri kapat.
echo ============================================================
pause
exit /b 0

REM ============================================================
REM Fonksiyon: verilen portu dinleyen PID varsa sor, istenirse sonlandir
REM ============================================================
:check_port
set "PORT=%~1"
set "FOUND_PID="
for /f "tokens=5" %%A in ('netstat -aon ^| findstr /r /c:":%PORT% .*LISTENING"') do (
    set "FOUND_PID=%%A"
)
if defined FOUND_PID (
    echo   UYARI: Port %PORT% dolu (PID !FOUND_PID!).
    for /f "tokens=1" %%N in ('tasklist /fi "PID eq !FOUND_PID!" /fo csv /nh 2^>nul') do set "PROC_NAME=%%~N"
    echo     Sureci kullanan uygulama: !PROC_NAME!
    choice /c EH /n /m "    Bu sureci sonlandirmak icin E, atlamak icin H tusuna bas: "
    if errorlevel 2 (
        echo     Atlandi - port %PORT% dolu kalabilir, sonraki adim basarisiz olabilir.
    ) else (
        taskkill /f /pid !FOUND_PID! >nul 2>&1
        echo     PID !FOUND_PID! sonlandirildi, port %PORT% bosaltildi.
    )
) else (
    echo   Port %PORT% bos.
)
exit /b 0
