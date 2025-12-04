import os
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS, Transformer
import csv
import pandas as pd
from pathlib import Path


def detect_utm_zone(raster_path):
    """
    Detecta automáticamente la zona UTM apropiada para el raster.

    Parameters:
    -----------
    raster_path : str or Path
        Ruta al raster en WGS84

    Returns:
    --------
    str : EPSG code de la zona UTM (ej: 'EPSG:32618')
    """
    with rasterio.open(raster_path) as src:
        # Obtener bounds en WGS84
        bounds = src.bounds

        # Calcular centroide
        lon_center = (bounds.left + bounds.right) / 2
        lat_center = (bounds.bottom + bounds.top) / 2

        # Calcular zona UTM
        utm_zone = int((lon_center + 180) / 6) + 1

        # Determinar hemisferio (Norte/Sur)
        if lat_center >= 0:
            epsg_code = f'EPSG:326{utm_zone:02d}'  # WGS84 UTM Norte
        else:
            epsg_code = f'EPSG:327{utm_zone:02d}'  # WGS84 UTM Sur

        return epsg_code


def calculate_sbn_areas(raster_path):
    """
    Calcula áreas de píxeles por rangos de valores normalizados (0-1).

    NO modifica el raster. Solo calcula áreas en m² usando reproyección temporal.

    Parameters:
    -----------
    raster_path : str or Path
        Ruta al raster normalizado (valores 0-1, proyección WGS84)

    Returns:
    --------
    dict : Áreas en m² por rango
        {
            '0-0.2': float,
            '0.2-0.4': float,
            '0.4-0.6': float,
            '0.6-0.8': float,
            '0.8-1.0': float
        }
    """

    # Detectar zona UTM apropiada
    utm_epsg = detect_utm_zone(raster_path)

    with rasterio.open(raster_path) as src:
        # Leer datos normalizados
        data = src.read(1, masked=True)
        nodata = src.nodata

        # Obtener transformación a UTM (solo para cálculo, NO para guardar)
        dst_crs = CRS.from_string(utm_epsg)
        transform_utm, width_utm, height_utm = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        # Calcular resolución en metros (área de un píxel)
        pixel_area_m2 = abs(transform_utm.a * transform_utm.e)

        # Inicializar diccionario de áreas
        areas = {
            '0-0.2': 0.0,
            '0.2-0.4': 0.0,
            '0.4-0.6': 0.0,
            '0.6-0.8': 0.0,
            '0.8-1.0': 0.0
        }

        # Contar píxeles en cada rango (ignorando nodata)
        valid_mask = ~data.mask  # Máscara de datos válidos
        valid_data = data[valid_mask]

        if len(valid_data) > 0:
            # Contar píxeles por rango
            count_0_02 = np.sum((valid_data >= 0.0) & (valid_data < 0.2))
            count_02_04 = np.sum((valid_data >= 0.2) & (valid_data < 0.4))
            count_04_06 = np.sum((valid_data >= 0.4) & (valid_data < 0.6))
            count_06_08 = np.sum((valid_data >= 0.6) & (valid_data < 0.8))
            count_08_10 = np.sum((valid_data >= 0.8) & (valid_data <= 1.0))

            # Calcular áreas en m²
            areas['0-0.2'] = float(count_0_02 * pixel_area_m2)
            areas['0.2-0.4'] = float(count_02_04 * pixel_area_m2)
            areas['0.4-0.6'] = float(count_04_06 * pixel_area_m2)
            areas['0.6-0.8'] = float(count_06_08 * pixel_area_m2)
            areas['0.8-1.0'] = float(count_08_10 * pixel_area_m2)

        return areas


def save_areas_csv(areas_data, output_path):
    """
    Guarda el diccionario de áreas por SbN en formato CSV.

    Parameters:
    -----------
    areas_data : dict
        Diccionario {sbn_code: {rango: area}}
        Ejemplo: {'SbN_01': {'0-0.2': 1234.56, ...}, 'SbN_02': {...}}
    output_path : str or Path
        Ruta donde guardar el CSV (debe incluir nombre "Area.csv")
    """

    # Ordenar códigos de SbN (SbN_01, SbN_02, ..., SbN_21)
    sorted_codes = sorted(areas_data.keys())

    # Definir encabezados
    headers = [
        'Code',
        'Area 0-0.2 (m2)',
        'Area 0.2-0.4 (m2)',
        'Area 0.4-0.6 (m2)',
        'Area 0.6-0.8 (m2)',
        'Area 0.8-1.0 (m2)'
    ]

    # Rangos correspondientes
    range_keys = ['0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']

    # Crear directorio si no existe
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escribir CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for sbn_code in sorted_codes:
            row = [sbn_code]
            for range_key in range_keys:
                area_value = areas_data[sbn_code].get(range_key, 0.0)
                row.append(f'{area_value:.2f}')
            writer.writerow(row)

    print(f"✓ Archivo Area.csv guardado en: {output_path}")


def compile_area_and_costs(project_folder):
    """
    Compila áreas y costos en un único archivo con disclaimer multiidioma.

    Lee Area.csv y Cost.csv, hace merge por código de SbN y genera
    Area_Cost_Compiler.csv con disclaimer legal en español, inglés y portugués.

    Parameters:
    -----------
    project_folder : str or Path
        Ruta a la carpeta del proyecto

    Returns:
    --------
    bool : True si fue exitoso, False si hubo error
    """
    try:
        project_folder = Path(project_folder)

        # Rutas de archivos
        area_csv = project_folder / "03-SbN" / "Area.csv"
        cost_csv = project_folder / "Cost.csv"
        output_csv = project_folder / "Area_Cost_Compiler.csv"

        # Verificar que Area.csv existe
        if not area_csv.exists():
            print(f"⚠️ No se encontró Area.csv en {area_csv}")
            print("   El archivo Area.csv se genera durante la delimitación de cuenca.")
            return False

        # Verificar que Cost.csv existe
        if not cost_csv.exists():
            print(f"⚠️ No se encontró Cost.csv en {cost_csv}")
            print("   El archivo Cost.csv se genera durante el análisis de SbN.")
            return False

        print("📊 Compilando áreas y costos...")

        # Leer Area.csv
        df_areas = pd.read_csv(area_csv, encoding='utf-8')
        print(f"✓ Area.csv leído: {len(df_areas)} SbN")

        # Leer Cost.csv
        df_costs = pd.read_csv(cost_csv, encoding='utf-8')
        print(f"✓ Cost.csv leído: {len(df_costs)} SbN")

        # Extraer ID numérico del código (SbN_01 → 1)
        df_areas['ID'] = df_areas['Code'].str.extract(r'(\d+)').astype(int)

        # Hacer merge por ID
        # Asumir que la primera columna de Cost.csv es el ID numérico
        cost_id_col = df_costs.columns[0]

        # Seleccionar solo columnas de costos (Cost_Mean_Inv, Cost_Mean_M, Cost_Mean_Total)
        cost_columns = [col for col in df_costs.columns if 'Cost_Mean' in col or col == cost_id_col]
        df_costs_selected = df_costs[cost_columns].copy()

        # Renombrar columnas de costos para que sean más claras
        df_costs_selected = df_costs_selected.rename(columns={
            cost_id_col: 'ID',
            'Cost_Mean_Inv': 'Investment (USD/m2)',
            'Cost_Mean_M': 'O&M (USD/m2/year)',
            'Cost_Mean_Total': 'Total Cost (USD/m2)'
        })

        # Hacer merge
        df_compiled = df_areas.merge(df_costs_selected, on='ID', how='left')

        # Eliminar columna temporal ID
        df_compiled = df_compiled.drop(columns=['ID'])

        # Reordenar columnas: Code, áreas, costos
        area_cols = [col for col in df_compiled.columns if 'Area' in col]
        cost_cols = ['Investment (USD/m2)', 'O&M (USD/m2/year)', 'Total Cost (USD/m2)']
        final_cols = ['Code'] + area_cols + [col for col in cost_cols if col in df_compiled.columns]
        df_compiled = df_compiled[final_cols]

        # Preparar disclaimers en 3 idiomas
        disclaimers = [
            [''],  # Fila vacía
            ['DISCLAIMER / AVISO LEGAL / AVISO LEGAL'],
            [''],  # Fila vacía
            ['[EN] LEGAL NOTICE: The costs presented are reference values based on regional information. These data should be considered solely as comparative indicators to identify the relative order of magnitude among different Nature-based Solutions (NbS). For detailed economic analyses or investment decision-making, it is imperative to conduct specific technical-economic studies adapted to the local context of the area of interest. The authors assume no responsibility for improper use of this information or decisions made based solely on these indicative values.'],
            [''],  # Fila vacía
            ['[ES] AVISO LEGAL: Los costos presentados son valores referenciales basados en información regional. Estos datos deben considerarse únicamente como indicadores comparativos para identificar el orden de magnitud relativo entre diferentes Soluciones basadas en la Naturaleza (SbN). Para análisis económicos detallados o toma de decisiones de inversión, es imperativo realizar estudios técnico-económicos específicos adaptados al contexto local del área de interés. Los autores no asumen responsabilidad por el uso inadecuado de esta información o decisiones tomadas basándose únicamente en estos valores indicativos.'],
            [''],  # Fila vacía
            ['[PT] AVISO LEGAL: Os custos apresentados são valores referenciais baseados em informação regional. Estes dados devem ser considerados unicamente como indicadores comparativos para identificar a ordem de magnitude relativa entre diferentes Soluções baseadas na Natureza (SbN). Para análises econômicas detalhadas ou tomada de decisões de investimento, é imperativo realizar estudos técnico-econômicos específicos adaptados ao contexto local da área de interesse. Os autores não assumem responsabilidade pelo uso inadequado desta informação ou decisões tomadas baseando-se unicamente nestes valores indicativos.']
        ]

        # Convertir disclaimers a DataFrame para concatenar
        df_disclaimers = pd.DataFrame(disclaimers)

        # Ajustar número de columnas del disclaimer al número de columnas de df_compiled
        while len(df_disclaimers.columns) < len(df_compiled.columns):
            df_disclaimers[len(df_disclaimers.columns)] = ''

        # Asignar nombres de columnas iguales
        df_disclaimers.columns = df_compiled.columns

        # Concatenar datos + disclaimers
        df_final = pd.concat([df_compiled, df_disclaimers], ignore_index=True)

        # Guardar CSV
        df_final.to_csv(output_csv, index=False, encoding='utf-8-sig')

        print(f"✅ Archivo compilado guardado en: {output_csv}")
        print(f"   - {len(df_compiled)} SbN procesadas")
        print(f"   - {len(area_cols)} columnas de áreas")
        print(f"   - {len([c for c in cost_cols if c in df_compiled.columns])} columnas de costos")
        print(f"   - Disclaimer incluido en 3 idiomas")

        return True

    except Exception as e:
        print(f"❌ Error compilando áreas y costos: {e}")
        import traceback
        traceback.print_exc()
        return False
