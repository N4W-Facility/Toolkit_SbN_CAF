# src/utils/precache.py
from typing import Tuple
import contextily as ctx

def precache_region_latlon(
    bbox_wgs84: Tuple[float, float, float, float],
    zmin: int,
    zmax: int,
    grid: int = 6,
    provider=None,
):
    """
    Precalienta la caché de contextily para un BBOX (WGS84) y niveles de zoom.
    Divide el BBOX en una rejilla grid×grid para no disparar RAM.
    - bbox_wgs84: (lon_min, lat_min, lon_max, lat_max)
    - zmin/zmax: niveles de zoom enteros (p.ej., 4..12)
    - grid: subdivisiones por lado (4–8 razonable)
    - provider: ctx.providers.X.Y (mismo que usarás al iniciar)
    """
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    src = provider if provider is not None else ctx.providers.OpenStreetMap.Mapnik

    def linspace(a, b, n):
        step = (b - a) / n
        return [a + i * step for i in range(n)] + [b]

    lons = linspace(lon_min, lon_max, grid)
    lats = linspace(lat_min, lat_max, grid)

    total_jobs = (zmax - zmin + 1) * (grid * grid)
    job = 0
    for z in range(zmin, zmax + 1):
        for i in range(grid):
            for j in range(grid):
                sub_lon_min = lons[i]
                sub_lon_max = lons[i + 1]
                sub_lat_min = lats[j]
                sub_lat_max = lats[j + 1]
                try:
                    # Esto descarga (si hace falta) y guarda en caché local
                    _img, _ext = ctx.bounds2img(
                        sub_lon_min, sub_lat_min, sub_lon_max, sub_lat_max,
                        source=src, zoom=z, ll=True, use_cache=True
                    )
                except Exception as e:
                    print(f"[z={z}] cell=({i},{j}) error: {e}")
                job += 1
                print(f"Precache {100.0*job/total_jobs:5.1f}%  | z={z}  cell={i},{j}")

    print("✅ Precarga finalizada.")
