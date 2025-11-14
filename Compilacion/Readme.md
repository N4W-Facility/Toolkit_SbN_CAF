# Guía de Compilación - SbN CAF Toolkit

### Paso 1: Preparar el Entorno
```cmd
# Abrir Anaconda Prompt
# Navegar a la carpeta
cd C:\WSL\04-CAF
```

### Paso 2: Ejecutar el Script de Compilación
```cmd
Compiler_SbN_Tool.bat
```

El script:
- Activará el entorno conda N4W_CAF
- Verificará que PyInstaller esté instalado
- Limpiará compilaciones anteriores
- Compilará usando el archivo `.spec` optimizado
- Mostrará un resumen de mejoras aplicadas

### Paso 3: Probar el Ejecutable
El ejecutable estará en:
```
C:\WSL\04-CAF\dist\Toolkit_SbN\Toolkit_SbN.exe
```