#Requires -Version 5.1
<#
.SYNOPSIS
    Yetkin360 local development launcher (called by baslat.bat).

.DESCRIPTION
    Prepares the local environment and runs backend API, outbox worker and
    frontend in ONE console window with prefixed, coloured log lines.
    Every service's output is also written to .logs\<service>.log.

    Steps are idempotent and cached: dependencies are only reinstalled when
    requirements.txt / package-lock.json change.

    Keys while running:  [B] open browser   [H] show summary   [Q] / Ctrl+C stop

.PARAMETER NoBrowser
    Do not open the browser when the frontend is ready.
#>
param(
    [switch]$NoBrowser
)

# Native tools (docker, alembic, npm) write progress to stderr; "Stop" would turn
# that into terminating errors under Windows PowerShell 5.1. Exit codes are checked
# explicitly instead.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$Root      = Split-Path -Parent $PSScriptRoot
$Backend   = Join-Path $Root 'backend'
$Frontend  = Join-Path $Root 'frontend'
$Py        = Join-Path $Backend '.venv\Scripts\python.exe'
$LogDir    = Join-Path $Root '.logs'
$AppUrl    = 'http://localhost:3000'
$ApiHealth = 'http://127.0.0.1:8000/health'
$TotalSteps = 5

$script:Step     = 0
$script:Services = @()
$esc = [char]27
$bel = [char]7
# CSI colour codes and OSC sequences (e.g. window-title escapes).
$script:Ansi = [regex]("$esc\[[0-9;?]*[A-Za-z]|$esc\][^$bel$esc]*(?:$bel|$esc\\)")

# ------------------------------------------------------------------ output helpers

function Write-Banner {
    Write-Host ''
    Write-Host '  Yetkin360' -NoNewline -ForegroundColor White
    Write-Host '  ·  yerel geliştirme ortamı' -ForegroundColor DarkGray
    Write-Host ('  ' + ('─' * 52)) -ForegroundColor DarkGray
}

function Write-Step([string]$Title) {
    $script:Step++
    Write-Host ''
    Write-Host ('  {0}/{1}  ' -f $script:Step, $TotalSteps) -NoNewline -ForegroundColor DarkGray
    Write-Host $Title -ForegroundColor White
}

function Write-Ok([string]$Message) {
    Write-Host '        ✓ ' -NoNewline -ForegroundColor Green
    Write-Host $Message
}

function Write-Note([string]$Message) {
    Write-Host "          $Message" -ForegroundColor DarkGray
}

function Write-Warn([string]$Message) {
    Write-Host '        ! ' -NoNewline -ForegroundColor Yellow
    Write-Host $Message -ForegroundColor Yellow
}

function Stop-WithError([string]$Message, [string[]]$Detail) {
    Write-Host '        ✗ ' -NoNewline -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    if ($Detail) {
        $Detail | Select-Object -Last 25 | ForEach-Object { Write-Host "          $_" -ForegroundColor DarkGray }
    }
    Write-Host ''
    exit 1
}

# Runs a native command, captures stdout+stderr, returns exit code and lines.
function Invoke-Captured([string]$File, [string[]]$Arguments, [string]$WorkDir = $Root) {
    Push-Location $WorkDir
    try {
        $lines = & $File @Arguments 2>&1 | ForEach-Object { "$_" }
        return [pscustomobject]@{ Code = $LASTEXITCODE; Output = @($lines) }
    } finally {
        Pop-Location
    }
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

# ------------------------------------------------------------------ child processes

function Start-DevProcess {
    param(
        [string]$Name,
        [ConsoleColor]$Color,
        [string]$FileName,
        [string]$Arguments,
        [string]$WorkDir,
        [hashtable]$Environment = @{}
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $FileName
    $psi.Arguments              = $Arguments
    $psi.WorkingDirectory       = $WorkDir
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    # Children must not read the launcher's key presses.
    $psi.RedirectStandardInput  = $true
    $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
    $psi.StandardErrorEncoding  = [Text.Encoding]::UTF8
    foreach ($key in $Environment.Keys) { $psi.EnvironmentVariables[$key] = $Environment[$key] }

    $proc = [System.Diagnostics.Process]::Start($psi)
    $log  = New-Object System.IO.StreamWriter((Join-Path $LogDir "$Name.log"), $false, (New-Object System.Text.UTF8Encoding $false))
    $log.AutoFlush = $true

    $svc = [pscustomobject]@{
        Name     = $Name
        Color    = $Color
        Proc     = $proc
        Log      = $log
        Reported = $false
        Readers  = @(
            [pscustomobject]@{ Reader = $proc.StandardOutput; Task = $proc.StandardOutput.ReadLineAsync() },
            [pscustomobject]@{ Reader = $proc.StandardError;  Task = $proc.StandardError.ReadLineAsync() }
        )
    }
    $script:Services += $svc
    return $svc
}

function Write-ServiceLine($Svc, [string]$Line) {
    $clean = $script:Ansi.Replace($Line, '')
    $stamp = Get-Date -Format 'HH:mm:ss'
    $Svc.Log.WriteLine("$stamp $clean")
    if ([string]::IsNullOrWhiteSpace($clean)) { return }

    $color = 'Gray'
    if ($clean -match '(?i)\b(error|exception|traceback|failed)\b|^\s+File "') { $color = 'Red' }
    elseif ($clean -match '(?i)\bwarn(ing)?\b') { $color = 'Yellow' }

    Write-Host "$stamp " -NoNewline -ForegroundColor DarkGray
    Write-Host $Svc.Name.PadRight(7) -NoNewline -ForegroundColor $Svc.Color
    Write-Host '│ ' -NoNewline -ForegroundColor DarkGray
    Write-Host $clean -ForegroundColor $color
}

# Non-blocking: prints every line the children produced since the last call.
function Receive-ServiceOutput {
    foreach ($svc in $script:Services) {
        foreach ($r in $svc.Readers) {
            $budget = 500
            while ($null -ne $r.Task -and $r.Task.IsCompleted -and $budget -gt 0) {
                $budget--
                $line = $null
                if (-not $r.Task.IsFaulted) { $line = $r.Task.Result }
                if ($null -eq $line) { $r.Task = $null; break }
                Write-ServiceLine $svc $line
                $r.Task = $r.Reader.ReadLineAsync()
            }
        }
        if (-not $svc.Reported -and $svc.Proc.HasExited) {
            $svc.Reported = $true
            Write-Host ''
            Write-Host "  ✗ $($svc.Name) durdu (çıkış kodu $($svc.Proc.ExitCode)). Ayrıntı: .logs\$($svc.Name).log" -ForegroundColor Red
            Write-Host ''
        }
    }
}

function Stop-DevProcesses {
    foreach ($svc in $script:Services) {
        if (-not $svc.Proc.HasExited) {
            # /T: uvicorn --reload and npm spawn child processes of their own.
            & taskkill.exe /T /F /PID $svc.Proc.Id 2>&1 | Out-Null
        }
        $svc.Log.Dispose()
    }
}

function Test-QuitKey {
    try {
        # Child processes (cmd.exe in particular) reset the shared console mode, which
        # turns Ctrl+C back into a signal: cmd then asks "Terminate batch job (Y/N)?".
        if (-not [Console]::TreatControlCAsInput) { [Console]::TreatControlCAsInput = $true }
        # next-server writes its own name into the console title.
        if ($Host.UI.RawUI.WindowTitle -ne 'Yetkin360') { $Host.UI.RawUI.WindowTitle = 'Yetkin360' }
        while ([Console]::KeyAvailable) {
            $k = [Console]::ReadKey($true)
            $ctrlC = ($k.Key -eq 'C') -and (($k.Modifiers -band [ConsoleModifiers]::Control) -ne 0)
            if ($ctrlC -or $k.Key -eq 'Q') { return 'quit' }
            if ($k.Key -eq 'B') { Start-Process $AppUrl }
            if ($k.Key -eq 'H') { Show-Summary }
        }
    } catch {
        # No interactive console (e.g. output redirected): keys are unavailable.
    }
    return $null
}

# Polls a URL without blocking log output. Returns $true once it answers 2xx/3xx.
function Wait-Http([string]$Url, [int]$TimeoutSec, $Svc) {
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $task = $null
    while ($watch.Elapsed.TotalSeconds -lt $TimeoutSec) {
        Receive-ServiceOutput
        if ((Test-QuitKey) -eq 'quit') { throw 'user-quit' }
        if ($Svc.Proc.HasExited) { return $false }
        if ($null -eq $task) {
            $client = New-Object System.Net.WebClient
            $client.Proxy = $null
            $task = $client.DownloadStringTaskAsync($Url)
        }
        if ($task.IsCompleted) {
            if (-not $task.IsFaulted) { return $true }
            $task = $null
            Start-Sleep -Milliseconds 600
        }
        Start-Sleep -Milliseconds 100
    }
    return $false
}

# ------------------------------------------------------------------ ports

$DockerProcessNames = @('wslrelay', 'com.docker.backend', 'com.docker.proxy', 'vpnkit', 'docker-proxy')

function Get-PortOwner([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $null }
    $owningPid = [int]$conn.OwningProcess
    $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
    if ($proc) { return [pscustomobject]@{ Pids = @($owningPid); Name = $proc.ProcessName } }

    # uvicorn --reload on Windows: the socket outlives the reloader that opened it and
    # stays reported under the dead PID; the worker children still hold it.
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$owningPid" -ErrorAction SilentlyContinue)
    if ($children.Count -gt 0) {
        return [pscustomobject]@{ Pids = @($children | ForEach-Object { [int]$_.ProcessId }); Name = $children[0].Name }
    }
    return [pscustomobject]@{ Pids = @($owningPid); Name = 'bilinmiyor' }
}

# Ports our containers publish: a non-Docker owner means compose will fail.
function Assert-ContainerPort([int]$Port, [string]$Label) {
    $owner = Get-PortOwner $Port
    if ($null -eq $owner -or $DockerProcessNames -contains $owner.Name) { return }
    Stop-WithError "Port $Port ($Label) başka bir süreçte: $($owner.Name) (PID $($owner.Pids -join ', '))." @(
        'Yerel bir PostgreSQL/MinIO servisi çalışıyorsa durdur, sonra tekrar başlat.'
    )
}

# Ports our dev servers use: usually a leftover from a previous run.
function Clear-AppPort([int]$Port, [string]$Label) {
    $owner = Get-PortOwner $Port
    if ($null -eq $owner) { Write-Ok "$Port boş ($Label)"; return }
    Write-Warn "$Port dolu ($Label): $($owner.Name), PID $($owner.Pids -join ', '). Muhtemelen önceki çalıştırmadan kaldı."
    $answer = Read-Host '          Sonlandırılsın mı? [E/h]'
    if ($answer -eq '' -or $answer -match '^[eEyY]') {
        foreach ($procId in $owner.Pids) { & taskkill.exe /T /F /PID $procId 2>&1 | Out-Null }
        Start-Sleep -Milliseconds 800
        if ($null -ne (Get-PortOwner $Port)) { Stop-WithError "$Port boşaltılamadı. Süreci Görev Yöneticisi'nden kapat." }
        Write-Ok "$Port boşaltıldı"
    } else {
        Stop-WithError "$Port dolu olduğu için $Label başlatılamaz."
    }
}

# ------------------------------------------------------------------ steps

function Test-Prerequisites {
    Write-Step 'Ön koşullar'
    $missing = @()
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { $missing += 'Docker Desktop  https://www.docker.com/products/docker-desktop' }
    if (-not (Get-Command node -ErrorAction SilentlyContinue))   { $missing += 'Node.js 20+     https://nodejs.org' }
    if (-not (Test-Path $Py) -and -not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        $missing += 'Python 3.12     https://www.python.org/downloads'
    }
    if ($missing.Count -gt 0) { Stop-WithError 'Eksik araç var:' $missing }
    Write-Ok "Docker, Node $(& node --version), Python bulundu"

    if (-not (Test-Path (Join-Path $Root '.env'))) {
        Copy-Item (Join-Path $Root '.env.example') (Join-Path $Root '.env')
        Write-Warn '.env yoktu, .env.example kopyalandı. DEGISTIR_ ile başlayan değerleri doldur.'
    } else {
        Write-Ok '.env mevcut'
    }
}

function Start-Docker {
    Write-Step 'Docker ve veritabanı'
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        $exe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if (-not (Test-Path $exe)) { Stop-WithError 'Docker çalışmıyor ve Docker Desktop bulunamadı. Elle başlat.' }
        Write-Note 'Docker Desktop başlatılıyor (30-60 sn)...'
        Start-Process $exe
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        do {
            Start-Sleep -Seconds 2
            & docker info *> $null
        } while ($LASTEXITCODE -ne 0 -and $watch.Elapsed.TotalSeconds -lt 120)
        if ($LASTEXITCODE -ne 0) { Stop-WithError 'Docker 2 dakikada ayağa kalkmadı.' }
    }
    Write-Ok 'Docker çalışıyor'

    Assert-ContainerPort 5432 'PostgreSQL'
    Assert-ContainerPort 9000 'MinIO'
    Assert-ContainerPort 9001 'MinIO konsol'

    # --wait blocks until the healthchecks in docker-compose.yml pass.
    $up = Invoke-Captured 'docker' @('compose', 'up', '-d', '--wait', '--wait-timeout', '120')
    if ($up.Code -ne 0) { Stop-WithError 'docker compose up başarısız.' $up.Output }
    Write-Ok 'PostgreSQL ve MinIO hazır (healthcheck geçti)'
}

function Initialize-Backend {
    Write-Step 'Backend'

    if (-not (Test-Path $Py)) {
        Write-Note 'Sanal ortam oluşturuluyor...'
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-Captured 'py' @('-3.12', '-m', 'venv', '.venv') $Backend | Out-Null
        }
        if (-not (Test-Path $Py)) { Invoke-Captured 'python' @('-m', 'venv', '.venv') $Backend | Out-Null }
        if (-not (Test-Path $Py)) { Stop-WithError '.venv oluşturulamadı. Python 3.12 kurulu mu?' }
    }

    # Compiled extensions built for another Python version look installed but fail on import.
    $health = Invoke-Captured $Py @('-c', 'import pydantic_core._pydantic_core, psycopg, cffi, pydantic_settings') $Backend
    $stampFile = Join-Path $Backend '.venv\.requirements.sha256'
    $reqHash = Get-Sha256 (Join-Path $Backend 'requirements.txt')
    $stamp = ''
    if (Test-Path $stampFile) { $stamp = (Get-Content $stampFile -Raw).Trim() }

    if ($health.Code -ne 0 -or $stamp -ne $reqHash) {
        $pipArgs = @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'requirements.txt')
        if ($health.Code -ne 0) {
            Write-Note 'Paketler eksik veya bozuk, yeniden kuruluyor...'
            $pipArgs += '--force-reinstall'
        } else {
            Write-Note 'requirements.txt değişmiş, paketler güncelleniyor...'
        }
        $pip = Invoke-Captured $Py $pipArgs $Backend
        if ($pip.Code -ne 0) { Stop-WithError 'pip install başarısız.' $pip.Output }
        Set-Content -Path $stampFile -Value $reqHash -Encoding ASCII
        Write-Ok 'Python paketleri kuruldu'
    } else {
        Write-Ok 'Python paketleri güncel'
    }

    $mig = Invoke-Captured $Py @('-m', 'alembic', 'upgrade', 'head') $Backend
    if ($mig.Code -ne 0) { Stop-WithError 'Migration başarısız (alembic upgrade head).' $mig.Output }
    $applied = @($mig.Output | Where-Object { $_ -match 'Running upgrade \S+ -> \S+, (.+)$' } | ForEach-Object { $Matches[1] })
    if ($applied.Count -gt 0) {
        Write-Ok "$($applied.Count) migration uygulandı"
        $applied | ForEach-Object { Write-Note "→ $_" }
    } else {
        Write-Ok 'Veritabanı şeması güncel'
    }

    $seed = Invoke-Captured $Py @('-m', 'scripts.seed') $Backend
    if ($seed.Code -ne 0) {
        Write-Warn 'Seed başarısız, devam ediliyor:'
        $seed.Output | Select-Object -Last 8 | ForEach-Object { Write-Note $_ }
    } else {
        Write-Ok 'Seed verisi hazır'
    }

    $bucket = Invoke-Captured $Py @('-m', 'scripts.ensure_bucket') $Backend
    if ($bucket.Code -ne 0) {
        Write-Warn 'MinIO bucket hazırlanamadı, kanıt yükleme çalışmaz:'
        $bucket.Output | Select-Object -Last 5 | ForEach-Object { Write-Note $_ }
    } else {
        Write-Ok 'Dosya deposu (MinIO bucket) hazır'
    }
}

function Initialize-Frontend {
    Write-Step 'Frontend'
    $stampFile = Join-Path $Frontend 'node_modules\.yetkin360-lock.sha256'
    $lockHash = Get-Sha256 (Join-Path $Frontend 'package-lock.json')
    $stamp = ''
    if (Test-Path $stampFile) { $stamp = (Get-Content $stampFile -Raw).Trim() }

    if ($stamp -ne $lockHash) {
        Write-Note 'Paketler kuruluyor (npm install)...'
        $npm = Invoke-Captured 'npm.cmd' @('install', '--no-audit', '--no-fund', '--loglevel=error') $Frontend
        if ($npm.Code -ne 0) { Stop-WithError 'npm install başarısız.' $npm.Output }
        Set-Content -Path $stampFile -Value $lockHash -Encoding ASCII
        Write-Ok 'npm paketleri kuruldu'
    } else {
        Write-Ok 'npm paketleri güncel'
    }
}

function Show-Summary {
    $line = '  ' + ('─' * 52)
    Write-Host ''
    Write-Host $line -ForegroundColor DarkGray
    Write-Host '  Uygulama    ' -NoNewline -ForegroundColor DarkGray; Write-Host $AppUrl -ForegroundColor White
    Write-Host '  API         ' -NoNewline -ForegroundColor DarkGray; Write-Host 'http://localhost:8000/docs'
    Write-Host '  MinIO       ' -NoNewline -ForegroundColor DarkGray; Write-Host 'http://localhost:9001'
    Write-Host ''
    Write-Host '  Seed hesapları  (şifre: SeedTest123!)' -ForegroundColor DarkGray
    Write-Host '    Öğrenci          ogrenci1..20@seed.local'
    Write-Host '    Keşfet dizini    dizin1..32@seed.local'
    Write-Host '    Kuruluş admini   org1..5-admin@seed.local'
    Write-Host '    Kurum admini     kurum1..5-admin@seed.local'
    Write-Host '    Koordinatör      kurum1..5-koordinator@seed.local'
    Write-Host '    Platform admini  admin@yetkin360.local  ' -NoNewline
    Write-Host '(şifre: .env → SEED_ADMIN_PASSWORD)' -ForegroundColor DarkGray
    Write-Host ''
    Write-Host '  Loglar      ' -NoNewline -ForegroundColor DarkGray; Write-Host '.logs\api.log  .logs\worker.log  .logs\web.log'
    Write-Host '              ' -NoNewline; Write-Host 'Destek kodunu (request_id) api.log içinde ara.' -ForegroundColor DarkGray
    Write-Host '  Kısayollar  ' -NoNewline -ForegroundColor DarkGray
    Write-Host '[B] tarayıcı   [H] bu özet   [Q] / Ctrl+C durdur'
    Write-Host $line -ForegroundColor DarkGray
    Write-Host ''
}

function Start-Services {
    Write-Step 'Sunucular'
    Clear-AppPort 8000 'API'
    Clear-AppPort 3000 'frontend'

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $pyEnv = @{ PYTHONUNBUFFERED = '1'; PYTHONIOENCODING = 'utf-8' }

    # From here on Ctrl+C is read as a key so the launcher can stop children cleanly.
    try { [Console]::TreatControlCAsInput = $true } catch { }

    $api = Start-DevProcess -Name 'api' -Color Cyan -FileName $Py `
        -Arguments '-m uvicorn app.main:app --reload --port 8000' -WorkDir $Backend -Environment $pyEnv
    Start-DevProcess -Name 'worker' -Color DarkYellow -FileName $Py `
        -Arguments '-m app.workers.outbox_worker' -WorkDir $Backend -Environment $pyEnv | Out-Null
    # Run next directly with node when package.json's dev script is plain "next ...":
    # no cmd.exe / npm.cmd layer that resets console mode or prompts on Ctrl+C.
    $webEnv = @{ NO_COLOR = '1' }
    $nextBin = Join-Path $Frontend 'node_modules\next\dist\bin\next'
    $devScript = (Get-Content (Join-Path $Frontend 'package.json') -Raw -Encoding UTF8 | ConvertFrom-Json).scripts.dev
    if ((Test-Path $nextBin) -and $devScript -match '^next(\s+.*)?$') {
        $web = Start-DevProcess -Name 'web' -Color Green -FileName 'node' `
            -Arguments ('"{0}"{1}' -f $nextBin, $Matches[1]) -WorkDir $Frontend -Environment $webEnv
    } else {
        $web = Start-DevProcess -Name 'web' -Color Green -FileName 'cmd.exe' `
            -Arguments '/d /c npm run dev' -WorkDir $Frontend -Environment $webEnv
    }

    if (Wait-Http $ApiHealth 60 $api) { Write-Ok 'API hazır' }
    else { Write-Warn 'API 60 sn içinde yanıt vermedi; yukarıdaki api loglarına bak.' }

    # Requesting "/" makes Next compile the landing page before the browser opens.
    Write-Note 'Frontend derleniyor (ilk açılışta 20-40 sn)...'
    if (Wait-Http $AppUrl 180 $web) { Write-Ok 'Frontend hazır' }
    else { Write-Warn 'Frontend 3 dakikada yanıt vermedi; yukarıdaki web loglarına bak.' }
}

# ------------------------------------------------------------------ main

function Invoke-Main {
    $Host.UI.RawUI.WindowTitle = 'Yetkin360'
    $started = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Banner
    try {
        Test-Prerequisites
        Start-Docker
        Initialize-Backend
        Initialize-Frontend
        Start-Services

        Write-Host ''
        Write-Host ('  Hazır · {0:N0} sn' -f $started.Elapsed.TotalSeconds) -ForegroundColor Green
        Show-Summary
        if (-not $NoBrowser) { Start-Process $AppUrl }

        while ($true) {
            Receive-ServiceOutput
            if ((Test-QuitKey) -eq 'quit') { break }
            $alive = @($script:Services | Where-Object { -not $_.Proc.HasExited })
            if ($alive.Count -eq 0) { Write-Warn 'Tüm servisler durdu.'; break }
            Start-Sleep -Milliseconds 80
        }
    } catch {
        if ("$_" -ne 'user-quit') { Write-Host "  Beklenmeyen hata: $_" -ForegroundColor Red }
    } finally {
        if ($script:Services.Count -gt 0) {
            Write-Host ''
            Write-Host '  Servisler durduruluyor...' -ForegroundColor DarkGray
            Stop-DevProcesses
            Write-Host '  Durduruldu. PostgreSQL ve MinIO açık kalır (durdurmak için: docker compose stop).' -ForegroundColor DarkGray
        }
        try { [Console]::TreatControlCAsInput = $false } catch { }
    }
}

# Dot-sourcing (". .\scripts\baslat.ps1") loads the functions without starting anything.
if ($MyInvocation.InvocationName -ne '.') { Invoke-Main }
