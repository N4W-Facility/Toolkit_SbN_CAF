# -*- coding: utf-8 -*-
"""
Gestor de caché de mapas con límite de tamaño automático.
Previene que el caché crezca indefinidamente.
"""
import os
import time
from pathlib import Path


class CacheManager:
    """Gestiona el tamaño del caché eliminando archivos viejos cuando se excede el límite."""

    def __init__(self, cache_dir, max_size_mb=500, target_size_mb=300):
        """
        Args:
            cache_dir: Directorio de caché
            max_size_mb: Tamaño máximo antes de limpiar (500 MB por defecto)
            target_size_mb: Tamaño objetivo después de limpiar (300 MB por defecto)
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.target_size_bytes = target_size_mb * 1024 * 1024

    def get_cache_size(self):
        """Calcula el tamaño total del caché en bytes."""
        total_size = 0
        file_count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1
        except Exception as e:
            print(f"⚠️ Error calculando tamaño del caché: {e}")

        return total_size, file_count

    def get_all_cache_files(self):
        """Obtiene todos los archivos del caché con su tiempo de acceso."""
        files = []
        try:
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        try:
                            atime = os.path.getatime(file_path)
                            size = os.path.getsize(file_path)
                            files.append((file_path, atime, size))
                        except Exception:
                            continue
        except Exception as e:
            print(f"⚠️ Error listando archivos del caché: {e}")

        return files

    def cleanup_cache(self):
        """Limpia archivos viejos del caché si excede el límite."""
        total_size, file_count = self.get_cache_size()

        if total_size < self.max_size_bytes:
            return  # No necesita limpieza

        print(f"🧹 Limpiando caché: {total_size / (1024*1024):.1f} MB > {self.max_size_bytes / (1024*1024):.1f} MB")

        # Obtener todos los archivos ordenados por tiempo de acceso (más viejos primero)
        files = self.get_all_cache_files()
        files.sort(key=lambda x: x[1])  # Ordenar por atime

        # Eliminar archivos viejos hasta alcanzar el tamaño objetivo
        deleted_size = 0
        deleted_count = 0

        for file_path, atime, size in files:
            if total_size - deleted_size <= self.target_size_bytes:
                break

            try:
                os.remove(file_path)
                deleted_size += size
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Error eliminando {file_path}: {e}")

        # Limpiar carpetas vacías
        self._remove_empty_dirs(self.cache_dir)

        final_size = total_size - deleted_size
        print(f"✓ Caché limpiado: {deleted_count} archivos eliminados ({deleted_size / (1024*1024):.1f} MB)")
        print(f"  Tamaño final: {final_size / (1024*1024):.1f} MB ({file_count - deleted_count} archivos)")

    def _remove_empty_dirs(self, path):
        """Elimina recursivamente directorios vacíos."""
        try:
            for dirpath, dirnames, filenames in os.walk(path, topdown=False):
                if dirpath == str(path):
                    continue
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                except Exception:
                    pass
        except Exception:
            pass

    def check_and_cleanup(self):
        """Verifica el tamaño y limpia si es necesario. Retorna info del caché."""
        total_size, file_count = self.get_cache_size()

        if total_size > self.max_size_bytes:
            self.cleanup_cache()
            total_size, file_count = self.get_cache_size()

        return {
            'size_mb': total_size / (1024 * 1024),
            'file_count': file_count,
            'max_mb': self.max_size_bytes / (1024 * 1024)
        }
