import sys
import os


def get_resource_path(relative_path):
    """
    Obtiene la ruta absoluta a un recurso, funciona tanto en desarrollo como en ejecutable empaquetado.

    Args:
        relative_path (str): Ruta relativa desde la carpeta 'src' (ej: 'locales/es.json')

    Returns:
        str: Ruta absoluta al recurso
    """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Si no existe _MEIPASS, estamos en desarrollo normal
        # __file__ está en src/utils/resource_path.py
        # Subimos un nivel para llegar a src/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Construir la ruta completa
    full_path = os.path.join(base_path, relative_path)

    return full_path
