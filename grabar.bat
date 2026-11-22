@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LSM-Connect - Grabacion

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

echo ================================================
echo   LSM-Connect - Grabacion de senas
echo ================================================
echo.
echo   1) Abrir la grabacion en el navegador  (recomendado: la persona graba sola)
echo   2) Ver avance de todas las personas
echo   3) Sacar los puntos de lo grabado  (al terminar el dia)
echo   4) Programa clasico con operador  (teclado)
echo.
set /p OPCION="Elige 1, 2, 3 o 4: "

if "%OPCION%"=="2" (
  "%PY%" herramientas\revisar_datos.py --avisos
  goto fin
)
if "%OPCION%"=="3" (
  "%PY%" herramientas\extraer_puntos.py
  goto fin
)
if "%OPCION%"=="4" goto clasico
if not "%OPCION%"=="1" goto fin

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] No encontre Node.js. Instalalo desde nodejs.org y vuelve a abrir este archivo.
  goto fin
)
if not exist "Frontend\lsm-connect\node_modules" (
  echo Instalando librerias de la interfaz, solo la primera vez...
  pushd "Frontend\lsm-connect"
  call npm install
  popd
)
start "LSM Backend" /d "%~dp0" cmd /k ""%PY%" -m uvicorn app.main:app --app-dir Backend --port 8000"
start "LSM Frontend" /d "%~dp0Frontend\lsm-connect" cmd /k "npm run dev"
echo.
echo Esperando al servidor...
set /a ESPERA=0
:esperar
curl.exe -s -o nul http://127.0.0.1:8000/salud && goto listo
set /a ESPERA+=1
if %ESPERA% GEQ 120 goto abrir
timeout /t 1 /nobreak >nul
goto esperar
:listo
:abrir
start "" "http://localhost:5173/grabar"
echo.
echo Listo: se abrio la grabacion en el navegador (usa Chrome o Edge).
echo Deja abiertas las dos ventanas negras. Para apagar todo: detener_demo.bat
goto fin

:clasico
set /p PERSONA="Codigo de la persona (ej. P01, NUNCA el nombre): "
set /p SESION="Sesion (1 o 2): "
set /p BLOQUES="Bloques (Enter = todos los de la sesion; ej. G para respuestas): "
if "%BLOQUES%"=="" (
  "%PY%" herramientas\captura.py --persona %PERSONA% --sesion %SESION%
) else (
  "%PY%" herramientas\captura.py --persona %PERSONA% --sesion %SESION% --bloques %BLOQUES%
)

:fin
echo.
pause
