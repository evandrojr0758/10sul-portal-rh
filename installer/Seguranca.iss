#define AppVersion "1.0.0"
[Setup]
AppId={{6FF1A8AA-9750-414F-8498-3BD6A39083DA}
AppName=10 SUL - Portal da Seguranca
AppVersion={#AppVersion}
AppPublisher=Evandro Junior
DefaultDirName={localappdata}\Programs\10SulSeguranca
DefaultGroupName=10 SUL
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Instalar_10Sul_Seguranca_1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\10SulSeguranca.exe
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "..\dist\10SulSeguranca\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autodesktop}\10 SUL - Seguranca"; Filename: "{app}\10SulSeguranca.exe"
Name: "{group}\10 SUL - Seguranca"; Filename: "{app}\10SulSeguranca.exe"
[Run]
Filename: "{app}\10SulSeguranca.exe"; Description: "Abrir Portal da Seguranca"; Flags: nowait postinstall skipifsilent
