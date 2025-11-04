"""
Generador de fichas técnicas de SbN en PDF.

Este módulo:
1. Categoriza costos mínimos y máximos de cada SbN
2. Actualiza las fichas en Excel (Fichas_SbN_{idioma}.xlsx)
3. Exporta cada ficha a PDF en carpeta 03-SbN
"""

import os
import time
import pandas as pd
import win32com.client
from pathlib import Path


class SbnSheetsGenerator:
    """
    Genera fichas técnicas de SbN en PDF con categorías de costos actualizadas.
    """

    # Mapeo de categorías numéricas a textos (multiidioma)
    CATEGORY_LABELS = {
        'es': {1: 'Muy bajo', 2: 'Bajo', 3: 'Medio', 4: 'Alto', 5: 'Muy alto'},
        'en': {1: 'Very low', 2: 'Low', 3: 'Medium', 4: 'High', 5: 'Very high'},
        'pt': {1: 'Muito baixo', 2: 'Baixo', 3: 'Médio', 4: 'Alto', 5: 'Muito alto'}
    }

    def __init__(self, project_folder, language='es', financial_option='investment_and_maintenance'):
        """
        Inicializar generador de fichas.

        Args:
            project_folder: Ruta del proyecto
            language: Idioma ('es', 'en', 'pt')
            financial_option: 'investment', 'maintenance', o 'investment_and_maintenance'
        """
        self.project_folder = os.path.normpath(project_folder)
        self.language = language
        self.financial_option = financial_option

        # Rutas
        self.base_path = os.path.dirname(os.path.dirname(__file__))
        self.weight_matrix_path = os.path.normpath(
            os.path.join(self.base_path, 'locales', 'Weight_Matrix.xlsx')
        )
        self.fichas_excel_path = os.path.normpath(
            os.path.join(self.base_path, 'locales', f'Fichas_SbN_{language}.xlsx')
        )
        self.output_folder = os.path.normpath(
            os.path.join(self.project_folder, '03-SbN')
        )

        # Crear carpeta de salida si no existe
        os.makedirs(self.output_folder, exist_ok=True)

        # DataFrames
        self.df_cost = None
        self.df_categories = None
        self.cost_categories_map = {}  # {sbn_id: {'min_cat': texto, 'max_cat': texto}}

    def load_cost_data(self):
        """
        Cargar datos de costos desde Weight_Matrix.xlsx.
        """
        print(f"📊 Cargando datos de costos desde Weight_Matrix.xlsx")

        try:
            # Leer hoja de costos
            self.df_cost = pd.read_excel(self.weight_matrix_path, sheet_name='Cost')
            print(f"✓ Costos cargados: {len(self.df_cost)} SbN")

            # Leer tabla de categorías
            self.df_categories = pd.read_excel(
                self.weight_matrix_path,
                sheet_name='Categorias_Costos'
            )
            print(f"✓ Categorías cargadas: {len(self.df_categories)} rangos")

            return True

        except Exception as e:
            print(f"❌ Error cargando datos de costos: {e}")
            import traceback
            traceback.print_exc()
            return False

    def categorize_costs_min_max(self):
        """
        Categorizar costos mínimos y máximos de cada SbN.

        Determina la categoría (1-5) para los valores mínimos y máximos
        según la opción financiera seleccionada.
        """
        print(f"🏷️  Categorizando costos min/max según opción: {self.financial_option}")

        # Determinar columnas según opción financiera
        if self.financial_option == 'investment':
            min_cost_col = 'Cost_Min_Inv'
            max_cost_col = 'Cost_Max_Inv'
            cat_min_col = 'Inv_Min'
            cat_max_col = 'Inv_Max'
        elif self.financial_option == 'maintenance':
            min_cost_col = 'Cost_Min_M'
            max_cost_col = 'Cost_Max_M'
            cat_min_col = 'Man_Min'
            cat_max_col = 'Man_Max'
        else:  # investment_and_maintenance
            min_cost_col = 'Cost_Min_Total'
            max_cost_col = 'Cost_Max_Total'
            cat_min_col = 'Total_Min'
            cat_max_col = 'Total_Max'

        # Verificar que existan las columnas
        if min_cost_col not in self.df_cost.columns or max_cost_col not in self.df_cost.columns:
            print(f"⚠️ No se encontraron columnas {min_cost_col} o {max_cost_col}")
            print(f"   Columnas disponibles: {list(self.df_cost.columns)}")
            # Usar valores por defecto si no existen
            min_cost_col = 'Cost_Mean_Inv' if 'Cost_Mean_Inv' in self.df_cost.columns else self.df_cost.columns[2]
            max_cost_col = min_cost_col

        # Categorizar cada SbN
        for idx, row in self.df_cost.iterrows():
            sbn_id = row['ID']

            # Obtener valores de costos
            min_value = pd.to_numeric(row.get(min_cost_col), errors='coerce')
            max_value = pd.to_numeric(row.get(max_cost_col), errors='coerce')

            # Categorizar
            min_category = self._find_category(min_value, cat_min_col, cat_max_col)
            max_category = self._find_category(max_value, cat_min_col, cat_max_col)

            # Convertir a texto según idioma
            min_label = self.CATEGORY_LABELS[self.language].get(min_category, 'N/A')
            max_label = self.CATEGORY_LABELS[self.language].get(max_category, 'N/A')

            self.cost_categories_map[sbn_id] = {
                'min_cat': min_label,
                'max_cat': max_label,
                'min_num': min_category,
                'max_num': max_category
            }

        print(f"✓ Categorizadas {len(self.cost_categories_map)} SbN")

        # Mostrar distribución
        min_dist = {}
        max_dist = {}
        for data in self.cost_categories_map.values():
            min_dist[data['min_num']] = min_dist.get(data['min_num'], 0) + 1
            max_dist[data['max_num']] = max_dist.get(data['max_num'], 0) + 1

        print(f"📊 Distribución categorías mínimas: {dict(sorted(min_dist.items()))}")
        print(f"📊 Distribución categorías máximas: {dict(sorted(max_dist.items()))}")

        return True

    def _find_category(self, value, min_col, max_col):
        """
        Buscar categoría para un valor dado.

        Args:
            value: Valor a categorizar
            min_col: Columna de mínimo en df_categories
            max_col: Columna de máximo en df_categories

        Returns:
            int: Categoría (1-5)
        """
        # Manejar valores nulos
        if pd.isna(value):
            return 1  # Categoría por defecto

        try:
            value = float(value)
        except (ValueError, TypeError):
            return 1

        # Buscar en rangos
        for idx, row in self.df_categories.iterrows():
            try:
                min_val = float(row[min_col])
                max_val = float(row[max_col])

                if min_val <= value <= max_val:
                    return int(row['Categoria'])
            except (ValueError, TypeError, KeyError):
                continue

        # Si no encuentra, asignar categoría más alta
        return int(self.df_categories['Categoria'].max())

    def generate_all_sheets(self):
        """
        Generar todas las fichas de SbN en PDF.

        Para cada SbN:
        1. Actualiza el selector en Excel
        2. Escribe categorías de costos en columnas L y M
        3. Exporta a PDF
        """
        print(f"\n📄 Generando fichas técnicas de SbN en PDF")
        print(f"   Excel fuente: {self.fichas_excel_path}")
        print(f"   Carpeta destino: {self.output_folder}")

        if not os.path.exists(self.fichas_excel_path):
            print(f"❌ No se encontró el archivo de fichas: {self.fichas_excel_path}")
            return False

        # Leer hoja SbN para obtener lista de IDs y nombres
        try:
            df_sbn = pd.read_excel(self.fichas_excel_path, sheet_name='SbN')
            # Filtrar filas con ID válido (segunda fila en adelante, primera es encabezado)
            df_sbn_valid = df_sbn[df_sbn['ID'].notna()].copy()

            # Crear lista de tuplas (ID, Nombre)
            # Columna A = ID, Columna B = SbN (nombre)
            sbn_list = []
            for idx, row in df_sbn_valid.iterrows():
                sbn_id = int(row['ID'])
                sbn_name = row.iloc[1]  # Columna B (segunda columna)
                sbn_list.append((sbn_id, sbn_name))

            print(f"✓ Encontradas {len(sbn_list)} SbN en el archivo")
        except Exception as e:
            print(f"❌ Error leyendo hoja SbN: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Iniciar COM de Excel
        print("📂 Iniciando Microsoft Excel (oculto)...")
        try:
            excel = win32com.client.Dispatch('Excel.Application')
            excel.Visible = False  # No mostrar Excel
            excel.DisplayAlerts = False  # No mostrar alertas
            excel.ScreenUpdating = False  # Acelerar procesamiento

            # Abrir workbook
            wb_path = os.path.abspath(self.fichas_excel_path)
            wb = excel.Workbooks.Open(wb_path)
            ws_fichas = wb.Worksheets('Fichas')

            print("✓ Archivo Excel abierto en modo oculto")

        except Exception as e:
            print(f"❌ Error abriendo Excel: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Procesar cada SbN
        successful = 0
        for sbn_id, sbn_name in sbn_list:
            try:
                print(f"\n  → SbN ID {sbn_id} - {sbn_name}:")

                # Buscar la celda del selector (primera vez, detectar automáticamente)
                # El selector usa el NOMBRE de la SbN, no el ID
                selector_cell = self._find_selector_cell(wb)

                if selector_cell:
                    # Actualizar selector con el NOMBRE de la SbN (columna B)
                    ws_fichas.Range(selector_cell).Value = sbn_name
                    print(f"    ✓ Selector actualizado: {selector_cell} = '{sbn_name}'")

                # Obtener categorías de costos
                cost_data = self.cost_categories_map.get(sbn_id)
                if cost_data:
                    # Escribir en columnas L y M (fila específica, asumir fila 2 o detectar)
                    # Necesito encontrar la fila correcta en la ficha
                    cost_row = self._find_cost_row(ws_fichas)

                    ws_fichas.Range(f'L{cost_row}').Value = cost_data['min_cat']
                    ws_fichas.Range(f'M{cost_row}').Value = cost_data['max_cat']
                    print(f"    ✓ Categorías escritas: L{cost_row}={cost_data['min_cat']}, M{cost_row}={cost_data['max_cat']}")
                else:
                    print(f"    ⚠️  No hay datos de costos para SbN {sbn_id}")

                # Guardar cambios antes de exportar
                wb.Save()

                # Exportar a PDF
                pdf_path = os.path.normpath(
                    os.path.join(self.output_folder, f'SbN_{sbn_id}.pdf')
                )
                pdf_path_abs = os.path.abspath(pdf_path)

                ws_fichas.ExportAsFixedFormat(0, pdf_path_abs)  # 0 = xlTypePDF
                print(f"    ✓ PDF generado: SbN_{sbn_id}.pdf")

                successful += 1

                # Esperar 0.1 segundos para evitar errores de COM
                time.sleep(0.1)

            except Exception as e:
                print(f"    ❌ Error procesando SbN {sbn_id}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Cerrar Excel
        try:
            wb.Close(SaveChanges=False)
            excel.ScreenUpdating = True  # Restaurar
            excel.Quit()
            print(f"\n✅ Excel cerrado")
        except:
            pass

        print(f"\n{'='*60}")
        print(f"✅ Generación completada: {successful}/{len(sbn_list)} fichas generadas")
        print(f"📁 Fichas guardadas en: {self.output_folder}")

        return successful > 0

    def _find_selector_cell(self, workbook):
        """
        Encontrar la celda del selector en la hoja Fichas.

        Busca en la fila 2 una celda que contenga un valor numérico
        que corresponda a un ID de SbN.

        Returns:
            str: Dirección de celda (ej: 'B2') o None
        """
        # Estrategia simple: asumir que el selector está en una celda específica
        # Por defecto, muchas hojas usan B2 o C2 para selectores
        # Retornar la primera celda común
        common_selector_cells = ['B2', 'C2', 'D2', 'E2']

        for cell in common_selector_cells:
            try:
                ws_fichas = workbook.Worksheets('Fichas')
                value = ws_fichas.Range(cell).Value
                if value and isinstance(value, (int, float)):
                    return cell
            except:
                continue

        # Si no encuentra, usar B2 por defecto
        return 'B2'

    def _find_cost_row(self, worksheet):
        """
        Encontrar la fila donde se deben escribir las categorías de costos.

        Busca en las columnas L y M una fila apropiada (puede ser fija o detectada).

        Returns:
            int: Número de fila
        """
        # Estrategia: buscar una fila que tenga etiquetas o esté vacía
        # Por simplicidad, usar una fila fija común
        # En muchas fichas, los datos están en filas específicas

        # Buscar entre filas 10-50 una celda vacía o con placeholder
        for row in range(10, 51):
            try:
                val_l = worksheet.Range(f'L{row}').Value
                val_m = worksheet.Range(f'M{row}').Value

                # Si ambas están vacías o tienen placeholder, usar esta fila
                if (val_l is None or val_l == '' or val_l == 'N/A') and \
                   (val_m is None or val_m == '' or val_m == 'N/A'):
                    return row
            except:
                continue

        # Fila por defecto si no encuentra
        return 20

    def process_all(self):
        """
        Ejecutar todo el pipeline de generación de fichas.

        Returns:
            bool: True si fue exitoso
        """
        print("🚀 Iniciando generación de fichas técnicas de SbN")

        success = True
        success &= self.load_cost_data()
        success &= self.categorize_costs_min_max()

        if success:
            success &= self.generate_all_sheets()

        if success:
            print("\n" + "="*60)
            print("✅ Generación de fichas completada exitosamente")
            print("="*60)
        else:
            print("\n⚠️ Generación completada con errores")

        return success
