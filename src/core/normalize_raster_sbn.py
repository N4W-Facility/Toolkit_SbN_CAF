import os
import numpy as np
import rasterio
from rasterio.windows import Window
from pathlib import Path
import tempfile
import shutil


def normalize_raster(input_path, overwrite=True):
    """
    Normaliza raster(s) usando min-max scaling al rango (0-1).
    Formula: (value - min) / (max - min) donde min → 0 y max → 1.

    Parameters:
    -----------
    input_path : str, Path, or list
        Ruta a un raster, directorio con rasters, o lista de rutas
    overwrite : bool
        Si True, sobrescribe los archivos originales (default: True)

    Returns:
    --------
    dict : Información de procesamiento
        Para un solo archivo: {'max_value': float, 'has_data': bool}
        Para múltiples archivos: {ruta: {'max_value': float, 'has_data': bool}}
    """

    # Detectar tipo de entrada y obtener lista de rasters
    raster_files = _get_raster_list(input_path)

    if not raster_files:
        print("No se encontraron archivos raster válidos")
        return {}

    results = {}

    for raster_path in raster_files:
        try:
            print(f"Procesando: {raster_path}")
            max_value, has_data = _normalize_single_raster(raster_path)
            results[str(raster_path)] = {
                'max_value': max_value,
                'has_data': has_data
            }
            print(f"  ✓ Completado (max: {max_value}, has_data: {has_data})")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[str(raster_path)] = {
                'max_value': 0.0,
                'has_data': False
            }

    # Si es un solo archivo, retornar directamente el dict de info
    if len(results) == 1:
        return list(results.values())[0]

    return results


def _get_raster_list(input_path):
    """Obtiene lista de archivos raster desde entrada (archivo/directorio/lista)"""
    
    # Si es lista, retornar directamente
    if isinstance(input_path, (list, tuple)):
        return [Path(p) for p in input_path]
    
    path = Path(input_path)
    
    # Si es archivo, retornar como lista
    if path.is_file():
        return [path]
    
    # Si es directorio, buscar todos los rasters
    if path.is_dir():
        extensions = {'.tif', '.tiff', '.img', '.vrt'}
        return [f for f in path.rglob('*') if f.suffix.lower() in extensions]
    
    return []


def _normalize_single_raster(raster_path):
    """
    Normaliza un único raster por bloques.

    Returns:
    --------
    tuple: (max_value: float, has_data: bool)
    """

    with rasterio.open(raster_path) as src:
        profile = src.profile.copy()
        nodata = src.nodata

        # Determinar tamaño de bloque óptimo
        height, width = src.height, src.width
        blocksize = min(256, height, width)

        # PASADA 1: Calcular mínimo y máximo globales
        min_global = np.inf
        max_global = -np.inf

        for row in range(0, height, blocksize):
            for col in range(0, width, blocksize):
                # Calcular tamaño del bloque actual
                block_height = min(blocksize, height - row)
                block_width = min(blocksize, width - col)

                window = Window(col, row, block_width, block_height)
                block = src.read(1, window=window, masked=True)

                if block.count() > 0:  # Si hay datos válidos
                    block_min = block.min()
                    block_max = block.max()
                    if block_min < min_global:
                        min_global = block_min
                    if block_max > max_global:
                        max_global = block_max

        # Si no hay datos válidos, escribir ceros preservando NaN
        if max_global == -np.inf or min_global == np.inf:
            print(f"  No hay datos válidos, escribiendo ceros preservando NaN...")
            _write_zeros_preserve_nan(src, raster_path, profile, blocksize, nodata)
            return 0.0, False

        # Si min == max, todos los valores son iguales
        if min_global == max_global:
            print(f"  Todos los valores son iguales ({min_global}), escribiendo 0.5 preservando NaN...")
            _write_constant_preserve_nan(src, raster_path, profile, blocksize, nodata, 0.5)
            return float(max_global), True

        print(f"  Rango: [{min_global}, {max_global}]")

        # Si el dtype original es entero, cambiar a float32 para guardar valores decimales
        original_dtype = profile['dtype']
        if np.issubdtype(original_dtype, np.integer):
            print(f"  Cambiando dtype de {original_dtype} a float32 para normalización")
            profile['dtype'] = 'float32'

        # Establecer valor NoData estándar a -9999 (siempre, independiente del original)
        profile['nodata'] = -9999
        print(f"  Configurando NoData = -9999")

        # Configurar compresión según dtype (usar el nuevo dtype si cambió)
        compression_config = _get_compression_config(profile['dtype'])
        profile.update(compression_config)

        # Desactivar tiling para evitar restricciones de múltiplos de 16
        profile.update({
            'tiled': False,
            'BIGTIFF': 'IF_NEEDED'
        })
        
        # Crear archivo temporal
        temp_fd, temp_path = tempfile.mkstemp(suffix='.tif', dir=raster_path.parent)
        os.close(temp_fd)
        
        # PASADA 2: Normalizar y escribir
        with rasterio.open(temp_path, 'w', **profile) as dst:
            for row in range(0, height, blocksize):
                for col in range(0, width, blocksize):
                    block_height = min(blocksize, height - row)
                    block_width = min(blocksize, width - col)
                    
                    window = Window(col, row, block_width, block_height)
                    block = src.read(1, window=window, masked=True)
                    
                    # Normalizar usando min-max scaling: (value - min) / (max - min)
                    # Esto mapea min_global → 0 y max_global → 1
                    normalized = (block - min_global) / (max_global - min_global)

                    # Escribir preservando máscara de nodata con valor estándar -9999
                    dst.write(normalized.filled(-9999), 1, window=window)

    # Sobrescribir original con temporal
    shutil.move(temp_path, raster_path)

    # Retornar información del procesamiento
    return float(max_global), True


def _write_zeros_preserve_nan(src_dataset, raster_path, profile, blocksize, nodata):
    """
    Escribe un raster en ceros preservando las máscaras NaN originales.

    Parameters:
    -----------
    src_dataset : rasterio dataset
        Dataset fuente abierto para leer máscaras originales
    raster_path : Path
        Ruta del raster a sobrescribir
    profile : dict
        Perfil del raster
    blocksize : int
        Tamaño de bloque para procesamiento
    nodata : float or None
        Valor de nodata del raster original
    """

    # Si el dtype original es entero, cambiar a float32 (aunque sea ceros,
    # mantener consistencia con rasters normalizados)
    original_dtype = profile['dtype']
    if np.issubdtype(original_dtype, np.integer):
        print(f"  Cambiando dtype de {original_dtype} a float32")
        profile['dtype'] = 'float32'

    # Establecer valor NoData estándar a -9999
    profile['nodata'] = -9999
    print(f"  Configurando NoData = -9999")

    compression_config = _get_compression_config(profile['dtype'])
    profile.update(compression_config)
    profile.update({
        'tiled': False
    })

    temp_fd, temp_path = tempfile.mkstemp(suffix='.tif', dir=raster_path.parent)
    os.close(temp_fd)

    height, width = profile['height'], profile['width']

    with rasterio.open(temp_path, 'w', **profile) as dst:
        for row in range(0, height, blocksize):
            for col in range(0, width, blocksize):
                block_height = min(blocksize, height - row)
                block_width = min(blocksize, width - col)

                window = Window(col, row, block_width, block_height)

                # Leer bloque original con máscara
                block = src_dataset.read(1, window=window, masked=True)

                # Crear bloque de ceros del mismo tamaño
                zeros = np.zeros((block_height, block_width), dtype=profile['dtype'])

                # Crear masked array con ceros donde hay datos válidos
                # y mantener la máscara donde había NaN
                zeros_masked = np.ma.array(zeros, mask=block.mask)

                # Escribir preservando la máscara de nodata con valor estándar -9999
                dst.write(zeros_masked.filled(-9999), 1, window=window)

    shutil.move(temp_path, raster_path)


def _write_constant_preserve_nan(src_dataset, raster_path, profile, blocksize, nodata, constant_value):
    """
    Escribe un raster con un valor constante preservando las máscaras NaN originales.
    Útil cuando todos los valores del raster original son iguales (min == max).

    Parameters:
    -----------
    src_dataset : rasterio dataset
        Dataset fuente abierto para leer máscaras originales
    raster_path : Path
        Ruta del raster a sobrescribir
    profile : dict
        Perfil del raster
    blocksize : int
        Tamaño de bloque para procesamiento
    nodata : float or None
        Valor de nodata del raster original
    constant_value : float
        Valor constante a escribir (típicamente 0.5 para valores iguales)
    """

    # Si el dtype original es entero, cambiar a float32
    original_dtype = profile['dtype']
    if np.issubdtype(original_dtype, np.integer):
        print(f"  Cambiando dtype de {original_dtype} a float32")
        profile['dtype'] = 'float32'

    # Establecer valor NoData estándar a -9999
    profile['nodata'] = -9999
    print(f"  Configurando NoData = -9999")

    compression_config = _get_compression_config(profile['dtype'])
    profile.update(compression_config)
    profile.update({
        'tiled': False
    })

    temp_fd, temp_path = tempfile.mkstemp(suffix='.tif', dir=raster_path.parent)
    os.close(temp_fd)

    height, width = profile['height'], profile['width']

    with rasterio.open(temp_path, 'w', **profile) as dst:
        for row in range(0, height, blocksize):
            for col in range(0, width, blocksize):
                block_height = min(blocksize, height - row)
                block_width = min(blocksize, width - col)

                window = Window(col, row, block_width, block_height)

                # Leer bloque original con máscara
                block = src_dataset.read(1, window=window, masked=True)

                # Crear bloque con valor constante
                constant_block = np.full((block_height, block_width), constant_value, dtype=profile['dtype'])

                # Crear masked array con valor constante donde hay datos válidos
                # y mantener la máscara donde había NaN
                constant_masked = np.ma.array(constant_block, mask=block.mask)

                # Escribir preservando la máscara de nodata con valor estándar -9999
                dst.write(constant_masked.filled(-9999), 1, window=window)

    shutil.move(temp_path, raster_path)


def _write_zeros(raster_path, profile, blocksize):
    """Escribe un raster completamente en ceros (deprecated, usar _write_zeros_preserve_nan)"""

    compression_config = _get_compression_config(profile['dtype'])
    profile.update(compression_config)
    profile.update({
        'tiled': False
    })

    temp_fd, temp_path = tempfile.mkstemp(suffix='.tif', dir=raster_path.parent)
    os.close(temp_fd)

    with rasterio.open(temp_path, 'w', **profile) as dst:
        zeros = np.zeros((blocksize, blocksize), dtype=profile['dtype'])

        for row in range(0, profile['height'], blocksize):
            for col in range(0, profile['width'], blocksize):
                block_height = min(blocksize, profile['height'] - row)
                block_width = min(blocksize, profile['width'] - col)

                window = Window(col, row, block_width, block_height)
                dst.write(zeros[:block_height, :block_width], 1, window=window)

    shutil.move(temp_path, raster_path)


def _get_compression_config(dtype):
    """Retorna configuración de compresión óptima según tipo de dato"""
    
    dtype_str = np.dtype(dtype).name
    
    # Float → ZSTD (mejor compresión para datos continuos)
    if 'float' in dtype_str:
        return {
            'compress': 'ZSTD',
            'zstd_level': 9,
            'predictor': 3  # floating point predictor
        }
    
    # Integer → LZW
    else:
        return {
            'compress': 'LZW',
            'predictor': 2  # horizontal differencing
        }
