@echo off
REM No enabledelayedexpansion: it swallows "!" in echo, e.g. the seed password.
setlocal
chcp 65001 >nul
title Yetkin360 - Baslatici
cd /d "%~dp0"

REM NOTE: Inside parenthesized blocks, never echo text containing "(" or ")".
REM An unescaped ")" closes the block early and cmd aborts with a syntax error.
REM This file must keep CRLF line endings (see .gitattributes), otherwise
REM goto/call :label break.

echo ============================================================
echo   Yetkin360 - Otomatik Baslatma
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1) Docker Desktop kontrolu
REM ------------------------------------------------------------
echo [1/7] Docker kontrol ediliyor...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok

echo   Docker calismiyor, Docker Desktop baslatiliyor...
set "DOCKER_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not exist "%DOCKER_EXE%" (
    echo   HATA: Docker Desktop bulunamadi: "%DOCKER_EXE%"
    echo   Docker Desktop'i elle baslatip bu scripti tekrar calistir.
    pause
    exit /b 1
)
start "" "%DOCKER_EXE%"
echo   Docker'in ayaga kalkmasi bekleniyor, bu 30-60 saniye surebilir...
set /a DOCKER_TRIES=0

:docker_wait
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
set /a DOCKER_TRIES+=1
if %DOCKER_TRIES% geq 60 (
    echo   HATA: Docker 2 dakika icinde ayaga kalkmadi. Elle kontrol et.
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto docker_wait

:docker_ok
echo   Docker calisiyor.
echo.

REM ------------------------------------------------------------
REM 2) Dolu port kontrolu (5432 postgres, 9000/9001 minio, 8000 backend, 3000 frontend)
REM    Doluysa portu kullanan sureci gosterip durdurmak isteyip istemedigini soruyoruz.
REM ------------------------------------------------------------
echo [2/7] Portlar kontrol ediliyor: 5432, 9000, 9001, 8000, 3000
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
    echo   gercek degerlerle degistirmen gerekebilir. Uretim icin zorunlu,
    echo   yerel gelistirme icin genelde varsayilanlar calisir.
)
echo   .env hazir.
echo.

REM ------------------------------------------------------------
REM 4) PostgreSQL + MinIO container'lari
REM ------------------------------------------------------------
echo [4/7] PostgreSQL + MinIO baslatiliyor: docker compose up -d
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
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo   Sanal ortam .venv bulunamadi, olusturuluyor...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo   HATA: .venv olusturulamadi. Python 3.12 kurulu mu?
    pause
    exit /b 1
)

REM Health check: compiled extensions built for another Python version (e.g. cp311
REM inside a 3.12 venv) look "installed" to pip but fail on import. Force reinstall then.
set "PIP_FORCE="
".venv\Scripts\python.exe" -c "import pydantic_core._pydantic_core, psycopg, cffi, pydantic_settings" >nul 2>&1
if errorlevel 1 set "PIP_FORCE=--force-reinstall"
if defined PIP_FORCE echo   .venv paketleri eksik veya bozuk, tum bagimliliklar yeniden kuruluyor...

echo   Bagimliliklar kontrol ediliyor / kuruluyor...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q %PIP_FORCE% -r requirements.txt
if errorlevel 1 (
    echo   HATA: Bagimliliklar kurulamadi. Yukaridaki hatayi incele.
    pause
    exit /b 1
)

echo   Migration uygulaniyor: alembic upgrade head
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    echo   HATA: Migration basarisiz oldu. Yukaridaki hatayi incele.
    pause
    exit /b 1
)

echo   Seed verisi yukleniyor, idempotent - tekrar calistirmak guvenli...
".venv\Scripts\python.exe" -m scripts.seed
if errorlevel 1 (
    echo   UYARI: Seed basarisiz oldu, devam ediliyor. Yukaridaki hatayi incele.
)

cd /d "%~dp0"
echo   Backend hazir.
echo.

REM ------------------------------------------------------------
REM 6) Frontend: node_modules
REM ------------------------------------------------------------
echo [6/7] Frontend hazirlaniyor...
cd /d "%~dp0frontend"
REM Always run: package.json may have gained packages since node_modules was created.
echo   Paketler kontrol ediliyor / kuruluyor: npm install
call npm install --no-audit --no-fund
if errorlevel 1 (
    echo   HATA: npm install basarisiz oldu.
    pause
    exit /b 1
)
cd /d "%~dp0"
echo   Frontend hazir.
echo.

REM ------------------------------------------------------------
REM 7) Backend ve frontend'i ayri pencerelerde baslat, tarayiciyi ac
REM ------------------------------------------------------------
echo [7/7] Sunucular baslatiliyor...
start "Yetkin360 - Backend 8000" /d "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Yetkin360 - Frontend 3000" /d "%~dp0frontend" cmd /k "npm run dev"

echo   Frontend'in ayaga kalkmasi bekleniyor, en fazla 90 saniye...
set /a FRONT_TRIES=0

:frontend_wait
netstat -aon | findstr /r /c:":3000 .*LISTENING" >nul
if not errorlevel 1 goto frontend_ok
set /a FRONT_TRIES+=1
if %FRONT_TRIES% geq 45 (
    echo   UYARI: Frontend 90 saniyede ayaga kalkmadi. Frontend penceresini kontrol et.
    goto frontend_ok
)
timeout /t 2 /nobreak >nul
goto frontend_wait

:frontend_ok
echo   Tarayici aciliyor: http://localhost:3000
echo   Ilk acilista sayfanin derlenmesi 15-20 saniye surebilir.
start "" "http://localhost:3000"

echo.
echo ============================================================
echo   Yetkin360 baslatildi.
echo   Frontend : http://localhost:3000
echo   Backend  : http://localhost:8000/docs  - FastAPI Swagger
echo   MinIO    : http://localhost:9001       - konsol
echo.
echo   Seed giris bilgileri - backend/scripts/seed.py, sabit test sifresi:
echo     Ogrenci      : ogrenci1@seed.local .. ogrenci20@seed.local
echo     Kurum admin  : kurum1-admin@seed.local .. kurum5-admin@seed.local
echo     Organizasyon : org1-admin@seed.local .. org5-admin@seed.local
echo     Sifre, hepsi : SeedTest123!
echo     Platform admin: admin@yetkin360.local - sifre .env icindeki SEED_ADMIN_PASSWORD
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
set "PROC_NAME=bilinmiyor"
for /f "tokens=5" %%A in ('netstat -aon ^| findstr /r /c:":%PORT% .*LISTENING"') do set "FOUND_PID=%%A"
if not defined FOUND_PID (
    echo   Port %PORT% bos.
    exit /b 0
)
for /f "tokens=1 delims=," %%N in ('tasklist /fi "PID eq %FOUND_PID%" /fo csv /nh 2^>nul') do set "PROC_NAME=%%~N"
REM Docker Desktop publishes container ports through these processes: our own containers.
if /i "%PROC_NAME%"=="wslrelay.exe" goto port_docker
if /i "%PROC_NAME%"=="com.docker.backend.exe" goto port_docker
if /i "%PROC_NAME%"=="vpnkit.exe" goto port_docker
echo   UYARI: Port %PORT% dolu - PID %FOUND_PID%, surec: %PROC_NAME%
choice /c EH /n /m "    Bu sureci sonlandirmak icin E, atlamak icin H tusuna bas: "
if errorlevel 2 (
    echo     Atlandi - port %PORT% dolu kalabilir, sonraki adim basarisiz olabilir.
    exit /b 0
)
taskkill /f /pid %FOUND_PID% >nul 2>&1
echo     PID %FOUND_PID% sonlandirildi, port %PORT% bosaltildi.
exit /b 0

:port_docker
echo   Port %PORT% Docker tarafindan kullaniliyor - %PROC_NAME%, container zaten ayakta olabilir.
exit /b 0
