@echo off
setlocal

set "APP_NAME=PDFTranslator"
set "APP_TITLE=PDF Translator"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\%APP_NAME%"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_TITLE%"
set "PDF_TRANSLATOR_PAYLOAD=%~dp0app.zip"
set "PDF_TRANSLATOR_INSTALL_DIR=%INSTALL_DIR%"

echo Installing %APP_TITLE%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%START_MENU%" mkdir "%START_MENU%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath $env:PDF_TRANSLATOR_PAYLOAD -DestinationPath $env:PDF_TRANSLATOR_INSTALL_DIR -Force"
if errorlevel 1 (
    echo Failed to extract application files.
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$installDir=$env:PDF_TRANSLATOR_INSTALL_DIR; $startMenu=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\PDF Translator'; New-Item -ItemType Directory -Path $startMenu -Force | Out-Null; $exe=Join-Path $installDir 'PDFTranslator.exe'; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'PDF Translator.lnk')); $s.TargetPath=$exe; $s.WorkingDirectory=$installDir; $s.IconLocation=$exe + ',0'; $s.Save(); $m=$ws.CreateShortcut((Join-Path $startMenu 'PDF Translator.lnk')); $m.TargetPath=$exe; $m.WorkingDirectory=$installDir; $m.IconLocation=$exe + ',0'; $m.Save(); $u=$ws.CreateShortcut((Join-Path $startMenu 'Uninstall PDF Translator.lnk')); $u.TargetPath=(Join-Path $installDir 'uninstall.cmd'); $u.WorkingDirectory=$installDir; $u.Save()"

echo.
echo Installation completed.
echo Desktop shortcut: PDF Translator
echo Installed to: %INSTALL_DIR%
