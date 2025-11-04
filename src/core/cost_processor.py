"""
Procesador de costos ajustados por país para SbN.

Este módulo maneja:
1. Cálculo de costos ajustados por país
2. Categorización de costos (1-5)
3. Recategorización de desafíos según costos
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path


class CostProcessor:
    """
    Procesa costos de SbN ajustados por país y recategoriza desafíos.
    """

    def __init__(self, project_folder, country_code=None):
        """
        Inicializar procesador de costos.

        Args:
            project_folder: Ruta a la carpeta del proyecto
            country_code: Código numérico del país (ej: 1, 2, 3...)
        """
        # Normalizar ruta del proyecto para Windows
        self.project_folder = os.path.normpath(project_folder)
        self.country_code = country_code

        # Ruta al archivo Weight_Matrix.xlsx
        self.weight_matrix_path = self._get_weight_matrix_path()

        # Rutas de salida (normalizadas para Windows)
        self.cost_csv = os.path.normpath(os.path.join(self.project_folder, "Cost.csv"))
        self.cost_cat_csv = os.path.normpath(os.path.join(self.project_folder, "Cost_Cat.csv"))
        self.tmp_folder = os.path.normpath(os.path.join(self.project_folder, "Tmp"))
        self.weight_cost_df_ws_csv = os.path.normpath(os.path.join(self.tmp_folder, "Weight_Cost_DF_WS.csv"))
        self.weight_cost_df_o_csv = os.path.normpath(os.path.join(self.tmp_folder, "Weight_Cost_DF_O.csv"))

        # Crear carpeta Tmp si no existe
        os.makedirs(self.tmp_folder, exist_ok=True)

    def _get_weight_matrix_path(self):
        """Obtener ruta al archivo Weight_Matrix.xlsx"""
        # Buscar en locales
        base_path = os.path.dirname(os.path.dirname(__file__))
        weight_matrix_path = os.path.join(base_path, "locales", "Weight_Matrix.xlsx")

        if not os.path.exists(weight_matrix_path):
            raise FileNotFoundError(f"No se encontró Weight_Matrix.xlsx en {weight_matrix_path}")

        return weight_matrix_path

    def calculate_adjusted_costs(self):
        """
        Calcular costos ajustados por país.

        Lee costos medios desde 'Cost' y los multiplica por el factor del país
        desde 'FactorCost'. Guarda resultado en Cost.csv.

        Returns:
            bool: True si fue exitoso
        """
        try:
            print(f"📊 Calculando costos ajustados para país: {self.country_code}")

            # Leer hoja Cost (costos medios)
            df_cost = pd.read_excel(self.weight_matrix_path, sheet_name="Cost")
            print(f"✓ Costos medios cargados: {len(df_cost)} SbN")

            # Si no hay código de país, usar costos sin ajustar
            if self.country_code is None:
                print("⚠️ No hay código de país, usando costos medios sin ajuste")
                df_cost.to_csv(self.cost_csv, index=False, encoding='utf-8-sig')
                return True

            # Leer hoja FactorCost (factores por país)
            df_factor = pd.read_excel(self.weight_matrix_path, sheet_name="FactorCost")

            # Buscar factor del país (código está en columna 0, factor en columna 2)
            country_row = df_factor[df_factor.iloc[:, 0] == self.country_code]

            if country_row.empty:
                print(f"⚠️ No se encontró factor para país {self.country_code}, usando factor 1.0")
                factor = 1.0
            else:
                # El factor numérico está en la tercera columna (índice 2)
                # Columna 0 = código, Columna 1 = nombre, Columna 2 = factor
                factor = float(country_row.iloc[0, 2])
                country_name = country_row.iloc[0, 1]
                print(f"✓ Factor de ajuste para {country_name} (código {self.country_code}): {factor}")

            # Aplicar factor a las columnas de costo
            df_adjusted = df_cost.copy()

            cost_columns = ['Cost_Mean_Inv', 'Cost_Mean_M', 'Cost_Mean_Total']
            for col in cost_columns:
                if col in df_adjusted.columns:
                    # Asegurar que la columna es numérica
                    df_adjusted[col] = pd.to_numeric(df_adjusted[col], errors='coerce')
                    # Aplicar factor
                    df_adjusted[col] = df_adjusted[col] * factor

            # Guardar costos ajustados
            df_adjusted.to_csv(self.cost_csv, index=False, encoding='utf-8-sig')
            print(f"✓ Costos ajustados guardados en: {self.cost_csv}")

            return True

        except Exception as e:
            print(f"❌ Error calculando costos ajustados: {e}")
            import traceback
            traceback.print_exc()
            return False

    def categorize_costs(self, financial_option='investment_and_maintenance'):
        """
        Categorizar costos según rangos (1-5).

        Args:
            financial_option: 'investment', 'maintenance', o 'investment_and_maintenance'

        Returns:
            bool: True si fue exitoso
        """
        try:
            print(f"📊 Categorizando costos según opción: {financial_option}")

            # Leer costos ajustados
            if not os.path.exists(self.cost_csv):
                print("⚠️ No existe Cost.csv, ejecutando calculate_adjusted_costs primero")
                self.calculate_adjusted_costs()

            df_cost = pd.read_csv(self.cost_csv, encoding='utf-8-sig')

            # Leer tabla de categorías
            df_cat = pd.read_excel(self.weight_matrix_path, sheet_name="Categorias_Costos")
            print(f"✓ Categorías cargadas: {len(df_cat)} rangos")

            # Determinar columna a usar según opción financiera
            if financial_option == 'investment':
                cost_column = 'Cost_Mean_Inv'
                min_col = 'Inv_Min'
                max_col = 'Inv_Max'
            elif financial_option == 'maintenance':
                cost_column = 'Cost_Mean_M'
                min_col = 'Man_Min'
                max_col = 'Man_Max'
            else:  # investment_and_maintenance
                cost_column = 'Cost_Mean_Total'
                min_col = 'Total_Min'
                max_col = 'Total_Max'

            print(f"✓ Usando columna: {cost_column}")

            # Asegurar que la columna de costo es numérica
            df_cost[cost_column] = pd.to_numeric(df_cost[cost_column], errors='coerce')

            # Categorizar cada SbN
            categories = []
            for idx, row in df_cost.iterrows():
                cost_value = row[cost_column]

                # Saltar valores nulos o no numéricos
                if pd.isna(cost_value):
                    categories.append(1)  # Categoría por defecto
                    continue

                # Buscar categoría
                category = self._find_category(cost_value, df_cat, min_col, max_col)
                categories.append(category)

            # Crear DataFrame de salida
            df_output = df_cost.copy()
            df_output['Cost_Category'] = categories

            # Guardar
            df_output.to_csv(self.cost_cat_csv, index=False, encoding='utf-8-sig')
            print(f"✓ Costos categorizados guardados en: {self.cost_cat_csv}")

            # Mostrar distribución
            cat_counts = pd.Series(categories).value_counts().sort_index()
            print(f"📊 Distribución de categorías: {dict(cat_counts)}")

            return True

        except Exception as e:
            print(f"❌ Error categorizando costos: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _find_category(self, value, df_cat, min_col, max_col):
        """
        Buscar categoría para un valor dado.

        Args:
            value: Valor a categorizar
            df_cat: DataFrame de categorías
            min_col: Nombre columna mínimo
            max_col: Nombre columna máximo

        Returns:
            int: Categoría (1-5)
        """
        try:
            value = float(value)
        except (ValueError, TypeError):
            return 1  # Categoría por defecto para valores inválidos

        for idx, row in df_cat.iterrows():
            try:
                min_val = float(row[min_col])
                max_val = float(row[max_col])

                if min_val <= value <= max_val:
                    return int(row['Categoria'])
            except (ValueError, TypeError):
                continue

        # Si no encuentra, asignar categoría más alta
        return int(df_cat['Categoria'].max())

    def recategorize_challenges(self):
        """
        Recategorizar pesos de desafíos según costos usando Matrix_CostEfe.

        Lee matrices de pesos originales desde Weight_Matrix.xlsx
        (hojas: Desafios_Seguridad_Hidrica, Desafios_Otros), categorías de costos
        (Cost_Cat.csv) y matriz de recategorización (Matrix_CostEfe).
        Genera nuevas matrices de pesos ajustadas por costos.

        Returns:
            bool: True si fue exitoso
        """
        try:
            print("📊 Recategorizando desafíos según costos")

            # Verificar que exista Cost_Cat.csv
            if not os.path.exists(self.cost_cat_csv):
                print("⚠️ No existe Cost_Cat.csv, ejecutando categorize_costs primero")
                self.categorize_costs()

            # Leer categorías de costos
            df_cost_cat = pd.read_csv(self.cost_cat_csv, encoding='utf-8-sig')

            # Crear diccionario SbN_ID -> Cost_Category
            cost_cat_dict = {}
            if 'ID' in df_cost_cat.columns and 'Cost_Category' in df_cost_cat.columns:
                cost_cat_dict = dict(zip(df_cost_cat['ID'], df_cost_cat['Cost_Category']))
            else:
                # Asumir que el índice es el ID
                cost_cat_dict = dict(zip(range(1, len(df_cost_cat) + 1), df_cost_cat['Cost_Category']))

            print(f"✓ Categorías de costo cargadas para {len(cost_cat_dict)} SbN")

            # Leer matriz de recategorización
            df_matrix = pd.read_excel(self.weight_matrix_path, sheet_name="Matrix_CostEfe")

            # Filtrar filas con NaN en la primera columna (filas vacías)
            df_matrix = df_matrix.dropna(subset=[df_matrix.columns[0]])

            print(f"✓ Matriz de recategorización cargada: {df_matrix.shape}")

            # Leer matrices de pesos originales desde Weight_Matrix.xlsx
            # Procesar desafíos de seguridad hídrica
            print("📊 Leyendo matriz de pesos: Desafios_Seguridad_Hidrica")
            df_ws_original = pd.read_excel(self.weight_matrix_path, sheet_name="Desafios_Seguridad_Hidrica")
            print(f"✓ Matriz cargada: {df_ws_original.shape}")

            df_ws_adjusted = self._apply_cost_matrix(df_ws_original, cost_cat_dict, df_matrix)
            df_ws_adjusted.to_csv(self.weight_cost_df_ws_csv, index=False, encoding='utf-8-sig')
            print(f"✓ Matriz ajustada guardada: {self.weight_cost_df_ws_csv}")

            # Procesar otros desafíos
            print("📊 Leyendo matriz de pesos: Desafios_Otros")
            df_o_original = pd.read_excel(self.weight_matrix_path, sheet_name="Desafios_Otros")
            print(f"✓ Matriz cargada: {df_o_original.shape}")

            # df_o_adjusted = self._apply_cost_matrix(df_o_original, cost_cat_dict, df_matrix)
            df_o_original.to_csv(self.weight_cost_df_o_csv, index=False, encoding='utf-8-sig')
            print(f"✓ Matriz original guardada (sin ajuste de costos): {self.weight_cost_df_o_csv}")

            return True

        except Exception as e:
            print(f"❌ Error recategorizando desafíos: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _apply_cost_matrix(self, df_original, cost_cat_dict, df_matrix):
        """
        Aplicar matriz de recategorización a un DataFrame de desafíos.

        Args:
            df_original: DataFrame original de desafíos
            cost_cat_dict: Dict {sbn_id: cost_category}
            df_matrix: DataFrame con matriz de recategorización (3 columnas: Cat_Costo, Cat_Desafio, New_Cat)

        Returns:
            DataFrame ajustado
        """
        df_adjusted = df_original.copy()

        # Convertir matriz a diccionario de lookup
        # Estructura: {(cat_costo, cat_desafio): new_cat}
        matrix_dict = {}
        for idx, row in df_matrix.iterrows():
            try:
                # Validar que no haya valores NaN
                if pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]) or pd.isna(row.iloc[2]):
                    continue

                cat_costo = int(row.iloc[0])      # Primera columna: categoría de costo
                cat_desafio = int(row.iloc[1])    # Segunda columna: categoría de desafío
                new_cat = int(row.iloc[2])        # Tercera columna: nueva categoría

                matrix_dict[(cat_costo, cat_desafio)] = new_cat

            except (ValueError, TypeError) as e:
                print(f"⚠️ Saltando fila inválida en matriz: {e}")
                continue

        print(f"✓ Diccionario de recategorización creado con {len(matrix_dict)} entradas")

        # Recategorizar cada celda
        # Las primeras dos columnas son ID y Nombre, las demás son desafíos
        for col_idx in range(2, len(df_adjusted.columns)):
            col_name = df_adjusted.columns[col_idx]

            for row_idx, row in df_adjusted.iterrows():
                # Obtener ID de la SbN (primera columna)
                sbn_id = row.iloc[0]
                original_value = row.iloc[col_idx]

                # Obtener categoría de costo para esta SbN
                cost_category = cost_cat_dict.get(sbn_id)

                if cost_category is None or pd.isna(original_value):
                    continue

                # Hacer lookup en el diccionario
                try:
                    cost_category = int(cost_category)
                    original_value = int(original_value)

                    lookup_key = (cost_category, original_value)
                    if lookup_key in matrix_dict:
                        new_value = matrix_dict[lookup_key]
                        df_adjusted.at[row_idx, col_name] = new_value
                    # No imprimir advertencia para evitar spam, la mayoría de combinaciones son válidas

                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error recategorizando SbN {sbn_id}, columna {col_name}: {e}")
                    continue

        return df_adjusted

    def process_all(self, financial_option='investment_and_maintenance'):
        """
        Ejecutar todo el pipeline de procesamiento.

        Args:
            financial_option: Opción financiera para categorización

        Returns:
            bool: True si todo fue exitoso
        """
        print("🚀 Iniciando procesamiento completo de costos")

        success = True
        success &= self.calculate_adjusted_costs()
        success &= self.categorize_costs(financial_option)
        success &= self.recategorize_challenges()

        if success:
            print("✅ Procesamiento de costos completado exitosamente")
        else:
            print("⚠️ Procesamiento completado con errores")

        return success
