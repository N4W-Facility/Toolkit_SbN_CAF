@echo off
echo Reemplazando archivos CSV de barreras...
echo.
echo IMPORTANTE: Cierra Excel y cualquier editor que tenga los archivos CSV abiertos antes de continuar.
echo.
pause

cd /d "%~dp0src\locales"

if exist "Barries_es_new.csv" (
    del /f "Barries_es.csv" 2>nul
    rename "Barries_es_new.csv" "Barries_es.csv"
    echo - Barries_es.csv actualizado
)

if exist "Barries_en_new.csv" (
    del /f "Barries_en.csv" 2>nul
    rename "Barries_en_new.csv" "Barries_en.csv"
    echo - Barries_en.csv actualizado
)

if exist "Barries_pt_new.csv" (
    del /f "Barries_pt.csv" 2>nul
    rename "Barries_pt_new.csv" "Barries_pt.csv"
    echo - Barries_pt.csv actualizado
)

echo.
echo Archivos actualizados exitosamente!
pause
