; Script de Inno Setup para SbN CAF Toolkit
; Crea un instalador profesional para Windows
; Requiere Inno Setup 6.0 o superior: https://jrsoftware.org/isdl.php

#define MyAppName "Toolkit - SbN para Seguridad Hídrica"
#define MyAppVersion "1.0.0.0"
#define MyAppPublisher "The Nature Conservancy - Nature For Water Facility"
#define MyAppURL "https://www.nature.org/"
#define MyAppExeName "Toolkit_SbN.exe"
#define MyAppYear "2025"

[Setup]
; Información de la aplicación
AppId={{A8B9C1D2-E3F4-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) {#MyAppYear} {#MyAppPublisher}. All rights reserved.

; Directorios de instalación
DefaultDirName={autopf}\SbN_CAF_Toolkit
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Directorio de salida del instalador
OutputDir=C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output
OutputBaseFilename=Toolkit_SbN_Setup_v{#MyAppVersion}

; Icono del instalador (opcional - puedes agregar un icono .ico aquí)
;SetupIconFile=C:\WSL\04-CAF\CODES\src\icons\app_icon.ico

; Compresión
Compression=lzma2/max
SolidCompression=yes

; Requiere privilegios de administrador
PrivilegesRequired=admin

; Arquitectura
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Apariencia del instalador
WizardStyle=modern
DisableWelcomePage=no
LicenseFile=

; Idioma
ShowLanguageDialog=auto

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Incluir TODA la carpeta compilada de cx_Freeze
Source: "C:\WSL\04-CAF\CODES\Compilacion\dist_cxfreeze\Toolkit_SbN\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: Esto incluye el .exe, todos los DLLs, lib/, Library/, src/, y todos los demás archivos

[Icons]
; Acceso directo en el menú inicio
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Herramienta de Evaluación de Soluciones Basadas en la Naturaleza para Seguridad Hídrica"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

; Acceso directo en el escritorio (opcional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Opción de ejecutar la aplicación al finalizar la instalación
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpiar archivos creados por la aplicación durante el uso
Type: filesandordirs; Name: "{userappdata}\SbN_CAF_Toolkit"
Type: filesandordirs; Name: "{localappdata}\SbN_CAF_Toolkit"

[Code]
// Función para verificar si hay una versión anterior instalada
function InitializeSetup(): Boolean;
var
  OldPath: String;
begin
  Result := True;
  // Verificar si existe una instalación previa
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A8B9C1D2-E3F4-5678-9ABC-DEF012345678}_is1', 'InstallLocation', OldPath) then
  begin
    if MsgBox('Se detectó una versión anterior de ' + ExpandConstant('{#MyAppName}') + '.' + #13#10#13#10 +
              'Se recomienda desinstalarla antes de continuar.' + #13#10#13#10 +
              '¿Desea continuar de todos modos?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

// Función para mostrar información al finalizar
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Aquí puedes agregar acciones post-instalación si es necesario
  end;
end;
