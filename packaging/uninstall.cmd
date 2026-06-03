@echo off
setlocal

set "APP_NAME=PDFTranslator"
set "APP_TITLE=PDF Translator"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\%APP_NAME%"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_TITLE%"

echo Uninstalling %APP_TITLE%...
del "%USERPROFILE%\Desktop\PDF Translator.lnk" 2>nul
rmdir /s /q "%START_MENU%" 2>nul

start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 1; Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA 'Programs\PDFTranslator') -Recurse -Force -ErrorAction SilentlyContinue"
echo Uninstall started.
