import pandas as pd
import os

# Archivos a procesar
csv_files = [
    'src/locales/Barries_es.csv',
    'src/locales/Barries_en.csv',
    'src/locales/Barries_pt.csv'
]

for csv_file in csv_files:
    print(f"\nProcesando {csv_file}...")

    # Leer CSV y guardar headers originales
    df_raw = pd.read_csv(csv_file, encoding='utf-8-sig')
    original_headers = list(df_raw.columns)

    # Trabajar con nombres normalizados
    df = df_raw.copy()
    df.columns = ['Codigo_Barrera', 'Descripcion', 'Grupo', 'Codigo_Grupo']

    # Crear diccionario de subcategorías
    subcategories = {}
    for _, row in df.iterrows():
        code = str(row['Codigo_Barrera'])
        # Si termina en número, es subcategoría
        if code and code[-1].isdigit():
            subcategories[code] = row['Descripcion']

    print(f"  Subcategorías encontradas: {len(subcategories)}")

    # Filtrar solo barreras (códigos con letra)
    barriers = []
    for _, row in df.iterrows():
        code = str(row['Codigo_Barrera'])
        # Si termina en letra, es barrera
        if code and code[-1].isalpha():
            # Extraer prefijo de subcategoría (ej: GB0101b -> GB0101)
            # Buscar el último dígito en el código
            subcat_code = ''
            for i, char in enumerate(code):
                if char.isdigit():
                    # Encontrar hasta dónde llega la secuencia de dígitos
                    j = i + 1
                    while j < len(code) and code[j].isdigit():
                        j += 1
                    subcat_code = code[:j]

            # Obtener descripción de subcategoría
            subcategory = subcategories.get(subcat_code, '')

            barriers.append({
                'Codigo_Barrera': code,
                'Descripcion': row['Descripcion'],
                'Subcategoria': subcategory,
                'Grupo': row['Grupo'],
                'Codigo_Grupo': row['Codigo_Grupo']
            })

    print(f"  Barreras encontradas: {len(barriers)}")

    # Crear nuevo DataFrame
    new_df = pd.DataFrame(barriers)

    # Determinar nombre de columna Subcategoria según idioma
    if 'es' in csv_file:
        subcat_header = 'Subcategoria'
    elif 'en' in csv_file:
        subcat_header = 'Subcategory'
    elif 'pt' in csv_file:
        subcat_header = 'Subcategoria'
    else:
        subcat_header = 'Subcategoria'

    # Restaurar headers originales + nueva columna
    new_df.columns = [original_headers[0], original_headers[1], subcat_header, original_headers[2], original_headers[3]]

    # Guardar con nuevo nombre
    new_file = csv_file.replace('.csv', '_new.csv')
    new_df.to_csv(new_file, index=False, encoding='utf-8-sig')
    print(f"  ✓ Archivo creado: {new_file}")

print("\n✓ Transformación completada!")
