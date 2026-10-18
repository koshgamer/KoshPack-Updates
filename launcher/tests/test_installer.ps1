$ErrorActionPreference = 'Stop'
if (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{2B0406F4-397F-49EB-891A-706D1AE53F31}_is1') {
    throw 'A real launcher installation already exists; refusing to modify its installer registration.'
}
$tempRoot = [IO.Path]::GetFullPath($env:TEMP)
$folder = Join-Path $tempRoot ('Meridian installer test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $folder | Out-Null
try {
    $installed = Join-Path $folder 'Launcher'
    $installer = (Resolve-Path 'dist/Project-Meridian-Launcher.exe').Path
    for ($attempt=0; $attempt -lt 2; $attempt++) {
        $process = Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS',('/DIR="' + $installed + '"') -WindowStyle Hidden -PassThru
        if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Installer timed out' }
        if ($process.ExitCode -ne 0) { throw 'Installer failed' }
        $app = Join-Path $installed 'Project-Meridian-Launcher.exe'
        if (-not (Test-Path (Join-Path $installed 'app/_internal/python312.dll'))) { throw 'Runtime was not installed' }
        $smoke = Start-Process -FilePath $app -ArgumentList '--smoke-ui' -PassThru -WindowStyle Hidden
        if (-not $smoke.WaitForExit(60000)) { $smoke.Kill(); throw 'Installed app smoke timed out' }
        if ($smoke.ExitCode -ne 0) { throw 'Installed app failed' }
    }
    $uninstaller = Join-Path $installed 'unins000.exe'
    $process = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Uninstaller timed out' }
    if ($process.ExitCode -ne 0) { throw 'Uninstaller failed' }
    if (Test-Path (Join-Path $installed 'Project-Meridian-Launcher.exe')) { throw 'Installed executable remains after uninstall' }
    Write-Host 'PASS: installer clean install, repeated install, app startup and uninstall'
} finally {
    if ($installed -and (Test-Path (Join-Path $installed 'unins000.exe'))) {
        $cleanupUninstaller = Start-Process -FilePath (Join-Path $installed 'unins000.exe') -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -PassThru
        $cleanupUninstaller.WaitForExit(60000) | Out-Null
    }
    $resolvedFolder = [IO.Path]::GetFullPath($folder)
    if (-not $resolvedFolder.StartsWith($tempRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test cleanup path' }
    Remove-Item -LiteralPath $resolvedFolder -Recurse -Force -ErrorAction SilentlyContinue
}
