# -*- coding: utf-8 -*-
"""
Configuración de cx_Freeze para SbN CAF Toolkit
"""
import sys
import os
from cx_Freeze import setup, Executable
import glob

# Rutas
conda_env = r'C:\Users\jonathan.nogales\miniconda3\envs\N4W_CAF'
library_bin = os.path.join(conda_env, 'Library', 'bin')
library_share = os.path.join(conda_env, 'Library', 'share')
main_script = r'C:\WSL\04-CAF\CODES\Compilacion\cxFreeze\main_freeze.py'  # Usar wrapper que configura PATH
codes_dir = r'C:\WSL\04-CAF\CODES'

# Recolectar TODOS los DLLs (igual que PyInstaller)
bin_files = []
if os.path.exists(library_bin):
    # Usar múltiples patrones para asegurar captura completa (como PyInstaller)
    for dll_pattern in ['*.dll', 'gdal*.dll', 'proj_*.dll', 'geos*.dll']:
        dll_files = glob.glob(os.path.join(library_bin, dll_pattern))
        for dll_file in dll_files:
            # Evitar duplicados
            dll_tuple = (dll_file, os.path.basename(dll_file))
            if dll_tuple not in bin_files:
                bin_files.append(dll_tuple)

print(f"Total DLLs encontrados: {len(bin_files)}")

# Paquetes a incluir
packages = [
    'rasterio',
    'geopandas',
    'shapely',
    'pyproj',
    'fiona',
    'osgeo',
    'rtree',  # Índices espaciales (requiere spatialindex_c-64.dll)
    'pysheds',  # Procesamiento hidrológico
    'pandas',
    'numpy',
    'openpyxl',  # Lectura/escritura de archivos Excel
    'tkinter',
    'customtkinter',
    'CTkToolTip',  # Tooltips para customtkinter
    'contextily',
    'folium',  # Mapas interactivos
    'matplotlib',  # Gráficos
    'fpdf',  # Generación de PDFs
    'pypdf',  # Generación de PDFs
    'win32com',  # Interacción con Office/Excel
    'src',  # Incluir src como paquete Python
]

# Módulos a incluir explícitamente (CRÍTICOS para cx_Freeze)
includes = [
    # Módulos fundamentales de Python (CRÍTICO)
    'encodings',
    'encodings.utf_8',
    'encodings.latin_1',
    'encodings.cp1252',
    'encodings.ascii',
    'encodings.idna',
    'encodings.mbcs',
    # Módulos de la aplicación
    'pandas',
    'numpy',
    'tkinter',
    'queue',
    'multiprocessing',
]

# Módulos a excluir (para reducir tamaño)
excludes = [
    'matplotlib.tests',
    'numpy.random._examples',
    'test',
    # NO excluir 'unittest' porque fpdf.sign lo necesita
]

# Archivos de datos a incluir (replicando PyInstaller)
include_files = [
    (r'C:\WSL\04-CAF\CODES\src', 'src'),  # Incluir toda la carpeta src como módulo
    (r'C:\WSL\04-CAF\CODES\main.py', 'main.py'),  # Incluir main.py para que main_freeze.py lo ejecute
]

# Agregar directorios de datos (igual que PyInstaller)
data_dirs = [
    (os.path.join(codes_dir, 'src', 'icons'), 'icons'),
    (os.path.join(codes_dir, 'src', 'locales'), 'locales'),
    (os.path.join(codes_dir, 'src', 'utilities', 'indicators'), os.path.join('utilities', 'indicators')),
]

for src_dir, dest_dir in data_dirs:
    if os.path.exists(src_dir):
        include_files.append((src_dir, dest_dir))
        print(f"Agregando: {src_dir} -> {dest_dir}")
    else:
        print(f"ADVERTENCIA: No existe {src_dir}")

# Agregar Library\share (CRÍTICO para GDAL/PROJ)
if os.path.exists(library_share):
    include_files.append((library_share, os.path.join('Library', 'share')))
    print(f"Agregando Library\\share")
else:
    print("ADVERTENCIA: No existe Library\\share")

# Agregar TODOS los DLLs al final
include_files += bin_files

# Opciones de build (replicando PyInstaller)
build_exe_options = {
    'packages': packages,
    'includes': includes,
    'excludes': excludes,
    'include_files': include_files,
    'optimize': 2,
    'path': sys.path + [r'C:\WSL\04-CAF\CODES'],  # Agregar raíz al path para que encuentre src
    'include_msvcr': True,  # Incluir Microsoft Visual C++ runtime
    'zip_include_packages': [],  # NO comprimir paquetes - descomprimir todo en lib/
    'zip_exclude_packages': ['*'],  # Excluir TODOS de compresión para evitar problemas
}

# Mensaje de resumen
print(f"\n{'='*60}")
print(f"RESUMEN DE CONFIGURACIÓN:")
print(f"{'='*60}")
print(f"Total DLLs a copiar: {len(bin_files)}")
print(f"Total archivos de datos: {len(include_files) - len(bin_files)}")
print(f"Paquetes: {len(packages)}")
print(f"{'='*60}\n")

# Configuración del ejecutable
base = None
if sys.platform == 'win32':
    base = 'Console'  # Usar 'Win32GUI' para ocultar consola

executables = [
    Executable(
        main_script,
        base=base,
        target_name='Toolkit_SbN.exe',
        icon=None,  # Agregar ícono si existe
    )
]

# Setup
setup(
    name='SbN CAF Toolkit',
    version='1.0.0.0',
    description='SbN CAF Toolkit - Nature-based Solutions Assessment Tool for Water Security',
    author='The Nature Conservancy',
    options={'build_exe': build_exe_options},
    executables=executables,
)
