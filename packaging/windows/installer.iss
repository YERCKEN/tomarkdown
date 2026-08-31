; Instalador de ToMarkdown para Windows (Inno Setup 6).
;
; La version entra por linea de comando:
;   ISCC /DAppVersion=1.2.3 packaging\windows\installer.iss
;
; Payload: dist\ToMarkdown.exe, el onefile que arma PyInstaller. El zip portable
; de ese mismo .exe se sigue publicando aparte; este instalador es adicional.
; Las rutas son relativas a este archivo (packaging\windows\).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "ToMarkdown"
#define AppPublisher "YERCKEN"
#define AppExeName "ToMarkdown.exe"
#define AppUrl "https://github.com/YERCKEN/tomarkdown"

[Setup]
AppId={{9195F4F7-F57C-4CCD-935A-734E6716DDFB}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\..\dist
OutputBaseFilename=ToMarkdown-Setup-{#AppVersion}
SetupIconFile=..\..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
