@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LSM-Connect - Iniciador

rem Uso: doble clic = modelos reales (si existen). Simulado: iniciar_demo.bat simulado
rem Otra ventanilla/dominio: iniciar_demo.bat real escolar
set "MODO=real"
if /i "%~1"=="simulado" set "MODO=simulado"
set "DOMINIO=escolar"
if not "%~2"=="" set "DOMINIO=%~2"

echo ================================================
echo   LSM-Connect - iniciando (modo: %MODO%, dominio: %DOMINIO%)
echo ================================================

set "PY="
for %%P in ("venv\Scripts\python.exe" ".venv\Scripts\python.exe") do (
  if not defined PY if exist %%P set "PY=%%~fP"
)
if not defined PY (
  python -c "import mediapipe" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo.
  echo [ERROR] No encontre el Python del proyecto. Desde esta carpeta corre:
  echo     python -m venv venv
  echo     venv\Scripts\activate
  echo     pip install -r requirements.txt
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

if /i "%MODO%"=="real" if not exist "modelos\senas.h5" if not exist "modelos\letras.h5" (
  echo.
  echo [AVISO] No hay modelos entrenados en la carpeta modelos. Se usara el modo simulado.
  echo Para entrenarlos: python herramientas\entrenar_senas.py y python herramientas\entrenar_letras.py
  set "MODO=simulado"
)

if not exist "Frontend\lsm-connect\node_modules" (
  echo Instalando librerias del front, solo la primera vez...
  pushd "Frontend\lsm-connect"
  call npm install
  popd
)

set "LSM_MOTOR=%MODO%"
start "LSM Backend" /d "%~dp0" cmd /k ""%PY%" -m uvicorn app.main:app --app-dir Backend --port 8000"
start "LSM Frontend" /d "%~dp0Frontend\lsm-connect" cmd /k "npm run dev"

echo.
echo Esperando a que el servidor cargue los modelos (puede tardar ~30 s la primera vez)...
set /a ESPERA=0
:esperar_backend
curl.exe -s -o nul http://127.0.0.1:8000/salud && goto backend_listo
set /a ESPERA+=1
if %ESPERA% GEQ 120 (
  echo [AVISO] El servidor no respondio en 2 minutos. Revisa la ventana "LSM Backend".
  goto abrir_navegador
)
timeout /t 1 /nobreak >nul
goto esperar_backend
:backend_listo
echo Servidor listo.
:abrir_navegador
start "" "http://localhost:5173/?dominio=%DOMINIO%"

echo.
echo Listo. Se abrieron dos ventanas negras (Backend y Frontend): dejalas abiertas.
echo Para apagar todo, usa detener_demo.bat
timeout /t 5 >nul
