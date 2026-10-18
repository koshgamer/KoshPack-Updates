$ErrorActionPreference = 'Stop'
$tempRoot = [IO.Path]::GetFullPath($env:TEMP)
$folder = Join-Path $tempRoot ('Meridian recovery test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $folder | Out-Null
try {
    $bootstrapSource = (Resolve-Path 'dist/Project-Meridian-Launcher/Project-Meridian-Launcher.exe').Path
    if ((Get-Item -LiteralPath $bootstrapSource).VersionInfo.FileDescription -ne 'Project Meridian Bootstrap') { throw 'Recovery bootstrap is missing' }
    $markerExecutable = Join-Path $folder 'marker.exe'
    Add-Type -TypeDefinition @'
using System;
using System.IO;
public class RecoveryMarker {
    public static void Main() {
        File.WriteAllText(Environment.GetCommandLineArgs()[0] + ".started", "ok");
    }
}
'@ -OutputAssembly $markerExecutable -OutputType ConsoleApplication
    foreach ($phase in @('before-swap','missing-app','uncommitted-app')) {
        $installed = Join-Path $folder $phase
        $backup = Join-Path $installed 'app.previous'
        New-Item -ItemType Directory $backup -Force | Out-Null
        Copy-Item -LiteralPath $markerExecutable -Destination (Join-Path $backup 'Project-Meridian-Launcher.exe')
        [IO.File]::WriteAllText((Join-Path $backup 'old-version'), 'previous good bundle')
        Copy-Item -LiteralPath $bootstrapSource -Destination (Join-Path $installed 'Project-Meridian-Launcher.exe')
        [IO.File]::WriteAllText((Join-Path $installed 'app.update-pending'), 'Project Meridian Launcher')
        if ($phase -eq 'before-swap') { Rename-Item -LiteralPath $backup -NewName 'app' }
        if ($phase -eq 'uncommitted-app') {
            New-Item -ItemType Directory (Join-Path $installed 'app') | Out-Null
            [IO.File]::WriteAllText((Join-Path $installed 'app/unverified'), 'interrupted replacement')
        }
        $process = Start-Process -FilePath (Join-Path $installed 'Project-Meridian-Launcher.exe') -ArgumentList '--smoke-ui' -PassThru -WindowStyle Hidden
        if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Recovery timed out' }
        if ($process.ExitCode -ne 0) { throw 'Recovery bootstrap failed' }
        if (-not (Test-Path (Join-Path $installed 'app/Project-Meridian-Launcher.exe.started'))) { throw 'Recovered app did not start' }
        if ((Test-Path (Join-Path $installed 'app.update-pending')) -or (Test-Path (Join-Path $installed 'app.previous'))) { throw 'Recovery did not complete' }
        if (-not (Test-Path (Join-Path $installed 'app/old-version'))) { throw 'Previous bundle was not restored' }
    }
    Write-Host 'PASS: independent bootstrap recovers at all three interrupted-swap stages'
} finally {
    $resolvedFolder = [IO.Path]::GetFullPath($folder)
    if (-not $resolvedFolder.StartsWith($tempRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test cleanup path' }
    Remove-Item -LiteralPath $resolvedFolder -Recurse -Force -ErrorAction SilentlyContinue
}
