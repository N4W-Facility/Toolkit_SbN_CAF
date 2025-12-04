@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo  Toolkit - SbN para Seguridad Hidrica
echo  Creador de Instalador con Inno Setup
echo ========================================
echo.

REM Verificar que Inno Setup esté instalado
set INNO_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_COMPILER% (
    echo ERROR: No se encuentra Inno Setup en la ruta esperada.
    echo.
    echo Por favor, instala Inno Setup 6 desde:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo O actualiza la ruta en este script si esta instalado en otra ubicacion.
    pause
    exit /b 1
)

REM Verificar que existe la compilacion de cx_Freeze
if not exist "..\dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe" (
    echo ERROR: No se encuentra la compilacion de cx_Freeze.
    echo.
    echo Primero debes compilar la aplicacion con cx_Freeze ejecutando:
    echo   Compiler_SbN_Tool_cxFreeze.bat
    echo.
    pause
    exit /b 1
)

REM Crear directorio de salida si no existe
if not exist "C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output" (
    mkdir "C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output"
)

echo.
echo Compilando instalador con Inno Setup...
echo.

REM Compilar el instalador
%INNO_COMPILER% "Toolkit_SbN_Installer.iss"

if errorlevel 1 (
    echo.
    echo ========================================
    echo  ERROR EN LA COMPILACION DEL INSTALADOR
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo  INSTALADOR CREADO EXITOSAMENTE!
echo ========================================
echo.
echo Ubicacion del instalador:
echo   C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output\Toolkit_SbN_Setup_v1.0.0.0.exe
echo.
echo Puedes distribuir este archivo a los usuarios.
echo El instalador incluye:
echo   - Aplicacion completa con todas las dependencias
echo   - Accesos directos en menu inicio y escritorio
echo   - Desinstalador automatico
echo   - Entrada en "Programas y caracteristicas"
echo.
echo ¿Deseas abrir la carpeta del instalador? (s/n)
set /p abrir=
if /i "!abrir!"=="s" (
    explorer "C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output"
)

pause
