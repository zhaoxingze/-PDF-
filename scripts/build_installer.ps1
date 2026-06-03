param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$DistDir = Join-Path $Root "dist"
$AppExe = Join-Path $DistDir "PDFTranslator.exe"
$BuildDir = Join-Path $Root "build"
$PayloadDir = Join-Path $BuildDir "installer_payload"
$InstallerDir = Join-Path $DistDir "installer"
$InstallerName = "PDFTranslatorSetup-$Version.exe"
$InstallerPath = Join-Path $InstallerDir $InstallerName
$IExpress = Join-Path $env:WINDIR "System32\iexpress.exe"

if (-not (Test-Path $IExpress)) {
    throw "IExpress was not found at $IExpress"
}

Set-Location $Root

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m PyInstaller --clean --noconfirm "packaging\PDFTranslator.spec"

if (-not (Test-Path $AppExe)) {
    throw "PyInstaller did not create $AppExe"
}

New-Item -ItemType Directory -Path $PayloadDir -Force | Out-Null
New-Item -ItemType Directory -Path $InstallerDir -Force | Out-Null
Remove-Item -LiteralPath (Join-Path $PayloadDir "app.zip") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $InstallerPath -Force -ErrorAction SilentlyContinue

$AppZip = Join-Path $PayloadDir "app.zip"
Copy-Item -LiteralPath $AppExe -Destination (Join-Path $PayloadDir "PDFTranslator.exe") -Force
Copy-Item -LiteralPath (Join-Path $Root "packaging\uninstall.cmd") -Destination (Join-Path $PayloadDir "uninstall.cmd") -Force
Compress-Archive -Path (Join-Path $PayloadDir "PDFTranslator.exe"), (Join-Path $PayloadDir "uninstall.cmd") -DestinationPath $AppZip -Force
Copy-Item -LiteralPath (Join-Path $Root "packaging\install.cmd") -Destination (Join-Path $PayloadDir "install.cmd") -Force

$SedPath = Join-Path $PayloadDir "installer.sed"
$Sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$InstallerPath
FriendlyName=PDF Translator Installer
AppLaunched=install.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="app.zip"
FILE1="install.cmd"
[SourceFiles]
SourceFiles0=$PayloadDir
[SourceFiles0]
%FILE0%=
%FILE1%=
"@

Set-Content -LiteralPath $SedPath -Value $Sed -Encoding ASCII

if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
    $oldNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}
& $IExpress /N /Q $SedPath
$iexpressExitCode = $LASTEXITCODE
if ($null -ne $oldNativeErrorPreference) {
    $PSNativeCommandUseErrorActionPreference = $oldNativeErrorPreference
}
$global:LASTEXITCODE = 0

if (-not (Test-Path $InstallerPath)) {
    throw "Installer was not created at $InstallerPath. IExpress exit code: $iexpressExitCode"
}

Write-Host "Built application: $AppExe"
Write-Host "Built installer: $InstallerPath"
exit 0
