@echo off
echo Apagando LSM-Connect...
taskkill /f /t /fi "WINDOWTITLE eq LSM Backend*" >nul 2>nul
taskkill /f /t /fi "WINDOWTITLE eq LSM Frontend*" >nul 2>nul
echo Listo.
timeout /t 2 >nul
