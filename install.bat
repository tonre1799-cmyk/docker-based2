@echo off
setlocal

echo ====================================================
echo   ML Heatmap ^& Tracking - Installer (Windows)
echo ====================================================

:: 1. Run Verification
python scripts\verify_installation.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pre-flight checks failed. Please fix issues and try again.
    pause
    exit /b 1
)

:: 2. Setup Environment
python scripts\setup_env.py

:: 3. Pull and Start
echo Pulling Docker images...
docker-compose pull

echo Starting services in detached mode...
docker-compose -f docker-compose.yml -f docker-compose.central.yml up -d

echo ====================================================
echo   🚀 INSTALLATION COMPLETE
echo ====================================================
echo Access the dashboard at: http://localhost:8501
echo Access Kerberos Vault at: http://localhost:8081
echo Check service status with: docker-compose ps
pause
