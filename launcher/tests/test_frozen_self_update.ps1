$ErrorActionPreference = 'Stop'
$tempRoot = [IO.Path]::GetFullPath($env:TEMP)
$folder = Join-Path $tempRoot ('Meridian updater test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $folder | Out-Null
try {
    $installed = Join-Path $folder 'Installed launcher'
    $payload = Join-Path $folder 'payload'
    $helperFolder = Join-Path $folder 'helper'
    New-Item -ItemType Directory (Join-Path $installed '_internal'),(Join-Path $payload '_internal'),$helperFolder | Out-Null
    Copy-Item -Path 'dist/Project-Meridian-Launcher/app/*' -Destination $helperFolder -Recurse
    $executable = 'Project-Meridian-Launcher.exe'
    $staged = Join-Path $payload $executable
    Add-Type -TypeDefinition @'
using System;
using System.IO;
public class Marker {
    public static void Main() {
        File.WriteAllText(Environment.GetCommandLineArgs()[0] + ".started", "ok");
    }
}
'@ -OutputAssembly $staged -OutputType ConsoleApplication
    [IO.File]::WriteAllText((Join-Path $installed $executable), 'old executable')
    [IO.File]::WriteAllText((Join-Path $installed '_internal/runtime.dll'), 'old runtime')
    [IO.File]::WriteAllText((Join-Path $installed 'unins000.dat'), 'uninstall data')
    [IO.File]::WriteAllText((Join-Path $payload '_internal/runtime.dll'), 'new runtime')
    $files = @{}
    $files[$executable] = (Get-FileHash $staged -Algorithm SHA256).Hash.ToLower()
    $files['_internal/runtime.dll'] = (Get-FileHash (Join-Path $payload '_internal/runtime.dll') -Algorithm SHA256).Hash.ToLower()
    $marker = @{ schema=1; product='Project Meridian Launcher'; version='2.0.0'; files=$files }
    [IO.File]::WriteAllText((Join-Path $payload 'bundle.json'), ($marker | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = Join-Path $folder 'update.zip'
    [IO.Compression.ZipFile]::CreateFromDirectory($payload, $archive)
    $parent = Start-Process powershell.exe -ArgumentList '-NoProfile','-Command','Start-Sleep -Seconds 2' -PassThru -WindowStyle Hidden
    $job = Join-Path $folder 'job.json'
    $data = @{ kind='bundle'; target=$installed; staged=$archive; sha256=(Get-FileHash $archive -Algorithm SHA256).Hash.ToLower(); pid=$parent.Id }
    [IO.File]::WriteAllText($job, ($data | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    $helper = Start-Process -FilePath (Join-Path $helperFolder $executable) -ArgumentList '--apply-self-update',('"' + $job + '"') -PassThru -WindowStyle Hidden
    if (-not $helper.WaitForExit(60000)) { $helper.Kill(); throw 'Frozen updater timed out' }
    if ($helper.ExitCode -ne 0) { throw 'Frozen updater failed' }
    if (-not (Test-Path (Join-Path $installed ($executable + '.started')))) { throw 'New executable was not started' }
    if ([IO.File]::ReadAllText((Join-Path $installed '_internal/runtime.dll')) -ne 'new runtime') { throw 'Dependencies were not updated' }
    if ([IO.File]::ReadAllText((Join-Path ($installed + '.previous') '_internal/runtime.dll')) -ne 'old runtime') { throw 'Dependency backup is missing' }
    if ([IO.File]::ReadAllText((Join-Path $installed 'unins000.dat')) -ne 'uninstall data') { throw 'Uninstaller state was lost' }
    Write-Host 'PASS: copied onedir helper waits, verifies, replaces all files, retains backup and restarts'
} finally {
    $resolvedFolder = [IO.Path]::GetFullPath($folder)
    if (-not $resolvedFolder.StartsWith($tempRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test cleanup path' }
    Remove-Item -LiteralPath $resolvedFolder -Recurse -Force -ErrorAction SilentlyContinue
}
