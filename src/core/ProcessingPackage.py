# Sistema y utilidades
import os
import glob
import shutil
import tempfile
import time
import math
from typing import List, Tuple, Optional

# Análisis numérico y datos
import numpy as np
import pandas as pd

# Análisis espacial y geometría
import geopandas as gpd
from shapely.geometry import box, Point, shape

# GDAL/OGR
from osgeo import gdal, ogr, osr

# Rasterio
import rasterio
import rasterio.mask
from rasterio.windows import Window
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds, transform_geom
from rasterio.features import shapes

# Procesamiento científico
from scipy.ndimage import convolve, distance_transform_edt
from sklearn.cluster import KMeans

# Hidrología
from pysheds.grid import Grid

# Configuración GDAL
gdal.SetConfigOption('GDAL_CACHEMAX', '1024')  # 1GB cache
gdal.UseExceptions()

# ----------------------------------------------------------------------------------------------------------------------
# CREAR CARPETAS DE PROYECTO
# ----------------------------------------------------------------------------------------------------------------------
def CreateFolders(base_path):
    '''
    Crea las carpetas requeridas para el análisis utilizando una ruta base especificada.

    :param base_path: Ruta base donde se crearán las carpetas.
    '''
    try:
        # Rutas de las carpetas
        folders = [
            os.path.join(base_path, '01-Watershed'),
            os.path.join(base_path, '02-Rasters'),
            os.path.join(base_path, '03-SbN'),
            os.path.join(base_path, 'Tmp'),
        ]

        # Crear cada carpeta si no existe
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            print(f'Carpeta creada: {folder}')

        print('Todas las carpetas han sido creadas con éxito.')
    except Exception as e:
        print(f'Error al crear las carpetas: {e}')

# ----------------------------------------------------------------------------------------------------------------------
# IDENTIFICACIÓN DE MACRO-CUENCA
# ----------------------------------------------------------------------------------------------------------------------
def C00_EncontrarMacrocuenca(latitud, longitud, archivo_macrocuencas,
                             columna_identificador='Name'):
    """
    Localiza la macrocuenca que contiene una coordenada y devuelve su identificador.

    Función simple que utiliza consulta vectorial point-in-polygon para encontrar
    el valor del atributo especificado de la macrocuenca que contiene el punto.

    Parameters
    ----------
    latitud : float
        Latitud en grados decimales, sistema de coordenadas WGS84 (EPSG:4326).
        Rango válido: -90.0 a 90.0

    longitud : float
        Longitud en grados decimales, sistema de coordenadas WGS84 (EPSG:4326).
        Rango válido: -180.0 a 180.0

    archivo_macrocuencas : str
        Ruta al archivo vectorial que contiene los polígonos de macrocuencas.
        Formatos soportados: .shp, .gpkg, .geojson, .kml, etc.

    columna_identificador : str, default 'Macro'
        Nombre de la columna que contiene el identificador de la macrocuenca.

    Returns
    -------
    str or None
        str : Valor del atributo en la columna especificada para la macrocuenca encontrada
        None : Si la coordenada no se encuentra dentro de ninguna macrocuenca

    Raises
    ------
    FileNotFoundError
        Si el archivo de macrocuencas no existe

    KeyError
        Si la columna especificada no existe en el archivo vectorial

    Examples
    --------
    >>> # Obtener identificador de macrocuenca
    >>> lat, lon = 4.6097, -74.0817  # Bogotá
    >>> archivo = "/datos/macrocuencas_colombia.shp"
    >>> identificador = C00_EncontrarMacrocuenca(lat, lon, archivo)
    >>> print(f"Macrocuenca: {identificador}")  # ej: "magdalena_cauca"

    >>> # Usar diferente columna
    >>> codigo = C00_EncontrarMacrocuenca(lat, lon, archivo, 'CODIGO')
    >>> print(f"Código: {codigo}")  # ej: "MC01"
    """

    print(f"🔍 Buscando macrocuenca para: ({latitud:.4f}, {longitud:.4f})")
    print(f"📁 Archivo: {archivo_macrocuencas}")
    print(f"🏷️  Campo: '{columna_identificador}'")

    try:
        # Cargar archivo vectorial
        print(f"\n📖 Cargando archivo vectorial...")
        gdf_macrocuencas = gpd.read_file(archivo_macrocuencas)
        print(f"✅ {len(gdf_macrocuencas)} macrocuencas cargadas")

        # Verificar que existe la columna
        if columna_identificador not in gdf_macrocuencas.columns:
            columnas_disponibles = list(gdf_macrocuencas.columns)
            raise KeyError(f"La columna '{columna_identificador}' no existe. "
                           f"Columnas disponibles: {columnas_disponibles}")

        # Asegurar WGS84
        if gdf_macrocuencas.crs != 'EPSG:4326':
            print(f"🔄 Reproyectando a WGS84...")
            gdf_macrocuencas = gdf_macrocuencas.to_crs('EPSG:4326')

        # Crear punto y consultar
        print(f"🎯 Ejecutando consulta espacial...")
        punto_consulta = Point(longitud, latitud)
        mask_contiene = gdf_macrocuencas.geometry.contains(punto_consulta)
        macrocuencas_encontradas = gdf_macrocuencas[mask_contiene]

        if len(macrocuencas_encontradas) == 0:
            print(f"❌ Coordenada no encontrada en ninguna macrocuenca")
            return None

        # Obtener el valor del atributo
        macrocuenca = macrocuencas_encontradas.iloc[0]
        valor_identificador = macrocuenca[columna_identificador]

        print(f"✅ ¡Encontrado! {columna_identificador} = '{valor_identificador}'")

        return valor_identificador

    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado - {archivo_macrocuencas}")
        raise
    except KeyError as e:
        print(f"❌ Error: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        raise

# ----------------------------------------------------------------------------------------------------------------------
# DELIMITACIÓN DE CUENCAS
# ----------------------------------------------------------------------------------------------------------------------
def get_utm_zone(lon, lat):
    """
    Calcula la zona UTM para una coordenada dada.

    Parameters
    ----------
    lon : float
        Longitud en grados decimales
    lat : float
        Latitud en grados decimales

    Returns
    -------
    zone_number : int
        Número de zona UTM
    hemisphere : str
        'N' para norte, 'S' para sur
    """
    zone_number = int((lon + 180) / 6) + 1
    hemisphere = 'N' if lat >= 0 else 'S'
    return zone_number, hemisphere

def calculate_pixel_area_geographic(grid, method='utm'):
    """
    Calcula el área de píxel para coordenadas geográficas.

    Parameters
    ----------
    grid : Grid
        Objeto Grid de pysheds
    method : str
        Método de cálculo: 'utm'

    Returns
    -------
    pixel_area : float
        Área del píxel en km²
    """
    # Método usando información UTM
    lat_center = (grid.extent[2] + grid.extent[3]) / 2
    lon_center = (grid.extent[0] + grid.extent[1]) / 2

    zone_number, hemisphere = get_utm_zone(lon_center, lat_center)

    # Factor de escala UTM aproximado
    central_meridian = (zone_number - 1) * 6 - 180 + 3
    lon_diff = abs(lon_center - central_meridian)
    scale_factor = 0.9996 + (lon_diff / 3) * 0.0004  # Aproximación

    # Calcular área considerando el factor de escala UTM
    deg_to_m_lat = 111320 * scale_factor
    deg_to_m_lon = 111320 * np.cos(np.radians(lat_center)) * scale_factor

    pixel_size_lat_m = abs(grid.viewfinder.dy_dx[1]) * deg_to_m_lat
    pixel_size_lon_m = abs(grid.viewfinder.dy_dx[0]) * deg_to_m_lon

    print(f"   - Zona UTM estimada: {zone_number}{hemisphere}")
    print(f"   - Factor de escala UTM: {scale_factor:.6f}")

    return (pixel_size_lat_m * pixel_size_lon_m) / 1E6

def C01_BasinDelineation(PathOut, Path_FlowDir, lat, lon, threshold=1.0):
    """
    Delinea una cuenca hidrográfica a partir de un raster de direcciones de flujo.
    Genera únicamente un shapefile de la cuenca en coordenadas geográficas EPSG:4326.

    Parameters
    ----------
    PathOut : str
        Ruta del directorio donde se guardará el shapefile de salida.
        Si no existe, se creará automáticamente.
    Path_FlowDir : str
        Ruta completa al archivo raster de direcciones de flujo.
        Debe ser un archivo raster válido (ej: .tif, .asc).
    lat : float
        Latitud del punto de interés en grados decimales. Debe estar dentro
        del área cubierta por el raster de direcciones de flujo.
    lon : float
        Longitud del punto de interés en grados decimales. Debe estar dentro
        del área cubierta por el raster de direcciones de flujo.
    threshold : float, optional
        Umbral de área acumulada en km² para definir la red de drenaje.
        Por defecto es 1.0 km².

    Returns
    -------
    dict
        Diccionario con las rutas de los archivos generados:
        - 'shapefile': Ruta al shapefile de la cuenca
        - 'accumarea_raster': Ruta al raster de área acumulada

    Notes
    -----
    - El punto de salida se ajusta automáticamente a la celda de red más cercana
    - El shapefile de salida está en coordenadas geográficas EPSG:4326
    - Se incluyen atributos de área de la cuenca en km²

    Examples
    --------
    >>> # Delinear cuenca para un punto usando direcciones de flujo existentes
    >>> result = BasinDelineation(
    ...     PathOut='/ruta/salida',
    ...     Path_FlowDir='/ruta/flow_direction.tif',
    ...     lat=4.5981,
    ...     lon=-74.0758,
    ...     threshold=1.5
    ... )
    >>> print(f"Cuenca: {result['shapefile']}")
    >>> print(f"Área acumulada: {result['accumarea_raster']}")

    Raises
    ------
    FileNotFoundError
        Si Path_FlowDir no existe o no es accesible
    PermissionError
        Si PathOut no tiene permisos de escritura
    ValueError
        Si las coordenadas lat, lon están fuera del área del raster
    """

    print("=" * 60)
    print("INICIANDO DELIMITACIÓN DE CUENCA HIDROGRÁFICA")
    print("=" * 60)
    print(f"Coordenadas del punto: Lat={lat}, Lon={lon}")
    print(f"Umbral de red de drenaje: {threshold} km²")
    print(f"Directorio de salida: {PathOut}")
    print()

    # Crear directorio de salida si no existe
    os.makedirs(PathOut, exist_ok=True)

    print("1. Cargando raster de direcciones de flujo...")
    # Crear objeto Grid vacío con las propiedades del raster de direcciones de flujo
    grid = Grid.from_raster(Path_FlowDir, data_name='flowdir')
    print(f"   ✓ Grid creado exitosamente")
    print(f"   - Dimensiones: {grid.viewfinder.shape}")
    print(f"   - Extensión: {grid.extent}")

    # Leer datos del raster de direcciones de flujo
    FlowDir = grid.read_raster(Path_FlowDir)
    print(f"   ✓ Datos de direcciones de flujo cargados")
    print(f"   - Tipo de datos: {FlowDir.dtype}")
    print()

    print("2. Calculando acumulación de flujo...")
    # Acumulaciones de Flujo
    FlowAccum = grid.accumulation(FlowDir)
    print(f"   ✓ Acumulación de flujo calculada")
    print(f"   - Valor máximo de acumulación: {np.max(FlowAccum)}")
    print()

    print("3. Calculando área acumulada...")
    # Verificar si las coordenadas están en grados (geográficas)
    if abs(grid.extent[0]) <= 180 and abs(grid.extent[2]) <= 90:
        print("   - Detectadas coordenadas geográficas (grados)")

        # Usar método UTM para mayor precisión
        PixelArea = calculate_pixel_area_geographic(grid, method='utm')

        # Información adicional
        lat_center = (grid.extent[2] + grid.extent[3]) / 2
        lon_center = (grid.extent[0] + grid.extent[1]) / 2
        print(f"   - Coordenadas centrales: {lon_center:.6f}°, {lat_center:.6f}°")
        print(f"   - Resolución en grados: {abs(grid.viewfinder.dy_dx[0]):.6f}° x {abs(grid.viewfinder.dy_dx[1]):.6f}°")
        print(f"   - Área por píxel (corregida): {PixelArea:.6f} km²")
    else:
        print("   - Detectadas coordenadas proyectadas (metros)")
        # Área acumulada [Km^2] para coordenadas proyectadas
        PixelArea = (grid.viewfinder.dy_dx[0] * grid.viewfinder.dy_dx[0]) / 1E6
        print(f"   - Área por píxel: {PixelArea:.6f} km²")

    AccumArea = FlowAccum * PixelArea
    print(f"   ✓ Área acumulada calculada")
    print(f"   - Área máxima acumulada: {np.max(AccumArea):.2f} km²")
    print()

    print("4. Generando red de drenaje...")
    # Red de drenaje basada en el umbral
    Network = AccumArea > threshold
    num_channels = np.sum(Network)
    print(f"   ✓ Red de drenaje generada con umbral de {threshold} km²")
    print(f"   - Número de celdas de canal: {num_channels}")
    print(f"   - Porcentaje del área total: {(num_channels / Network.size) * 100:.2f}%")

    if num_channels == 0:
        raise ValueError(f"No se encontraron celdas de red con umbral {threshold} km². Prueba con un umbral menor.")
    print()

    print("5. Ajustando coordenadas del punto de salida a la red de drenaje...")
    print(f"   - Coordenadas originales: ({lon}, {lat})")

    # Usar la función snap_to_mask de pysheds con la sintaxis correcta
    # Snap point to network cells (where AccumArea > threshold)
    x_new, y_new = grid.snap_to_mask(AccumArea > threshold, (lon, lat))

    print(f"   ✓ Punto ajustado a la red de drenaje: ({x_new:.6f}, {y_new:.6f})")

    # Verificar el área acumulada en el punto ajustado
    col_snap, row_snap = grid.nearest_cell(x_new, y_new)
    accum_at_snap = float(AccumArea[row_snap, col_snap])  # Convertir a float
    print(f"   - Área acumulada en el punto ajustado: {accum_at_snap:.2f} km²")

    print("6. Delimitando cuenca hidrográfica...")
    # Delinear la cuenca usando el punto ajustado a la red
    Watershed = grid.catchment(x=x_new, y=y_new, fdir=FlowDir, xytype='coordinate')
    Watershed = Watershed.astype(np.uint8)

    # Calcular estadísticas de la cuenca
    watershed_cells = np.sum(Watershed)
    watershed_area_km2 = watershed_cells * PixelArea
    print(f"   ✓ Cuenca delimitada exitosamente")
    print(f"   - Número de celdas: {watershed_cells}")
    print(f"   - Área de la cuenca: {watershed_area_km2:.2f} km²")
    print(f"   - Punto de salida final: ({x_new:.6f}, {y_new:.6f})")
    print()

    print("7. Guardando resultados...")

    # Obtener el bounding box de la cuenca delimitada
    print("   - Calculando extensión de la cuenca...")
    watershed_rows, watershed_cols = np.where(Watershed == 1)

    # Calcular bounding box con un pequeño buffer
    buffer_cells = 5  # Buffer de 5 celdas alrededor de la cuenca
    row_min = max(0, watershed_rows.min() - buffer_cells)
    row_max = min(Watershed.shape[0], watershed_rows.max() + buffer_cells + 1)
    col_min = max(0, watershed_cols.min() - buffer_cells)
    col_max = min(Watershed.shape[1], watershed_cols.max() + buffer_cells + 1)

    print(f"   - Cuenca original: {Watershed.shape[1]}x{Watershed.shape[0]} píxeles")
    print(f"   - Cuenca recortada: {col_max - col_min}x{row_max - row_min} píxeles")
    print(
        f"   - Reducción: {((1 - ((col_max - col_min) * (row_max - row_min)) / (Watershed.shape[1] * Watershed.shape[0])) * 100):.1f}%")

    # Recortar área acumulada al dominio de la cuenca
    AccumArea_clipped = AccumArea[row_min:row_max, col_min:col_max]

    # Recortar cuenca para la máscara
    Watershed_clipped = Watershed[row_min:row_max, col_min:col_max]

    # Aplicar máscara de cuenca (opcional: poner 0 fuera de la cuenca)
    AccumArea_masked = AccumArea_clipped.copy()
    AccumArea_masked[Watershed_clipped == 0] = 0  # Poner 0 fuera de la cuenca

    # Calcular nuevo transform para el área recortada
    from rasterio.transform import from_bounds

    # Coordenadas del área recortada
    x_min = grid.extent[0] + (col_min * grid.viewfinder.dy_dx[0])
    x_max = grid.extent[0] + (col_max * grid.viewfinder.dy_dx[0])
    y_max = grid.extent[3] - (row_min * grid.viewfinder.dy_dx[0])
    y_min = grid.extent[3] - (row_max * grid.viewfinder.dy_dx[0])

    transform_clipped = from_bounds(
        x_min, y_min, x_max, y_max,
        col_max - col_min, row_max - row_min
    )

    # Nombres de archivos de salida
    output_shapefile = os.path.join(PathOut, "01-Watershed", f"Watershed.shp")
    output_accumarea = os.path.join(PathOut, "02-Rasters", f"AccumArea.tif")

    # Guardar raster de área acumulada recortado con compresión y factor de escala
    print("   - Guardando raster de área acumulada recortado y comprimido...")

    # Aplicar factor de escala (factor 100: 1 km² = 1000 unidades enteras)
    scale_factor = 1000
    AccumArea_scaled = (AccumArea_masked * scale_factor).astype(np.uint32)

    print(f"   - Factor de escala aplicado: x{scale_factor}")
    print(
        f"   - Rango de valores escalados: {np.min(AccumArea_scaled[AccumArea_scaled > 0])} - {np.max(AccumArea_scaled)}")

    # Guardar usando rasterio directamente
    import rasterio

    with rasterio.open(
            output_accumarea,
            'w',
            driver='GTiff',
            height=AccumArea_scaled.shape[0],
            width=AccumArea_scaled.shape[1],
            count=1,
            dtype=np.uint32,
            crs=grid.viewfinder.crs,
            transform=transform_clipped,
            nodata=0,
            compress='lzw',
            tiled=True,
            blockxsize=256,
            blockysize=256
    ) as dst:
        dst.write(AccumArea_scaled, 1)
        # Agregar metadatos
        dst.update_tags(
            scale_factor=scale_factor,
            units='km2_x100',
            description=f'Accumulated area scaled by factor {scale_factor}. Divide by {scale_factor} to get km². Clipped to watershed extent.',
            compression='LZW',
            original_nodata='NaN converted to 0',
            watershed_lat=lat,
            watershed_lon=lon,
            clipped_extent=f'{x_min:.6f},{y_min:.6f},{x_max:.6f},{y_max:.6f}'
        )

    print(f"   ✓ Área acumulada recortada guardada: {os.path.basename(output_accumarea)}")
    print(f"   - Tipo de datos: uint32 (factor escala x{scale_factor})")
    print(f"   - Compresión: LZW con tiles 256x256")
    print(f"   - Valor nodata: 0")
    print(f"   - Dominio: Solo cuenca + buffer de {buffer_cells} celdas")

    # Convertir cuenca a shapefile
    print("   - Convirtiendo cuenca a shapefile...")

    # Crear transform para rasterio
    from rasterio.transform import from_bounds
    transform = from_bounds(
        grid.extent[0], grid.extent[2], grid.extent[1], grid.extent[3],
        grid.viewfinder.shape[1], grid.viewfinder.shape[0]
    )

    # Convertir raster a polígonos
    print("   - Vectorizando raster de cuenca...")
    watershed_shapes = list(shapes(Watershed, mask=Watershed, transform=transform))

    # Crear geometrías y unificarlas en una sola cuenca
    geometries = []
    for geom, value in watershed_shapes:
        if value == 1:  # Solo polígonos de cuenca
            geometries.append(shape(geom))

    if not geometries:
        raise ValueError("No se pudo generar la geometría de la cuenca")

    print(f"   - Se encontraron {len(geometries)} polígono(s)")

    # Si hay múltiples polígonos, unificarlos en uno solo
    if len(geometries) > 1:
        from shapely.ops import unary_union
        unified_geometry = unary_union(geometries)
        print("   - Múltiples polígonos unificados en una geometría")
    else:
        unified_geometry = geometries[0]

    # Crear GeoDataFrame con una sola geometría y nombres de columna cortos
    gdf = gpd.GeoDataFrame({
        'area_km2': [float(watershed_area_km2)],
        'area_cells': [int(watershed_cells)],
        'lat_orig': [float(lat)],
        'lon_orig': [float(lon)],
        'lat_snap': [float(y_new)],
        'lon_snap': [float(x_new)],
        'threshold': [float(threshold)],
        'accum_km2': [accum_at_snap],
        'n_polygons': [len(geometries)]
    }, geometry=[unified_geometry], crs='EPSG:4326')

    print("   - Guardando shapefile...")
    gdf.to_file(output_shapefile)
    print(f"   ✓ Shapefile guardado: {os.path.basename(output_shapefile)}")
    print()

    print("=" * 60)
    print("DELIMITACIÓN DE CUENCA COMPLETADA")
    print("=" * 60)
    print("RESUMEN:")
    print(f"  • Área de la cuenca: {watershed_area_km2:.2f} km²")
    print(f"  • Número de celdas: {watershed_cells}")
    print(f"  • Sistema de coordenadas: EPSG:4326 (WGS84)")
    print("ARCHIVOS GENERADOS:")
    print(f"  • Shapefile cuenca: {os.path.basename(output_shapefile)}")
    print(f"  • Raster área acum.: {os.path.basename(output_accumarea)} (LZW, x{100})")
    print(f"  • Ubicación: {PathOut}")
    print("NOTA: Para obtener km² reales del raster, dividir valores por 100")
    print("=" * 60)

    return {
        'shapefile': output_shapefile,
        'accumarea_raster': output_accumarea
    }

# ----------------------------------------------------------------------------------------------------------------------
# CREAR MOSAICO - RECORTAR BASES DE DATOS PARA LA CUENCA DE ANÁLISIS
# ----------------------------------------------------------------------------------------------------------------------
def C02_Crear_Mosaico_V1_Ok(ruta_rasters, archivo_poligono, crs_salida='EPSG:4326', archivo_salida=None):
    """
    Crea un mosaico de rasters para un área específica definida por un polígono.

    Esta función utiliza GDAL nativo para máximo rendimiento. Crea un VRT (Virtual Raster)
    con los rasters intersectantes y usa gdal.Warp para recortar y reproyectar en una
    sola operación ultrarrápida.

    OPTIMIZACIONES IMPLEMENTADAS:
    - Índice CSV para identificación rápida de intersecciones
    - VRT (Virtual Raster) para evitar carga de datos innecesaria
    - gdal.Warp para recorte + reproyección en una sola operación
    - Optimización automática de tipos de datos y compresión LZW

    Parámetros:
    -----------
    ruta_rasters : str
        Ruta de la carpeta que contiene los archivos raster
    archivo_poligono : str
        Ruta del archivo shapefile (.shp) con el polígono de interés
    crs_salida : str, opcional
        Sistema de coordenadas de salida (por defecto 'EPSG:4326')
    archivo_salida : str, opcional
        Ruta del archivo de salida. Si no se especifica, se genera automáticamente

    Retorna:
    --------
    str
        Ruta del archivo de salida creado

    Ejemplo:
    --------
    >>> archivo_resultado = crear_mosaico_raster(
    ...     ruta_rasters='/ruta/a/rasters/',
    ...     archivo_poligono='/ruta/poligono.shp',
    ...     crs_salida='EPSG:4326',
    ...     archivo_salida='/ruta/mosaico_resultado.tif'
    ... )
    """

    print("=== INICIANDO PROCESO DE MOSAICO CON GDAL ===")

    # 1. Validar entradas
    print(f"📁 Verificando carpeta de rasters: {ruta_rasters}")
    if not os.path.exists(ruta_rasters):
        raise FileNotFoundError(f"La carpeta {ruta_rasters} no existe")

    print(f"📍 Verificando archivo de polígono: {archivo_poligono}")
    if not os.path.exists(archivo_poligono):
        raise FileNotFoundError(f"El archivo {archivo_poligono} no existe")

    # 2. Definir archivo de índice
    archivo_indice = os.path.join(ruta_rasters, 'rasters_index.csv')
    print(f"📋 Archivo de índice: {archivo_indice}")

    # 3. Buscar archivos raster actuales
    extensiones_raster = ['*.tif', '*.tiff', '*.TIF', '*.TIFF']
    archivos_raster = []
    for ext in extensiones_raster:
        archivos_raster.extend(glob.glob(os.path.join(ruta_rasters, ext)))

    print(f"🗂️  Archivos raster encontrados: {len(archivos_raster)}")
    if len(archivos_raster) == 0:
        raise ValueError("No se encontraron archivos raster en la carpeta especificada")

    # 4. Verificar si existe índice y si está actualizado
    crear_indice = False
    if os.path.exists(archivo_indice):
        print("📖 Leyendo índice existente...")
        try:
            df_indice = pd.read_csv(archivo_indice)

            # Verificar si todos los archivos del índice existen y si hay archivos nuevos
            archivos_en_indice = set(df_indice['archivo'].apply(lambda x: os.path.join(ruta_rasters, x)))
            archivos_actuales = set(archivos_raster)

            archivos_faltantes = archivos_actuales - archivos_en_indice
            archivos_eliminados = archivos_en_indice - archivos_actuales

            if len(archivos_faltantes) > 0 or len(archivos_eliminados) > 0:
                print(f"🔄 Archivos nuevos detectados: {len(archivos_faltantes)}")
                print(f"🔄 Archivos eliminados detectados: {len(archivos_eliminados)}")
                crear_indice = True
            else:
                print("✅ Índice está actualizado")

        except Exception as e:
            print(f"⚠️  Error leyendo índice: {e}")
            crear_indice = True
    else:
        print("📝 Índice no existe, se creará uno nuevo")
        crear_indice = True

    # 5. Crear o actualizar índice si es necesario
    if crear_indice:
        print("🏗️  Creando/actualizando índice de rasters con GDAL...")
        datos_indice = []

        for i, archivo in enumerate(archivos_raster):
            print(f"📊 Procesando {i + 1}/{len(archivos_raster)}: {os.path.basename(archivo)}")

            try:
                # Abrir raster con GDAL
                dataset = gdal.Open(archivo, gdal.GA_ReadOnly)
                if dataset is None:
                    print(f"⚠️  No se pudo abrir: {archivo}")
                    continue

                # Obtener extent
                geotransform = dataset.GetGeoTransform()
                width = dataset.RasterXSize
                height = dataset.RasterYSize

                minx = geotransform[0]
                maxy = geotransform[3]
                maxx = minx + (width * geotransform[1])
                miny = maxy + (height * geotransform[5])

                # Obtener CRS
                srs = osr.SpatialReference()
                srs.ImportFromWkt(dataset.GetProjection())
                crs = srs.GetAuthorityCode(None)
                if crs:
                    crs = f"EPSG:{crs}"
                else:
                    crs = dataset.GetProjection()

                datos_indice.append({
                    'archivo': os.path.basename(archivo),
                    'minx': minx,
                    'miny': miny,
                    'maxx': maxx,
                    'maxy': maxy,
                    'crs': crs
                })

                # Cerrar dataset
                dataset = None

            except Exception as e:
                print(f"⚠️  Error procesando {archivo}: {e}")
                continue

        # Guardar índice
        df_indice = pd.DataFrame(datos_indice)
        df_indice.to_csv(archivo_indice, index=False)
        print(f"✅ Índice guardado con {len(df_indice)} rasters")

    # 6. Leer polígono con GeoPandas
    print("📖 Leyendo polígono...")
    gdf_poligono = gpd.read_file(archivo_poligono)
    print(f"📐 Sistema de coordenadas del polígono: {gdf_poligono.crs}")

    # 7. Obtener sistema de coordenadas de los rasters
    print("🔍 Analizando sistema de coordenadas de los rasters...")
    crs_rasters = df_indice['crs'].iloc[0]
    print(f"📐 Sistema de coordenadas de los rasters: {crs_rasters}")

    # 8. Reproyectar polígono al sistema de coordenadas de los rasters
    print("🔄 Reproyectando polígono para intersección...")
    if str(gdf_poligono.crs) != str(crs_rasters):
        gdf_poligono_reproj = gdf_poligono.to_crs(crs_rasters)
        print(f"✅ Polígono reproyectado de {gdf_poligono.crs} a {crs_rasters}")
    else:
        gdf_poligono_reproj = gdf_poligono.copy()
        print("✅ Polígono ya está en el sistema correcto")

    # 9. Identificar rasters que intersectan usando el índice
    print("🎯 Identificando rasters intersectantes con índice ultrarrápido...")
    bounds_poligono = gdf_poligono_reproj.total_bounds
    bbox_poligono = box(bounds_poligono[0], bounds_poligono[1],
                        bounds_poligono[2], bounds_poligono[3])

    rasters_intersectantes = []

    for _, row in df_indice.iterrows():
        bbox_raster = box(row['minx'], row['miny'], row['maxx'], row['maxy'])

        if bbox_raster.intersects(bbox_poligono):
            archivo_completo = os.path.join(ruta_rasters, row['archivo'])
            if os.path.exists(archivo_completo):
                rasters_intersectantes.append(archivo_completo)

    print(f"📊 Rasters intersectantes: {len(rasters_intersectantes)} de {len(df_indice)}")
    print("🚀 ¡Intersección calculada súper rápido usando índice!")

    if len(rasters_intersectantes) == 0:
        raise ValueError("Ningún raster intersecta con el polígono especificado")

    # 10. Crear VRT con los rasters intersectantes
    print("🌐 Creando VRT (Virtual Raster) con GDAL...")

    # Crear archivo temporal para VRT
    with tempfile.NamedTemporaryFile(suffix='.vrt', delete=False) as tmp_vrt:
        archivo_vrt = tmp_vrt.name

    # Crear VRT con gdal.BuildVRT
    opciones_vrt = gdal.BuildVRTOptions(
        resolution='highest',  # Usar la resolución más alta
        resampleAlg='nearest'  # Método de remuestreo
    )

    vrt_dataset = gdal.BuildVRT(archivo_vrt, rasters_intersectantes, options=opciones_vrt)
    if vrt_dataset is None:
        raise RuntimeError("Error creando VRT")

    vrt_dataset = None  # Cerrar para liberar memoria
    print(f"✅ VRT creado exitosamente: {archivo_vrt}")

    # 11. Preparar archivo de salida
    if archivo_salida is None:
        nombre_base = os.path.splitext(os.path.basename(archivo_poligono))[0]
        archivo_salida = f"mosaico_{nombre_base}.tif"

    # 12. Crear shapefile temporal del polígono para recorte
    print("📝 Preparando polígono para recorte...")
    with tempfile.NamedTemporaryFile(suffix='.shp', delete=False) as tmp_shp:
        archivo_shp_temp = tmp_shp.name

    # Guardar polígono reproyectado temporalmente
    gdf_poligono_reproj.to_file(archivo_shp_temp.replace('.shp', '_temp.shp'))
    archivo_shp_temp = archivo_shp_temp.replace('.shp', '_temp.shp')

    # 13. Usar gdal.Warp para recortar + reproyectar en una sola operación
    print(f"⚡ Ejecutando gdal.Warp: recorte + reproyección a {crs_salida} en una operación...")

    # Opciones de Warp
    opciones_warp = gdal.WarpOptions(
        format='GTiff',
        dstSRS=crs_salida,
        cutlineDSName=archivo_shp_temp,
        cropToCutline=True,
        dstNodata=-9999,
        creationOptions=[
            'COMPRESS=LZW',
            'TILED=YES',
            'BIGTIFF=IF_SAFER'
        ],
        resampleAlg='nearest'
    )

    # Ejecutar Warp
    resultado_warp = gdal.Warp(archivo_salida, archivo_vrt, options=opciones_warp)
    if resultado_warp is None:
        raise RuntimeError("Error en gdal.Warp")

    resultado_warp = None  # Cerrar dataset
    print("✅ gdal.Warp completado exitosamente")

    # 14. Optimizar tipo de datos
    print("🔧 Optimizando tipo de datos...")

    # Leer el archivo resultante para optimizar
    dataset_resultado = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
    if dataset_resultado is None:
        raise RuntimeError("Error abriendo archivo resultado")

    # Leer muestra de datos para determinar rango
    band = dataset_resultado.GetRasterBand(1)
    width = dataset_resultado.RasterXSize
    height = dataset_resultado.RasterYSize

    # Leer muestra (máximo 1000x1000 para eficiencia)
    sample_size = min(1000, width, height)
    step_x = max(1, width // sample_size)
    step_y = max(1, height // sample_size)

    sample_data = band.ReadAsArray(0, 0, width, height, buf_xsize=sample_size, buf_ysize=sample_size)
    nodata = band.GetNoDataValue()

    dataset_resultado = None

    # Calcular estadísticas excluyendo nodata
    if nodata is not None:
        datos_validos = sample_data[sample_data != nodata]
    else:
        datos_validos = sample_data.flatten()

    if len(datos_validos) > 0:
        min_val = np.min(datos_validos)
        max_val = np.max(datos_validos)

        print(f"📈 Rango de valores (muestra): {min_val} a {max_val}")

        # Determinar tipo de datos óptimo
        if min_val >= 0 and max_val <= 255:
            dtype_gdal = gdal.GDT_Byte
            dtype_nombre = "Byte (uint8)"
        elif min_val >= -128 and max_val <= 127:
            dtype_gdal = gdal.GDT_Int16  # GDAL no tiene Int8, usar Int16
            dtype_nombre = "Int16"
        elif min_val >= 0 and max_val <= 65535:
            dtype_gdal = gdal.GDT_UInt16
            dtype_nombre = "UInt16"
        elif min_val >= -32768 and max_val <= 32767:
            dtype_gdal = gdal.GDT_Int16
            dtype_nombre = "Int16"
        elif min_val >= 0 and max_val <= 4294967295:
            dtype_gdal = gdal.GDT_UInt32
            dtype_nombre = "UInt32"
        elif min_val >= -2147483648 and max_val <= 2147483647:
            dtype_gdal = gdal.GDT_Int32
            dtype_nombre = "Int32"
        else:
            dtype_gdal = gdal.GDT_Float32
            dtype_nombre = "Float32"

        print(f"🎯 Tipo de datos óptimo: {dtype_nombre}")

        # Si necesita cambio de tipo de datos, crear versión optimizada
        dataset_actual = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
        band_actual = dataset_actual.GetRasterBand(1)
        tipo_actual = band_actual.DataType

        if tipo_actual != dtype_gdal:
            print("🔄 Convirtiendo a tipo de datos óptimo...")

            # Crear archivo temporal optimizado
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_opt:
                archivo_optimizado = tmp_opt.name

            # Usar gdal.Translate para cambiar tipo de datos
            opciones_translate = gdal.TranslateOptions(
                format='GTiff',
                outputType=dtype_gdal,
                creationOptions=[
                    'COMPRESS=LZW',
                    'TILED=YES',
                    'BIGTIFF=IF_SAFER'
                ]
            )

            resultado_translate = gdal.Translate(archivo_optimizado, archivo_salida, options=opciones_translate)
            if resultado_translate is not None:
                resultado_translate = None

                # Reemplazar archivo original con optimizado
                try:
                    os.replace(archivo_optimizado, archivo_salida)
                    print("✅ Tipo de datos optimizado")
                except OSError:
                    # Si falla replace (diferentes unidades), usar copy + remove
                    import shutil
                    shutil.copy2(archivo_optimizado, archivo_salida)
                    os.remove(archivo_optimizado)
                    print("✅ Tipo de datos optimizado (con copy)")
            else:
                print("⚠️  No se pudo optimizar tipo de datos, manteniendo original")
                if os.path.exists(archivo_optimizado):
                    os.remove(archivo_optimizado)

        dataset_actual = None

    # 15. Limpiar archivos temporales
    print("🧹 Limpiando archivos temporales...")
    archivos_temporales = [archivo_vrt, archivo_shp_temp]

    # Buscar archivos auxiliares del shapefile
    base_shp = archivo_shp_temp.replace('.shp', '')
    for ext in ['.shx', '.dbf', '.prj', '.cpg']:
        archivo_aux = base_shp + ext
        if os.path.exists(archivo_aux):
            archivos_temporales.append(archivo_aux)

    for archivo_temp in archivos_temporales:
        try:
            if os.path.exists(archivo_temp):
                os.remove(archivo_temp)
        except:
            pass  # Ignorar errores al borrar temporales

    # 16. Mostrar información final
    if os.path.exists(archivo_salida):
        tamaño_archivo = os.path.getsize(archivo_salida) / (1024 * 1024)  # MB
        print(f"✅ Proceso completado exitosamente!")
        print(f"📁 Archivo de salida: {archivo_salida}")
        print(f"📏 Tamaño del archivo: {tamaño_archivo:.2f} MB")
        print(f"🗜️  Compresión: LZW")
        print(f"📋 Índice guardado en: {archivo_indice}")
        print("=== FIN DEL PROCESO ===")

        return archivo_salida
    else:
        raise RuntimeError("Error: No se pudo crear el archivo de salida")


def C02_Crear_Mosaico(ruta_rasters, archivo_poligono, crs_salida='EPSG:4326', archivo_salida=None,
                      raster_referencia=None, resolucion=None):
    """
    Crea un mosaico de rasters para un área específica definida por un polígono.

    Esta función utiliza GDAL nativo para máximo rendimiento. Crea un VRT (Virtual Raster)
    con los rasters intersectantes y usa gdal.Warp para recortar y reproyectar en una
    sola operación ultrarrápida.

    OPTIMIZACIONES IMPLEMENTADAS:
    - Índice CSV para identificación rápida de intersecciones
    - VRT (Virtual Raster) para evitar carga de datos innecesaria
    - gdal.Warp para recorte + reproyección en una sola operación
    - Optimización automática de tipos de datos y compresión LZW
    - Control de resolución mediante raster de referencia o valor específico

    Parámetros:
    -----------
    ruta_rasters : str
        Ruta de la carpeta que contiene los archivos raster
    archivo_poligono : str
        Ruta del archivo shapefile (.shp) con el polígono de interés
    crs_salida : str, opcional
        Sistema de coordenadas de salida (por defecto 'EPSG:4326')
    archivo_salida : str, opcional
        Ruta del archivo de salida. Si no se especifica, se genera automáticamente
    raster_referencia : str, opcional
        Ruta de un raster de referencia para usar su resolución
    resolucion : float o tuple, opcional
        Resolución específica. Puede ser un valor (resolución cuadrada) o
        tuple (res_x, res_y). Unidades del sistema de coordenadas de salida.

    Nota sobre resolución:
    ---------------------
    - Si se especifica raster_referencia, se usa su resolución
    - Si se especifica resolucion, se usa ese valor
    - Si se especifican ambos, raster_referencia tiene prioridad
    - Si no se especifica ninguno, se usa 'highest' (resolución más alta disponible)

    Retorna:
    --------
    str
        Ruta del archivo de salida creado

    Ejemplo:
    --------
    >>> # Usar resolución más alta disponible
    >>> archivo_resultado = C02_Crear_Mosaico(
    ...     ruta_rasters='/ruta/a/rasters/',
    ...     archivo_poligono='/ruta/poligono.shp'
    ... )

    >>> # Usar resolución de un raster específico
    >>> archivo_resultado = C02_Crear_Mosaico(
    ...     ruta_rasters='/ruta/a/rasters/',
    ...     archivo_poligono='/ruta/poligono.shp',
    ...     raster_referencia='/ruta/referencia.tif'
    ... )

    >>> # Usar resolución específica (10 metros)
    >>> archivo_resultado = C02_Crear_Mosaico(
    ...     ruta_rasters='/ruta/a/rasters/',
    ...     archivo_poligono='/ruta/poligono.shp',
    ...     resolucion=10.0
    ... )

    >>> # Usar resolución específica diferente en X y Y
    >>> archivo_resultado = C02_Crear_Mosaico(
    ...     ruta_rasters='/ruta/a/rasters/',
    ...     archivo_poligono='/ruta/poligono.shp',
    ...     resolucion=(10.0, 5.0)  # 10m en X, 5m en Y
    ... )
    """

    print("=== INICIANDO PROCESO DE MOSAICO CON GDAL ===")

    # 1. Validar entradas
    print(f"📁 Verificando carpeta de rasters: {ruta_rasters}")
    if not os.path.exists(ruta_rasters):
        raise FileNotFoundError(f"La carpeta {ruta_rasters} no existe")

    print(f"📍 Verificando archivo de polígono: {archivo_poligono}")
    if not os.path.exists(archivo_poligono):
        raise FileNotFoundError(f"El archivo {archivo_poligono} no existe")

    # 1.1 Validar raster de referencia si se proporciona
    if raster_referencia is not None:
        print(f"🎯 Verificando raster de referencia: {raster_referencia}")
        if not os.path.exists(raster_referencia):
            raise FileNotFoundError(f"El raster de referencia {raster_referencia} no existe")

    # 1.2 Validar parámetro de resolución
    target_res_x = None
    target_res_y = None

    if raster_referencia is not None:
        print("📐 Obteniendo resolución del raster de referencia...")
        ds_ref = gdal.Open(raster_referencia, gdal.GA_ReadOnly)
        if ds_ref is None:
            raise ValueError(f"No se pudo abrir el raster de referencia: {raster_referencia}")

        gt_ref = ds_ref.GetGeoTransform()
        target_res_x = abs(gt_ref[1])  # Resolución en X
        target_res_y = abs(gt_ref[5])  # Resolución en Y

        # Obtener CRS del raster de referencia
        srs_ref = osr.SpatialReference()
        srs_ref.ImportFromWkt(ds_ref.GetProjection())
        crs_referencia = srs_ref.GetAuthorityCode(None)
        if crs_referencia:
            crs_referencia = f"EPSG:{crs_referencia}"
        else:
            crs_referencia = ds_ref.GetProjection()

        ds_ref = None

        # Si el CRS del raster de referencia es diferente al de salida, advertir
        if crs_referencia != crs_salida:
            print(f"⚠️  NOTA: Raster de referencia en {crs_referencia}, salida en {crs_salida}")
            print("   La resolución se interpretará en las unidades del CRS de salida")

        print(f"✅ Resolución del raster de referencia: {target_res_x:.6f} x {target_res_y:.6f}")

    elif resolucion is not None:
        print("📐 Procesando resolución especificada...")
        if isinstance(resolucion, (int, float)):
            target_res_x = float(resolucion)
            target_res_y = float(resolucion)
            print(f"✅ Resolución cuadrada: {target_res_x:.6f}")
        elif isinstance(resolucion, (list, tuple)) and len(resolucion) == 2:
            target_res_x = float(resolucion[0])
            target_res_y = float(resolucion[1])
            print(f"✅ Resolución X,Y: {target_res_x:.6f} x {target_res_y:.6f}")
        else:
            raise ValueError("El parámetro 'resolucion' debe ser un número o una tupla (res_x, res_y)")

        if target_res_x <= 0 or target_res_y <= 0:
            raise ValueError("Los valores de resolución deben ser positivos")
    else:
        print("📐 Sin resolución especificada, usando resolución más alta disponible")

    # 2. Definir archivo de índice
    archivo_indice = os.path.join(ruta_rasters, 'rasters_index.csv')
    print(f"📋 Archivo de índice: {archivo_indice}")

    # 3. Buscar archivos raster actuales
    #extensiones_raster = ['*.tif', '*.tiff', '*.TIF', '*.TIFF']
    extensiones_raster = ['*.tif']
    archivos_raster = []
    for ext in extensiones_raster:
        archivos_raster.extend(glob.glob(os.path.join(ruta_rasters, ext)))

    print(f"🗂️  Archivos raster encontrados: {len(archivos_raster)}")
    if len(archivos_raster) == 0:
        raise ValueError("No se encontraron archivos raster en la carpeta especificada")

    # 4. Verificar si existe índice y si está actualizado
    crear_indice = False
    if os.path.exists(archivo_indice):
        print("📖 Leyendo índice existente...")
        try:
            df_indice = pd.read_csv(archivo_indice)

            # Verificar si todos los archivos del índice existen y si hay archivos nuevos
            archivos_en_indice = set(df_indice['archivo'].apply(lambda x: os.path.join(ruta_rasters, x)))
            archivos_actuales = set(archivos_raster)

            archivos_faltantes = archivos_actuales - archivos_en_indice
            archivos_eliminados = archivos_en_indice - archivos_actuales

            if len(archivos_faltantes) > 0 or len(archivos_eliminados) > 0:
                print(f"🔄 Archivos nuevos detectados: {len(archivos_faltantes)}")
                print(f"🔄 Archivos eliminados detectados: {len(archivos_eliminados)}")
                crear_indice = True
            else:
                print("✅ Índice está actualizado")

        except Exception as e:
            print(f"⚠️  Error leyendo índice: {e}")
            crear_indice = True
    else:
        print("📝 Índice no existe, se creará uno nuevo")
        crear_indice = True

    # 5. Crear o actualizar índice si es necesario
    if crear_indice:
        print("🏗️  Creando/actualizando índice de rasters con GDAL...")
        datos_indice = []

        for i, archivo in enumerate(archivos_raster):
            print(f"📊 Procesando {i + 1}/{len(archivos_raster)}: {os.path.basename(archivo)}")

            try:
                # Abrir raster con GDAL
                dataset = gdal.Open(archivo, gdal.GA_ReadOnly)
                if dataset is None:
                    print(f"⚠️  No se pudo abrir: {archivo}")
                    continue

                # Obtener extent
                geotransform = dataset.GetGeoTransform()
                width = dataset.RasterXSize
                height = dataset.RasterYSize

                minx = geotransform[0]
                maxy = geotransform[3]
                maxx = minx + (width * geotransform[1])
                miny = maxy + (height * geotransform[5])

                # Obtener CRS
                srs = osr.SpatialReference()
                srs.ImportFromWkt(dataset.GetProjection())
                crs = srs.GetAuthorityCode(None)
                if crs:
                    crs = f"EPSG:{crs}"
                else:
                    crs = dataset.GetProjection()

                datos_indice.append({
                    'archivo': os.path.basename(archivo),
                    'minx': minx,
                    'miny': miny,
                    'maxx': maxx,
                    'maxy': maxy,
                    'crs': crs
                })

                # Cerrar dataset
                dataset = None

            except Exception as e:
                print(f"⚠️  Error procesando {archivo}: {e}")
                continue

        # Guardar índice
        df_indice = pd.DataFrame(datos_indice)
        df_indice.to_csv(archivo_indice, index=False)
        print(f"✅ Índice guardado con {len(df_indice)} rasters")

    # 6. Leer polígono con GeoPandas
    print("📖 Leyendo polígono...")
    gdf_poligono = gpd.read_file(archivo_poligono)
    print(f"📐 Sistema de coordenadas del polígono: {gdf_poligono.crs}")

    # 7. Obtener sistema de coordenadas de los rasters
    print("🔍 Analizando sistema de coordenadas de los rasters...")
    crs_rasters = df_indice['crs'].iloc[0]
    print(f"📐 Sistema de coordenadas de los rasters: {crs_rasters}")

    # 8. Reproyectar polígono al sistema de coordenadas de los rasters
    print("🔄 Reproyectando polígono para intersección...")
    if str(gdf_poligono.crs) != str(crs_rasters):
        gdf_poligono_reproj = gdf_poligono.to_crs(crs_rasters)
        print(f"✅ Polígono reproyectado de {gdf_poligono.crs} a {crs_rasters}")
    else:
        gdf_poligono_reproj = gdf_poligono.copy()
        print("✅ Polígono ya está en el sistema correcto")

    # 9. Identificar rasters que intersectan usando el índice
    print("🎯 Identificando rasters intersectantes con índice ultrarrápido...")
    bounds_poligono = gdf_poligono_reproj.total_bounds
    bbox_poligono = box(bounds_poligono[0], bounds_poligono[1],
                        bounds_poligono[2], bounds_poligono[3])

    rasters_intersectantes = []

    for _, row in df_indice.iterrows():
        bbox_raster = box(row['minx'], row['miny'], row['maxx'], row['maxy'])

        if bbox_raster.intersects(bbox_poligono):
            archivo_completo = os.path.join(ruta_rasters, row['archivo'])
            if os.path.exists(archivo_completo):
                rasters_intersectantes.append(archivo_completo)

    print(f"📊 Rasters intersectantes: {len(rasters_intersectantes)} de {len(df_indice)}")
    print("🚀 ¡Intersección calculada súper rápido usando índice!")

    if len(rasters_intersectantes) == 0:
        raise ValueError("Ningún raster intersecta con el polígono especificado")

    # 10. Crear VRT con los rasters intersectantes
    print("🌐 Creando VRT (Virtual Raster) con GDAL...")

    # Crear archivo temporal para VRT
    with tempfile.NamedTemporaryFile(suffix='.vrt', delete=False) as tmp_vrt:
        archivo_vrt = tmp_vrt.name

    # Configurar opciones del VRT según la resolución especificada
    if target_res_x is not None and target_res_y is not None:
        # Si hay resolución específica, usar 'user' y especificar la resolución en Warp
        opciones_vrt = gdal.BuildVRTOptions(
            resolution='user',
            xRes=target_res_x,
            yRes=target_res_y,
            resampleAlg='nearest'
        )
        print(f"🎯 VRT configurado con resolución específica: {target_res_x:.6f} x {target_res_y:.6f}")
    else:
        # Usar resolución más alta disponible
        opciones_vrt = gdal.BuildVRTOptions(
            resolution='highest',
            resampleAlg='nearest'
        )
        print("🎯 VRT configurado con resolución más alta disponible")

    vrt_dataset = gdal.BuildVRT(archivo_vrt, rasters_intersectantes, options=opciones_vrt)
    if vrt_dataset is None:
        raise RuntimeError("Error creando VRT")

    vrt_dataset = None  # Cerrar para liberar memoria
    print(f"✅ VRT creado exitosamente: {archivo_vrt}")

    # 11. Preparar archivo de salida
    if archivo_salida is None:
        nombre_base = os.path.splitext(os.path.basename(archivo_poligono))[0]
        if raster_referencia is not None:
            nombre_ref = os.path.splitext(os.path.basename(raster_referencia))[0]
            archivo_salida = f"mosaico_{nombre_base}_res_{nombre_ref}.tif"
        elif resolucion is not None:
            if isinstance(resolucion, (int, float)):
                archivo_salida = f"mosaico_{nombre_base}_res_{resolucion:.3f}.tif"
            else:
                archivo_salida = f"mosaico_{nombre_base}_res_{resolucion[0]:.3f}x{resolucion[1]:.3f}.tif"
        else:
            archivo_salida = f"mosaico_{nombre_base}.tif"

    # 12. Crear shapefile temporal del polígono para recorte
    print("📝 Preparando polígono para recorte...")
    with tempfile.NamedTemporaryFile(suffix='.shp', delete=False) as tmp_shp:
        archivo_shp_temp = tmp_shp.name

    # Guardar polígono reproyectado temporalmente
    gdf_poligono_reproj.to_file(archivo_shp_temp.replace('.shp', '_temp.shp'))
    archivo_shp_temp = archivo_shp_temp.replace('.shp', '_temp.shp')

    # 13. Determinar valor NoData apropiado de los rasters fuente
    print("🔍 Analizando valores NoData de los rasters fuente...")

    valores_nodata = []
    tipos_datos = []

    # Examinar una muestra de rasters intersectantes para determinar NoData común
    muestra_rasters = rasters_intersectantes[:min(5, len(rasters_intersectantes))]

    for raster_path in muestra_rasters:
        try:
            ds_temp = gdal.Open(raster_path, gdal.GA_ReadOnly)
            if ds_temp is not None:
                band_temp = ds_temp.GetRasterBand(1)
                nodata_val = band_temp.GetNoDataValue()
                data_type = band_temp.DataType

                valores_nodata.append(nodata_val)
                tipos_datos.append(data_type)

                print(
                    f"   📊 {os.path.basename(raster_path)}: NoData = {nodata_val}, Tipo = {gdal.GetDataTypeName(data_type)}")
                ds_temp = None
        except Exception as e:
            print(f"⚠️  Error leyendo NoData de {raster_path}: {e}")

    # Determinar el valor NoData más común (excluyendo None)
    valores_nodata_validos = [v for v in valores_nodata if v is not None]

    from collections import Counter
    if valores_nodata_validos:
        # Usar el valor NoData más común
        contador_nodata = Counter(valores_nodata_validos)
        nodata_final = contador_nodata.most_common(1)[0][0]
        print(f"✅ Valor NoData detectado más común: {nodata_final}")
    else:
        # Si ningún raster tiene NoData definido, usar un valor seguro basado en el tipo de datos
        tipo_mas_common = Counter(tipos_datos).most_common(1)[0][0] if tipos_datos else gdal.GDT_Float32

        # Valores NoData seguros por tipo de datos
        if tipo_mas_common in [gdal.GDT_Byte]:
            nodata_final = 255  # Para uint8, usar 255
        elif tipo_mas_common in [gdal.GDT_UInt16]:
            nodata_final = 65535  # Para uint16, usar valor máximo
        elif tipo_mas_common in [gdal.GDT_Int16]:
            nodata_final = -32768  # Para int16, usar valor mínimo
        elif tipo_mas_common in [gdal.GDT_UInt32]:
            nodata_final = 4294967295  # Para uint32, usar valor máximo
        elif tipo_mas_common in [gdal.GDT_Int32]:
            nodata_final = -2147483648  # Para int32, usar valor mínimo
        else:
            nodata_final = -9999.0  # Para float, usar -9999

        print(f"✅ No se detectó NoData en rasters fuente. Usando valor seguro: {nodata_final}")

    # 14. Configurar opciones de Warp
    print(f"⚡ Configurando gdal.Warp: recorte + reproyección a {crs_salida}...")

    # Opciones base de Warp
    warp_options = {
        'format': 'GTiff',
        'dstSRS': crs_salida,
        'cutlineDSName': archivo_shp_temp,
        'cropToCutline': True,
        'dstNodata': nodata_final,
        'creationOptions': [
            'COMPRESS=LZW',
            'TILED=YES',
            'BIGTIFF=IF_SAFER'
        ],
        'resampleAlg': 'nearest'
    }

    # 15. Añadir resolución específica si está definida
    if target_res_x is not None and target_res_y is not None:
        warp_options['xRes'] = target_res_x
        warp_options['yRes'] = target_res_y
        print(f"🎯 Warp configurado con resolución: {target_res_x:.6f} x {target_res_y:.6f}")

    opciones_warp = gdal.WarpOptions(**warp_options)

    # 16. Ejecutar Warp
    print("⚡ Ejecutando gdal.Warp...")
    resultado_warp = gdal.Warp(archivo_salida, archivo_vrt, options=opciones_warp)
    if resultado_warp is None:
        raise RuntimeError("Error en gdal.Warp")

    resultado_warp = None  # Cerrar dataset
    print("✅ gdal.Warp completado exitosamente")

    # 17. Mostrar información de resolución final y NoData
    print("📐 Verificando información final del raster...")
    ds_final = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
    if ds_final is not None:
        gt_final = ds_final.GetGeoTransform()
        res_x_final = abs(gt_final[1])
        res_y_final = abs(gt_final[5])

        band_final = ds_final.GetRasterBand(1)
        nodata_resultado = band_final.GetNoDataValue()

        print(f"✅ Resolución final del mosaico: {res_x_final:.6f} x {res_y_final:.6f}")
        print(f"✅ Valor NoData final: {nodata_resultado}")
        ds_final = None

    # 18. Optimizar tipo de datos (preservando NoData correcto)
    print("🔧 Optimizando tipo de datos...")

    # Leer el archivo resultante para optimizar
    dataset_resultado = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
    if dataset_resultado is None:
        raise RuntimeError("Error abriendo archivo resultado")

    # Leer muestra de datos para determinar rango
    band = dataset_resultado.GetRasterBand(1)
    width = dataset_resultado.RasterXSize
    height = dataset_resultado.RasterYSize

    # Obtener el valor NoData actual
    nodata_actual = band.GetNoDataValue()
    print(f"📊 Valor NoData preservado: {nodata_actual}")

    # Leer muestra (máximo 1000x1000 para eficiencia)
    sample_size = min(1000, width, height)
    step_x = max(1, width // sample_size)
    step_y = max(1, height // sample_size)

    sample_data = band.ReadAsArray(0, 0, width, height, buf_xsize=sample_size, buf_ysize=sample_size)
    dataset_resultado = None

    # Calcular estadísticas excluyendo el valor NoData correcto
    if nodata_actual is not None:
        # Usar una tolerancia pequeña para comparaciones de punto flotante
        if isinstance(nodata_actual, float):
            mask_validos = ~np.isclose(sample_data, nodata_actual, rtol=1e-10, atol=1e-10)
        else:
            mask_validos = sample_data != nodata_actual
        datos_validos = sample_data[mask_validos]
    else:
        datos_validos = sample_data.flatten()

    if len(datos_validos) > 0:
        min_val = np.min(datos_validos)
        max_val = np.max(datos_validos)

        print(f"📈 Rango de valores válidos (excluyendo NoData): {min_val} a {max_val}")

        # Determinar tipo de datos óptimo considerando el valor NoData
        # Necesitamos asegurar que el tipo de datos puede representar tanto los datos como el NoData
        valores_a_considerar = [min_val, max_val]
        if nodata_actual is not None:
            valores_a_considerar.append(nodata_actual)

        rango_total_min = min(valores_a_considerar)
        rango_total_max = max(valores_a_considerar)

        print(f"📈 Rango total (incluyendo NoData): {rango_total_min} a {rango_total_max}")

        # Determinar tipo de datos óptimo que pueda contener todos los valores
        if rango_total_min >= 0 and rango_total_max <= 255:
            dtype_gdal = gdal.GDT_Byte
            dtype_nombre = "Byte (uint8)"
        elif rango_total_min >= -128 and rango_total_max <= 127:
            dtype_gdal = gdal.GDT_Int16  # GDAL no tiene Int8, usar Int16
            dtype_nombre = "Int16"
        elif rango_total_min >= 0 and rango_total_max <= 65535:
            dtype_gdal = gdal.GDT_UInt16
            dtype_nombre = "UInt16"
        elif rango_total_min >= -32768 and rango_total_max <= 32767:
            dtype_gdal = gdal.GDT_Int16
            dtype_nombre = "Int16"
        elif rango_total_min >= 0 and rango_total_max <= 4294967295:
            dtype_gdal = gdal.GDT_UInt32
            dtype_nombre = "UInt32"
        elif rango_total_min >= -2147483648 and rango_total_max <= 2147483647:
            dtype_gdal = gdal.GDT_Int32
            dtype_nombre = "Int32"
        else:
            dtype_gdal = gdal.GDT_Float32
            dtype_nombre = "Float32"

        print(f"🎯 Tipo de datos óptimo: {dtype_nombre}")

        # Si necesita cambio de tipo de datos, crear versión optimizada
        dataset_actual = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
        band_actual = dataset_actual.GetRasterBand(1)
        tipo_actual = band_actual.DataType

        if tipo_actual != dtype_gdal:
            print("🔄 Convirtiendo a tipo de datos óptimo...")

            # Crear archivo temporal optimizado
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_opt:
                archivo_optimizado = tmp_opt.name

            # Usar gdal.Translate para cambiar tipo de datos, preservando NoData
            opciones_translate = gdal.TranslateOptions(
                format='GTiff',
                outputType=dtype_gdal,
                noData=nodata_actual,  # Preservar el valor NoData original
                creationOptions=[
                    'COMPRESS=LZW',
                    'TILED=YES',
                    'BIGTIFF=IF_SAFER'
                ]
            )

            resultado_translate = gdal.Translate(archivo_optimizado, archivo_salida, options=opciones_translate)
            if resultado_translate is not None:
                resultado_translate = None

                # Reemplazar archivo original con optimizado
                try:
                    os.replace(archivo_optimizado, archivo_salida)
                    print("✅ Tipo de datos optimizado (NoData preservado)")
                except OSError:
                    # Si falla replace (diferentes unidades), usar copy + remove
                    import shutil
                    shutil.copy2(archivo_optimizado, archivo_salida)
                    os.remove(archivo_optimizado)
                    print("✅ Tipo de datos optimizado con copy (NoData preservado)")
            else:
                print("⚠️  No se pudo optimizar tipo de datos, manteniendo original")
                if os.path.exists(archivo_optimizado):
                    os.remove(archivo_optimizado)
        else:
            print("✅ Tipo de datos ya es óptimo")

        dataset_actual = None

    # 17. Limpiar archivos temporales
    print("🧹 Limpiando archivos temporales...")
    archivos_temporales = [archivo_vrt, archivo_shp_temp]

    # Buscar archivos auxiliares del shapefile
    base_shp = archivo_shp_temp.replace('.shp', '')
    for ext in ['.shx', '.dbf', '.prj', '.cpg']:
        archivo_aux = base_shp + ext
        if os.path.exists(archivo_aux):
            archivos_temporales.append(archivo_aux)

    for archivo_temp in archivos_temporales:
        try:
            if os.path.exists(archivo_temp):
                os.remove(archivo_temp)
        except:
            pass  # Ignorar errores al borrar temporales

    # 18. Mostrar información final
    if os.path.exists(archivo_salida):
        tamaño_archivo = os.path.getsize(archivo_salida) / (1024 * 1024)  # MB
        print(f"✅ Proceso completado exitosamente!")
        print(f"📁 Archivo de salida: {archivo_salida}")
        print(f"📏 Tamaño del archivo: {tamaño_archivo:.2f} MB")

        # Mostrar información de resolución utilizada
        if target_res_x is not None and target_res_y is not None:
            if raster_referencia is not None:
                print(f"🎯 Resolución (del raster de referencia): {target_res_x:.6f} x {target_res_y:.6f}")
            else:
                print(f"🎯 Resolución (especificada): {target_res_x:.6f} x {target_res_y:.6f}")
        else:
            print("🎯 Resolución: Más alta disponible")

        # Verificar el valor NoData final
        ds_verificacion = gdal.Open(archivo_salida, gdal.GA_ReadOnly)
        if ds_verificacion is not None:
            band_verificacion = ds_verificacion.GetRasterBand(1)
            nodata_final_verificado = band_verificacion.GetNoDataValue()
            ds_verificacion = None
            print(f"🔍 Valor NoData final verificado: {nodata_final_verificado}")

        print(f"🗜️  Compresión: LZW")
        print(f"📋 Índice guardado en: {archivo_indice}")
        print("=== FIN DEL PROCESO ===")

        return archivo_salida
    else:
        raise RuntimeError("Error: No se pudo crear el archivo de salida")

# ----------------------------------------------------------------------------------------------------------------------
# DISTANCIA DE PIXELES
# ----------------------------------------------------------------------------------------------------------------------
def calcular_distancia_a_valor(
        raster_path: str,
        valor_objetivo: int,
        salida_path: str,
        unidad_distancia: str = "metros"
) -> Tuple[float, float, int]:
    """
    Calcula la distancia euclidiana desde cada píxel hasta el píxel más cercano
    que tenga un valor igual al valor objetivo.

    Esta función utiliza la transformada de distancia euclidiana para calcular
    eficientemente la distancia desde cada píxel hasta el píxel objetivo más cercano.
    Las distancias se calculan considerando la resolución espacial del raster.

    Parameters
    ----------
    raster_path : str
        Ruta del raster de entrada (valores categóricos o continuos).
    valor_objetivo : int
        Valor del píxel al cual se quiere calcular la distancia.
    salida_path : str
        Ruta donde se guardará el raster de distancia resultante.
    unidad_distancia : str, optional
        Unidad de medida para las distancias ("metros", "kilometros", "pixeles").
        Por defecto es "metros".

    Returns
    -------
    Tuple[float, float, int]
        Tupla con (distancia_mínima, distancia_máxima, píxeles_objetivo_encontrados)

    Raises
    ------
    ValueError
        Si no se encuentran píxeles con el valor objetivo.
        Si la unidad de distancia no es válida.
    FileNotFoundError
        Si el archivo raster no existe.

    Examples
    --------
    >>> min_dist, max_dist, n_pixels = calcular_distancia_a_valor(
    ...     "land_cover.tif",
    ...     valor_objetivo=13,
    ...     salida_path="distancia_bosque.tif"
    ... )
    >>> print(f"Distancias: {min_dist:.2f} - {max_dist:.2f} m, {n_pixels} píxeles objetivo")

    Notes
    -----
    - La función utiliza scipy.ndimage.distance_transform_edt para cálculos eficientes
    - Las distancias se calculan en unidades del sistema de coordenadas del raster
    - Los píxeles NoData se excluyen del cálculo
    - El resultado se guarda como float32 con compresión LZW
    """
    print("🎯 INICIANDO CÁLCULO DE DISTANCIA A VALOR OBJETIVO")
    print("=" * 60)

    # Validar unidad de distancia
    unidades_validas = {"metros", "kilometros", "pixeles"}
    if unidad_distancia not in unidades_validas:
        raise ValueError(f"Unidad '{unidad_distancia}' no válida. Use: {unidades_validas}")

    print(f"📁 Raster de entrada: {raster_path}")
    print(f"🎯 Valor objetivo: {valor_objetivo}")
    print(f"📏 Unidad de distancia: {unidad_distancia}")
    print(f"💾 Archivo de salida: {salida_path}")
    print()

    total_start = time.time()

    with rasterio.open(raster_path) as src:
        print("📊 INFORMACIÓN DEL RASTER:")
        print(f"  📐 Dimensiones: {src.width} x {src.height}")
        print(f"  🌍 CRS: {src.crs}")
        print(f"  📏 Resolución: {src.transform[0]:.6f} x {abs(src.transform[4]):.6f}")
        print()

        # Leer datos y máscara
        read_start = time.time()
        data = src.read(1)
        mask = src.read_masks(1) > 0  # máscara de datos válidos (no NoData)
        transform = src.transform
        perfil = src.profile.copy()
        read_time = time.time() - read_start

        print(f"⏱️  Datos leídos en: {read_time:.3f}s")

        # Obtener resolución en X e Y
        res_x = abs(transform.a)
        res_y = abs(transform.e)
        print(f"📏 Resolución espacial: {res_x:.6f} x {res_y:.6f}")

        # Análisis inicial de datos
        analysis_start = time.time()
        pixeles_validos = np.sum(mask)
        pixeles_objetivo = np.sum((data == valor_objetivo) & mask)
        valores_unicos = np.unique(data[mask])
        analysis_time = time.time() - analysis_start

        print(f"📊 ANÁLISIS DE DATOS:")
        print(f"  📈 Píxeles válidos: {pixeles_validos:,} de {data.size:,}")
        print(f"  🎯 Píxeles con valor objetivo ({valor_objetivo}): {pixeles_objetivo:,}")
        print(f"  🔢 Valores únicos en el raster: {len(valores_unicos)}")
        print(f"  📊 Rango de valores: {valores_unicos.min()} - {valores_unicos.max()}")
        print(f"⏱️  Análisis completado en: {analysis_time:.3f}s")
        print()

        if pixeles_objetivo == 0:
            raise ValueError(f"No se encontraron píxeles con valor {valor_objetivo}")

        # Crear matriz para cálculo de distancia
        print("🔧 PREPARANDO CÁLCULO DE DISTANCIA...")
        prep_start = time.time()

        # Crear máscara booleana: True donde NO está el valor objetivo
        # (distance_transform_edt calcula distancia desde False/0)
        matriz_origen = ~((data == valor_objetivo) & mask)

        # Aplicar máscara de nodata - forzar NoData a ser parte del fondo
        matriz_origen[~mask] = True

        prep_time = time.time() - prep_start
        print(f"  ✅ Matriz de origen preparada en: {prep_time:.3f}s")
        print(f"  🎯 Píxeles origen (valor {valor_objetivo}): {np.sum(~matriz_origen):,}")
        print(f"  🌫️  Píxeles fondo (otros valores + NoData): {np.sum(matriz_origen):,}")
        print()

        # Calcular distancia euclidiana
        print("📐 CALCULANDO DISTANCIA EUCLIDIANA...")
        dist_start = time.time()

        # Calcular en píxeles y convertir a unidades espaciales
        distancia_pix = distance_transform_edt(
            matriz_origen,
            sampling=(res_y, res_x)
        )

        dist_time = time.time() - dist_start
        print(f"⏱️  Cálculo de distancia completado en: {dist_time:.3f}s")

        # Convertir unidades si es necesario
        conversion_start = time.time()
        if unidad_distancia == "metros":
            distancia_final = distancia_pix.astype('float32')
            factor_conversion = 1.0
            unidad_texto = "metros"
        elif unidad_distancia == "kilometros":
            distancia_final = (distancia_pix / 1000.0).astype('float32')
            factor_conversion = 1000.0
            unidad_texto = "kilómetros"
        else:  # pixeles
            distancia_final = (distancia_pix / ((res_x + res_y) / 2)).astype('float32')
            factor_conversion = (res_x + res_y) / 2
            unidad_texto = "píxeles"

        conversion_time = time.time() - conversion_start

        # Aplicar máscara NoData al resultado
        distancia_final[~mask] = np.nan

        # Estadísticas del resultado
        stats_start = time.time()
        distancias_validas = distancia_final[mask & np.isfinite(distancia_final)]
        min_distancia = np.min(distancias_validas) if len(distancias_validas) > 0 else 0.0
        max_distancia = np.max(distancias_validas) if len(distancias_validas) > 0 else 0.0
        media_distancia = np.mean(distancias_validas) if len(distancias_validas) > 0 else 0.0
        stats_time = time.time() - stats_start

        print(f"📊 ESTADÍSTICAS DE DISTANCIA:")
        print(f"  📏 Unidad final: {unidad_texto}")
        if factor_conversion != 1.0:
            print(f"  🔄 Factor de conversión aplicado: {factor_conversion:.6f}")
        print(f"  📈 Distancia mínima: {min_distancia:.3f} {unidad_texto}")
        print(f"  📈 Distancia máxima: {max_distancia:.3f} {unidad_texto}")
        print(f"  📈 Distancia promedio: {media_distancia:.3f} {unidad_texto}")
        print(f"  📊 Píxeles con distancia válida: {len(distancias_validas):,}")
        print(f"⏱️  Estadísticas calculadas en: {stats_time:.3f}s")
        print()

        # Preparar perfil de salida
        print("💾 GUARDANDO RESULTADO...")
        save_start = time.time()

        perfil.update(
            dtype='float32',
            compress='lzw',
            nodata=np.nan
        )

        # Escribir raster de salida
        with rasterio.open(salida_path, 'w', **perfil) as dst:
            dst.write(distancia_final, 1)

        save_time = time.time() - save_start
        total_time = time.time() - total_start

        print(f"⏱️  Archivo guardado en: {save_time:.3f}s")
        print()

    print("🎉 CÁLCULO DE DISTANCIA COMPLETADO!")
    print("=" * 60)
    print(f"⏱️  Tiempo total: {total_time:.2f}s")
    print(f"💾 Raster de distancias guardado en: {salida_path}")
    print(f"✅ Proceso finalizado correctamente")

    return min_distancia, max_distancia, pixeles_objetivo

# ----------------------------------------------------------------------------------------------------------------------
# VECINOS
# ----------------------------------------------------------------------------------------------------------------------
def seleccionar_pixels_con_vecinos(
        raster_path: str,
        valor_objetivo: int,
        vecinos_minimos: int,
        tam_kernel: int,
        salida_path: str,
        incluir_centro: bool = False
) -> Tuple[int, int, float]:
    """
    Selecciona píxeles con un valor específico que tienen al menos N vecinos contiguos
    con el mismo valor, dentro de una vecindad definida por un kernel cuadrado.

    Esta función identifica píxeles que forman parte de parches o clusters del valor
    objetivo, útil para filtrar píxeles aislados y mantener solo áreas conectadas
    de un tamaño mínimo.

    Parameters
    ----------
    raster_path : str
        Ruta del raster de entrada.
    valor_objetivo : int
        Valor objetivo a analizar.
    vecinos_minimos : int
        Número mínimo de vecinos con el mismo valor requeridos para seleccionar el píxel.
    tam_kernel : int
        Tamaño del kernel cuadrado de vecindad (debe ser impar: 3, 5, 7, etc.).
    salida_path : str
        Ruta donde se guardará el raster binario resultante (1: cumple, 0: no cumple).
    incluir_centro : bool, optional
        Si True, incluye el píxel central en el conteo de vecinos.
        Por defecto es False.

    Returns
    -------
    Tuple[int, int, float]
        Tupla con (píxeles_originales, píxeles_seleccionados, porcentaje_retenido)

    Raises
    ------
    AssertionError
        Si el tamaño del kernel no es impar.
    ValueError
        Si no se encuentran píxeles con el valor objetivo.
    FileNotFoundError
        Si el archivo raster no existe.

    Examples
    --------
    >>> orig, sel, pct = seleccionar_pixels_con_vecinos(
    ...     "land_cover.tif",
    ...     valor_objetivo=13,
    ...     vecinos_minimos=5,
    ...     tam_kernel=3,
    ...     salida_path="bosque_filtrado.tif"
    ... )
    >>> print(f"Píxeles retenidos: {sel}/{orig} ({pct:.1f}%)")

    Notes
    -----
    - El kernel se centra en cada píxel y cuenta vecinos dentro de la ventana
    - La convolución se realiza con scipy.ndimage.convolve
    - Solo píxeles con el valor objetivo pueden ser seleccionados
    - Los píxeles NoData se excluyen del análisis
    - El resultado es un raster binario (uint8) con compresión LZW
    """
    print("🔍 INICIANDO SELECCIÓN DE PÍXELES CON VECINOS")
    print("=" * 60)

    # Validaciones
    assert tam_kernel % 2 == 1, "El tamaño del kernel debe ser un número impar (3, 5, 7, ...)."
    assert tam_kernel >= 3, "El tamaño mínimo del kernel es 3."
    assert vecinos_minimos >= 0, "El número de vecinos mínimos debe ser >= 0."

    print(f"📁 Raster de entrada: {raster_path}")
    print(f"🎯 Valor objetivo: {valor_objetivo}")
    print(f"👥 Vecinos mínimos requeridos: {vecinos_minimos}")
    print(f"🔲 Tamaño del kernel: {tam_kernel} x {tam_kernel}")
    print(f"🎯 Incluir píxel central en conteo: {incluir_centro}")
    print(f"💾 Archivo de salida: {salida_path}")
    print()

    total_start = time.time()

    with rasterio.open(raster_path) as src:
        print("📊 INFORMACIÓN DEL RASTER:")
        print(f"  📐 Dimensiones: {src.width} x {src.height}")
        print(f"  🌍 CRS: {src.crs}")
        print(f"  📏 Resolución: {src.transform[0]:.6f} x {abs(src.transform[4]):.6f}")
        print()

        # Leer datos y máscara
        read_start = time.time()
        data = src.read(1)
        mask = src.read_masks(1) > 0  # máscara de datos válidos
        perfil = src.profile.copy()
        read_time = time.time() - read_start

        print(f"⏱️  Datos leídos en: {read_time:.3f}s")

        # Análisis inicial de datos
        analysis_start = time.time()
        pixeles_validos = np.sum(mask)
        pixeles_objetivo_total = np.sum((data == valor_objetivo) & mask)
        valores_unicos = np.unique(data[mask])
        analysis_time = time.time() - analysis_start

        print(f"📊 ANÁLISIS DE DATOS:")
        print(f"  📈 Píxeles válidos: {pixeles_validos:,} de {data.size:,}")
        print(f"  🎯 Píxeles con valor objetivo ({valor_objetivo}): {pixeles_objetivo_total:,}")
        print(f"  🔢 Valores únicos en el raster: {len(valores_unicos)}")
        print(f"  📊 Rango de valores: {valores_unicos.min()} - {valores_unicos.max()}")
        print(f"⏱️  Análisis completado en: {analysis_time:.3f}s")
        print()

        if pixeles_objetivo_total == 0:
            raise ValueError(f"No se encontraron píxeles con valor {valor_objetivo}")

        # Crear máscara binaria de píxeles con valor objetivo
        print("🔧 CREANDO MÁSCARA BINARIA...")
        mask_start = time.time()

        binaria = (data == valor_objetivo) & mask

        mask_time = time.time() - mask_start
        print(f"  ✅ Máscara binaria creada en: {mask_time:.3f}s")
        print(f"  🎯 Píxeles True en máscara: {np.sum(binaria):,}")
        print()

        # Crear kernel dinámicamente
        print("🔲 CREANDO KERNEL DE VECINDAD...")
        kernel_start = time.time()

        kernel = np.ones((tam_kernel, tam_kernel), dtype=np.uint8)
        centro = tam_kernel // 2

        if not incluir_centro:
            kernel[centro, centro] = 0  # excluir el píxel central del conteo

        vecinos_max_posibles = np.sum(kernel)

        kernel_time = time.time() - kernel_start
        print(f"  🔲 Kernel {tam_kernel}x{tam_kernel} creado en: {kernel_time:.3f}s")
        print(f"  👥 Máximo vecinos posibles por píxel: {vecinos_max_posibles}")
        print(f"  🎯 Píxel central incluido: {incluir_centro}")
        print()

        # Aplicar convolución para contar vecinos válidos
        print("🔄 CALCULANDO CONTEO DE VECINOS...")
        conv_start = time.time()

        conteo_vecinos = convolve(
            binaria.astype(np.uint8),
            kernel,
            mode='constant',
            cval=0
        )

        conv_time = time.time() - conv_start
        print(f"⏱️  Convolución completada en: {conv_time:.3f}s")

        # Estadísticas del conteo de vecinos
        stats_start = time.time()
        conteos_objetivo = conteo_vecinos[binaria]
        if len(conteos_objetivo) > 0:
            min_vecinos = np.min(conteos_objetivo)
            max_vecinos = np.max(conteos_objetivo)
            media_vecinos = np.mean(conteos_objetivo)
            print(
                f"  📊 Vecinos por píxel objetivo - Min: {min_vecinos}, Max: {max_vecinos}, Media: {media_vecinos:.1f}")

        # Distribución de vecinos
        hist_vecinos, bins = np.histogram(conteos_objetivo, bins=min(vecinos_max_posibles + 1, 20))
        print(f"  📈 Distribución de vecinos:")
        for i, count in enumerate(hist_vecinos):
            if count > 0:
                print(f"    {i} vecinos: {count:,} píxeles ({count / len(conteos_objetivo) * 100:.1f}%)")

        stats_time = time.time() - stats_start
        print(f"⏱️  Estadísticas calculadas en: {stats_time:.3f}s")
        print()

        # Selección final: píxel objetivo Y vecinos suficientes
        print("✨ APLICANDO CRITERIO DE SELECCIÓN...")
        selection_start = time.time()

        seleccion = binaria & (conteo_vecinos >= vecinos_minimos)
        pixeles_seleccionados = np.sum(seleccion)
        porcentaje_retenido = (
                                          pixeles_seleccionados / pixeles_objetivo_total) * 100 if pixeles_objetivo_total > 0 else 0.0

        selection_time = time.time() - selection_start

        print(f"  🎯 Píxeles originales con valor {valor_objetivo}: {pixeles_objetivo_total:,}")
        print(f"  ✅ Píxeles seleccionados (>= {vecinos_minimos} vecinos): {pixeles_seleccionados:,}")
        print(f"  📊 Porcentaje retenido: {porcentaje_retenido:.2f}%")
        print(f"  🗑️  Píxeles filtrados (insuficientes vecinos): {pixeles_objetivo_total - pixeles_seleccionados:,}")
        print(f"⏱️  Selección aplicada en: {selection_time:.3f}s")
        print()

        # Estadísticas espaciales adicionales
        if pixeles_seleccionados > 0:
            print("📍 ANÁLISIS ESPACIAL ADICIONAL...")
            spatial_start = time.time()

            # Encontrar coordenadas de píxeles seleccionados
            coords_seleccionados = np.where(seleccion)
            if len(coords_seleccionados[0]) > 0:
                # Calcular dispersión espacial
                coords_y, coords_x = coords_seleccionados
                centro_y, centro_x = np.mean(coords_y), np.mean(coords_x)
                dispersión = np.sqrt(np.mean((coords_y - centro_y) ** 2 + (coords_x - centro_x) ** 2))

                # Bounding box
                min_y, max_y = np.min(coords_y), np.max(coords_y)
                min_x, max_x = np.min(coords_x), np.max(coords_x)
                bbox_height = max_y - min_y + 1
                bbox_width = max_x - min_x + 1

                print(f"  📍 Centro geométrico: ({centro_x:.1f}, {centro_y:.1f})")
                print(f"  📏 Dispersión espacial: {dispersión:.1f} píxeles")
                print(f"  📦 Bounding box: {bbox_width} x {bbox_height} píxeles")

            spatial_time = time.time() - spatial_start
            print(f"⏱️  Análisis espacial en: {spatial_time:.3f}s")
            print()

        # Preparar y guardar resultado
        print("💾 GUARDANDO RESULTADO...")
        save_start = time.time()

        # Actualizar perfil de salida
        perfil.update(
            dtype='uint8',
            compress='lzw',
            nodata=0
        )

        with rasterio.open(salida_path, 'w', **perfil) as dst:
            # Convertir a uint8 para guardar espacio
            resultado_uint8 = seleccion.astype('uint8')
            dst.write(resultado_uint8, 1)

        save_time = time.time() - save_start
        total_time = time.time() - total_start

        print(f"⏱️  Archivo guardado en: {save_time:.3f}s")
        print()

    print("🎉 SELECCIÓN DE PÍXELES COMPLETADA!")
    print("=" * 60)
    print(f"⏱️  Tiempo total: {total_time:.2f}s")
    print(f"📊 Resumen final:")
    print(f"  🎯 Píxeles originales: {pixeles_objetivo_total:,}")
    print(f"  ✅ Píxeles seleccionados: {pixeles_seleccionados:,}")
    print(f"  📈 Porcentaje retenido: {porcentaje_retenido:.2f}%")
    print(f"💾 Raster binario guardado en: {salida_path}")
    print(f"✅ Proceso finalizado correctamente")


# ----------------------------------------------------------------------------------------------------------------------
# Extraer valores de desafíos
# ----------------------------------------------------------------------------------------------------------------------
def extract_pixel_counts(shapefile_path, raster_path, output_csv=None, NameCol='cantidad_pixeles'):
    """
    Extrae conteos de píxeles por valor de un raster recortado por una cuenca.

    Descripción:
        Recorta un raster usando la geometría de una cuenca y cuenta la frecuencia
        de cada valor de píxel. Optimizado para rasters con valores enteros 0-5.

    Parámetros:
        shapefile_path (str): Ruta al archivo shapefile de la cuenca.
                             Debe estar en coordenadas EPSG:4326.
        raster_path (str): Ruta al archivo raster a procesar.
                          Debe estar en coordenadas EPSG:4326 con valores enteros 0-5.
        output_csv (str, opcional): Ruta donde guardar el resultado en formato CSV.
                                   Si es None, no se guarda archivo.

    Retorna:
        pandas.DataFrame: DataFrame con columnas:
            - 'categoria' (int): Valor del píxel (0-5)
            - 'cantidad_pixeles' (int): Número de píxeles con ese valor

    Errores:
        FileNotFoundError: Si no se encuentran los archivos de entrada
        ValueError: Si no hay intersección entre shapefile y raster

    Ejemplo:
        >>> df = extract_pixel_counts('cuenca.shp', 'landuse.tif', 'conteo.csv')
        >>> print(df)
           categoria  cantidad_pixeles
        0          1               150
        1          2               320
        2          3               180

    Notas:
        - Usa procesamiento en disco para eficiencia con archivos grandes
        - Solo procesa la primera banda del raster
        - Filtra automáticamente valores NoData
    """

    print("📍 Iniciando extracción de conteos de píxeles...")

    # Leer geometría de la cuenca
    print("📂 Cargando geometría de la cuenca...")
    cuenca = gpd.read_file(shapefile_path)
    geometry = cuenca.geometry.iloc[0]
    print(f"   ✓ Shapefile cargado: {len(cuenca)} feature(s)")
    print(f"   ✓ CRS: {cuenca.crs}")
    print(f"   ✓ Área polígono: {geometry.area:.8f} grados²")

    # Abrir raster y recortar con máscara (procesamiento en disco)
    print("🔄 Procesando raster...")
    with rasterio.open(raster_path) as src:
        print(f"   ✓ Raster abierto: {src.width}x{src.height} píxeles")
        print(f"   ✓ CRS raster: {src.crs}")
        print(f"   ✓ NoData value: {src.nodata}")

        # Recortar usando la geometría como máscara
        print("✂️  Recortando raster con geometría de la cuenca...")
        masked_data, masked_transform = rasterio.mask.mask(
            src, [geometry], crop=True, nodata=src.nodata
        )

        # Extraer solo la primera banda (asumir raster de una banda)
        pixel_values = masked_data[0]
        print(f"   ✓ Dimensiones del recorte: {pixel_values.shape}")
        print(f"   ✓ Total píxeles en recorte: {pixel_values.size}")

        # Filtrar valores válidos (no-nodata)
        print("🔍 Filtrando píxeles válidos...")
        valid_mask = pixel_values != src.nodata if src.nodata is not None else np.ones_like(pixel_values, dtype=bool)
        valid_pixels = pixel_values[valid_mask]
        print(f"   ✓ Píxeles válidos encontrados: {len(valid_pixels)}")
        print(f"   ✓ Píxeles NoData descartados: {pixel_values.size - len(valid_pixels)}")

    # Contar valores únicos de forma eficiente
    print("📊 Contando valores únicos...")
    unique_values, counts = np.unique(valid_pixels, return_counts=True)
    print(f"   ✓ Valores únicos encontrados: {len(unique_values)}")
    print(f"   ✓ Rango de valores: {unique_values.min()} - {unique_values.max()}")

    # Crear DataFrame resultado
    print("📋 Creando DataFrame resultado...")
    df = pd.DataFrame({
        'categoria': unique_values.astype(int),
        NameCol: counts
    })

    # Filtrar solo valores 0-5 si es necesario
    original_rows = len(df)
    df = df[df['categoria'].between(0, 5)].reset_index(drop=True)
    filtered_rows = original_rows - len(df)

    if filtered_rows > 0:
        print(f"   ⚠️  {filtered_rows} categorías fuera del rango 0-5 fueron excluidas")

    print(f"   ✓ DataFrame creado: {len(df)} categorías")
    print(f"   ✓ Total píxeles clasificados: {df[NameCol].sum()}")

    # Mostrar resumen de resultados
    print("\n📈 Resumen de conteos por categoría:")
    for _, row in df.iterrows():
        percentage = (row[NameCol] / df[NameCol].sum()) * 100
        print(f"   Categoría {row['categoria']}: {row[NameCol]} píxeles ({percentage:.1f}%)")

    # Guardar CSV si se especifica ruta
    if output_csv:
        print(f"\n💾 Guardando resultado en: {output_csv}")
        df.to_csv(output_csv, index=False)
        print("   ✓ Archivo CSV guardado exitosamente")

    print("✅ Proceso completado exitosamente")
    df = df.set_index("categoria")
    return df


def classify_continuous_raster_old(shapefile_path, raster_path, method='quantiles', custom_breaks=None, output_csv=None, NameCol='cantidad_pixeles'):
    """
    Clasifica un raster continuo en 5 categorías y extrae conteos de píxeles.

    Descripción:
        Recorta un raster con valores continuos usando una geometría de cuenca,
        clasifica los valores en 5 categorías mediante diferentes métodos estadísticos
        y cuenta la frecuencia de píxeles en cada categoría.

    Parámetros:
        shapefile_path (str): Ruta al archivo shapefile de la cuenca.
                             Debe estar en coordenadas EPSG:4326.
        raster_path (str): Ruta al archivo raster con valores continuos.
                          Debe estar en coordenadas EPSG:4326.
        method (str): Método de clasificación a utilizar:
                     - 'quantiles': Percentiles 20, 40, 60, 80
                     - 'equal': Intervalos iguales
                     - 'jenks': Natural breaks (aproximado con K-means)
                     - 'std': Basado en desviación estándar
                     - 'custom': Rangos definidos manualmente
        custom_breaks (list, opcional): Lista con exactamente 6 valores numéricos
                                       [min, break1, break2, break3, break4, max].
                                       Requerido solo cuando method='custom'.
        output_csv (str, opcional): Ruta donde guardar el resultado en formato CSV.
                                   Si es None, no se guarda archivo.

    Retorna:
        pandas.DataFrame: DataFrame con columnas:
            - 'categoria' (int): Número de categoría (1-5)
            - 'cantidad_pixeles' (int): Número de píxeles en cada categoría
            - 'rango_min' (float): Valor mínimo del rango de la categoría
            - 'rango_max' (float): Valor máximo del rango de la categoría

    Errores:
        FileNotFoundError: Si no se encuentran los archivos de entrada
        ValueError: Si method='custom' y custom_breaks no tiene 6 valores
        ValueError: Si no hay intersección entre shapefile y raster
        ValueError: Si method no es válido

    Ejemplo:
        >>> # Clasificación por cuantiles
        >>> df = classify_continuous_raster('cuenca.shp', 'elevation.tif',
        ...                                method='quantiles', output_csv='result.csv')
        >>> print(df)
           categoria  cantidad_pixeles  rango_min  rango_max
        0          1               120      0.000      1.250
        1          2               118      1.250      2.890

        >>> # Clasificación personalizada
        >>> custom_ranges = [0, 10, 25, 50, 75, 100]
        >>> df = classify_continuous_raster('cuenca.shp', 'slope.tif',
        ...                                method='custom', custom_breaks=custom_ranges)

    Notas:
        - Para method='jenks' se usa K-means como aproximación rápida a natural breaks
        - Los rangos se calculan automáticamente según el método seleccionado
        - Los valores NoData y NaN se excluyen automáticamente del análisis
        - Para datasets grandes (>10,000 píxeles), jenks usa muestreo aleatorio
    """

    print("🎯 Iniciando clasificación de raster continuo...")
    print(f"   📊 Método de clasificación: {method}")

    # Leer cuenca
    print("📂 Cargando geometría de la cuenca...")
    cuenca = gpd.read_file(shapefile_path)
    geometry = cuenca.geometry.iloc[0]
    print(f"   ✓ Shapefile cargado: {len(cuenca)} feature(s)")
    print(f"   ✓ CRS: {cuenca.crs}")
    print(f"   ✓ Área polígono: {geometry.area:.8f} grados²")

    # Recortar raster
    print("🔄 Procesando raster continuo...")
    with rasterio.open(raster_path) as src:
        print(f"   ✓ Raster abierto: {src.width}x{src.height} píxeles")
        print(f"   ✓ CRS raster: {src.crs}")
        print(f"   ✓ NoData value: {src.nodata}")
        print(f"   ✓ Tipo de datos: {src.dtypes[0]}")

        print("✂️  Recortando raster con geometría de la cuenca...")
        masked_data, _ = rasterio.mask.mask(src, [geometry], crop=True, nodata=src.nodata)
        pixel_values = masked_data[0]
        print(f"   ✓ Dimensiones del recorte: {pixel_values.shape}")
        print(f"   ✓ Total píxeles en recorte: {pixel_values.size}")

        # Filtrar valores válidos
        print("🔍 Filtrando píxeles válidos...")
        if src.nodata is not None:
            valid_mask = (pixel_values != src.nodata) & (~np.isnan(pixel_values))
        else:
            valid_mask = ~np.isnan(pixel_values)

        valid_pixels = pixel_values[valid_mask].flatten()

        invalid_count = pixel_values.size - len(valid_pixels)
        print(f"   ✓ Píxeles válidos: {len(valid_pixels)}")
        print(f"   ✓ Píxeles inválidos (NoData/NaN): {invalid_count}")

        if len(valid_pixels) == 0:
            raise ValueError("No hay píxeles válidos en la intersección")

        print(f"   ✓ Rango de valores: {valid_pixels.min():.6f} - {valid_pixels.max():.6f}")
        print(f"   ✓ Media: {valid_pixels.mean():.6f}, Desv. estándar: {valid_pixels.std():.6f}")

    # Definir rangos de clasificación
    print(f"📏 Calculando rangos de clasificación con método '{method}'...")

    if method == 'custom':
        if custom_breaks is None or len(custom_breaks) != 6:
            raise ValueError(
                "custom_breaks debe tener exactamente 6 valores [min, break1, break2, break3, break4, max]")
        breaks = np.array(custom_breaks)
        print("   ✓ Usando rangos personalizados")

    elif method == 'quantiles':
        breaks = np.percentile(valid_pixels, [0, 20, 40, 60, 80, 100])
        print("   ✓ Calculando cuantiles (percentiles 20, 40, 60, 80)")

    elif method == 'equal':
        breaks = np.linspace(valid_pixels.min(), valid_pixels.max(), 6)
        print("   ✓ Calculando intervalos iguales")

    elif method == 'jenks':
        print("   🔄 Calculando natural breaks (K-means)...")
        # Usar muestra si hay demasiados píxeles
        if len(valid_pixels) > 10000:
            sample_pixels = np.random.choice(valid_pixels, 10000, replace=False)
            print(f"     📊 Usando muestra de 10,000 píxeles de {len(valid_pixels)} totales")
        else:
            sample_pixels = valid_pixels

        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        kmeans.fit(sample_pixels.reshape(-1, 1))
        centers = np.sort(kmeans.cluster_centers_.flatten())
        breaks = np.concatenate([[valid_pixels.min()],
                                 (centers[:-1] + centers[1:]) / 2,
                                 [valid_pixels.max()]])
        print("   ✓ Natural breaks calculados")

    elif method == 'std':
        print("   📊 Calculando rangos basados en desviación estándar...")
        mean_val = valid_pixels.mean()
        std_val = valid_pixels.std()
        breaks = [valid_pixels.min(),
                  mean_val - std_val,
                  mean_val - 0.5 * std_val,
                  mean_val + 0.5 * std_val,
                  mean_val + std_val,
                  valid_pixels.max()]
        breaks = np.clip(breaks, valid_pixels.min(), valid_pixels.max())
        print(f"     Media: {mean_val:.6f}, Desv. estándar: {std_val:.6f}")

    else:
        raise ValueError("method debe ser: 'quantiles', 'equal', 'jenks', 'std', 'custom'")

    print("   ✓ Rangos de clasificación:")
    for i in range(5):
        print(f"     Categoría {i + 1}: [{breaks[i]:.6f}, {breaks[i + 1]:.6f}]")

    # Clasificar píxeles
    print("🏷️  Clasificando píxeles en categorías...")
    categories = np.zeros(len(valid_pixels), dtype=int)

    for i in range(5):
        if i == 0:
            mask = (valid_pixels >= breaks[i]) & (valid_pixels <= breaks[i + 1])
        else:
            mask = (valid_pixels > breaks[i]) & (valid_pixels <= breaks[i + 1])
        categories[mask] = i + 1
        pixels_in_category = np.sum(mask)
        percentage = (pixels_in_category / len(valid_pixels)) * 100
        print(f"   ✓ Categoría {i + 1}: {pixels_in_category} píxeles ({percentage:.1f}%)")

    # Verificar píxeles sin clasificar
    unclassified = np.sum(categories == 0)
    if unclassified > 0:
        print(f"   ⚠️  Píxeles sin clasificar: {unclassified}")

    # Contar por categoría
    print("📊 Generando conteos finales...")
    unique_cats, counts = np.unique(categories[categories > 0], return_counts=True)

    # Crear DataFrame
    print("📋 Creando DataFrame resultado...")
    df_list = []
    for cat in range(1, 6):
        if cat in unique_cats:
            count = counts[unique_cats == cat][0]
        else:
            count = 0

        # df_list.append({
        #     'categoria': cat,
        #     'cantidad_pixeles': count,
        #     'rango_min': round(breaks[cat - 1], 6),
        #     'rango_max': round(breaks[cat], 6)
        # })

        df_list.append({
            'categoria': cat,
            NameCol: count
        })

    df = pd.DataFrame(df_list)

    print(f"   ✓ DataFrame creado: 5 categorías")
    print(f"   ✓ Total píxeles clasificados: {df[NameCol].sum()}")

    # Mostrar resumen final
    print("\n📈 Resumen final de clasificación:")
    for _, row in df.iterrows():
        if row[NameCol] > 0:
            percentage = (row[NameCol] / df[NameCol].sum()) * 100
            print(f"   Cat {row['categoria']}: {row[NameCol]} píxeles ({percentage:.1f}%) ")
        else:
            print(f"   Cat {row['categoria']}: 0 píxeles (0.0%) ")

    # Guardar CSV si se especifica ruta
    if output_csv:
        print(f"\n💾 Guardando resultado en: {output_csv}")
        df.to_csv(output_csv, index=False)
        print("   ✓ Archivo CSV guardado exitosamente")

    print("✅ Clasificación completada exitosamente")
    df = df.set_index("categoria")
    return df


def classify_continuous_raster(shapefile_path, raster_path, method='quantiles', custom_breaks=None,
                               output_csv=None, NameCol='cantidad_pixeles', sample_size=1000000, random_seed=42):
    """
    Clasifica un raster continuo en 5 categorías usando rangos globales.
    OPTIMIZADA para rasters grandes (como cuenca del Amazonas) usando muestreo eficiente.

    Descripción:
        Calcula rangos de clasificación usando muestreo estadístico del raster completo,
        luego recorta el raster con la geometría de cuenca y cuenta la frecuencia de píxeles
        en cada categoría dentro del área de interés. Maneja eficientemente rasters grandes.

    Parámetros:
        shapefile_path (str): Ruta al archivo shapefile de la cuenca.
        raster_path (str): Ruta al archivo raster con valores continuos.
        method (str): Método de clasificación:
                     - 'quantiles': Percentiles 20, 40, 60, 80 del raster completo
                     - 'equal': Intervalos iguales del raster completo
                     - 'jenks': Natural breaks del raster completo (K-means)
                     - 'std': Basado en desviación estándar del raster completo
                     - 'custom': Rangos definidos manualmente
        custom_breaks (list, opcional): Lista con 6 valores [min, break1, break2, break3, break4, max]
        output_csv (str, opcional): Ruta donde guardar el resultado CSV
        NameCol (str): Nombre de la columna de conteo (default: 'cantidad_pixeles')
        sample_size (int): Píxeles para muestreo estadístico (default: 1,000,000)
        random_seed (int): Semilla para reproducibilidad (default: 42)

    Retorna:
        pandas.DataFrame: DataFrame con categorías y conteos de píxeles

    Ejemplo:
        >>> # Para raster grande como Amazonas
        >>> df = classify_continuous_raster('cuenca_amazonas.shp', 'elevation_amazonas.tif',
        ...                                method='quantiles', sample_size=2000000)
    """

    print("🎯 Iniciando clasificación de raster continuo (optimizada para rasters grandes)...")
    print(f"   📊 Método de clasificación: {method}")
    print(f"   🔬 Tamaño de muestra: {sample_size:,}")
    print(f"   🎲 Semilla aleatoria: {random_seed}")

    # Establecer semilla para reproducibilidad
    np.random.seed(random_seed)

    # Leer cuenca
    print("📂 Cargando geometría de la cuenca...")
    cuenca = gpd.read_file(shapefile_path)
    geometry = cuenca.geometry.iloc[0]
    print(f"   ✓ Shapefile cargado: {len(cuenca)} feature(s)")
    print(f"   ✓ CRS: {cuenca.crs}")
    print(f"   ✓ Área polígono: {geometry.area:.8f} grados²")

    print("🌍 Análisis eficiente del raster completo...")
    with rasterio.open(raster_path) as src:
        print(f"   ✓ Raster: {src.width:,} x {src.height:,} píxeles")
        total_pixels = src.width * src.height
        print(f"   ✓ Total píxeles: {total_pixels:,}")
        print(f"   ✓ CRS raster: {src.crs}")
        print(f"   ✓ NoData value: {src.nodata}")
        print(f"   ✓ Tipo de datos: {src.dtypes[0]}")

        # Estimar tamaño y decidir estrategia
        estimated_size_gb = (total_pixels * 4) / 1e9  # Asumiendo float32
        print(f"   ✓ Tamaño estimado: {estimated_size_gb:.1f} GB")

        # ESTRATEGIA ADAPTATIVA: Decidir método según tamaño
        if estimated_size_gb < 2.0:
            # RASTER PEQUEÑO: Cargar completo
            print("📖 Raster pequeño: cargando completo en memoria...")
            full_raster = src.read(1)

            if src.nodata is not None:
                valid_mask = (full_raster != src.nodata) & (~np.isnan(full_raster))
            else:
                valid_mask = ~np.isnan(full_raster)

            sample_pixels = full_raster[valid_mask].flatten()
            print(f"   ✓ Píxeles válidos: {len(sample_pixels):,}")

            # Limitar muestra si es muy grande
            if len(sample_pixels) > sample_size:
                sample_pixels = np.random.choice(sample_pixels, sample_size, replace=False)
                print(f"   ✓ Muestra reducida a: {len(sample_pixels):,}")

        elif src.overviews(1):
            # RASTER GRANDE CON OVERVIEWS: Usar overview
            print("📊 Raster grande: usando overviews para muestreo rápido...")
            overview_level = src.overviews(1)[0]
            overview_data = src.read(1, out_shape=(
                src.height // overview_level,
                src.width // overview_level
            ), resampling=Resampling.average)

            if src.nodata is not None:
                valid_mask = (overview_data != src.nodata) & (~np.isnan(overview_data))
            else:
                valid_mask = ~np.isnan(overview_data)

            sample_pixels = overview_data[valid_mask].flatten()
            print(f"   ✓ Overview muestreado: {len(sample_pixels):,} píxeles")

            if len(sample_pixels) > sample_size:
                sample_pixels = np.random.choice(sample_pixels, sample_size, replace=False)

        else:
            # RASTER GRANDE SIN OVERVIEWS: Muestreo por bloques
            print("📊 Raster grande: muestreo aleatorio por bloques...")
            sample_pixels = []

            block_height, block_width = 1024, 1024
            total_blocks = ((src.height + block_height - 1) // block_height) * \
                           ((src.width + block_width - 1) // block_width)

            blocks_to_sample = min(max(50, int(sample_size / (block_height * block_width))), total_blocks)
            print(f"   📦 Muestreando {blocks_to_sample} de {total_blocks:,} bloques...")

            sampled_blocks = 0
            attempts = 0
            max_attempts = blocks_to_sample * 3

            while len(sample_pixels) < sample_size and attempts < max_attempts:
                attempts += 1

                # Posición aleatoria del bloque
                row_start = np.random.randint(0, max(1, src.height - block_height))
                col_start = np.random.randint(0, max(1, src.width - block_width))

                window = Window(col_start, row_start,
                                min(block_width, src.width - col_start),
                                min(block_height, src.height - row_start))

                try:
                    block_data = src.read(1, window=window)

                    if src.nodata is not None:
                        valid_mask = (block_data != src.nodata) & (~np.isnan(block_data))
                    else:
                        valid_mask = ~np.isnan(block_data)

                    valid_pixels = block_data[valid_mask].flatten()
                    if len(valid_pixels) > 0:
                        sample_pixels.extend(valid_pixels)
                        sampled_blocks += 1

                        # Progreso cada 10 bloques
                        if sampled_blocks % 10 == 0:
                            print(f"     📊 Procesados {sampled_blocks} bloques, {len(sample_pixels):,} píxeles...")

                except Exception:
                    continue

            sample_pixels = np.array(sample_pixels)
            print(f"   ✓ Muestra obtenida: {len(sample_pixels):,} píxeles de {sampled_blocks} bloques")

            # Limitar al tamaño solicitado
            if len(sample_pixels) > sample_size:
                sample_pixels = np.random.choice(sample_pixels, sample_size, replace=False)
                print(f"   ✓ Muestra final: {len(sample_pixels):,} píxeles")

        if len(sample_pixels) == 0:
            raise ValueError("No se pudieron obtener píxeles válidos para el muestreo")

        print(f"   ✓ Rango muestreado: {sample_pixels.min():.6f} - {sample_pixels.max():.6f}")
        print(f"   ✓ Media muestreada: {sample_pixels.mean():.6f}")
        print(f"   ✓ Desv. estándar: {sample_pixels.std():.6f}")

        # CALCULAR RANGOS DE CLASIFICACIÓN
        print(f"📏 Calculando rangos globales con método '{method}'...")

        if method == 'custom':
            if custom_breaks is None or len(custom_breaks) != 6:
                raise ValueError(
                    "custom_breaks debe tener exactamente 6 valores [min, break1, break2, break3, break4, max]")
            breaks = np.array(custom_breaks)
            print("   ✓ Usando rangos personalizados")

        elif method == 'quantiles':
            breaks = np.percentile(sample_pixels, [0, 20, 40, 60, 80, 100])
            print("   ✓ Cuantiles calculados de la muestra representativa")

        elif method == 'equal':
            breaks = np.linspace(sample_pixels.min(), sample_pixels.max(), 6)
            print("   ✓ Intervalos iguales calculados")

        elif method == 'jenks':
            print("   🔄 Calculando natural breaks (K-means)...")
            # Usar muestra para jenks
            jenks_sample = sample_pixels
            if len(jenks_sample) > 100000:
                jenks_sample = np.random.choice(jenks_sample, 100000, replace=False)
                print(f"     📊 Muestra para jenks: {len(jenks_sample):,} píxeles")

            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(jenks_sample.reshape(-1, 1))
            centers = np.sort(kmeans.cluster_centers_.flatten())
            breaks = np.concatenate([[sample_pixels.min()],
                                     (centers[:-1] + centers[1:]) / 2,
                                     [sample_pixels.max()]])
            print("   ✓ Natural breaks calculados")

        elif method == 'std':
            print("   📊 Calculando rangos basados en desviación estándar...")
            mean_val = sample_pixels.mean()
            std_val = sample_pixels.std()
            breaks = [sample_pixels.min(),
                      mean_val - std_val,
                      mean_val - 0.5 * std_val,
                      mean_val + 0.5 * std_val,
                      mean_val + std_val,
                      sample_pixels.max()]
            breaks = np.clip(breaks, sample_pixels.min(), sample_pixels.max())
            print(f"     Media: {mean_val:.6f}, Desv. estándar: {std_val:.6f}")

        else:
            raise ValueError("method debe ser: 'quantiles', 'equal', 'jenks', 'std', 'custom'")

        print("   ✅ Rangos de clasificación globales:")
        for i in range(5):
            print(f"     Categoría {i + 1}: [{breaks[i]:.6f}, {breaks[i + 1]:.6f}]")

        # APLICAR MÁSCARA DEL SHAPEFILE
        print("✂️  Recortando raster con geometría de la cuenca...")
        masked_data, transform = rasterio.mask.mask(src, [geometry], crop=True, nodata=src.nodata)
        area_pixel_values = masked_data[0]

        print(f"   ✓ Dimensiones del recorte: {area_pixel_values.shape}")
        print(f"   ✓ Píxeles en recorte: {area_pixel_values.size:,}")

        if total_pixels > 0:
            reduction = ((total_pixels - area_pixel_values.size) / total_pixels * 100)
            print(f"   ✓ Reducción de área: {reduction:.1f}%")

        # Filtrar valores válidos del área de interés
        print("🔍 Filtrando píxeles válidos del área de interés...")
        if src.nodata is not None:
            area_valid_mask = (area_pixel_values != src.nodata) & (~np.isnan(area_pixel_values))
        else:
            area_valid_mask = ~np.isnan(area_pixel_values)

        area_valid_pixels = area_pixel_values[area_valid_mask].flatten()
        area_invalid_count = area_pixel_values.size - len(area_valid_pixels)

        print(f"   ✓ Píxeles válidos en área: {len(area_valid_pixels):,}")
        print(f"   ✓ Píxeles inválidos en área: {area_invalid_count:,}")

        if len(area_valid_pixels) == 0:
            raise ValueError("No hay píxeles válidos en la intersección con el shapefile")

        print(f"   ✓ Rango en área: {area_valid_pixels.min():.6f} - {area_valid_pixels.max():.6f}")
        print(f"   ✓ Media en área: {area_valid_pixels.mean():.6f}")

    # CLASIFICAR PÍXELES DEL ÁREA
    print("🏷️  Clasificando píxeles del área usando rangos globales...")
    categories = np.zeros(len(area_valid_pixels), dtype=int)

    for i in range(5):
        if i == 0:
            mask = (area_valid_pixels >= breaks[i]) & (area_valid_pixels <= breaks[i + 1])
        else:
            mask = (area_valid_pixels > breaks[i]) & (area_valid_pixels <= breaks[i + 1])
        categories[mask] = i + 1
        pixels_in_category = np.sum(mask)
        percentage = (pixels_in_category / len(area_valid_pixels)) * 100 if len(area_valid_pixels) > 0 else 0
        print(f"   ✓ Categoría {i + 1}: {pixels_in_category:,} píxeles ({percentage:.1f}%)")

    # Verificar píxeles sin clasificar
    unclassified = np.sum(categories == 0)
    if unclassified > 0:
        print(f"   ⚠️  Píxeles sin clasificar: {unclassified:,}")

    # GENERAR CONTEOS FINALES
    print("📊 Generando conteos finales...")
    unique_cats, counts = np.unique(categories[categories > 0], return_counts=True)

    # Crear DataFrame
    print("📋 Creando DataFrame resultado...")
    df_list = []
    for cat in range(1, 6):
        if cat in unique_cats:
            count = counts[unique_cats == cat][0]
        else:
            count = 0
        df_list.append({'categoria': cat, NameCol: count})

    df = pd.DataFrame(df_list)

    print(f"   ✓ DataFrame creado: 5 categorías")
    print(f"   ✓ Total píxeles clasificados: {df[NameCol].sum():,}")

    # Mostrar resumen final
    print("\n📈 Resumen final de clasificación:")
    total_area_pixels = df[NameCol].sum()
    for _, row in df.iterrows():
        if row[NameCol] > 0:
            percentage = (row[NameCol] / total_area_pixels) * 100
            range_info = f"[{breaks[row['categoria'] - 1]:.6f}, {breaks[row['categoria']]:.6f}]"
            print(f"   Cat {row['categoria']}: {row[NameCol]:,} píxeles ({percentage:.1f}%) - Rango: {range_info}")
        else:
            range_info = f"[{breaks[row['categoria'] - 1]:.6f}, {breaks[row['categoria']]:.6f}]"
            print(f"   Cat {row['categoria']}: 0 píxeles (0.0%) - Rango: {range_info}")

    # Guardar CSV si se especifica
    if output_csv:
        print(f"\n💾 Guardando resultado en: {output_csv}")
        df.to_csv(output_csv, index=False)
        print("   ✓ Archivo CSV guardado exitosamente")

    print("✅ Clasificación completada exitosamente")
    df = df.set_index("categoria")
    return df


# ----------------------------------------------------------------------------------------------------------------------
# Estadistica enun poligono
# ----------------------------------------------------------------------------------------------------------------------
import numpy as np
import rasterio
from rasterio.features import geometry_mask
import geopandas as gpd
import os


def polygon_pixel_stats(raster_path, shapefile_path, stat='sum', max_memory_mb=1024):
    """
    Calcula estadísticas de píxeles dentro de polígonos usando procesamiento en disco.

    Args:
        raster_path (str): Ruta al archivo raster
        shapefile_path (str): Ruta al shapefile con polígonos
        stat (str): Estadística a calcular ('sum', 'mean', 'count', 'std')
        max_memory_mb (int): Memoria máxima a usar en MB

    Returns:
        list: Lista con estadísticas para cada polígono
    """

    # Cargar geometrías
    gdf = gpd.read_file(shapefile_path)
    print(f"Procesando {len(gdf)} polígonos")

    results = []

    with rasterio.open(raster_path) as src:
        # Auto-detectar tipo de datos eficiente
        dtype = src.dtypes[0]
        compute_dtype = np.float32 if dtype in ['uint8', 'int16', 'uint16'] else np.float64

        print(f"Raster: {src.width}x{src.height}, dtype: {dtype}")

        for idx, geometry in enumerate(gdf.geometry):
            try:
                # Crear ventana basada en bounds del polígono
                geom_bounds = geometry.bounds
                window = rasterio.windows.from_bounds(*geom_bounds, src.transform)
                window = window.intersection(rasterio.windows.Window(0, 0, src.width, src.height))

                if window.width <= 0 or window.height <= 0:
                    results.append(0 if stat == 'sum' else np.nan)
                    continue

                # Leer solo la ventana necesaria
                data = src.read(1, window=window, masked=True)

                if data.size == 0:
                    results.append(0 if stat == 'sum' else np.nan)
                    continue

                # Crear máscara geométrica para la ventana
                window_transform = rasterio.windows.transform(window, src.transform)
                geom_mask = geometry_mask([geometry],
                                          out_shape=data.shape,
                                          transform=window_transform,
                                          invert=True)

                # Aplicar máscara y calcular estadística
                masked_data = data[geom_mask & ~data.mask]

                if len(masked_data) == 0:
                    result = 0 if stat == 'sum' else np.nan
                else:
                    masked_data = masked_data.astype(compute_dtype)

                    if stat == 'sum':
                        result = float(np.sum(masked_data))
                    elif stat == 'mean':
                        result = float(np.mean(masked_data))
                    elif stat == 'min':
                        result = float(np.min(masked_data))
                    elif stat == 'max':
                        result = float(np.max(masked_data))
                    elif stat == 'count':
                        result = len(masked_data)
                    elif stat == 'std':
                        result = float(np.std(masked_data))
                    else:
                        raise ValueError(f"Estadística '{stat}' no soportada")

                results.append(result)

                if (idx + 1) % 100 == 0:
                    print(f"Procesados {idx + 1}/{len(gdf)} polígonos")

            except Exception as e:
                print(f"Error en polígono {idx}: {e}")
                results.append(np.nan)

    print(f"Proceso completado: {len(results)} resultados")
    return results


import geopandas as gpd

# ----------------------------------------------------------------------------------------------------------------------
# Área de la cuenca
# ----------------------------------------------------------------------------------------------------------------------
def cuenca_area_perimetro(shapefile_path):
    """
    Calcula área y perímetro de cuenca en coordenadas planas UTM.

    Args:
        shapefile_path (str): Ruta al shapefile de la cuenca en WGS84

    Returns:
        tuple: (area_km2, perimetro_km)
    """

    # Cargar shapefile
    gdf = gpd.read_file(shapefile_path)

    # Obtener centroide para determinar zona UTM
    centroide = gdf.geometry.centroid.iloc[0]
    lon, lat = centroide.x, centroide.y

    # Calcular zona UTM automáticamente
    zona_utm = int((lon + 180) / 6) + 1
    hemisferio = 'north' if lat >= 0 else 'south'

    # Crear CRS UTM
    crs_utm = f'EPSG:{32600 + zona_utm if hemisferio == "north" else 32700 + zona_utm}'

    # Reproyectar a UTM
    gdf_utm = gdf.to_crs(crs_utm)

    # Calcular área y perímetro
    area_m2 = gdf_utm.geometry.area.sum()
    perimetro_m = gdf_utm.geometry.length.sum()

    # Convertir a kilómetros
    area_km2 = area_m2 / 1_000_000
    perimetro_km = perimetro_m / 1_000

    print(f"Zona UTM: {zona_utm}{hemisferio[0].upper()}")
    print(f"Área: {area_km2:.2f} km²")
    print(f"Perímetro: {perimetro_km:.2f} km")

    return area_km2, perimetro_km