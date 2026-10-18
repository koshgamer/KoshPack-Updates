param([string]$Compiler, [switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
$version = (Select-String -Path launcher/source/launcher.py -Pattern 'APP_VERSION = "([^\"]+)"').Matches[0].Groups[1].Value
python launcher/source/make_icon.py
if ($LASTEXITCODE -ne 0) { throw 'Icon build failed' }
$distribution = [IO.Path]::GetFullPath((Join-Path (Get-Location) 'dist'))
$launcherDirectory = [IO.Path]::GetFullPath((Join-Path $distribution 'Project-Meridian-Launcher'))
if ([IO.Path]::GetDirectoryName($launcherDirectory) -ne $distribution) { throw 'Unsafe build directory' }
foreach ($directory in @($distribution, $launcherDirectory)) {
    if ((Test-Path -LiteralPath $directory) -and ((Get-Item -LiteralPath $directory -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Linked build directory is not supported' }
}
if (Test-Path -LiteralPath $launcherDirectory) { Remove-Item -LiteralPath $launcherDirectory -Recurse -Force }
New-Item -ItemType Directory $launcherDirectory -Force | Out-Null
python -m PyInstaller --noconfirm --clean --distpath $launcherDirectory launcher/build/launcher.spec
if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed' }
$nativeCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$compilerArguments = @('/nologo', '/target:winexe', '/codepage:65001', '/reference:System.Windows.Forms.dll',
    ('/win32icon:' + (Resolve-Path 'launcher/meridian.ico').Path),
    ('/out:' + (Join-Path $launcherDirectory 'Project-Meridian-Launcher.exe')),
    (Resolve-Path 'launcher/build/bootstrap.cs').Path)
& $nativeCompiler @compilerArguments
if ($LASTEXITCODE -ne 0) { throw 'Recovery bootstrap build failed' }
python launcher/tools/package_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Bundle packaging failed' }
if ($SkipInstaller) { return }
if (-not $Compiler) {
    $installedCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($installedCompiler) { $Compiler = $installedCompiler.Source }
    elseif (Test-Path 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe') { $Compiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' }
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler)) { throw 'Inno Setup compiler is required; pass -Compiler or use -SkipInstaller for a bundle-only build.' }
$bundleDirectory = (Resolve-Path 'dist/Project-Meridian-Launcher').Path
$outputDirectory = (Resolve-Path 'dist').Path
& $Compiler '/Q' "/DAppVersion=$version" "/DBundleDir=$bundleDirectory" "/DOutputDirectory=$outputDirectory" launcher/build/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
python launcher/tools/package_launcher.py --installer
if ($LASTEXITCODE -ne 0) { throw 'Installer metadata failed' }
