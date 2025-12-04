# -*- coding: utf-8 -*-
"""
Script de entrada para cx_Freeze
Configura el entorno antes de ejecutar main.py
"""
import os
import sys

# Agregar el directorio del ejecutable al PATH (crítico para DLLs)
if getattr(sys, 'frozen', False):
    # Estamos ejecutando desde el ejecutable compilado
    exe_dir = os.path.dirname(sys.executable)

    # Agregar directorio del ejecutable al PATH
    os.environ['PATH'] = exe_dir + os.pathsep + os.environ.get('PATH', '')

    # Configurar variables de entorno para GDAL/PROJ (crítico)
    gdal_data = os.path.join(exe_dir, 'Library', 'share', 'gdal')
    proj_lib = os.path.join(exe_dir, 'Library', 'share', 'proj')

    if os.path.exists(gdal_data):
        os.environ['GDAL_DATA'] = gdal_data

    if os.path.exists(proj_lib):
        os.environ['PROJ_LIB'] = proj_lib

    # Configurar RTREE para que encuentre spatialindex_c-64.dll (CRÍTICO)
    # Nombre correcto según rtree/finder.py línea 19
    os.environ['SPATIALINDEX_C_LIBRARY'] = exe_dir

    # Agregar directorio lib si existe
    lib_dir = os.path.join(exe_dir, 'lib')
    if os.path.exists(lib_dir):
        os.environ['PATH'] = lib_dir + os.pathsep + os.environ['PATH']

    # Agregar directorio del ejecutable al sys.path (donde está src como subdirectorio)
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)

# Ahora importar y ejecutar main.py
if getattr(sys, 'frozen', False):
    # En ejecutable compilado, main.py está en el directorio del ejecutable
    exe_dir = os.path.dirname(sys.executable)
    main_py_path = os.path.join(exe_dir, 'main.py')

    # Ejecutar main.py
    with open(main_py_path, 'r', encoding='utf-8') as f:
        code = compile(f.read(), main_py_path, 'exec')
        exec(code)
else:
    # En desarrollo, importar desde ubicación original
    exec(open(r'C:\WSL\04-CAF\CODES\main.py', encoding='utf-8').read())
