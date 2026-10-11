#!/usr/bin/env bash
# Yetkin360 local launcher for macOS and Linux (the Windows twin is baslat.ps1).
#
# Prepares the environment and runs backend API, outbox worker and frontend in
# ONE terminal with prefixed, coloured log lines. Each service also logs to
# .logs/<service>.log. Steps are idempotent; dependencies are reinstalled only
# when requirements.txt / package-lock.json change.
#
# Keys while running:  [B] browser   [H] summary   [Q] / Ctrl+C stop
# Options:             --no-browser
#
# Written for bash 3.2 (the macOS default): no associative arrays, no mapfile.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV_PY="$BACKEND/.venv/bin/python"
LOG_DIR="$ROOT/.logs"
APP_URL="http://localhost:3000"
API_HEALTH="http://127.0.0.1:8000/health"
TOTAL_STEPS=5
STEP=0
OPEN_BROWSER=1
PIDS=""
for arg in "$@"; do
    [ "$arg" = "--no-browser" ] && OPEN_BROWSER=0
done

if [ -t 1 ]; then
    C_RESET=$'\033[0m'; C_DIM=$'\033[90m'; C_BOLD=$'\033[1m'; C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_CYAN=$'\033[36m'; C_MAGENTA=$'\033[35m'
    C_ORANGE=$'\033[33m'
else
    C_RESET=""; C_DIM=""; C_BOLD=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_CYAN=""; C_MAGENTA=""; C_ORANGE=""
fi

# ------------------------------------------------------------------ output helpers

banner() {
    printf '\n  %sYetkin360%s  %s·  yerel geliştirme ortamı%s\n' "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
    printf '  %s────────────────────────────────────────────────────%s\n' "$C_DIM" "$C_RESET"
}
step()  { STEP=$((STEP + 1)); printf '\n  %s%s/%s%s  %s%s%s\n' "$C_DIM" "$STEP" "$TOTAL_STEPS" "$C_RESET" "$C_BOLD" "$1" "$C_RESET"; }
ok()    { printf '        %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
note()  { printf '          %s%s%s\n' "$C_DIM" "$1" "$C_RESET"; }
warn()  { printf '        %s! %s%s\n' "$C_YELLOW" "$1" "$C_RESET"; }
die() {
    printf '        %s✗ %s%s\n' "$C_RED" "$1" "$C_RESET"
    shift
    for line in "$@"; do note "$line"; done
    echo
    exit 1
}

# Runs a command quietly; on failure prints the last lines of its output.
run_quiet() {
    local label="$1"; shift
    local out
    if ! out="$("$@" 2>&1)"; then
        die "$label" "$(printf '%s\n' "$out" | tail -n 25)"
    fi
    LAST_OUTPUT="$out"
}

sha256() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    else sha256sum "$1" | cut -d' ' -f1; fi
}

open_url() {
    if command -v open >/dev/null 2>&1; then open "$1" >/dev/null 2>&1
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1
    fi
}

env_value() {
    [ -f "$ROOT/.env" ] || return 0
    grep -E "^[[:space:]]*$1[[:space:]]*=" "$ROOT/.env" | tail -n 1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

port_pids() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null; }

# ------------------------------------------------------------------ steps

find_python() {
    local cand
    for cand in python3.13 python3.12 python3 python; do
        if command -v "$cand" >/dev/null 2>&1 \
            && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
            echo "$cand"; return 0
        fi
    done
    return 1
}

check_prerequisites() {
    step 'Ön koşullar'
    local missing=()
    command -v docker >/dev/null 2>&1 || missing+=('Docker Desktop  https://www.docker.com/products/docker-desktop')
    command -v node   >/dev/null 2>&1 || missing+=('Node.js 20+     https://nodejs.org')
    command -v lsof   >/dev/null 2>&1 || missing+=('lsof            (Linux: sudo apt install lsof)')
    SYS_PY="$(find_python || true)"
    if [ ! -x "$VENV_PY" ] && [ -z "$SYS_PY" ]; then
        missing+=('Python 3.12+    https://www.python.org/downloads  (macOS: brew install python@3.12)')
    fi
    [ ${#missing[@]} -gt 0 ] && die 'Eksik araç var:' "${missing[@]}"

    local node_major
    node_major="$(node -p 'process.versions.node.split(".")[0]')"
    [ "$node_major" -ge 20 ] 2>/dev/null || die "Node.js 20+ gerekli (bulunan: $(node --version))." 'https://nodejs.org'
    ok "Docker, Node $(node --version), Python bulundu"

    # scripts/init_env.py: creates .env with random secrets, or repairs a missing
    # SEED_ADMIN_PASSWORD (without it the whole seed rolls back). Stdlib only.
    local py="$SYS_PY"
    [ -x "$VENV_PY" ] && py="$VENV_PY"
    run_quiet '.env hazırlanamadı.' "$py" "$ROOT/scripts/init_env.py"
    case "$(printf '%s\n' "$LAST_OUTPUT" | tail -n 1)" in
        created)            ok '.env oluşturuldu (rastgele parolalarla, elle düzenleme gerekmez)' ;;
        admin-password-set) ok '.env mevcut; platform yöneticisi şifresi eklendi' ;;
        *)                  ok '.env mevcut' ;;
    esac
}

assert_container_port() {
    local pids name
    pids="$(port_pids "$1")"
    [ -z "$pids" ] && return 0
    name="$(ps -p "$(echo "$pids" | head -n 1)" -o comm= 2>/dev/null | xargs basename 2>/dev/null)"
    case "$name" in
        *docker*|*Docker*|*vpnkit*|*com.docker*|*rootlessport*) return 0 ;;
    esac
    die "Port $1 ($2) başka bir süreçte: ${name:-bilinmiyor} (PID $(echo $pids))." \
        'Yerel bir PostgreSQL/MinIO servisi çalışıyorsa durdur (ör. brew services stop postgresql), sonra tekrar başlat.'
}

start_docker() {
    step 'Docker ve veritabanı'
    if ! docker info >/dev/null 2>&1; then
        if [ "$(uname)" = "Darwin" ] && open -a Docker >/dev/null 2>&1; then
            note 'Docker Desktop başlatılıyor (30-60 sn)...'
            local waited=0
            until docker info >/dev/null 2>&1; do
                sleep 2; waited=$((waited + 2))
                [ $waited -ge 120 ] && die 'Docker 2 dakikada ayağa kalkmadı.'
            done
        else
            die 'Docker çalışmıyor. Docker Desktop’ı (veya Linux’ta docker servisini) başlatıp tekrar dene.'
        fi
    fi
    ok 'Docker çalışıyor'

    assert_container_port 5432 'PostgreSQL'
    assert_container_port 9000 'MinIO'
    assert_container_port 9001 'MinIO konsol'

    # --wait blocks until the healthchecks in docker-compose.yml pass.
    (cd "$ROOT" && run_quiet 'docker compose up başarısız.' docker compose up -d --wait --wait-timeout 120) || exit 1
    ok 'PostgreSQL ve MinIO hazır (healthcheck geçti)'
}

init_backend() {
    step 'Backend'
    cd "$BACKEND" || exit 1

    if [ ! -x "$VENV_PY" ]; then
        note 'Sanal ortam oluşturuluyor...'
        run_quiet '.venv oluşturulamadı.' "$SYS_PY" -m venv .venv
    fi
    "$VENV_PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' \
        || die 'backend/.venv Python 3.12 veya üstü değil.' 'backend/.venv klasörünü silip tekrar başlat.'

    local stamp_file="$BACKEND/.venv/.requirements.sha256" req_hash stamp="" healthy=1
    req_hash="$(sha256 requirements.txt)"
    [ -f "$stamp_file" ] && stamp="$(cat "$stamp_file")"
    "$VENV_PY" -c 'import pydantic_core._pydantic_core, psycopg, cffi, pydantic_settings' >/dev/null 2>&1 || healthy=0

    if [ $healthy -eq 0 ] || [ "$stamp" != "$req_hash" ]; then
        note 'Python paketleri kuruluyor (ilk açılışta 1-2 dk)...'
        run_quiet 'pip install başarısız.' "$VENV_PY" -m pip install --disable-pip-version-check -q -r requirements.txt
        echo "$req_hash" > "$stamp_file"
        ok 'Python paketleri kuruldu'
    else
        ok 'Python paketleri güncel'
    fi

    run_quiet 'Migration başarısız (alembic upgrade head).' "$VENV_PY" -m alembic upgrade head
    local applied
    applied="$(printf '%s\n' "$LAST_OUTPUT" | grep -c 'Running upgrade' || true)"
    if [ "$applied" -gt 0 ]; then ok "$applied migration uygulandı"; else ok 'Veritabanı şeması güncel'; fi

    if out="$("$VENV_PY" -m scripts.seed 2>&1)"; then
        ok 'Demo verisi hazır'
    else
        warn 'Seed başarısız, devam ediliyor:'
        printf '%s\n' "$out" | tail -n 8 | while IFS= read -r l; do note "$l"; done
    fi

    if out="$("$VENV_PY" -m scripts.ensure_bucket 2>&1)"; then
        ok 'Dosya deposu (MinIO bucket) hazır'
    else
        warn 'MinIO bucket hazırlanamadı, kanıt yükleme çalışmaz:'
        printf '%s\n' "$out" | tail -n 5 | while IFS= read -r l; do note "$l"; done
    fi
    cd "$ROOT" || exit 1
}

init_frontend() {
    step 'Frontend'
    local stamp_file="$FRONTEND/node_modules/.yetkin360-lock.sha256" lock_hash stamp=""
    lock_hash="$(sha256 "$FRONTEND/package-lock.json")"
    [ -f "$stamp_file" ] && stamp="$(cat "$stamp_file")"
    if [ "$stamp" != "$lock_hash" ]; then
        note 'Paketler kuruluyor (npm install, ilk açılışta 1-3 dk)...'
        (cd "$FRONTEND" && run_quiet 'npm install başarısız.' npm install --no-audit --no-fund --loglevel=error) || exit 1
        echo "$lock_hash" > "$stamp_file"
        ok 'npm paketleri kuruldu'
    else
        ok 'npm paketleri güncel'
    fi
}

summary() {
    local line="  ${C_DIM}────────────────────────────────────────────────────${C_RESET}"
    local admin_pw admin_email
    admin_pw="$(env_value SEED_ADMIN_PASSWORD)"
    admin_email="$(env_value SEED_ADMIN_EMAIL)"
    [ -z "$admin_email" ] && admin_email='admin@yetkin360.test'  # backend/app/core/config.py default
    echo
    echo "$line"
    printf '  %sUygulama%s    %s%s%s\n' "$C_DIM" "$C_RESET" "$C_BOLD" "$APP_URL" "$C_RESET"
    printf '  %sAPI%s         http://localhost:8000/docs\n' "$C_DIM" "$C_RESET"
    printf '  %sMinIO%s       http://localhost:9001\n' "$C_DIM" "$C_RESET"
    echo
    printf '  %sHazır demo hesapları — yeni hesap açmanız gerekmez%s\n' "$C_BOLD" "$C_RESET"
    printf '  %sOrtak şifre:%s %sSeedTest123!%s\n' "$C_DIM" "$C_RESET" "$C_YELLOW" "$C_RESET"
    echo   '    Bireysel         ayse.yilmaz@posta.test'
    echo   '    Kuruluş admini   murat.demirci@yelkovanyazilim.test'
    echo   '    Onaylayıcı       mehmet.karaca@yelkovanyazilim.test'
    echo   '    Aday doğrulayan  seda.gurbuz@gundogusuenerji.test'
    echo   '    Kurum admini     nermin.basaran@cinaralti.edu.test'
    echo   '    Koordinatör      kerem.taskin@cinaralti.edu.test'
    printf '  %sPlatform yöneticisi%s  %s  %s%s%s\n' "$C_DIM" "$C_RESET" "$admin_email" "$C_YELLOW" "${admin_pw:-(.env → SEED_ADMIN_PASSWORD)}" "$C_RESET"
    printf '    %sGiriş:%s %s/admin/giris\n' "$C_DIM" "$C_RESET" "$APP_URL"
    echo
    printf '  %sYeni hesap açarsanız: e-posta gönderilmez; doğrulama bağlantısı%s\n' "$C_DIM" "$C_RESET"
    printf '  %saşağıda %s[EMAIL]%s%s satırında görünür — tarayıcıya yapıştırın.%s\n' "$C_DIM" "$C_MAGENTA" "$C_RESET" "$C_DIM" "$C_RESET"
    echo
    printf '  %sLoglar%s      .logs/api.log  .logs/worker.log  .logs/web.log\n' "$C_DIM" "$C_RESET"
    printf '  %sKısayollar%s  [B] tarayıcı   [H] bu özet   [Q] / Ctrl+C durdur\n' "$C_DIM" "$C_RESET"
    echo "$line"
    echo
}

# ------------------------------------------------------------------ services

# Prefixes every line, colours errors / [EMAIL] lines, and mirrors to .logs/<name>.log.
prefix_output() {
    local name="$1" color="$2"
    # The log path goes through ENVIRON: awk -v would interpret backslashes in it.
    PREFIX_LOG="$LOG_DIR/$name.log" awk -v name="$name" -v color="$color" -v dim="$C_DIM" -v reset="$C_RESET" \
        -v red="$C_RED" -v yellow="$C_YELLOW" -v magenta="$C_MAGENTA" '
        BEGIN { logf = ENVIRON["PREFIX_LOG"] }
        {
            gsub(/\033\[[0-9;?]*[A-Za-z]/, "")
            cmd = "date +%H:%M:%S"; cmd | getline stamp; close(cmd)
            print stamp " " $0 >> logf; fflush(logf)
            if ($0 ~ /^[ \t]*$/) next
            c = ""
            if ($0 ~ /\[EMAIL\]/) c = magenta
            else if (tolower($0) ~ /(error|exception|traceback|failed)/) c = red
            else if (tolower($0) ~ /warn/) c = yellow
            printf "%s%s%s %s%-7s%s%s│%s %s%s%s\n", dim, stamp, reset, color, name, reset, dim, reset, c, $0, reset
            fflush()
        }'
}

start_service() {
    local name="$1" color="$2" dir="$3"; shift 3
    : > "$LOG_DIR/$name.log"
    ( cd "$dir" && exec "$@" ) < /dev/null > >(prefix_output "$name" "$color") 2>&1 &
    PIDS="$PIDS $!"
}

kill_tree() {
    local child
    for child in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$child"; done
    kill "$1" 2>/dev/null
}

stop_services() {
    [ -z "$PIDS" ] && return
    echo
    note 'Servisler durduruluyor...'
    local pid
    for pid in $PIDS; do kill_tree "$pid"; done
    sleep 1
    for pid in $PIDS; do kill -9 "$pid" 2>/dev/null; done
    PIDS=""
    note 'Durduruldu. PostgreSQL ve MinIO açık kalır (durdurmak için: docker compose stop).'
    stty sane 2>/dev/null
}

clear_app_port() {
    local pids answer
    pids="$(port_pids "$1")"
    if [ -z "$pids" ]; then ok "$1 boş ($2)"; return; fi
    warn "$1 dolu ($2): PID $(echo $pids). Muhtemelen önceki çalıştırmadan kaldı."
    printf '          Sonlandırılsın mı? [E/h] '
    read -r answer
    case "$answer" in
        ''|[eEyY]*)
            for pid in $pids; do kill_tree "$pid"; done
            sleep 1
            [ -n "$(port_pids "$1")" ] && die "$1 boşaltılamadı."
            ok "$1 boşaltıldı" ;;
        *) die "$1 dolu olduğu için $2 başlatılamaz." ;;
    esac
}

wait_http() {
    local url="$1" timeout="$2" waited=0
    while [ $waited -lt "$timeout" ]; do
        curl -fs -o /dev/null --max-time 5 "$url" && return 0
        sleep 1; waited=$((waited + 1))
    done
    return 1
}

start_services() {
    step 'Sunucular'
    clear_app_port 8000 'API'
    clear_app_port 3000 'frontend'
    mkdir -p "$LOG_DIR"
    export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

    start_service api    "$C_CYAN"   "$BACKEND"  "$VENV_PY" -m uvicorn app.main:app --reload --port 8000
    start_service worker "$C_ORANGE" "$BACKEND"  "$VENV_PY" -m app.workers.outbox_worker
    NO_COLOR=1 start_service web "$C_GREEN" "$FRONTEND" npm run dev

    if wait_http "$API_HEALTH" 60; then ok 'API hazır'
    else warn 'API 60 sn içinde yanıt vermedi; yukarıdaki api loglarına bak.'; fi
    note 'Frontend derleniyor (ilk açılışta 20-40 sn)...'
    # Requesting "/" makes Next compile the landing page before the browser opens.
    if wait_http "$APP_URL" 180; then ok 'Frontend hazır'
    else warn 'Frontend 3 dakikada yanıt vermedi; yukarıdaki web loglarına bak.'; fi
}

# ------------------------------------------------------------------ main

main() {
    local started=$SECONDS key
    printf '\033]0;Yetkin360\007'
    banner
    check_prerequisites
    start_docker
    init_backend
    init_frontend
    trap 'stop_services; exit 0' INT TERM
    trap 'stop_services' EXIT
    start_services

    printf '\n  %sHazır · %s sn%s\n' "$C_GREEN" "$((SECONDS - started))" "$C_RESET"
    summary
    [ $OPEN_BROWSER -eq 1 ] && open_url "$APP_URL"

    while true; do
        if [ -t 0 ] && read -rsn1 -t 1 key; then
            case "$key" in
                b|B) open_url "$APP_URL" ;;
                h|H) summary ;;
                q|Q) break ;;
            esac
        else
            [ -t 0 ] || sleep 1
        fi
        local alive=0 pid
        for pid in $PIDS; do kill -0 "$pid" 2>/dev/null && alive=1; done
        if [ $alive -eq 0 ]; then warn 'Tüm servisler durdu.'; break; fi
    done
}

main
