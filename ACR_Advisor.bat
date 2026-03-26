@echo off
:: ============================================================
::  ACR Telemetry Advisor — Launcher
::  Haz doble clic en este fichero para arrancar la aplicación.
:: ============================================================

title ACR Telemetry Advisor
color 0A

echo.
echo  =========================================
echo   ACR Telemetry Advisor — Iniciando...
echo  =========================================
echo.

:: Moverse a la carpeta donde está este .bat (sea cual sea)
cd /d "%~dp0"

:: Buscar Python (primero el del PATH, luego ubicaciones comunes)
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python no encontrado en el PATH.
    echo  Instala Python 3.11+ desde https://www.python.org
    pause
    exit /b 1
)

:: Mostrar versión detectada
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Python detectado: %PYVER%
echo.

:: Verificar dependencias antes de lanzar
echo  Comprobando dependencias...
python launcher_check.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Hay dependencias faltantes. Instálalas con:
    echo          pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo  Todo correcto. Arrancando la aplicación...
echo.

:: Lanzar la aplicación
python main.py

:: Si la app cierra con error, mostrar el mensaje
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] La aplicación se cerró con errores (código %errorlevel%).
    echo  Revisa el log anterior para más detalles.
    pause
)

