# Creación de Instalador para Toolkit SbN

Este directorio contiene los archivos necesarios para crear un instalador de Windows para el Toolkit - SbN para Seguridad Hídrica.

## Proceso Completo

### Paso 1: Compilar la aplicación con cx_Freeze

```batch
.\Compiler_SbN_Tool_cxFreeze.bat
```

Esto crea la carpeta `dist_cxfreeze\Toolkit_SbN` con todos los archivos necesarios.

### Paso 2: Instalar Inno Setup

Si aún no lo tienes instalado:

1. Descargar Inno Setup 6 desde: https://jrsoftware.org/isdl.php
2. Ejecutar el instalador
3. Aceptar la ubicación por defecto: `C:\Program Files (x86)\Inno Setup 6\`

### Paso 3: Crear el instalador

```batch
.\Crear_Instalador.bat
```

Esto genera el archivo instalador en:
```
C:\WSL\04-CAF\CODES\Compilacion\InnoSetup_Output\Toolkit_SbN_Setup_v1.0.0.0.exe
```

## ¿Qué hace el instalador?

El instalador creado:

✅ Instala la aplicación en `C:\Program Files\SbN_CAF_Toolkit\`
✅ Crea acceso directo en el menú inicio
✅ Crea acceso directo en el escritorio (opcional)
✅ Agrega entrada en "Programas y características"
✅ Incluye desinstalador automático
✅ Verifica versiones anteriores
✅ Requiere permisos de administrador

## Distribución

El archivo `Toolkit_SbN_Setup_v1.0.0.0.exe` es el único archivo que necesitas distribuir.

Los usuarios solo deben:
1. Ejecutar el instalador
2. Seguir el asistente
3. La aplicación quedará instalada profesionalmente

## Personalización

Puedes modificar `Toolkit_SbN_Installer.iss` para:

- Cambiar la versión (línea 7)
- Agregar un icono personalizado (línea 28)
- Agregar archivo de licencia (línea 44)
- Cambiar directorio de instalación (línea 20)
- Modificar mensajes del instalador

## Notas Importantes

- El instalador tiene **menos detección de antivirus** que PyInstaller
- cx_Freeze + Inno Setup es una combinación profesional y confiable
- El instalador es compatible con Windows 10/11 de 64 bits
- Tamaño aproximado del instalador: 300-500 MB (dependiendo de las dependencias)

## Solución de Problemas

**Error: "Inno Setup no encontrado"**
- Verifica que Inno Setup esté instalado en `C:\Program Files (x86)\Inno Setup 6\`
- O actualiza la ruta en `Crear_Instalador.bat` línea 12

**Error: "Compilación de cx_Freeze no encontrada"**
- Primero ejecuta `Compiler_SbN_Tool_cxFreeze.bat`
- Verifica que exista `dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe`

**El instalador no aparece**
- Revisa la carpeta `InnoSetup_Output`
- Verifica los mensajes de error en la consola
