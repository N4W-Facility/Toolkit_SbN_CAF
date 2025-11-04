# -*- coding: utf-8 -*-
# Delimitación de cuenca: procesamiento en disco con remuestreo de FlowAccum a la malla de FlowDir
import os
from collections import OrderedDict, deque
from typing import Tuple, Dict

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import Affine
from rasterio.features import shapes
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling
from shapely.geometry import shape
from shapely.ops import unary_union
import geopandas as gpd


# ============================== Utilidades básicas ==============================

def get_utm_zone(lon: float, lat: float):
    zone_number = int((lon + 180) / 6) + 1
    hemisphere = 'N' if lat >= 0 else 'S'
    return zone_number, hemisphere

def calculate_pixel_area_geographic_from_ds(ds) -> float:
    """
    Área por píxel (km²) para datasets en grados, aproximando a UTM en el centro.
    """
    bounds = ds.bounds
    lon_center = (bounds.left + bounds.right) / 2.0
    lat_center = (bounds.bottom + bounds.top) / 2.0

    zone_number, _ = get_utm_zone(lon_center, lat_center)
    central_meridian = (zone_number - 1) * 6 - 180 + 3
    lon_diff = abs(lon_center - central_meridian)
    scale_factor = 0.9996 + (lon_diff / 3.0) * 0.0004

    resx = abs(ds.transform.a)
    resy = abs(ds.transform.e)

    deg_to_m_lat = 111320 * scale_factor
    deg_to_m_lon = 111320 * np.cos(np.radians(lat_center)) * scale_factor

    px_m = resy * deg_to_m_lat
    py_m = resx * deg_to_m_lon
    return (px_m * py_m) / 1e6  # km²


# ======================= Infraestructura de lectura por tiles ====================

# D8 estilo Esri: 1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE
VALID_CODES = {1, 2, 4, 8, 16, 32, 64, 128}
UPSTREAM_NEIGHBORS = [
    (-1, -1, 2),   # NW -> SE
    (-1,  0, 4),   # N  -> S
    (-1,  1, 8),   # NE -> SW
    ( 0, -1, 1),   # W  -> E
    ( 0,  1, 16),  # E  -> W
    ( 1, -1, 128), # SW -> NE
    ( 1,  0, 64),  # S  -> N
    ( 1,  1, 32),  # SE -> NW
]

class TileCache:
    """Caché LRU de tiles para ráster grande."""
    def __init__(self, ds: rasterio.io.DatasetReader, preferred_block=1024, max_tiles_in_mem=64):
        self.ds = ds
        try:
            bh, bw = ds.block_shapes[0]
            self.tile_h = max(bh or preferred_block, 512)
            self.tile_w = max(bw or preferred_block, 512)
        except Exception:
            self.tile_h = self.tile_w = preferred_block
        self.max_tiles_in_mem = max_tiles_in_mem
        self._lru: "OrderedDict[Tuple[int,int], np.ndarray]" = OrderedDict()

    def tile_index(self, row: int, col: int):
        tr = row // self.tile_h
        tc = col // self.tile_w
        lr = row - tr * self.tile_h
        lc = col - tc * self.tile_w
        return tr, tc, lr, lc

    def _read_tile(self, tr: int, tc: int):
        row_off = tr * self.tile_h
        col_off = tc * self.tile_w
        h = min(self.tile_h, self.ds.height - row_off)
        w = min(self.tile_w, self.ds.width - col_off)
        if h <= 0 or w <= 0:
            return None
        win = Window(col_off, row_off, w, h)
        return self.ds.read(1, window=win, masked=False)

    def get(self, tr: int, tc: int):
        key = (tr, tc)
        if key in self._lru:
            arr = self._lru.pop(key)
            self._lru[key] = arr
            return arr
        arr = self._read_tile(tr, tc)
        if arr is None:
            return None
        self._lru[key] = arr
        if len(self._lru) > self.max_tiles_in_mem:
            self._lru.popitem(last=False)
        return arr


def _compute_global_max_streaming(ds: rasterio.io.DatasetReader) -> float:
    """Máximo global en streaming (no carga todo el ráster)."""
    maxv = None
    for _, win in ds.block_windows(1):
        arr = ds.read(1, window=win, masked=False)
        m = np.nanmax(arr)
        if maxv is None or m > maxv:
            maxv = float(m)
    return 0.0 if maxv is None else maxv


def _snap_to_network_on_disk(acc_ds, x, y, threshold_km2, pixel_area_km2, max_expand=16384):
    """
    Ajuste (snap) al píxel de acumulación ≥ umbral (km²), buscando en ventanas crecientes.
    Devuelve (x_snap, y_snap, row_acc, col_acc, accum_km2_en_snap) en grid de FlowAccum.
    """
    row0, col0 = acc_ds.index(x, y)
    H, W = acc_ds.height, acc_ds.width

    radius = 256
    while radius <= max(H, W) and radius <= max_expand:
        rmin = max(0, row0 - radius)
        rmax = min(H, row0 + radius + 1)
        cmin = max(0, col0 - radius)
        cmax = min(W, col0 + radius + 1)
        win = Window(cmin, rmin, cmax - cmin, rmax - rmin)

        block = acc_ds.read(1, window=win, masked=False).astype(np.float64) * pixel_area_km2
        mask = block >= threshold_km2

        if np.any(mask):
            rr, cc = np.where(mask)
            rr_abs = rr + rmin
            cc_abs = cc + cmin
            dr = rr_abs - row0
            dc = cc_abs - col0
            idx = np.argmin(dr * dr + dc * dc)
            row_snap = int(rr_abs[idx])
            col_snap = int(cc_abs[idx])

            x_snap, y_snap = rasterio.transform.xy(acc_ds.transform, row_snap, col_snap, offset="center")
            v = float(acc_ds.read(1, window=Window(col_snap, row_snap, 1, 1), masked=False)[0, 0]) * pixel_area_km2
            return x_snap, y_snap, row_snap, col_snap, v

        radius *= 2

    # Si no se encuentra, retorna el original
    x_snap, y_snap = rasterio.transform.xy(acc_ds.transform, row0, col0, offset="center")
    v = float(acc_ds.read(1, window=Window(col0, row0, 1, 1), masked=False)[0, 0]) * pixel_area_km2
    return x_snap, y_snap, int(row0), int(col0), v


def _delineate_basin_bfs_on_disk(fdir_ds, row_seed, col_seed, max_tiles_in_mem=64):
    """
    Delimitación de cuenca por BFS río-arriba (D8 Esri) leyendo tiles on-disk.
    Retorna (mask_MBR, (min_r,max_r,min_c,max_c)), donde mask_MBR es uint8 0/1.
    """
    cache = TileCache(fdir_ds, preferred_block=1024, max_tiles_in_mem=max_tiles_in_mem)
    visited = {}
    inbasin = {}

    min_r = max_r = row_seed
    min_c = max_c = col_seed

    q = deque()
    q.append((row_seed, col_seed))

    tr0, tc0, lr0, lc0 = cache.tile_index(row_seed, col_seed)
    tarr = cache.get(tr0, tc0)
    if tarr is None:
        raise RuntimeError("No se pudo leer el tile inicial de FlowDir.")

    visited[(tr0, tc0)] = np.zeros_like(tarr, dtype=np.uint8)
    inbasin[(tr0, tc0)] = np.zeros_like(tarr, dtype=np.uint8)
    visited[(tr0, tc0)][lr0, lc0] = 1
    inbasin[(tr0, tc0)][lr0, lc0] = 1

    H, W = fdir_ds.height, fdir_ds.width
    total = 1

    while q:
        r, c = q.popleft()
        if r < min_r: min_r = r
        if r > max_r: max_r = r
        if c < min_c: min_c = c
        if c > max_c: max_c = c

        for dr, dc, need_code in UPSTREAM_NEIGHBORS:
            rr = r + dr
            cc = c + dc
            if rr < 0 or rr >= H or cc < 0 or cc >= W:
                continue

            tr, tc, lr, lc = cache.tile_index(rr, cc)
            arr = cache.get(tr, tc)
            if arr is None:
                continue

            if (tr, tc) not in visited:
                visited[(tr, tc)] = np.zeros_like(arr, dtype=np.uint8)
            if (tr, tc) not in inbasin:
                inbasin[(tr, tc)] = np.zeros_like(arr, dtype=np.uint8)

            if visited[(tr, tc)][lr, lc] != 0:
                continue

            code = arr[lr, lc]
            if code not in VALID_CODES:
                visited[(tr, tc)][lr, lc] = 1
                continue

            if code == need_code:
                inbasin[(tr, tc)][lr, lc] = 1
                visited[(tr, tc)][lr, lc] = 1
                q.append((rr, cc))
                total += 1
            else:
                visited[(tr, tc)][lr, lc] = 1

        if total % 500000 == 0:
            print(f"   - Visitadas ~{total:,} celdas…")

    out_h = max_r - min_r + 1
    out_w = max_c - min_c + 1
    out_mask = np.zeros((out_h, out_w), dtype=np.uint8)

    for (tr, tc), tile_mask in inbasin.items():
        row_off = tr * cache.tile_h
        col_off = tc * cache.tile_w
        r0 = max(row_off, min_r)
        c0 = max(col_off, min_c)
        r1 = min(row_off + tile_mask.shape[0], max_r + 1)
        c1 = min(col_off + tile_mask.shape[1], max_c + 1)
        if r1 <= r0 or c1 <= c0:
            continue

        rr0 = r0 - row_off
        cc0 = c0 - col_off
        rr1 = rr0 + (r1 - r0)
        cc1 = cc0 + (c1 - c0)

        or0 = r0 - min_r
        oc0 = c0 - min_c
        or1 = or0 + (r1 - r0)
        oc1 = oc0 + (c1 - c0)

        out_mask[or0:or1, oc0:oc1] |= tile_mask[rr0:rr1, cc0:cc1].astype(np.uint8)

    return out_mask, (min_r, max_r, min_c, max_c)


# =============================== FUNCIÓN PRINCIPAL ===============================

def C01_BasinDelineation(PathOut, Path_FlowDir, Path_FlowAccum, lat, lon, threshold=1.0):
    """
    Delinea una cuenca hidrográfica manteniendo firma y salidas originales.
    - Remuestrea FlowAccum a la malla de FlowDir si difieren (sin tocar FlowDir).
    - Procesa por tiles (on-disk).
    - Exporta:
        • 01-Watershed/Watershed.shp  (en EPSG:4326)
        • 02-Rasters/AccumArea.tif    (uint32, LZW, x1000)
    Retorna: {'shapefile': <ruta_shp>, 'accumarea_raster': <ruta_tif>}
    """
    print("=" * 60)
    print("INICIANDO DELIMITACIÓN DE CUENCA HIDROGRÁFICA")
    print("=" * 60)
    print(f"Coordenadas del punto: Lat={lat}, Lon={lon}")
    print(f"Umbral de red de drenaje: {threshold} km²")
    print(f"Directorio de salida: {PathOut}")
    print()

    os.makedirs(PathOut, exist_ok=True)
    os.makedirs(os.path.join(PathOut, "01-Watershed"), exist_ok=True)
    os.makedirs(os.path.join(PathOut, "02-Rasters"), exist_ok=True)

    # Configuración de GDAL para Rasterio
    env_opts = dict(GDAL_NUM_THREADS="ALL_CPUS", GDAL_CACHEMAX=512)

    with rasterio.Env(**env_opts):
        # 1) Abrir rásteres
        print("1. Cargando raster de direcciones de flujo...")
        with rasterio.open(Path_FlowDir) as fdir_ds, rasterio.open(Path_FlowAccum) as acc_ds:
            H, W = fdir_ds.height, fdir_ds.width
            bounds = fdir_ds.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            print(f"   ✓ Grid de FlowDir cargado")
            print(f"   - Dimensiones FlowDir: ({H}, {W})")
            print(f"   - Extensión FlowDir: {extent}")
            print()

            # 2) Máximo global de FlowAccum (en su propio grid)
            print("2. Calculando acumulación de flujo (máximo global)…")
            acc_max = _compute_global_max_streaming(acc_ds)
            print(f"   ✓ Valor máximo de acumulación (celdas FlowAccum): {acc_max}")
            print()

            # 3) Áreas por píxel
            print("3. Calculando áreas por píxel…")
            # FlowDir
            crs_is_geo_fd = (fdir_ds.crs is not None and fdir_ds.crs.is_geographic)
            if crs_is_geo_fd or (abs(extent[0]) <= 180 and abs(extent[2]) <= 90):
                print("   - FlowDir en grados")
                PixelArea_FDIR = calculate_pixel_area_geographic_from_ds(fdir_ds)
            else:
                print("   - FlowDir en metros")
                PixelArea_FDIR = (abs(fdir_ds.transform.a) * abs(fdir_ds.transform.e)) / 1e6
            print(f"   - Área por píxel FlowDir: {PixelArea_FDIR:.6f} km²")

            # FlowAccum
            b_acc = acc_ds.bounds
            crs_is_geo_acc = (acc_ds.crs is not None and acc_ds.crs.is_geographic)
            if crs_is_geo_acc or (abs(b_acc.left) <= 180 and abs(b_acc.bottom) <= 90):
                print("   - FlowAccum en grados")
                PixelArea_ACC = calculate_pixel_area_geographic_from_ds(acc_ds)
            else:
                print("   - FlowAccum en metros")
                PixelArea_ACC = (abs(acc_ds.transform.a) * abs(acc_ds.transform.e)) / 1e6
            print(f"   - Área por píxel FlowAccum: {PixelArea_ACC:.6f} km²")
            print()

            # 4) Snap a la red de drenaje (umbral en km² usando el grid de FlowAccum)
            print("4. Ajustando coordenadas del punto de salida a la red de drenaje…")
            print(f"   - Coordenadas originales: ({lon}, {lat})")
            x_snap, y_snap, row_acc, col_acc, accum_at_snap = _snap_to_network_on_disk(
                acc_ds, lon, lat, threshold_km2=float(threshold), pixel_area_km2=PixelArea_ACC
            )
            # La semilla para FlowDir es el píxel de FlowDir más cercano a (x_snap, y_snap)
            row_seed, col_seed = fdir_ds.index(x_snap, y_snap)
            print(f"   ✓ Punto ajustado: ({x_snap:.6f}, {y_snap:.6f})")
            print(f"   - Área acumulada en el punto ajustado: {accum_at_snap:.2f} km²")
            print(f"   - Semilla en grid FlowDir: row={row_seed}, col={col_seed}")
            print()

            # 5) Delimitación de cuenca (BFS río-arriba) en FlowDir
            print("5. Delimitando cuenca hidrográfica…")
            basin_mask, (rmin, rmax, cmin, cmax) = _delineate_basin_bfs_on_disk(
                fdir_ds, row_seed=row_seed, col_seed=col_seed, max_tiles_in_mem=64
            )
            basin_cells = int(basin_mask.sum())
            basin_area_km2 = basin_cells * PixelArea_FDIR
            print(f"   ✓ Cuenca delimitada")
            print(f"   - Celdas: {basin_cells}")
            print(f"   - Área: {basin_area_km2:.2f} km²")
            print()

            # 6) Guardar resultados
            print("6. Guardando resultados…")
            buffer_cells = 5
            rmin_b = max(0, rmin - buffer_cells)
            rmax_b = min(H, rmax + buffer_cells + 1)
            cmin_b = max(0, cmin - buffer_cells)
            cmax_b = min(W, cmax + buffer_cells + 1)
            win_clip = Window(cmin_b, rmin_b, cmax_b - cmin_b, rmax_b - rmin_b)
            out_h = int(win_clip.height)
            out_w = int(win_clip.width)

            print(f"   - Cuenca original: {W}x{H} px")
            print(f"   - Cuenca recortada: {out_w}x{out_h} px")

            # Transform de la subventana (en la malla de FlowDir)
            transform_clip = rasterio.windows.transform(win_clip, fdir_ds.transform)

            # Remuestrear FlowAccum a la malla/ventana de FlowDir (solo lo necesario)
            print("   - Remuestreando FlowAccum a la malla de FlowDir (ventana de salida)…")
            with WarpedVRT(
                acc_ds,
                crs=fdir_ds.crs,
                transform=transform_clip,
                width=out_w,
                height=out_h,
                resampling=Resampling.nearest  # preserva conteos
            ) as acc_vrt:
                acc_clip_counts = acc_vrt.read(1, masked=False).astype(np.float64)

            # Convertir a km² con el área por píxel del grid original de FlowAccum
            acc_clip_km2 = acc_clip_counts * PixelArea_ACC

            # Construir máscara de cuenca en ventana con buffer
            r0 = rmin - rmin_b
            c0 = cmin - cmin_b
            rb = r0 + (rmax - rmin + 1)
            cb = c0 + (cmax - cmin + 1)
            basin_mask_buffer = np.zeros((out_h, out_w), dtype=np.uint8)
            basin_mask_buffer[r0:rb, c0:cb] = basin_mask

            acc_masked = acc_clip_km2.copy()
            acc_masked[basin_mask_buffer == 0] = 0.0

            # Escalado y escritura
            scale_factor = 1000  # km² * 1000
            acc_scaled = (acc_masked * scale_factor).astype(np.uint32)

            output_accumarea = os.path.join(PathOut, "02-Rasters", "AccumArea.tif")
            print("   - Escribiendo AccumArea.tif…")
            with rasterio.open(
                output_accumarea, 'w',
                driver='GTiff',
                height=out_h,
                width=out_w,
                count=1,
                dtype=np.uint32,
                crs=fdir_ds.crs,
                transform=transform_clip,
                nodata=0,
                compress='lzw',
                tiled=True,
                blockxsize=256,
                blockysize=256,
                BIGTIFF="IF_SAFER"
            ) as dst:
                dst.write(acc_scaled, 1)
                dst.update_tags(
                    scale_factor=scale_factor,
                    units='km2_x1000',
                    description=f'Accumulated area (km²) * {scale_factor}. Divide to recover km². Clipped to watershed.',
                    watershed_lat=lat,
                    watershed_lon=lon
                )
            print(f"   ✓ Guardado: {output_accumarea}")

            # Vectorizar cuenca (MBR sin buffer) y exportar shapefile en EPSG:4326
            print("   - Vectorizando cuenca…")
            new_transform = Affine(
                fdir_ds.transform.a, fdir_ds.transform.b, fdir_ds.transform.c + cmin * fdir_ds.transform.a,
                fdir_ds.transform.d, fdir_ds.transform.e, fdir_ds.transform.f + rmin * fdir_ds.transform.e
            )
            watershed_shapes = list(shapes(basin_mask.astype(np.uint8), mask=basin_mask, transform=new_transform))
            geoms = [shape(geom) for geom, val in watershed_shapes if val == 1]
            if not geoms:
                raise ValueError("No se pudo generar la geometría de la cuenca.")
            geom_u = unary_union(geoms) if len(geoms) > 1 else geoms[0]

            gdf = gpd.GeoDataFrame({
                'area_km2':   [float(basin_area_km2)],
                'area_cells': [int(basin_cells)],
                'lat_orig':   [float(lat)],
                'lon_orig':   [float(lon)],
                'lat_snap':   [float(y_snap)],
                'lon_snap':   [float(x_snap)],
                'threshold':  [float(threshold)],
                'accum_km2':  [float(accum_at_snap)]
            }, geometry=[geom_u], crs=fdir_ds.crs)

            # A EPSG:4326 para compatibilidad (Folium, etc.)
            gdf_4326 = gdf.to_crs(epsg=4326)

            output_shapefile = os.path.join(PathOut, "01-Watershed", "Watershed.shp")
            gdf_4326.to_file(output_shapefile)
            print(f"   ✓ Guardado: {output_shapefile}")
            print()

    print("=" * 60)
    print("DELIMITACIÓN DE CUENCA COMPLETADA")
    print("=" * 60)
    print(f"  • Área de la cuenca: {basin_area_km2:.2f} km²")
    print(f"  • Celdas: {basin_cells}")
    print(f"  • Shapefile: {output_shapefile}")
    print(f"  • AccumArea: {output_accumarea}")
    print("=" * 60)

    return {
        'shapefile': output_shapefile,
        'accumarea_raster': output_accumarea
    }
