@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo  Toolkit - SbN para Seguridad Hidrica
echo ========================================
echo.

REM Verificar si conda está disponible
where conda >nul 2>&1
if errorlevel 1 (
    echo Intentando activar conda desde ruta base...
    if exist "C:\Users\jonathan.nogales\AppData\Local\anaconda3\Scripts\conda.exe" (
        call "C:\Users\jonathan.nogales\AppData\Local\anaconda3\Scripts\activate.bat" "C:\Users\jonathan.nogales\AppData\Local\anaconda3\envs\N4W_CAF"
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

REM Verificar que pyinstaller esté disponible
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller no está instalado en el entorno
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Limpiar compilaciones anteriores
echo Limpiando archivos anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo.
echo ========================================
echo Iniciando compilacion con PyInstaller...
echo ========================================
echo.
echo NOTA: Esta compilacion se configura para:
echo   - Desactivar UPX (sin compresion sospechosa)
echo   - Incluir metadatos de version
echo   - Agregar manifiesto de Windows
echo   - Declarar permisos explicitamente
echo.

REM Verificar que los archivos de configuración existen
if not exist "Toolkit_SbN.spec" (
    echo ERROR: No se encuentra el archivo Toolkit_SbN.spec
    echo Asegurate de que el archivo .spec este en el directorio actual
    pause
    exit /b 1
)

if not exist "version_info.txt" (
    echo ADVERTENCIA: No se encuentra version_info.txt
    echo El ejecutable no tendra metadatos de version
    echo.
)

if not exist "app.manifest" (
    echo ADVERTENCIA: No se encuentra app.manifest
    echo El ejecutable no tendra manifiesto de Windows
    echo.
)

REM Ejecutar PyInstaller usando el archivo .spec
echo Compilando usando Toolkit_SbN.spec...
echo.
pyinstaller --clean Toolkit_SbN.spec

echo.
if exist "dist\Toolkit_SbN\Toolkit_SbN.exe" (
    echo ========================================
    echo  COMPILACION EXITOSA!
    echo ========================================
    echo  Ejecutable creado en: dist\Toolkit_SbN\Toolkit_SbN.exe
    echo.
    echo  Tamaño:
    dir "dist\Toolkit_SbN\Toolkit_SbN.exe" | find "Toolkit_SbN.exe"
    echo ========================================
    echo.
    echo ¿Deseas ejecutar el programa compilado? (s/n)
    set /p ejecutar=
    if /i "!ejecutar!"=="s" (
        start "" "dist\Toolkit_SbN\Toolkit_SbN.exe"
    )
) else (
    echo ========================================
    echo  ERROR EN LA COMPILACION
    echo  Revisa los mensajes anteriores
    echo ========================================
    echo.
    echo Posibles soluciones:
    echo 1. Ejecutar desde Anaconda Prompt
    echo 2. Verificar que todas las dependencias estén instaladas
    echo 3. Verificar que los archivos .spec, version_info.txt y app.manifest existan
    echo 4. Ejecutar: pip install pyinstaller
    echo.
    echo Archivos de configuracion:
    if exist "Toolkit_SbN.spec" (echo   [OK] Toolkit_SbN.spec) else (echo   [X] Toolkit_SbN.spec NO ENCONTRADO)
    if exist "version_info.txt" (echo   [OK] version_info.txt) else (echo   [!] version_info.txt NO ENCONTRADO)
    if exist "app.manifest" (echo   [OK] app.manifest) else (echo   [!] app.manifest NO ENCONTRADO)
)

echo.
echo Presiona cualquier tecla para continuar...
pause >nul
