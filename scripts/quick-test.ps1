# ============================================
# Quick Test - Central Server ML Pipeline
# ============================================
# Tests the ML processing using a sample video file.
# Uses Development mode (MongoDB + SQLite + local Python).
# ============================================

param(
    [string]$VideoFile = "..\NA - HD CCTV Camera video 3MP 4MP iProx CCTV HDCCTVCameras.net retail store.mp4"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Quick Test - ML Pipeline               " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Video File: $VideoFile" -ForegroundColor Gray
Write-Host ""

# ============================================
# Step 1: Create Data Directories
# ============================================
Write-Host "[1/7] Creating data directories..." -ForegroundColor Yellow

$DataDir = Join-Path $ProjectRoot "data"
$RecordingsDir = Join-Path $DataDir "recordings\test-cam\$(Get-Date -Format 'yyyy-MM-dd')"
$ProcessedDir = Join-Path $DataDir "processed"
$HeatmapsDir = Join-Path $DataDir "heatmaps"

New-Item -ItemType Directory -Force -Path $RecordingsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ProcessedDir | Out-Null
New-Item -ItemType Directory -Force -Path $HeatmapsDir | Out-Null

Write-Host "  -> Created: $RecordingsDir" -ForegroundColor Gray

# ============================================
# Step 2: Copy Test Video to Recordings
# ============================================
Write-Host "[2/7] Copying test video to recordings..." -ForegroundColor Yellow

# Try to find the video file
$SourceVideo = $null

# Try relative path from project root
$VideoNames = @(
    "NA - HD CCTV Camera video 3MP 4MP iProx CCTV HDCCTVCameras.net retail store.mp4"
)

foreach ($vidName in $VideoNames) {
    $testPath = Join-Path $ProjectRoot $vidName
    if (Test-Path $testPath) {
        $SourceVideo = $testPath
        break
    }
}

# Try if VideoFile param is absolute path
if (-not $SourceVideo -and (Test-Path $VideoFile)) {
    $SourceVideo = $VideoFile
}

if (-not $SourceVideo) {
    Write-Host "ERROR: Video file not found!" -ForegroundColor Red
    Write-Host "Looked for: $VideoFile" -ForegroundColor Gray
    Write-Host "In: $ProjectRoot" -ForegroundColor Gray
    exit 1
}

$DestVideo = Join-Path $RecordingsDir "test_$(Get-Date -Format 'HHmmss').mp4"
Copy-Item $SourceVideo -Destination $DestVideo -Force
Write-Host "  -> Copied to: $DestVideo" -ForegroundColor Gray

# ============================================
# Step 3: Start MongoDB (Docker)
# ============================================
Write-Host "[3/7] Starting MongoDB (Docker)..." -ForegroundColor Yellow

Push-Location $ProjectRoot
try {
    # Temporarily allow errors during docker check
    $ErrorActionPreference = "Continue"
    $mongoRunning = docker ps --filter "name=kerberos-mongodb" --format "{{.Names}}" 2>&1
    $ErrorActionPreference = "Stop"
    
    if ($mongoRunning -like "*kerberos-mongodb*") {
        Write-Host "  -> MongoDB already running" -ForegroundColor Gray
    } else {
        docker compose up -d mongodb 2>&1
        Write-Host "  -> MongoDB started" -ForegroundColor Gray
        Start-Sleep -Seconds 3  # Wait for MongoDB to be ready
    }
} catch {
    Write-Host "  -> Docker warning (continuing): $_" -ForegroundColor Yellow
    try {
        docker compose up -d mongodb 2>&1
        Write-Host "  -> MongoDB started" -ForegroundColor Gray
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "  -> Could not start MongoDB, continuing anyway" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

# ============================================
# Step 4: Set Environment Variables
# ============================================
Write-Host "[4/7] Setting environment variables..." -ForegroundColor Yellow

$env:RECORDINGS_DIR = Join-Path $DataDir "recordings"
$env:PROCESSED_DIR = $ProcessedDir
$env:DB_PATH = Join-Path $DataDir "analytics.db"
$env:CONFIG_DIR = Join-Path $ProjectRoot "config"
$env:HEATMAP_OUTPUT_DIR = $HeatmapsDir

Write-Host "  -> RECORDINGS_DIR: $env:RECORDINGS_DIR" -ForegroundColor Gray
Write-Host "  -> DB_PATH: $env:DB_PATH" -ForegroundColor Gray
Write-Host "  -> CONFIG_DIR: $env:CONFIG_DIR" -ForegroundColor Gray

# ============================================
# Step 5: Build ML Worker Image
# ============================================
Write-Host "[5/7] Building ML Worker Docker Image..." -ForegroundColor Yellow

Push-Location $ProjectRoot
try {
    docker build -t ml-worker:test ./ml_worker 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  -> Image built: ml-worker:test" -ForegroundColor Gray
} finally {
    Pop-Location
}

# ============================================
# Step 6: Run ML Worker Container
# ============================================
Write-Host "[6/7] Running ML Worker Container..." -ForegroundColor Yellow
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   ML Worker Processing (Docker)         " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop after processing" -ForegroundColor Gray
Write-Host ""

# Convert paths to absolute for Docker mount
$AbsDataDir = (Resolve-Path $DataDir).Path
$AbsConfigDir = (Resolve-Path $env:CONFIG_DIR).Path

# Run container
# Mounting entire data dir to /app/data so db and recordings are accessible
# Network host to access mongodb if needed (or just use bridge/link if defined)
# but for this quick test we use SQLite so no network needed really, 
# except if we wanted to talk to Mongo (but we are skipping Vault for now)

docker run --rm -it `
    --name ml-worker-test `
    -v "${AbsDataDir}:/app/data" `
    -v "${AbsConfigDir}:/app/config" `
    -e "RECORDINGS_DIR=/app/data/recordings" `
    -e "PROCESSED_DIR=/app/data/processed" `
    -e "DB_PATH=/app/data/analytics.db" `
    -e "CONFIG_DIR=/app/config" `
    -e "DB_TYPE=sqlite" `
    ml-worker:test

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Test Complete!                        " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to: $env:DB_PATH" -ForegroundColor Green


Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Test Complete!                        " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to: $env:DB_PATH" -ForegroundColor Green
Write-Host ""
Write-Host "To view the dashboard, run:" -ForegroundColor Yellow
Write-Host "  streamlit run dashboard/app.py" -ForegroundColor White
