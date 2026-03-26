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

:: Buscar Python en el PATH
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
    echo  [ERROR] Hay dependencias faltantes. Instalalas con:
    echo          pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Obtener la ruta de pythonw.exe (mismo directorio que python.exe, sin consola)
for /f "tokens=*" %%p in ('python -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set PYTHONW=%%p

:: Comprobar si pythonw.exe existe; si no, usar python normal
if not exist "%PYTHONW%" set PYTHONW=python

echo.
echo  Lanzando ACR Telemetry Advisor...
echo  (Esta ventana se cerrara automaticamente)
echo.

:: Lanzar la app grafica en proceso independiente y cerrar esta consola
:: "start /b" lanza sin nueva ventana de consola; pythonw no abre consola
start "" "%PYTHONW%" "%~dp0main.py"

:: Pequeña pausa para dar tiempo a que arranque, luego cierra la consola
timeout /t 2 /nobreak >nul
exit

