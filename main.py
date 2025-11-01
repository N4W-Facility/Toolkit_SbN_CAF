# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.window_manager import WindowManager
from src.windows.startup_window import StartupWindow
from src.windows.database_selection_dialog import check_and_configure_database

# 👇 Añade estos imports
from src.utils.precache import precache_region_latlon
import contextily as ctx

def main():
    # Verificar y configurar base de datos antes de continuar
    if not check_and_configure_database():
        print("Aplicación cerrada: No se configuró la base de datos")
        return

    """
    # --- 👇 PRECARGA ANTES DE CREAR LA VENTANA ---
    # BBOX de LatAm + Centroamérica (ajusta si quieres menos área)
    BBOX_LATAM = (-118.0, -56.0, -34.0, 33.0)

    
    # Usa el MISMO provider con el que inicias el basemap en tu app.
    # Si por defecto arrancas con OpenStreetMap:
    PROVIDER = ctx.providers.OpenStreetMap.Mapnik
    # (Si inicias con CartoDB Positron, usa: ctx.providers.CartoDB.Positron)

    # Rango de zoom razonable para vista continental→urbana
    ZMIN, ZMAX = 4, 6

    try:
        print("🚀 Precargando tiles de Latinoamérica...")
        precache_region_latlon(BBOX_LATAM, ZMIN, ZMAX, grid=6, provider=PROVIDER)
        print("✅ Precarga completa. Abriendo UI...")
    except Exception as e:
        # No abortes si falla; la app igual podrá cargar on-the-fly
        print(f"⚠️ Precarga falló: {e}. Continuando...")
    """
    # --- UI ---
    window_manager = WindowManager()
    app = StartupWindow(window_manager)
    window_manager.set_main_window(app)
    app.mainloop()

if __name__ == "__main__":
    main()
