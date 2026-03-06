param(
    [int]$VideoLimit = 30,
    [int]$CommentPages = 2,
    [int]$PageSize = 20,
    [double]$Sleep = 0.2,
    [int]$Port = 8501,
    [switch]$SkipPipeline
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$StreamlitExe = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Python executable not found: $PythonExe" -ForegroundColor Red
    Write-Host "Create venv first: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $StreamlitExe)) {
    Write-Host "Streamlit executable not found: $StreamlitExe" -ForegroundColor Red
    Write-Host "Install deps: .venv\Scripts\python.exe -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

if (-not $SkipPipeline) {
    Write-Host "[1/2] Running pipeline (Bilibili hot topics + sentiment analysis)..." -ForegroundColor Cyan

    & $PythonExe -m src.pipeline --mode bilibili --video-limit $VideoLimit --comment-pages $CommentPages --page-size $PageSize --sleep $Sleep

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Pipeline failed. Startup aborted." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
else {
    Write-Host "[1/2] Pipeline skipped. Using existing data." -ForegroundColor Yellow
}

Write-Host "[2/2] Starting dashboard..." -ForegroundColor Cyan
Write-Host "Open in browser: http://localhost:$Port" -ForegroundColor Green

& $StreamlitExe run app/dashboard.py --server.port $Port
