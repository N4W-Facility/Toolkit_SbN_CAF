import pandas as pd
import sys

"""
Script para limpiar Barriers.csv de proyectos existentes
Elimina filas de subcategorías (códigos que terminan en número)
"""

if len(sys.argv) < 2:
    print("Uso: python clean_project_barriers.py <ruta_al_Barriers.csv>")
    print("Ejemplo: python clean_project_barriers.py C:/WSL/04-CAF/CODES/Dummy/Barriers.csv")
    sys.exit(1)

csv_path = sys.argv[1]

try:
    # Leer CSV
    print(f"Leyendo {csv_path}...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    total_rows = len(df)
    print(f"Total filas encontradas: {total_rows}")

    # Filtrar solo códigos que terminan en letra (barreras evaluables)
    # Eliminar códigos que terminan en número (subcategorías)
    df_clean = df[df.iloc[:, 0].astype(str).str[-1].str.isalpha()]

    cleaned_rows = len(df_clean)
    removed_rows = total_rows - cleaned_rows

    print(f"Filas de barreras evaluables: {cleaned_rows}")
    print(f"Filas de subcategorías eliminadas: {removed_rows}")

    # Guardar backup
    backup_path = csv_path.replace('.csv', '_backup.csv')
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"Backup creado: {backup_path}")

    # Guardar archivo limpio
    df_clean.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ Archivo limpiado exitosamente: {csv_path}")

    # Mostrar ejemplos de lo que se eliminó
    if removed_rows > 0:
        removed_codes = df[~df.iloc[:, 0].astype(str).str[-1].str.isalpha()].iloc[:, 0].tolist()
        print(f"\nCódigos eliminados (primeros 10): {removed_codes[:10]}")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
