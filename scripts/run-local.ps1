# Run System Locally (Hybrid Mode)
# Runs Vault in Docker, but ML/Dashboard in local Python

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Starting Hybrid System (Local ML)      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Start Infrastructure (Vault + Mongo)
Write-Host "`n[1/4] Starting Vault & Database (Docker)..." -ForegroundColor Yellow
cd central
docker compose up -d vault mongodb
cd ..

# 2. Install Dependencies
Write-Host "`n[2/4] Installing Python Requirements..." -ForegroundColor Yellow
pip install -r ml_worker/requirements.txt
pip install -r dashboard/requirements.txt

# 3. Set Environment Variables
# Point to the local path where Docker volume is mounted
$Env:RECORDINGS_DIR = "$PSScriptRoot\..\central\data\vault\recordings"
$Env:DB_PATH = "$PSScriptRoot\..\central\data\analytics.db"
$Env:CONFIG_DIR = "$PSScriptRoot\..\config"

# Create data dir if missing
New-Item -ItemType Directory -Force -Path "central/data" | Out-Null

Write-Host "`n[3/4] Starting Dashboard (Browser)..." -ForegroundColor Yellow
# Start Streamlit in background
Start-Process streamlit -ArgumentList "run dashboard/app.py" 

Write-Host "`n[4/4] Starting ML Worker (Console)..." -ForegroundColor Yellow
Write-Host "-> ML Worker is watching: $Env:RECORDINGS_DIR" -ForegroundColor Gray
Write-Host "-> Press Ctrl+C to stop" -ForegroundColor Gray

# Run ML Worker directly in this console
python ml_worker/consumer.py
