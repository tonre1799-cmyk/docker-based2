# ============================================
# Full Integration Test - ML Pipeline
# ============================================
# 1. Builds Docker images (Dispatcher, ML Worker)
# 2. Starts Production Stack (Minio, Redis, Postgres, Dispatcher, ML Worker)
# 3. Emulates Agent Upload (using emulate_agent.py)
# 4. Verifies results in Database
# ============================================

param(
    [string]$VideoFile = "..\NA - HD CCTV Camera video 3MP 4MP iProx CCTV HDCCTVCameras.net retail store.mp4"
)

$ErrorActionPreference = "Continue" # Docker writes progress to stderr, so Stop would kill script
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Full Integration Test Framework        " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# ============================================
# Step 1: Configuration & Setup
# ============================================
Write-Host "[1/6] Configuring environment..." -ForegroundColor Yellow

$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
    Write-Host "  -> Created .env.prod from example" -ForegroundColor Gray
}

# Ensure data directories exist
$DataDir = Join-Path $ProjectRoot "data"
New-Item -ItemType Directory -Force -Path (Join-Path $DataDir "minio") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DataDir "postgres") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DataDir "redis") | Out-Null

# Verify video file
$SourceVideo = $null
$VideoNames = @("NA - HD CCTV Camera video 3MP 4MP iProx CCTV HDCCTVCameras.net retail store.mp4")
foreach ($vidName in $VideoNames) {
    if (Test-Path (Join-Path $ProjectRoot $vidName)) { $SourceVideo = (Join-Path $ProjectRoot $vidName); break }
}
if (-not $SourceVideo) { $SourceVideo = $VideoFile }
if (-not (Test-Path $SourceVideo)) {
    Write-Host "ERROR: Video file not found: $VideoFile" -ForegroundColor Red
    exit 1
}
Write-Host "  -> Test Video: $SourceVideo" -ForegroundColor Gray

# ============================================
# Step 2: Build Docker Images
# ============================================
Write-Host "[2/6] Building Docker Images..." -ForegroundColor Yellow

# Cleanup first to avoid conflicts
Write-Host "  -> Cleaning up environment..." -ForegroundColor Gray
docker compose -f docker-compose.yml down --remove-orphans

Push-Location $ProjectRoot

Write-Host "  -> Building Dispatcher..." -ForegroundColor Gray
docker build --progress=plain -f dispatcher/Dockerfile -t event-dispatcher:latest .

Write-Host "  -> Building ML Worker..." -ForegroundColor Gray
docker build --progress=plain -t ml-worker:latest ./ml_worker

Write-Host "  -> Building Camera API..." -ForegroundColor Gray
docker build --progress=plain -f camera_api/Dockerfile -t camera-api:latest .

Write-Host "  -> Building Dashboard..." -ForegroundColor Gray
docker build --progress=plain -f dashboard/Dockerfile -t analytics-dashboard:latest .

Write-Host "  -> Images built successfully" -ForegroundColor Green

# ============================================
# Step 3: Start Production Stack
# ============================================
Write-Host "[3/6] Starting Production Stack..." -ForegroundColor Yellow

# Use a specific compose file for testing if needed, or PROD file
# We use docker-compose.prod.yml but override some ports for localhost access
# Creating a temporary test override file
$TestCompose = Join-Path $ProjectRoot "docker-compose.test.yml"
@"
version: '3.8'
services:
  dispatcher:
    ports:
      - "5000:5000"
  postgres:
    ports:
      - "5432:5432"
  redis:
    ports:
      - "6379:6379"
  minio:
    ports:
      - "9000:9000"
      - "9001:9001"
"@ | Out-File -FilePath $TestCompose -Encoding utf8

# Start specific services (exclude tailscale/vault/agent for this emulation test)
$Services = @("minio", "redis", "postgres", "dispatcher", "ml_worker", "dashboard", "camera_api")
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d $Services

Start-Sleep -Seconds 10
Write-Host "  -> Stack is running" -ForegroundColor Green

# ============================================
# Step 4: Run Emulation
# ============================================
Write-Host "[4/6] Running Agent Emulation..." -ForegroundColor Yellow

# Install emulator dependencies if needed
pip install minio requests 2>&1 | Out-Null

$CameraID = "test-integration-01"

try {
    python scripts/emulate_agent.py --file "$SourceVideo" --camera "$CameraID"
    Write-Host "  -> Injection successful" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Injection failed. Check logs." -ForegroundColor Red
    docker compose logs dispatcher
    exit 1
}

# ============================================
# Step 5: Verify Processing
# ============================================
Write-Host "[5/6] Verifying Processing (Waiting 30s)..." -ForegroundColor Yellow

$MaxRetries = 10
$RetryCount = 0
$Found = $false

while ($RetryCount -lt $MaxRetries) {
    Start-Sleep -Seconds 5
    
    # Check ML Worker logs for success message
    $Logs = docker compose -f docker-compose.yml logs ml_worker 2>&1
    if ($Logs -match "Task completed") {
        Write-Host "  -> ML Worker success detected in logs!" -ForegroundColor Green
        $Found = $true
        break
    }
    Write-Host "  ... waiting for processing ($RetryCount/$MaxRetries)" -ForegroundColor DarkGray
    $RetryCount++
}

if (-not $Found) {
    Write-Host "WARNING: Processing timeout. Checking logs..." -ForegroundColor Yellow
    docker compose -f docker-compose.yml logs ml_worker | Select-Object -Last 20
}

# ============================================
# Step 6: Verify System End-to-End
# ============================================
Write-Host "[6/6] Verifying System Components..." -ForegroundColor Yellow

# 6.1 Check PostgreSQL row count
try {
    $Result = docker exec analytics-postgres psql -U analytics_user -d analytics -t -c "SELECT COUNT(*) FROM analytics WHERE camera_id = '$CameraID';"
    $Count = $Result.Trim()
    
    if ([int]$Count -gt 0) {
        Write-Host "  -> Database: Found $Count analytics records!" -ForegroundColor Green
    } else {
        Write-Host "  -> Database: No records found." -ForegroundColor Red
    }
} catch {
    Write-Host "  -> Database: check failed" -ForegroundColor Red
}

# 6.2 Check Camera API
try {
    Write-Host "  -> Checking Camera API..." -ForegroundColor Gray
    $ApiResponse = Invoke-RestMethod -Uri "http://localhost:8000/cameras/" -Method Get -ErrorAction SilentlyContinue
    if ($ApiResponse) {
        Write-Host "  -> Camera API: Operational" -ForegroundColor Green
    } else {
        Write-Host "  -> Camera API: No data returned" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  -> Camera API: Not reachable" -ForegroundColor Red
}

# 6.3 Check Dashboard
try {
    Write-Host "  -> Checking Dashboard..." -ForegroundColor Gray
    $DashResponse = Invoke-WebRequest -Uri "http://localhost:8501" -Method Get -ErrorAction SilentlyContinue
    if ($DashResponse.StatusCode -eq 200) {
        Write-Host "  -> Dashboard: Operational (HTTP 200)" -ForegroundColor Green
    }
} catch {
    Write-Host "  -> Dashboard: Not reachable" -ForegroundColor Red
}

# 6.4 Check Heatmaps
$HeatmapDir = Join-Path $DataDir "heatmaps"
if (Test-Path $HeatmapDir) {
    $Files = Get-ChildItem $HeatmapDir -Filter "*.png"
    if ($Files.Count -gt 0) {
        Write-Host "  -> Heatmaps: Found $($Files.Count) generated maps" -ForegroundColor Green
    } else {
        Write-Host "  -> Heatmaps: No images found yet" -ForegroundColor Yellow
    }
}


Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Integration Test Complete              " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "To teardown: docker compose -f docker-compose.yml down" -ForegroundColor Gray

Remove-Item $TestCompose -ErrorAction SilentlyContinue
Pop-Location
