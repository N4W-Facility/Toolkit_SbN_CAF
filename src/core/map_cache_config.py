import os


def get_cache_directory():
    """
    Obtiene la ruta del directorio de caché en AppData.

    Retorna: C:\\Users\\{usuario}\\AppData\\Local\\SbN_Toolkit\\map_cache\\
    """
    # Obtener ruta de AppData\Local para Windows
    local_appdata = os.getenv('LOCALAPPDATA')
    if not local_appdata:
        # Fallback si LOCALAPPDATA no está definido (muy raro en Windows)
        local_appdata = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')

    # Crear carpeta de caché para tiles de mapa
    cache_dir = os.path.join(local_appdata, 'SbN_Toolkit', 'map_cache')
    os.makedirs(cache_dir, exist_ok=True)

    return cache_dir


def configure_map_cache():
    """
    Configura el caché de tiles de mapas de contextily para usar AppData.

    IMPORTANTE: Debe ejecutarse DESPUÉS de importar contextily.
    Usa ctx.set_cache_dir() para configurar la ubicación del caché.

    Ubicación del caché: C:\\Users\\{usuario}\\AppData\\Local\\SbN_Toolkit\\map_cache\\
    """
    import contextily as ctx
    import atexit

    cache_dir = get_cache_directory()

    # Configurar directorio de caché usando la API de contextily
    ctx.set_cache_dir(cache_dir)

    # CRÍTICO: Desregistrar el _clear_cache de contextily para evitar que borre el caché
    # Contextily registra atexit._clear_cache que borra el directorio temporal al salir
    # Como estamos usando un directorio permanente en AppData, NO queremos que se borre
    try:
        # Buscar y remover la función _clear_cache de los handlers de atexit
        import contextily.tile as ctx_tile
        if hasattr(ctx_tile, '_clear_cache'):
            # Intentar desregistrar el handler
            for handler in atexit._exithandlers[:]:
                if handler[0] == ctx_tile._clear_cache:
                    atexit._exithandlers.remove(handler)
                    print("✓ Cleanup de caché temporal deshabilitado (caché persistente en AppData)")
                    break
    except Exception as e:
        print(f"⚠️ No se pudo desregistrar cleanup: {e}")

    return cache_dir
