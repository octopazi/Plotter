param(
    [string]$Version
)


$ErrorActionPreference = "Stop"

$pythonExe = $null
$pythonPrefixArgs = @()

if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
    $pythonPrefixArgs = @("-3")
}
else {
    throw "Python executable not found in PATH."
}

function Invoke-Python {
    param([string[]]$CommandArgs)
    & $pythonExe @pythonPrefixArgs @CommandArgs
}

Write-Host "[1/6] Validating version naming rules..."
if (-not $Version) {
    $Version = Invoke-Python -CommandArgs @("scripts/validate_version.py", "--print-version")
    $Version = "$Version".Trim()
} else {
    Invoke-Python -CommandArgs @("scripts/validate_version.py", "--expected", $Version)
}

Invoke-Python -CommandArgs @(
    "scripts/validate_version.py",
    "--expected", $Version,
    "--changelog", "CHANGELOG.md",
    "--release-notes", "RELEASE_NOTES.md"
)

Write-Host "[2/6] Cleaning old build outputs..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

Write-Host "[3/6] Installing dependencies..."
Invoke-Python -CommandArgs @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Python -CommandArgs @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-Python -CommandArgs @("-m", "pip", "install", "pyinstaller")

Write-Host "[4/6] Building PyInstaller bundle for version $Version..."
$env:PLOTTER_VERSION = $Version
Invoke-Python -CommandArgs @("-m", "PyInstaller", "--clean", "--noconfirm", "main.spec")

$distDir = Join-Path "dist" "Plotter-$Version"
if (-not (Test-Path $distDir)) {
    throw "Expected build output not found: $distDir"
}

Write-Host "[5/6] Packaging release archive..."
$zipPath = Join-Path "dist" "Plotter-$Version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $zipPath

Write-Host "[6/6] Done. Release artifacts:"
Write-Host " - $distDir"
Write-Host " - $zipPath"
