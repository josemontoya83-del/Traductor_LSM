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
echo   1) Probar camara (encuadre, luz y fps)
echo   2) Grabar una sesion
echo   3) Ver avance de todas las personas
echo.
set /p OPCION="Elige 1, 2 o 3: "

if "%OPCION%"=="1" (
  "%PY%" herramientas\captura.py --probar-camara
  goto fin
)
if "%OPCION%"=="3" (
  "%PY%" herramientas\revisar_datos.py --avisos
  goto fin
)
if not "%OPCION%"=="2" goto fin

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
