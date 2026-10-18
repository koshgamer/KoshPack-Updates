#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifndef BundleDir
  #error BundleDir must point to the verified onedir build
#endif
#ifndef OutputDirectory
  #error OutputDirectory is required
#endif

[Setup]
AppId={{2B0406F4-397F-49EB-891A-706D1AE53F31}
AppName=Project Meridian Launcher
AppVersion={#AppVersion}
AppPublisher=Project Meridian
DefaultDirName={localappdata}\Programs\Project Meridian Launcher
DefaultGroupName=Project Meridian
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDirectory}
OutputBaseFilename=Project-Meridian-Launcher
SetupIconFile={#BundleDir}\app\_internal\meridian.ico
UninstallDisplayIcon={app}\Project-Meridian-Launcher.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Project Meridian Launcher"; Filename: "{app}\Project-Meridian-Launcher.exe"
Name: "{autodesktop}\Project Meridian Launcher"; Filename: "{app}\Project-Meridian-Launcher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Project-Meridian-Launcher.exe"; Description: "Запустить Project Meridian Launcher"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\app.previous"
Type: filesandordirs; Name: "{app}\app.failed-*"
Type: files; Name: "{app}\app.update-pending"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if DirExists(ExpandConstant('{app}\instance')) or FileExists(ExpandConstant('{app}\state.json')) then
    Result := 'Выберите отдельную папку для программы. Здесь находятся данные Minecraft.';
end;
