$ErrorActionPreference = 'Stop'
$tempRoot = [IO.Path]::GetFullPath($env:TEMP)
$folder = Join-Path $tempRoot ('Meridian session test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $folder | Out-Null
try {
    $fakeGame = Join-Path $folder 'game.ps1'
    @'
Write-Output "launched`t123"
Start-Sleep -Milliseconds 500
$status = Get-Content (Join-Path $PSScriptRoot 'status.json') -Raw | ConvertFrom-Json
if ($status.state -eq 'ready') { throw 'Old game log was mistaken for current startup' }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'latest.log'), "[new] [Render thread/INFO] [FancyMenu]: ScreenCustomizationLayer registered: title_screen`n")
Start-Sleep -Seconds 2
Write-Output "log_raw`tgame survived accessToken=secret"
Write-Output "terminated`t0"
'@ | Set-Content -LiteralPath $fakeGame -Encoding UTF8
    $job = Join-Path $folder 'job.json'
    $log = Join-Path $folder 'game.log'
    $gameLog = Join-Path $folder 'latest.log'
    [IO.File]::WriteAllText($gameLog, "[old] [Render thread/INFO] [FancyMenu]: ScreenCustomizationLayer registered: title_screen`n")
    $data = @{ command=@('powershell.exe','-NoProfile','-File',$fakeGame); cwd=$folder; log=$log; game_log=$gameLog; grace=0.1 }
    [IO.File]::WriteAllText($job, ($data | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    $helper = Start-Process -FilePath (Resolve-Path 'dist/Project-Meridian-Launcher/app/Project-Meridian-Launcher.exe') -ArgumentList '--game-session',('"' + $job + '"') -PassThru -WindowStyle Hidden
    $ready = $false
    for ($attempt=0; $attempt -lt 200; $attempt++) {
        $statusPath = Join-Path $folder 'status.json'
        if (Test-Path $statusPath) {
            $state = Get-Content $statusPath -Raw | ConvertFrom-Json
            if ($state.state -eq 'ready') { $ready = $true; break }
            if ($state.state -eq 'error') { throw $state.message }
        }
        if ($helper.HasExited) { break }
        Start-Sleep -Milliseconds 50
    }
    if (-not $ready -or $helper.HasExited) { throw 'Game readiness was not confirmed independently' }
    if (-not $helper.WaitForExit(15000)) { $helper.Kill(); throw 'Game session did not finish' }
    if ($helper.ExitCode -ne 0) { throw 'Game session failed' }
    $text = Get-Content $log -Raw
    if (-not $text.Contains('game survived') -or $text.Contains('accessToken=secret')) { throw 'Independent logging or token masking failed' }
    Write-Host 'PASS: frozen supervisor detects the current game log, ignores stale readiness and masks tokens'
} finally {
    $resolvedFolder = [IO.Path]::GetFullPath($folder)
    if (-not $resolvedFolder.StartsWith($tempRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe test cleanup path' }
    Remove-Item -LiteralPath $resolvedFolder -Recurse -Force -ErrorAction SilentlyContinue
}
