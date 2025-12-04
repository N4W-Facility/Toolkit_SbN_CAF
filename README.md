# Toolkit SbN CAF - Nature-based Solutions Assessment Tool

## Descripción

El **Toolkit SbN CAF** es una herramienta de escritorio desarrollada para evaluar y priorizar soluciones basadas en naturaleza orientadas a mejorar la seguridad hídrica en cuencas hidrográficas.

### Características principales:
- **Análisis de cuencas hidrográficas**: Delimitación y caracterización de áreas de interés
- **Evaluación de seguridad hídrica**: Análisis de indicadores de disponibilidad, calidad y riesgo
- **Priorización de SbN**: Herramientas para identificar y priorizar soluciones basadas en naturaleza
- **Análisis de barreras**: Identificación de obstáculos para la implementación de SbN
- **Generación de reportes**: Exportación de resultados en múltiples formatos
- **Interfaz multiidioma**: Soporte para español, inglés y portugués

---

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración del Entorno](#configuración-del-entorno)
3. [Proceso de Compilación](#proceso-de-compilación)
4. [Creación del Instalador con Inno Setup](#creación-del-instalador-con-inno-setup)
5. [Troubleshooting](#troubleshooting)
6. [Estructura del Proyecto](#estructura-del-proyecto)
7. [Configuración de Archivos de Localización y Datos](#configuración-de-archivos-de-localización-y-datos)

---

## Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Conda o Miniconda**: Gestor de entornos y paquetes de Python
  - Descarga Miniconda: [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html)
- **Sistema Operativo**: Windows 10 o superior
- **Espacio en disco**: Mínimo 5 GB libres para el entorno y compilación
- **Git** (opcional): Para clonar el repositorio

---

## Configuración del Entorno

### 1. Clonar o descargar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd CODES
```

### 2. Crear el entorno Conda

El proyecto incluye el archivo `N4W_CAF_EnvPython.yml` con todas las dependencias necesarias.

```bash
conda env create -f N4W_CAF_EnvPython.yml
```

Este comando creará un entorno llamado **`N4W_CAF`** con:
- Python 3.8
- Librerías geoespaciales (GDAL, Geopandas, Rasterio, Shapely, Fiona)
- Librerías de análisis (Pandas, NumPy, SciPy, Scikit-learn)
- Librerías de visualización (Matplotlib, Folium, Contextily)
- Librerías de interfaz gráfica (CustomTkinter, CTkToolTip)
- Herramientas de compilación (cx_Freeze, PyInstaller)

### 3. Activar el entorno

```bash
conda activate N4W_CAF
```

### 4. Verificar la instalación

```bash
python --version
# Debe mostrar: Python 3.8.20

python -c "import geopandas; import rasterio; import customtkinter; print('Entorno configurado correctamente')"
```

---

## Proceso de Compilación

La aplicación se compila usando **cx_Freeze**, que genera un ejecutable standalone para Windows.

### Configuración de Rutas Personalizadas

**IMPORTANTE**: Antes de compilar, debes ajustar las rutas según tu sistema.

#### A. Archivo `Compilacion/cxFreeze/setup_cxfreeze.py`

Abre el archivo y modifica las siguientes líneas:

**Línea 11** - Ruta del entorno Conda:
```python
conda_env = r'C:\Users\TU_USUARIO\miniconda3\envs\N4W_CAF'
```
Reemplaza `TU_USUARIO` con tu nombre de usuario de Windows. Si usas Anaconda en lugar de Miniconda, la ruta sería:
```python
conda_env = r'C:\Users\TU_USUARIO\anaconda3\envs\N4W_CAF'
```

**Línea 14** - Ruta del script principal:
```python
main_script = r'C:\TU_RUTA\CODES\Compilacion\cxFreeze\main_freeze.py'
```
Reemplaza `TU_RUTA` con la ubicación donde clonaste el repositorio.

**Línea 15** - Directorio del proyecto:
```python
codes_dir = r'C:\TU_RUTA\CODES'
```

**Líneas 84-92** - Rutas de archivos de datos (ajustar solo si cambiaste la estructura):
```python
include_files = [
    (r'C:\TU_RUTA\CODES\src', 'src'),
    (r'C:\TU_RUTA\CODES\main.py', 'main.py'),
]

data_dirs = [
    (os.path.join(codes_dir, 'src', 'icons'), 'icons'),
    (os.path.join(codes_dir, 'src', 'locales'), 'locales'),
    (os.path.join(codes_dir, 'src', 'utilities', 'indicators'), os.path.join('utilities', 'indicators')),
]
```

#### B. Archivo `Compilacion/cxFreeze/Compiler_SbN_Tool_cxFreeze.bat`

**Líneas 14-15** - Ruta de conda.exe (si conda no está en el PATH):
```batch
if exist "C:\Users\TU_USUARIO\miniconda3\Scripts\conda.exe" (
    call "C:\Users\TU_USUARIO\miniconda3\Scripts\activate.bat" "C:\Users\TU_USUARIO\miniconda3\envs\N4W_CAF"
```
Reemplaza `TU_USUARIO` con tu nombre de usuario.

**Línea 24** - Nombre del entorno (solo si lo cambiaste):
```batch
call conda activate N4W_CAF
```

### Ejecutar la Compilación

1. Abre **Anaconda Prompt** o **Command Prompt**

2. Navega al directorio de compilación:
```bash
cd C:\TU_RUTA\CODES\Compilacion\cxFreeze
```

3. Ejecuta el script de compilación:
```bash
Compiler_SbN_Tool_cxFreeze.bat
```

4. El proceso tomará entre **5-15 minutos** y mostrará:
   - Activación del entorno
   - Recolección de dependencias
   - Copia de DLLs geoespaciales
   - Creación del ejecutable

5. El ejecutable final se ubicará en:
```
CODES\Compilacion\dist_cxfreeze\Toolkit_SbN\Toolkit_SbN.exe
```

### Tamaño Esperado

- Ejecutable: ~50-100 MB
- Carpeta completa con dependencias: ~1.5-2 GB

---

## Creación del Instalador con Inno Setup

Después de compilar la aplicación con cx_Freeze, puedes crear un instalador profesional para distribuir la aplicación a los usuarios finales.

### Requisito Previo

**Inno Setup 6.0 o superior**: Herramienta para crear instaladores de Windows

- Descarga desde: [https://jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
- Instala con las opciones por defecto

### Configuración de Rutas en InnoSetup

Antes de crear el instalador, debes ajustar las rutas en dos archivos:

#### A. Archivo `Compilacion/cxFreeze/Toolkit_SbN_Installer.iss`

**Línea 30** - Directorio de salida del instalador:
```pascal
OutputDir=C:\TU_RUTA\CODES\Compilacion\InnoSetup_Output
```

**Línea 64** - Ruta de los archivos compilados:
```pascal
Source: "C:\TU_RUTA\CODES\Compilacion\dist_cxfreeze\Toolkit_SbN\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```

**Opcional - Línea 34** - Icono del instalador (si tienes uno):
```pascal
SetupIconFile=C:\TU_RUTA\CODES\src\icons\app_icon.ico
```

#### B. Archivo `Compilacion/cxFreeze/Crear_Instalador.bat`

**Línea 11** - Ruta de Inno Setup Compiler (si está en otra ubicación):
```batch
set INNO_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

**Línea 35** - Directorio de salida:
```batch
if not exist "C:\TU_RUTA\CODES\Compilacion\InnoSetup_Output" (
    mkdir "C:\TU_RUTA\CODES\Compilacion\InnoSetup_Output"
)
```

### Crear el Instalador

1. Asegúrate de haber compilado la aplicación con cx_Freeze primero (debe existir `dist_cxfreeze/Toolkit_SbN/Toolkit_SbN.exe`)

2. Navega al directorio de compilación:
```bash
cd C:\TU_RUTA\CODES\Compilacion\cxFreeze
```

3. Ejecuta el script de creación del instalador:
```bash
Crear_Instalador.bat
```

4. El proceso tomará **2-5 minutos** y creará un instalador comprimido

5. El instalador final se ubicará en:
```
CODES\Compilacion\InnoSetup_Output\Toolkit_SbN_Setup_v1.0.0.0.exe
```

### Características del Instalador

El instalador incluye:
- ✅ Instalación guiada con interfaz moderna
- ✅ Soporte multiidioma (Español e Inglés)
- ✅ Creación automática de accesos directos en:
  - Menú Inicio
  - Escritorio (opcional)
- ✅ Desinstalador automático
- ✅ Entrada en "Programas y características" de Windows
- ✅ Detección de versiones anteriores instaladas
- ✅ Compresión LZMA2 para reducir tamaño del instalador

### Tamaño del Instalador

- Instalador comprimido: ~300-500 MB
- Aplicación instalada: ~1.5-2 GB

### Distribución

El archivo `.exe` del instalador puede ser distribuido directamente a los usuarios:
- Puede ejecutarse sin necesidad de instalar Python o Conda
- Funciona en cualquier Windows 10 o superior de 64 bits
- Los usuarios solo necesitan ejecutar el instalador y seguir las instrucciones

---

## Troubleshooting

### Error: "conda no reconocido como comando"

**Solución**:
- Ejecuta desde **Anaconda Prompt** en lugar de Command Prompt normal
- O agrega Conda al PATH del sistema

### Error: "cx_Freeze no está instalado"

**Solución**:
```bash
conda activate N4W_CAF
pip install cx_Freeze
```

### Error: "No se encuentra el archivo setup_cxfreeze.py"

**Solución**: Asegúrate de estar en el directorio correcto:
```bash
cd C:\TU_RUTA\CODES\Compilacion\cxFreeze
```

### Error: "No module named 'src'"

**Solución**: Verifica que las rutas en `setup_cxfreeze.py` líneas 84-92 sean correctas y que la carpeta `src` exista.

### El ejecutable no inicia o da error de DLL

**Solución**:
- Verifica que la línea 11 de `setup_cxfreeze.py` apunte al entorno Conda correcto
- Asegúrate de que el entorno `N4W_CAF` esté completamente instalado

### Error: "FileNotFoundError" al ejecutar el .exe

**Solución**: Algunos archivos de datos no se copiaron correctamente. Revisa las rutas en `setup_cxfreeze.py` líneas 90-92.

### El ejecutable es detectado como virus por el antivirus

**Solución**: Esto es un falso positivo común con ejecutables generados por cx_Freeze. Puedes:
- Agregar el archivo a las excepciones del antivirus
- cx_Freeze tiene menos detecciones que PyInstaller

### Error: "No se encuentra Inno Setup"

**Solución**:
- Descarga e instala Inno Setup 6 desde [https://jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
- Verifica la ruta en `Crear_Instalador.bat` línea 11

### Error: "No se encuentra la compilación de cx_Freeze"

**Solución**: Debes compilar primero con cx_Freeze antes de crear el instalador:
```bash
cd Compilacion\cxFreeze
Compiler_SbN_Tool_cxFreeze.bat
```

### El instalador falla al ejecutarse

**Solución**:
- Verifica que las rutas en `Toolkit_SbN_Installer.iss` sean correctas (líneas 30 y 64)
- Asegúrate de que la carpeta `dist_cxfreeze\Toolkit_SbN` exista y tenga todos los archivos

---

## Estructura del Proyecto

```
CODES/
├── main.py                          # Punto de entrada principal
├── N4W_CAF_EnvPython.yml           # Archivo de entorno Conda
├── src/                            # Código fuente
│   ├── components/                 # Componentes reutilizables
│   ├── core/                       # Núcleo de la aplicación
│   ├── icons/                      # Iconos e imágenes
│   ├── locales/                    # Archivos de traducción
│   ├── reports/                    # Generación de reportes
│   ├── utilities/                  # Utilidades y herramientas
│   ├── utils/                      # Funciones auxiliares
│   └── windows/                    # Ventanas de la interfaz
└── Compilacion/
    └── cxFreeze/
        ├── setup_cxfreeze.py       # Configuración de compilación
        ├── Compiler_SbN_Tool_cxFreeze.bat  # Script de compilación
        ├── main_freeze.py          # Wrapper para ejecutable
        └── init_script.py          # Script de inicialización
```

---

## Configuración de Archivos de Localización y Datos

La carpeta `src/locales/` contiene todos los archivos de configuración, textos y datos que utiliza la herramienta. Estos archivos permiten personalizar el contenido sin modificar el código fuente de la aplicación.

### Archivos Multiidioma

La aplicación soporta tres idiomas: **Español (es)**, **Inglés (en)** y **Portugués (pt)**.

#### 1. Taxonomía CAF (`Taxonomia_CAF_*.csv`)

**Archivos:**
- `Taxonomia_CAF_es.csv` (Español)
- `Taxonomia_CAF_en.csv` (Inglés)
- `Taxonomia_CAF_pt.csv` (Portugués)

**Descripción:** Contiene la estructura completa de la taxonomía CAF de Soluciones basadas en Naturaleza.

**Estructura del archivo:**
```csv
ID,Categoria,Subcategoria,Actividad,Objetivo
1,A.1. Gestión y Suministro de Agua,A.1.1. Medidas...,A.1.1.1. Mejora de...,A. Adaptación...
```

**⚠️ IMPORTANTE al modificar:**
- **Conservar la estructura de columnas**: `ID`, `Categoria`, `Subcategoria`, `Actividad`, `Objetivo`
- **Mantener los IDs numéricos** en la primera columna
- **No alterar el orden de las columnas**
- Si se agrega una nueva taxonomía, agregar nuevas filas con IDs consecutivos
- Los cambios deben replicarse en los **tres idiomas** (es, en, pt)

#### 2. Barreras (`Barries_*.csv`)

**Archivos:**
- `Barries_es.csv` (Español)
- `Barries_en.csv` (Inglés)
- `Barries_pt.csv` (Portugués)

**Descripción:** Define las barreras para la implementación de SbN.

**Estructura del archivo:**
```csv
Codigo_Barrera,Descripcion,Subcategoria,Grupo,Codigo_Grupo
GB0101b,La coordinación entre...,Desconexión entre...,Barreras políticas,GB01
```

**⚠️ IMPORTANTE al modificar:**
- **Conservar la estructura**: `Codigo_Barrera`, `Descripcion`, `Subcategoria`, `Grupo`, `Codigo_Grupo`
- **No modificar los códigos** (`Codigo_Barrera`) de barreras existentes
- Los códigos deben ser únicos y seguir el formato `GBXXXX`
- Mantener consistencia en los **tres idiomas**

#### 3. Tooltips de Desafíos (`TooltipsChallenges_*.csv`)

**Archivos:**
- `TooltipsChallenges_es.csv` (Español)
- `TooltipsChallenges_en.csv` (Inglés)
- `TooltipsChallenges_pt.csv` (Portugués)

**Descripción:** Textos de ayuda (tooltips) que se muestran en la interfaz para los diferentes desafíos.

**⚠️ IMPORTANTE al modificar:**
- Conservar la estructura de columnas del archivo original
- Los cambios deben replicarse en los **tres idiomas**

#### 4. Indicadores (`Indicator_*.csv`)

**Archivos:**
- `Indicator_es.csv` (Español)
- `Indicator_en.csv` (Inglés)
- `Indicator_pt.csv` (Portugués)

**Descripción:** Define los indicadores priorizados para cada tipo de SbN.

**Estructura del archivo:**
```csv
id,SbN,Indicadores priorizados,Unidad de medida
8,Área de filtro verde,Carga de sedimentos...,t/año
```

**⚠️ IMPORTANTE al modificar:**
- **Conservar la estructura**: `id`, `SbN`, `Indicadores priorizados`, `Unidad de medida`
- El `id` debe coincidir entre idiomas para el mismo tipo de SbN
- Mantener consistencia en las unidades de medida

#### 5. Fichas de SbN (`Fichas_SbN_*.xlsx`)

**Archivos:**
- `Fichas_SbN_es.xlsx` (Español)
- `Fichas_SbN_en.xlsx` (Inglés)
- `Fichas_SbN_pt.xlsx` (Portugués)

**Descripción:** Archivos Excel con información detallada de cada tipo de Solución basada en Naturaleza, incluyendo descripción, beneficios, implementación, etc.

**⚠️ IMPORTANTE al modificar:**
- **No cambiar el nombre de las hojas** (sheets) del Excel
- **Conservar la estructura de las tablas** (encabezados, columnas)
- Los cambios deben replicarse en los **tres idiomas**
- Mantener el formato de celdas (estilos, colores) si es relevante para la aplicación

#### 6. Archivos JSON de Traducción (`*.json`)

**Archivos:**
- `es.json` (Español)
- `en.json` (Inglés)
- `pt.json` (Portugués)

**Descripción:** Contienen **todos los textos de la interfaz** de la aplicación (botones, etiquetas, mensajes, títulos de ventanas, etc.).

**Ejemplo de estructura:**
```json
{
  "app_title": "Toolkit - SbN para Seguridad Hídrica",
  "button_start": "Iniciar",
  "message_welcome": "Bienvenido a la herramienta",
  ...
}
```

**⚠️ IMPORTANTE al modificar:**
- **NO cambiar las claves** (keys) del JSON, solo los valores (values)
- Ejemplo correcto:
  ```json
  "button_start": "Comenzar"  ✅ (solo cambió el valor)
  ```
- Ejemplo incorrecto:
  ```json
  "boton_iniciar": "Comenzar"  ❌ (cambió la clave)
  ```
- Respetar el formato JSON (comillas, comas, llaves)
- Los cambios deben replicarse en los **tres idiomas**
- Usar codificación UTF-8 para caracteres especiales

#### 7. Árbol de Taxonomía JSON (`CAF_taxonomy_tree_*.json`)

**Archivos:**
- `CAF_taxonomy_tree_es.json` (Español)
- `CAF_taxonomy_tree_en.json` (Inglés)
- `CAF_taxonomy_tree_pt.json` (Portugués)

**Descripción:** Representación jerárquica de la taxonomía CAF en formato JSON para visualización en árbol.

**⚠️ IMPORTANTE al modificar:**
- Mantener la estructura jerárquica del JSON
- Los IDs deben coincidir con los de `Taxonomia_CAF_*.csv`

### Otros Archivos de Configuración

#### `SbN_Prioritization.csv` y `SbN_Weights.csv`
Archivos de configuración para el sistema de priorización de SbN. Modificar con precaución.

#### `Weight_Matrix.xlsx`
Matriz de pesos para cálculos de priorización.

#### `InfoDataBase_Other.pdf` y `InfoDataBase_WS.pdf`
Documentación sobre las bases de datos utilizadas por la herramienta.

---

### Recomendaciones Generales

1. **Siempre hacer backup**: Antes de modificar cualquier archivo, crear una copia de seguridad
2. **Probar después de modificar**: Ejecutar la aplicación después de cada cambio
3. **Codificación UTF-8**: Guardar todos los archivos CSV y JSON con codificación UTF-8 (con BOM para CSV)
4. **Consistencia multiidioma**: Cualquier cambio debe aplicarse a los tres idiomas
5. **Validar formato**: Verificar que los archivos CSV no tengan columnas faltantes o IDs duplicados
6. **No usar Excel para CSV**: Preferir editores de texto o herramientas especializadas para evitar problemas de formato

---

## Licencia

Este proyecto está licenciado bajo **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

### ¿Qué significa esto?

Usted es libre de:
- **Compartir**: Copiar y redistribuir el material en cualquier medio o formato
- **Adaptar**: Remezclar, transformar y construir a partir del material para cualquier propósito, incluso comercialmente

Bajo los siguientes términos:
- **Atribución**: Debe dar crédito de manera adecuada, brindar un enlace a la licencia, e indicar si se han realizado cambios. Puede hacerlo en cualquier forma razonable, pero no de forma tal que sugiera que usted o su uso tienen el apoyo del licenciante.

### Cómo citar este trabajo

```
Toolkit SbN CAF - Nature-based Solutions Assessment Tool for Water Security
Desarrollado por: The Nature Conservancy y CAF - Banco de Desarrollo de América Latina y el Caribe
Año: 2025
Licencia: CC BY 4.0
```

### Texto completo de la licencia

Para ver una copia de esta licencia, visite: [https://creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/)
