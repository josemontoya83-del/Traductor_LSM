@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LSM-Connect - Iniciador

rem Uso: doble clic = motor real. Para el simulado: iniciar_demo.bat simulado
set "MODO=real"
if /i "%~1"=="simulado" set "MODO=simulado"
rem Diagnostico: iniciar_demo.bat debug = motor real + imprime cada seña en la ventana del Backend
set "LSM_DEBUG=0"
if /i "%~1"=="debug" set "LSM_DEBUG=1"

echo ================================================
echo   LSM-Connect - iniciando demo (modo: %MODO%)
echo ================================================

set "PY="
for %%P in ("venv\Scripts\python.exe" ".venv\Scripts\python.exe" "Backend\venv\Scripts\python.exe" "Backend\.venv\Scripts\python.exe") do (
  if not defined PY if exist %%P set "PY=%%~fP"
)
if not defined PY (
  python -c "import uvicorn" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo.
  echo [ERROR] No encontre el Python con uvicorn instalado.
  echo Abre el PowerShell del entorno venv desde Visual Studio y corre:
  echo     pip install -r Backend\requirements-backend.txt
  echo Si el venv esta en otra carpeta, avisame la ruta.
  pause
  exit /b 1
)
echo Python: %PY%

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] No encontre Node.js. Instalalo desde nodejs.org y vuelve a abrir este archivo.
  pause
  exit /b 1
)

if /i "%MODO%"=="real" if not exist "Modelo_ia\lsm_tramites.h5" (
  echo.
  echo [AVISO] No existe Modelo_ia\lsm_tramites.h5. Se usara el modo simulado.
  echo Para generar el modelo: python Modelo_ia\entrenar_modelo.py --guardar
  set "MODO=simulado"
)

if not exist "Frontend\lsm-connect\node_modules" (
  echo Instalando librerias del front, solo la primera vez...
  pushd "Frontend\lsm-connect"
  call npm install
  popd
)

set "LSM_MOTOR=%MODO%"
start "LSM Backend" /d "%~dp0Backend" cmd /k ""%PY%" -m uvicorn app.main:app --port 8000"
start "LSM Frontend" /d "%~dp0Frontend\lsm-connect" cmd /k "npm run dev"

echo.
echo Esperando a que arranque todo...
timeout /t 8 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo Listo. Se abrieron dos ventanas negras (Backend y Frontend): dejalas abiertas.
echo Para apagar todo, usa detener_demo.bat
timeout /t 5 >nul
