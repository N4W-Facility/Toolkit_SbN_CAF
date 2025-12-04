@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo  Toolkit - SbN para Seguridad Hidrica
echo  Compilador con cx_Freeze
echo ========================================
echo.

REM Verificar si conda está disponible
where conda >nul 2>&1
if errorlevel 1 (
    echo Intentando activar conda desde ruta base...
    if exist "C:\Users\jonathan.nogales\miniconda3\Scripts\conda.exe" (
        call "C:\Users\jonathan.nogales\miniconda3\Scripts\activate.bat" "C:\Users\jonathan.nogales\miniconda3\envs\N4W_CAF"
    ) else (
        echo ERROR: No se puede encontrar conda
        echo Asegurate de que conda este en el PATH o ejecuta desde Anaconda Prompt
        pause
        exit /b 1
    )
) else (
    echo Activando entorno N4W_CAF...
    call conda activate N4W_CAF
)

REM Verificar que cx_Freeze esté disponible
python -c "import cx_Freeze" 2>nul
if errorlevel 1 (
    echo ERROR: cx_Freeze no está instalado en el entorno
    echo Instalando cx_Freeze...
    pip install cx_Freeze
)

REM Limpiar compilaciones anteriores
echo.
echo Limpiando archivos anteriores...
if exist "build" rmdir /s /q "build"
if exist "..\dist_cxfreeze" rmdir /s /q "..\dist_cxfreeze"

echo.
echo ========================================
echo Iniciando compilacion con cx_Freeze...
echo ========================================
echo.
echo NOTA: Esta compilacion se configura para:
echo   - Incluir todos los modulos geoespaciales
echo   - Incluir DLLs de GDAL/PROJ/GEOS
echo   - Menos deteccion de antivirus que PyInstaller
echo   - Compilacion rapida (5-15 minutos)
echo.

REM Verificar que el archivo setup existe
if not exist "setup_cxfreeze.py" (
    echo ERROR: No se encuentra el archivo setup_cxfreeze.py
    echo Asegurate de que el archivo este en el directorio actual
    pause
    exit /b 1
)

REM Ejecutar cx_Freeze
echo Compilando...
echo.
python setup_cxfreeze.py build

echo.
REM Detectar carpeta de build (puede ser 3.8, 3.9, 3.10, 3.11, etc.)
for /d %%i in ("build\exe.*") do set BUILD_DIR=%%i

if exist "%BUILD_DIR%\Toolkit_SbN.exe" (
    echo ========================================
    echo  COMPILACION EXITOSA!
    echo ========================================
    echo.
    echo Carpeta de build detectada: %BUILD_DIR%
    echo Moviendo ejecutable a carpeta dist_cxfreeze...
    if not exist "..\dist_cxfreeze" mkdir "..\dist_cxfreeze"
    xcopy "%BUILD_DIR%" "..\dist_cxfreeze\Toolkit_SbN" /E /I /Y >nul

    echo  Ejecutable creado en: ..\dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe
    echo.
    echo  Tamaño:
    dir "..\dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe" | find "Toolkit_SbN.exe"
    echo ========================================
    echo.
    echo NOTA: cx_Freeze tiene MENOS deteccion de antivirus que PyInstaller
    echo       porque es menos popular entre distribuidores de malware.
    echo.
    echo ¿Deseas ejecutar el programa compilado? (s/n)
    set /p ejecutar=
    if /i "!ejecutar!"=="s" (
        start "" "..\dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe"
    )
) else (
    echo ========================================
    echo  ERROR EN LA COMPILACION
    echo  Revisa los mensajes anteriores
    echo ========================================
    echo.
    echo Buscando ejecutable en otras ubicaciones...
    dir /s /b build\*.exe | find "Toolkit_SbN.exe"
    echo.
    echo Posibles soluciones:
    echo 1. Ejecutar desde Anaconda Prompt
    echo 2. Verificar que todas las dependencias estén instaladas
    echo 3. Ejecutar: pip install cx_Freeze
    echo 4. Revisar el archivo setup_cxfreeze.py
    echo.
)

echo.
echo Presiona cualquier tecla para continuar...
pause >nul
