# -*- coding: utf-8 -*-
"""
Script de inicialización para cx_Freeze
Agrega el directorio del ejecutable al PATH para que los DLLs sean encontrados
"""
import os
import sys

# Agregar el directorio del ejecutable al PATH
if hasattr(sys, 'frozen'):
    exe_dir = os.path.dirname(sys.executable)
    os.environ['PATH'] = exe_dir + os.pathsep + os.environ.get('PATH', '')

    # También agregar subdirectorio lib si existe
    lib_dir = os.path.join(exe_dir, 'lib')
    if os.path.exists(lib_dir):
        os.environ['PATH'] = lib_dir + os.pathsep + os.environ['PATH']
