# Docker Test Pipeline
# Runs all 3 stages of strict testing

$ErrorActionPreference = "Stop"

Write-Host "1️⃣  Stage 1: Container-Level Tests (Build Gate)" -ForegroundColor Cyan
docker build -t myapp:test --target test .
if ($LASTEXITCODE -ne 0) { Write-Error "Stage 1 Failed"; exit 1 }

Write-Host "2️⃣  Stage 2: Integration Tests (Docker Compose)" -ForegroundColor Cyan
docker compose -f docker-compose.integration.yml up --build --abort-on-container-exit
if ($LASTEXITCODE -ne 0) { Write-Error "Stage 2 Failed"; exit 1 }
docker compose -f docker-compose.integration.yml down -v

Write-Host "3️⃣  Stage 3: E2E Tests (System Wiring)" -ForegroundColor Cyan
docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit
if ($LASTEXITCODE -ne 0) { 
    docker compose -f docker-compose.e2e.yml logs app
    Write-Error "Stage 3 Failed" 
    docker compose -f docker-compose.e2e.yml down -v
    exit 1 
}
docker compose -f docker-compose.e2e.yml down -v

Write-Host "✅ All Docker Tests Passed!" -ForegroundColor Green
