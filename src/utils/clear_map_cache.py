# -*- coding: utf-8 -*-
"""
Script para limpiar completamente el caché de mapas.
Útil si el caché está corrupto o muy grande.

Nota: La aplicación tiene limpieza automática a 500MB,
pero este script permite limpieza manual total.
"""
import os
import sys
import shutil

# Agregar src al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.map_cache_config import get_cache_directory

def clear_cache():
    cache_dir = get_cache_directory()

    if os.path.exists(cache_dir):
        # Calcular tamaño
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(cache_dir):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1

        total_size_mb = total_size / (1024 * 1024)
        print(f"\n📊 Caché actual:")
        print(f"   Ubicación: {cache_dir}")
        print(f"   Tamaño: {total_size_mb:.1f} MB")
        print(f"   Archivos: {file_count}")
        print(f"\nNota: La aplicación mantiene automáticamente el caché bajo 500 MB.")

        if total_size_mb < 100:
            print(f"\n✓ El caché está en buen tamaño ({total_size_mb:.1f} MB). No es necesario limpiar.")
            return

        respuesta = input(f"\n¿Eliminar TODO el caché ({total_size_mb:.1f} MB)? (s/n): ")
        if respuesta.lower() == 's':
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            print("✓ Caché eliminado completamente")
            print("  Los tiles se descargarán nuevamente cuando navegues el mapa.")
        else:
            print("Cancelado")
    else:
        print("No hay caché para eliminar")

if __name__ == "__main__":
    clear_cache()
