; 鸟类相册 Windows 安装脚本（Inno Setup 6）
; 编译：ISCC.exe bird_album.iss

#define MyAppName "鸟类相册"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "BirdAlbum"
#define MyAppExeName "鸟类相册.exe"

[Setup]
AppId={{8B2E9C4A-5F3D-4A1B-9C2E-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 用户数据（数据库/照片）存放于 %APPDATA%\BirdAlbum，卸载时保留
UninstallDisplayName={#MyAppName}

[Dirs]
Name: "{userappdata}\BirdAlbum"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载{#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动{#MyAppName}"; Flags: nowait postinstall skipifsilent
