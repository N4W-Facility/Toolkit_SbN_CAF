# -*- coding: utf-8 -*-
import sys
import os
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.window_manager import WindowManager
from src.windows.startup_window import StartupWindow
from src.windows.database_selection_dialog import check_and_configure_database
from src.utils.precache import precache_region_latlon
import contextily as ctx

# IMPORTANTE: Configurar caché DESPUÉS de importar contextily
# Contextily tiene su propia API: ctx.set_cache_dir()
from src.core.map_cache_config import configure_map_cache
configure_map_cache()
print("✓ Caché de mapas configurado en AppData")


def background_tile_preload():
    """
    Precarga de tiles de mapas en segundo plano.
    Se ejecuta después de que la UI está lista.
    Solo precarga si el caché está vacío o muy pequeño.
    """
    from src.core.map_cache_config import get_cache_directory

    # Verificar tamaño del caché antes de precargar
    cache_dir = get_cache_directory()

    # Calcular tamaño del caché
    total_size = 0
    file_count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(cache_dir):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)
                file_count += 1
    except Exception as e:
        print(f"⚠️ Error calculando tamaño del caché: {e}")

    total_size_mb = total_size / (1024 * 1024)

    # Si ya hay más de 50MB en caché, asumir que ya está precargado
    if total_size_mb > 50 and file_count > 100:
        print(f"✓ Caché ya existe ({total_size_mb:.1f} MB, {file_count} archivos). Saltando precarga.")
        return

    # BBOX de Latinoamérica
    BBOX_LATAM = (-118.0, -56.0, -34.0, 33.0)

    # Provider por defecto
    PROVIDER = ctx.providers.OpenStreetMap.Mapnik

    # Niveles de zoom: 4 (continental) hasta 8 (regional detallado)
    ZMIN, ZMAX = 4, 8

    try:
        print(f"🚀 Precargando tiles de Latinoamérica en segundo plano (z=4 a z=8)...")
        print(f"   Caché actual: {total_size_mb:.1f} MB, {file_count} archivos")
        precache_region_latlon(BBOX_LATAM, ZMIN, ZMAX, grid=6, provider=PROVIDER)
        print("✅ Precarga de tiles completa")
    except Exception as e:
        print(f"⚠️ Precarga de tiles falló: {e}")


def main():
    # Verificar y configurar base de datos antes de continuar
    if not check_and_configure_database():
        print("Aplicación cerrada: No se configuró la base de datos")
        return

    # Gestión de caché: limpiar si excede el límite
    from src.utils.cache_manager import CacheManager
    from src.core.map_cache_config import get_cache_directory

    cache_dir = get_cache_directory()
    cache_mgr = CacheManager(cache_dir, max_size_mb=500, target_size_mb=300)
    cache_info = cache_mgr.check_and_cleanup()
    print(f"✓ Caché de mapas: {cache_info['size_mb']:.1f} MB ({cache_info['file_count']} archivos), límite: {cache_info['max_mb']:.0f} MB")

    # --- UI ---
    window_manager = WindowManager()
    app = StartupWindow(window_manager)
    window_manager.set_main_window(app)

    app.mainloop()

if __name__ == "__main__":
    main()
