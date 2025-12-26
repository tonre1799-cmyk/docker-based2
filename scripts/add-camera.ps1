<#
.SYNOPSIS
    Add a new camera to the system
.DESCRIPTION
    Interactive script to add a camera to cameras.yml and generate remote .env
.EXAMPLE
    .\add-camera.ps1
#>

$ErrorActionPreference = "Stop"
$ConfigPath = Join-Path $PSScriptRoot "..\config\cameras.yml"
$RemoteEnvTemplate = Join-Path $PSScriptRoot "..\remote\.env.template"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Add New Camera" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Gather camera information
$CameraId = Read-Host "Camera ID (e.g., cam-02, warehouse-a)"
$CameraName = Read-Host "Camera Name (e.g., Warehouse Camera)"
$Location = Read-Host "Location (e.g., Cairo - Nasr City)"
$IpAddress = Read-Host "Camera IP Address (e.g., 192.168.1.100)"
$Port = Read-Host "Stream Port (default: 81)"
if ([string]::IsNullOrEmpty($Port)) { $Port = "81" }

# Read central server info for remote .env
Write-Host ""
Write-Host "Central Server Configuration:" -ForegroundColor Yellow
$VaultUri = Read-Host "Central Vault URI (e.g., http://192.168.1.10:8081)"
$VaultAccessKey = Read-Host "Vault Access Key"
$VaultSecretKey = Read-Host "Vault Secret Key"

# Append to cameras.yml
Write-Host ""
Write-Host "Adding camera to cameras.yml..." -ForegroundColor Yellow

$CameraEntry = @"

  - id: "$CameraId"
    name: "$CameraName"
    location: "$Location"
    ip: "$IpAddress"
    port: $Port
    enabled: true
"@

Add-Content -Path $ConfigPath -Value $CameraEntry

# Generate remote .env for this camera
$RemoteEnvPath = Join-Path $PSScriptRoot "..\remote\deployments\$CameraId\.env"
$RemoteEnvDir = Split-Path $RemoteEnvPath -Parent
if (-not (Test-Path $RemoteEnvDir)) {
    New-Item -ItemType Directory -Path $RemoteEnvDir -Force | Out-Null
}

$EnvContent = @"
# ==========================================
# Remote Agent: $CameraName
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ==========================================

CAMERA_ID=$CameraId
CAMERA_NAME=$CameraName

CAMERA_STREAM_URL=http://${IpAddress}:${Port}/stream

VAULT_URI=$VaultUri
VAULT_ACCESS_KEY=$VaultAccessKey
VAULT_SECRET_KEY=$VaultSecretKey
"@

Set-Content -Path $RemoteEnvPath -Value $EnvContent

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Camera Added Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Camera ID:     $CameraId" -ForegroundColor White
Write-Host "  Config added:  config/cameras.yml" -ForegroundColor White
Write-Host "  Remote .env:   remote/deployments/$CameraId/.env" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy 'remote/' folder to camera location" -ForegroundColor White
Write-Host "  2. Copy 'remote/deployments/$CameraId/.env' to 'remote/.env'" -ForegroundColor White
Write-Host "  3. Run: .\deploy-remote.ps1 -CameraId $CameraId" -ForegroundColor White
Write-Host ""
