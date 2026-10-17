$ErrorActionPreference = 'Stop'
$folder = Join-Path $env:TEMP ('Meridian updater test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $folder | Out-Null
try {
    $staged = Join-Path $folder 'new.exe'
    $target = Join-Path $folder 'Launcher with spaces.exe'
    Add-Type -TypeDefinition @'
using System;
using System.IO;
public class Marker {
    public static void Main() {
        File.WriteAllText(Environment.GetCommandLineArgs()[0] + ".started", "ok");
    }
}
'@ -OutputAssembly $staged -OutputType ConsoleApplication
    [IO.File]::WriteAllText($target, 'old executable backup fixture')
    $parent = Start-Process powershell.exe -ArgumentList '-NoProfile', '-Command', 'Start-Sleep -Seconds 3' -PassThru -WindowStyle Hidden
    $job = Join-Path $folder 'job.json'
    $data = @{ target=$target; staged=$staged; sha256=(Get-FileHash $staged -Algorithm SHA256).Hash.ToLower(); pid=$parent.Id }
    [IO.File]::WriteAllText($job, ($data | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    $helper = Start-Process -FilePath (Resolve-Path 'dist/Project-Meridian-Launcher.exe') -ArgumentList '--apply-self-update', ('"' + $job + '"') -PassThru
    if (-not $helper.WaitForExit(45000)) { $helper.Kill(); throw 'Frozen updater timed out' }
    if ($helper.ExitCode -ne 0) { throw 'Frozen updater failed' }
    for ($i=0; $i -lt 50 -and -not (Test-Path "$target.started"); $i++) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path "$target.started")) { throw 'Replacement EXE was not started' }
    if ((Get-FileHash $target -Algorithm SHA256).Hash.ToLower() -ne $data.sha256) { throw 'Wrong replacement bytes' }
    $backup = [IO.Path]::ChangeExtension($target, '.previous.exe')
    if ([IO.File]::ReadAllText($backup) -ne 'old executable backup fixture') { throw 'Old EXE backup missing' }
    Write-Host 'PASS: frozen helper waits, replaces EXE with spaces in path, keeps backup, restarts replacement'
} finally {
    Remove-Item -Recurse -Force $folder -ErrorAction SilentlyContinue
}
