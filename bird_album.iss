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
UninstallDisplayName={#MyAppName}
; 版本资源：安装包 exe 的「属性 → 详细信息」。默认只有产品名称/产品版本，
; FileVersion 是空的；代码签名（SignPath）的 artifact configuration 会校验
; 这些元数据，所以显式写全，见项目记忆第 8 节。
VersionInfoVersion={#MyAppVersion}.0
VersionInfoTextVersion={#MyAppVersion}.0
VersionInfoProductVersion={#MyAppVersion}.0
VersionInfoProductTextVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoCopyright=GPL-3.0
; 用户数据（数据库 / 照片 / 设置）由程序首次启动时自行创建于
; %APPDATA%\BirdAlbum，卸载时保留，不使用 [Dirs] 预建该目录：
; 管理员模式安装时 {userappdata} 指向的是被提升的账户而非当前用户，
; 会把目录建到错误的用户配置下（Inno 也会因此报 UsedUserAreasWarning）。

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; GPL-3.0 要求分发时附带许可证全文（PySide6 / Qt 另适用 LGPLv3）
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载{#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动{#MyAppName}"; Flags: nowait postinstall skipifsilent
