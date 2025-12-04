# -*- coding: utf-8 -*-
"""
report_generator.py (optimized)
-------------------------------
Generador de PDF con FPDF (fpdf2) usando HELVETICA (fuente core, sin TTF),
con un sistema de estilos reutilizable (título, subtítulo, h1, h2, párrafo,
encabezados/filas de tabla) y helpers para:
  - tablas con alto de fila automático y wrap por columna
  - secciones con encabezados consistentes
  - numeración de páginas en pie de página

Mantiene el API original:
  class ReportGenerator(project_path, language='es')
    - load_data()
    - generate_pdf(output_path)

Estructura de datos esperada (como en tu proyecto original):
  - locales/<lang>.json  -> etiquetas (report, water_security.challenges, ...)
  - utilities/indicators/<lang>.json -> indicadores por SbN
  - locales/CAF_taxonomy_tree.json   -> taxonomía
  - project.json                     -> info de proyecto (name, objective, ...)
  - SbN_Prioritization.csv           -> columnas: ID, Prioridad, order (solo muestra order > 0)
  - DF_WS*.csv                       -> seguridad hídrica
  - *Barriers*.csv                   -> barreras
  - DF_OC* / Otros / DF_Otros*.csv   -> otros desafíos (nombres alternativos)

Requisitos:
    pip install fpdf2
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Sequence, Optional, Dict, Any, Tuple
from tkinter import messagebox
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfWriter, PdfReader
from src.utils.resource_path import get_resource_path
from src.reports.sbn_sheets_generator import SbnSheetsGenerator
from src.core.language_manager import get_text

print('##### Usa este codigo #####')
# ============================================================
# Estilos para PDF (HELVTICA core) y utilidades
# ============================================================
class StyledPDF(FPDF):
    """FPDF con tema/estilos reutilizables y helpers de tablas y secciones."""

    def __init__(self, orientation: str = "P", unit: str = "mm", format: str = "A4"):
        super().__init__(orientation=orientation, unit=unit, format=format)
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

        # Paleta
        self.colors = {
            "primary": (33, 150, 243),      # azul secciones
            "secondary": (66, 165, 245),    # azul subsecciones
            "text": (0, 0, 0),
            "muted": (97, 97, 97),
            "table_header_bg": (238, 238, 238),
        }

        # Tipografía base (Arial con soporte Unicode completo para español/portugués)
        # Registrar familia Arial desde Windows Fonts
        import platform

        # Rutas de fuentes según sistema operativo
        if platform.system() == "Windows":
            fonts_dir = "C:\\Windows\\Fonts\\"
        else:
            # Para otros sistemas, fpdf2 intentará encontrar Arial
            fonts_dir = ""

        # Registrar variantes de Arial
        self.add_font("Arial", "", f"{fonts_dir}arial.ttf" if fonts_dir else "arial.ttf")
        self.add_font("Arial", "B", f"{fonts_dir}arialbd.ttf" if fonts_dir else "arialbd.ttf")
        self.add_font("Arial", "I", f"{fonts_dir}ariali.ttf" if fonts_dir else "ariali.ttf")
        self.add_font("Arial", "BI", f"{fonts_dir}arialbi.ttf" if fonts_dir else "arialbi.ttf")

        self.base_family = "Arial"
        self._build_default_styles()

        # Encabezado/pie
        self.show_header = False
        self.show_footer = True

    # ------------------ Estilos ------------------
    def _build_default_styles(self):
        self.styles = {
            "title":        {"family": self.base_family, "style": "B", "size": 16, "color": self.colors["primary"], "lead": 10},
            "subtitle":     {"family": self.base_family, "style": "I", "size": 10, "color": self.colors["muted"],   "lead": 5},
            "h1":           {"family": self.base_family, "style": "B", "size": 12, "color": self.colors["primary"], "lead": 8},
            "h2":           {"family": self.base_family, "style": "B", "size": 10, "color": self.colors["secondary"], "lead": 6},
            "p":            {"family": self.base_family, "style": "",  "size": 9,  "color": self.colors["text"],    "lead": 5},
            "caption":      {"family": self.base_family, "style": "I", "size": 8,  "color": self.colors["muted"],   "lead": 4},
            "table_header": {"family": self.base_family, "style": "B", "size": 9,  "color": self.colors["text"],    "lead": 6},
            "table_cell":   {"family": self.base_family, "style": "",  "size": 8,  "color": self.colors["text"],    "lead": 5},
        }

    def set_style(self, name: str) -> int:
        st = self.styles.get(name, self.styles["p"])
        self.set_font(st["family"], st["style"], st["size"])
        self.set_text_color(*st["color"])
        return st.get("lead", 5)

    # ------------------ Encabezado y pie ------------------
    def header(self):
        if not self.show_header:
            return

    def footer(self):
        if not self.show_footer:
            return
        self.set_y(-15)
        self.set_style("caption")
        self.cell(0, 10, f"Página {self.page_no()}", align="R")

    # ------------------ Bloques de texto ------------------
    def hr(self, y_offset: float = 2):
        y = self.get_y()
        self.set_draw_color(*self.colors["primary"])
        self.set_line_width(0.4)
        self.line(self.l_margin, y + y_offset, self.w - self.r_margin, y + y_offset)
        self.ln(4)

    def h1(self, text: str):
        lead = self.set_style("h1")
        self.cell(0, 8, text, ln=True)
        self.ln(max(0, lead - 3))

    def h2(self, text: str):
        lead = self.set_style("h2")
        self.cell(0, 6, text, ln=True)
        self.ln(max(0, lead - 3))

    def p(self, text: str, w: float = 0):
        lead = self.set_style("p")
        self.multi_cell(w or 0, 5, "" if text is None else str(text))
        self.ln(max(0, lead - 5))

    def caption(self, text: str):
        lead = self.set_style("caption")
        self.multi_cell(0, 4, "" if text is None else str(text))
        self.ln(max(0, lead - 4))

    # ------------------ Tablas ------------------
    def _split_text(self, text: str, max_w: float) -> List[str]:
        text = "" if text is None else str(text)
        try:
            # fpdf2: split_only disponible
            lines = self.multi_cell(max_w, 4, text, split_only=True)  # type: ignore
            return lines
        except TypeError:
            # Fallback aproximado
            words = text.replace("\r", "").split()
            lines, current = [], ""
            for w in words:
                test = (current + " " + w).strip()
                if self.get_string_width(test) <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = w
            if current:
                lines.append(current)
            flat = []
            for line in lines:
                flat.extend(line.split("\n"))
            return flat or [""]

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]],
        col_widths: Sequence[float],
        align: Optional[Sequence[str]] = None,
        header_fill: bool = True,
        borders: int = 1,
    ) -> None:
        if not headers or not col_widths:
            return
        ncol = len(headers)
        if align is None:
            align = ["L"] * ncol
        if len(col_widths) != ncol:
            raise ValueError("col_widths debe tener la misma longitud que headers")
        if len(align) != ncol:
            raise ValueError("align debe tener la misma longitud que headers")

        # Encabezado
        self.set_style("table_header")
        if header_fill:
            self.set_fill_color(*self.colors["table_header_bg"])
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, "" if h is None else str(h), border=1 if borders else 0, ln=0, align="C", fill=header_fill)
        self.ln(6)

        # Filas
        self.set_style("table_cell")
        for row in rows:
            # altura según el máximo # líneas
            lines_per_cell = []
            for i, cell in enumerate(row[:ncol]):
                cw = col_widths[i]
                lines = self._split_text("" if cell is None else str(cell), cw)
                lines_per_cell.append(len(lines) if len(lines) > 0 else 1)
            row_h = 4 * max(lines_per_cell)

            x0 = self.get_x()
            y0 = self.get_y()

            for i, cell in enumerate(row[:ncol]):
                cw = col_widths[i]
                ax = align[i]
                if borders:
                    self.rect(self.get_x(), self.get_y(), cw, row_h)
                txt = "" if cell is None else str(cell)
                x, y = self.get_x(), self.get_y()
                self.multi_cell(cw, 4, txt, border=0, align=ax)
                self.set_xy(x + cw, y)

            self.set_xy(x0, y0 + row_h)


# ============================================================
# Report Generator (API original + PDF estilizado)
# ============================================================
class ReportGenerator:
    def __init__(self, project_path: str, language: str = 'es'):
        self.project_path = project_path
        self.language = language
        self.project_data: Dict[str, Any] = {}
        self.selected_sbn: List[int] = []
        self.sbn_orders: Dict[int, int] = {}  # Mapeo de sbn_id -> order (prioridad)
        self.water_security_data: List[Dict[str, Any]] = []
        self.barriers_data: List[Dict[str, Any]] = []
        self.other_challenges_data: List[Dict[str, Any]] = []
        self.indicators_data: Dict[str, Any] = {}
        self.taxonomy_tree: Dict[str, Any] = {}
        self.texts: Dict[str, str] = {}
        self.water_challenges_texts: Dict[str, str] = {}
        self.other_challenges_texts: Dict[str, str] = {}
        self.barrier_groups_texts: Dict[str, str] = {}
        self.barriers_translations: Dict[str, Dict[str, str]] = {}
        self.barrier_values_texts: Dict[str, str] = {}
        self.sbn_solutions: Dict[str, str] = {}

    # ------------------ Carga de datos ------------------
    def load_data(self):
        """Cargar textos, tablas CSV y JSON auxiliares desde el proyecto/utilidades."""
        # Textos multiidioma
        locale_path = get_resource_path(os.path.join('locales', f'{self.language}.json'))
        if os.path.exists(locale_path):
            with open(locale_path, 'r', encoding='utf-8') as f:
                locale = json.load(f)
                self.texts = locale.get('report', {})
                self.water_challenges_texts = locale.get('water_security', {}).get('challenges', {})
                self.other_challenges_texts = locale.get('other_challenges', {}).get('challenges', {})
                self.barrier_groups_texts = locale.get('barriers', {}).get('groups', {})
                self.sbn_solutions = locale.get('sbn_solutions', {})

                # Crear mapeo de códigos de valor de barreras a textos
                barriers_info = locale.get('barriers', {})
                value_labels = barriers_info.get('value_labels', {})
                value_labels_code = barriers_info.get('value_labels_code', {})

                # Invertir value_labels_code para obtener {código: clave}
                for key, code in value_labels_code.items():
                    if key in value_labels:
                        self.barrier_values_texts[code] = value_labels[key]

        # project.json
        project_json = os.path.join(self.project_path, 'project.json')
        if os.path.exists(project_json):
            with open(project_json, 'r', encoding='utf-8') as f:
                self.project_data = json.load(f)

        # SbN priorizadas (cargadas desde SbN_Prioritization.csv con columna 'order')
        prioritization_csv = os.path.join(self.project_path, 'SbN_Prioritization.csv')
        if os.path.exists(prioritization_csv):
            try:
                with open(prioritization_csv, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    # Cargar solo SbN con order > 0, mantener el orden
                    sbn_data = [(int(row['ID']), int(row.get('order', 0)))
                                for row in reader
                                if int(row.get('order', 0)) > 0]
                    # Ordenar por order ascendente (1, 2, 3...)
                    sbn_data.sort(key=lambda x: x[1])
                    self.selected_sbn = [sbn_id for sbn_id, _ in sbn_data]
                    self.sbn_orders = {sbn_id: order for sbn_id, order in sbn_data}
            except Exception as e:
                print(f"Error loading prioritization: {e}")
                self.selected_sbn = []
                self.sbn_orders = {}
        else:
            self.selected_sbn = []
            self.sbn_orders = {}

        # Seguridad hídrica
        water_csv = self._find_csv('DF_WS')
        if water_csv and os.path.exists(water_csv):
            with open(water_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.water_security_data = list(reader)

        # Barreras
        barriers_csv = self._find_csv('Barriers')
        if barriers_csv and os.path.exists(barriers_csv):
            with open(barriers_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.barriers_data = list(reader)

        # Nombres de columnas del CSV de barreras según idioma
        self.barrier_col_code = self.texts.get('barriers', {}).get('csv_headers', {}).get('barrier_code', 'Codigo_Barrera')
        self.barrier_col_value = self.texts.get('barriers', {}).get('csv_headers', {}).get('numeric_value', 'Valor_Numerico')
        self.barrier_col_group_code = self.texts.get('barriers', {}).get('csv_headers', {}).get('group_code', 'Codigo_Grupo')
        self.barrier_col_group_enabled = self.texts.get('barriers', {}).get('csv_headers', {}).get('group_enabled', 'Grupo_Habilitado')

        # Traducciones de barreras
        barriers_locale_path = get_resource_path(os.path.join('locales', f'Barries_{self.language}.csv'))
        if os.path.exists(barriers_locale_path):
            with open(barriers_locale_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get(self.barrier_col_code,'')
                    if code:
                        self.barriers_translations[code] = {
                            'descripcion': row.get('Descripcion', ''),
                            'subcategoria': row.get('Subcategoria', ''),
                            'grupo': row.get('Grupo', ''),
                            'codigo_grupo': row.get(self.barrier_col_group_code, '')
                        }

        # Otros desafíos (nombres alternativos para mayor robustez)
        other_csv = self._find_csv('D_O')
        if other_csv and os.path.exists(other_csv):
            with open(other_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.other_challenges_data = list(reader)

        # Indicadores
        ind_path = get_resource_path(os.path.join('utilities', 'indicators', f'{self.language}.json'))
        if os.path.exists(ind_path):
            with open(ind_path, 'r', encoding='utf-8') as f:
                self.indicators_data = json.load(f)

        # Taxonomía CAF (según idioma)
        tax_filename = f'CAF_taxonomy_tree_{self.language}.json'
        tax_path = get_resource_path(os.path.join('locales', tax_filename))

        # Si no existe el archivo del idioma, usar español como fallback
        if not os.path.exists(tax_path):
            tax_filename = 'CAF_taxonomy_tree_es.json'
            tax_path = get_resource_path(os.path.join('locales', tax_filename))

        if os.path.exists(tax_path):
            with open(tax_path, 'r', encoding='utf-8') as f:
                self.taxonomy_tree = json.load(f)

    def _find_csv(self, *names) -> Optional[str]:
        import glob
        for name in names:
            matches = glob.glob(os.path.join(self.project_path, f'*{name}*.csv'))
            if matches:
                return matches[0]
        return None

    # ------------------ Render helpers ------------------
    def _auto_map_path(self) -> Optional[str]:
        """Busca una imagen de mapa común dentro del proyecto."""
        # Primero busca en 01-Watershed (estructura V1)
        img_path = os.path.join(self.project_path, '01-Watershed', 'Watershed.jpg')
        if os.path.exists(img_path):
            return img_path

        # Fallback: busca en raíz del proyecto
        candidates = [
            "Watershed.jpg", "Watershed.png", "map.png", "mapa.png", "Mapa.png", "cuenca.png",
        ]
        for c in candidates:
            p = os.path.join(self.project_path, c)
            if os.path.exists(p):
                return p
        return None

    def _pair_list_to_rows(self, pairs: List[Tuple[str, str]]) -> List[List[str]]:
        out = []
        for k, v in pairs:
            kk = "" if k is None else str(k)
            vv = "" if v is None else str(v)
            out.append([kk, vv])
        return out

    # ------------------ Generación de PDF ------------------
    def generate_pdf(self, output_path: str, generate_sbn_sheets: bool = True) -> bool:
        """
        Generar reporte PDF principal.

        Args:
            output_path: Ruta del PDF de salida
            generate_sbn_sheets: Si es True, genera fichas técnicas de SbN en PDF

        Returns:
            bool: True si fue exitoso
        """
        self.load_data()
        pdf = StyledPDF()
        pdf.add_page()

        # ---------- Portada ----------
        title_text = self.texts.get('title', 'Reporte final')
        project_info = self.project_data.get('project_info', {})
        name = project_info.get('name', '')
        if name:
            title_text = f"{title_text}"

        pdf.set_style("title")
        pdf.cell(0, 10, title_text, ln=True)
        pdf.cell(0, 10, name, ln=True)
        pdf.set_style("subtitle")
        pdf.cell(0, 10, datetime.now().strftime("%d/%m/%Y"), ln=True)
        pdf.ln(2)
        pdf.hr()

        # ---------- 1. Introducción ----------
        pdf.h1(self.texts.get('intro_title', '1 Introducción'))
        pdf.p(self.texts.get('intro_text', ''))

        # ---------- 2. Descripción general ----------
        pdf.h1(self.texts.get('section2_title', '2 Descripción general'))
        total_w = pdf.w - pdf.l_margin - pdf.r_margin
        col_widths = [total_w * 0.35, total_w * 0.65]  # 35% para campo, 65% para valor

        # Construir localización completa (país + ubicación)
        country_name = project_info.get('country_name', '')
        location = project_info.get('location', '')
        full_location = ''
        if country_name and location:
            full_location = f"{country_name} ({location})"
        elif country_name:
            full_location = country_name
        elif location:
            full_location = location
        else:
            full_location = self.texts.get('not_specified', 'No especificado')

        data_pairs = [
            (self.texts.get('acronym', 'Acrónimo'), project_info.get('acronym', self.texts.get('not_specified', 'No especificado'))),
            (self.texts.get('project_title', 'Nombre del proyecto'), name or self.texts.get('not_specified', 'No especificado')),
            (self.texts.get('description', 'Descripción'), project_info.get('description', self.texts.get('not_specified', 'No especificado')) or self.texts.get('not_specified', 'No especificado')),
            (self.texts.get('location', 'Localización'), full_location),
            (self.texts.get('objectives', 'Objetivos'), project_info.get('objective', self.texts.get('not_specified', 'No especificado')) or self.texts.get('not_specified', 'No especificado')),
            (self.texts.get('objectives_caf', 'Objetivo de financiamiento verde CAF'), project_info.get('caf_objective', self.texts.get('not_specified', 'No especificado'))),
            (self.texts.get('category_caf', 'Categoría CAF'), project_info.get('caf_category', self.texts.get('not_specified', 'No especificado'))),
            (self.texts.get('subcategory_caf', 'Subcategoría CAF'), project_info.get('caf_subcategory', self.texts.get('not_specified', 'No especificado'))),
            (self.texts.get('activity_caf', 'Actividad CAF'), project_info.get('caf_activity', self.texts.get('not_specified', 'No especificado'))),
        ]
        pdf.table([self.texts.get('field', 'Campo'), self.texts.get('value', 'Valor')],
                  self._pair_list_to_rows(data_pairs),
                  col_widths=col_widths, align=["L", "L"])
        pdf.ln(4)

        pdf.add_page()
        # ---------- 3. Caracterización de la cuenca ----------
        pdf.h1(self.texts.get('section3_title', '3 Caracterización de la cuenca'))

        # 3.1 Mapa - Ajustar dinámicamente al espacio disponible en página 1
        pdf.h2(self.texts.get('section3_1', '3.1 Mapa de referencia'))
        map_path = self._auto_map_path()
        if map_path:
            pdf.caption(self.texts.get('figure1', 'Figura 1. Delimitación de la cuenca.'))

            # Calcular espacio disponible en la página actual
            current_y = pdf.get_y()
            page_height = pdf.h
            bottom_margin = pdf.b_margin
            available_height = page_height - current_y - bottom_margin - 5  # 5mm de margen de seguridad
            available_width = pdf.w - pdf.l_margin - pdf.r_margin

            # Establecer límites razonables
            min_height = 50  # mínimo 50mm
            max_height = 120  # máximo 120mm

            # Obtener dimensiones reales de la imagen para calcular aspect ratio
            try:
                from PIL import Image
                img = Image.open(map_path)
                img_width_px, img_height_px = img.size
                aspect_ratio = img_width_px / img_height_px
            except Exception:
                # Si falla, asumir aspect ratio 4:3
                aspect_ratio = 4 / 3

            # Determinar espacio objetivo
            if available_height >= max_height:
                target_height = max_height
            elif available_height >= min_height:
                target_height = available_height
            else:
                # No hay suficiente espacio, ir a nueva página
                pdf.add_page()
                current_y = pdf.get_y()
                available_height = page_height - current_y - bottom_margin - 5
                target_height = min(max_height, available_height)

            # Calcular dimensiones proporcionales
            # Opción 1: ajustar por altura
            img_height = target_height
            img_width = img_height * aspect_ratio

            # Si el ancho excede el disponible, ajustar por ancho
            if img_width > available_width:
                img_width = available_width
                img_height = img_width / aspect_ratio

            # Centrar imagen horizontalmente
            x_offset = pdf.l_margin + (available_width - img_width) / 2

            # Insertar imagen con dimensiones proporcionales
            pdf.image(map_path, x=x_offset, w=img_width, h=img_height)
            pdf.ln(2)
        else:
            pdf.caption(self.texts.get('figure1_missing', 'No se encontró la imagen. Continúa el informe sin el mapa.'))

        # 3.2 Métricas morfología/clima - Nueva página para la tabla
        pdf.h2(self.texts.get('section3_2', '3.2 Caracterización'))
        watershed = self.project_data.get('watershed_data', {})
        morph   = watershed.get('morphometry', {})
        climate = watershed.get('climate', {})

        wdata_pairs = [
            (self.texts.get('area', 'Área'), str(morph.get('area', 'N/A'))),
            (self.texts.get('perimeter', 'Perímetro'), str(morph.get('perimeter', 'N/A'))),
            (self.texts.get('min_elevation', 'Elevación mínima'), str(morph.get('min_elevation', 'N/A'))),
            (self.texts.get('max_elevation', 'Elevación máxima'), str(morph.get('max_elevation', 'N/A'))),
            (self.texts.get('avg_slope', 'Pendiente media'), str(morph.get('avg_slope', 'N/A'))),
            (self.texts.get('precipitation', 'Precipitación'), str(climate.get('precipitation', 'N/A'))),
            (self.texts.get('temperature', 'Temperatura'), str(climate.get('temperature', 'N/A'))),
        ]
        pdf.table([self.texts.get('metric', 'Métrica'), self.texts.get('value', 'Valor')],
                  self._pair_list_to_rows(wdata_pairs),
                  col_widths=col_widths, align=["L", "L"])
        pdf.ln(3)

        # ---------- 4. Seguridad hídrica (DF_WS) ----------
        pdf.h1(self.texts.get('section4_title', '4 Seguridad hídrica (desafíos)'))
        headers = [self.texts.get('challenge', 'Desafío'), self.texts.get('qualification', 'Calificación')]
        colw = [total_w * 0.82, total_w * 0.18]  # 82% para desafío, 18% para calificación

        rows = []
        if self.water_security_data:
            # muestra hasta 4 filas
            for row in self.water_security_data:
                code = row.get('Codigo_Desafio', '')
                name = self.water_challenges_texts.get(code, code)
                value = row.get('Valor_Importancia', self.texts.get('not_available', 'No disponible'))
                rows.append([name, str(value)])
        else:
            rows.append([self.texts.get('not_available', 'No disponible'), ''])

        pdf.table(headers, rows, col_widths=colw, align=["L", "C"])
        pdf.ln(3)

        # ---------- 5. Barreras ----------
        pdf.h1(self.texts.get('section5_title', '5 Barreras'))
        headers_b = [
            self.texts.get('group', 'Grupo'),
            self.texts.get('subcategory', 'Subcategoría'),
            self.texts.get('description', 'Descripción'),
            self.texts.get('qualification', 'Calificación')
        ]
        colw_b = [total_w * 0.19, total_w * 0.25, total_w * 0.36, total_w * 0.20]  # Proporción balanceada

        if not self.barriers_data or not self.barriers_translations:
            pdf.table(headers_b, [[self.texts.get('not_available', 'No disponible'), '', '', '']], col_widths=colw_b,
                      align=["L", "L", "L", "C"])
        else:
            # Filtrar barreras habilitadas y hacer join con traducciones
            barriers_full = []
            for barrier in self.barriers_data:
                grupo_habilitado = str(barrier.get('Status', '0')).strip()
                if grupo_habilitado == '1':
                    codigo_barrera = barrier.get('Code', '')
                    valor = barrier.get('Value', '')
                    if codigo_barrera in self.barriers_translations:
                        trans = self.barriers_translations[codigo_barrera]
                        barriers_full.append({
                            'grupo': trans.get('grupo', ''),
                            'subcategoria': trans.get('subcategoria', ''),
                            'descripcion': trans.get('descripcion', ''),
                            'valor': str(valor)
                        })

            if not barriers_full:
                pdf.table(headers_b, [[self.texts.get('not_available', 'No disponible'), '', '', '']],
                          col_widths=colw_b, align=["L", "L", "L", "C"])
            else:
                # Ordenar por grupo y subcategoría
                barriers_full.sort(key=lambda x: (x['grupo'], x['subcategoria']))

                # Helper para dibujar encabezados
                def draw_headers():
                    pdf.set_style("table_header")
                    pdf.set_fill_color(*pdf.colors["table_header_bg"])
                    for i, h in enumerate(headers_b):
                        pdf.cell(colw_b[i], 6, h, border=1, ln=0, align="C", fill=True)
                    pdf.ln(6)
                    pdf.set_style("table_cell")  # Restaurar estilo normal después de encabezados

                # Dibujar encabezados iniciales
                draw_headers()

                prev_grupo = None
                prev_subcat = None

                for barrier in barriers_full:
                    grupo = barrier['grupo']
                    subcat = barrier['subcategoria']
                    desc = barrier['descripcion']
                    valor_num = barrier['valor']

                    # Transformar valor numérico a texto según idioma
                    valor = self.barrier_values_texts.get(valor_num, valor_num)

                    # Calcular altura estimada de la fila
                    pdf.set_style("table_cell")  # Asegurar estilo normal
                    lines_desc = pdf._split_text(desc, colw_b[2])
                    estimated_height = 4 * max(len(lines_desc), 1)

                    # Verificar espacio disponible
                    space_left = pdf.h - pdf.get_y() - pdf.b_margin
                    if space_left < estimated_height + 10:  # +10 margen de seguridad
                        pdf.add_page()
                        draw_headers()
                        prev_grupo = None
                        prev_subcat = None

                    # Determinar qué mostrar (agrupación visual)
                    display_grupo = grupo if grupo != prev_grupo else ''
                    display_subcat = subcat if (grupo != prev_grupo or subcat != prev_subcat) else ''

                    # Asegurar estilo normal para las celdas
                    pdf.set_style("table_cell")

                    # Dibujar fila
                    x0 = pdf.get_x()
                    y0 = pdf.get_y()

                    # Columna 1: Grupo
                    pdf.rect(x0, y0, colw_b[0], estimated_height)
                    pdf.set_xy(x0, y0)
                    pdf.multi_cell(colw_b[0], 4, display_grupo, border=0, align="L")

                    # Columna 2: Subcategoría
                    x1 = x0 + colw_b[0]
                    pdf.rect(x1, y0, colw_b[1], estimated_height)
                    pdf.set_xy(x1, y0)
                    pdf.multi_cell(colw_b[1], 4, display_subcat, border=0, align="L")

                    # Columna 3: Descripción
                    x2 = x1 + colw_b[1]
                    pdf.rect(x2, y0, colw_b[2], estimated_height)
                    pdf.set_xy(x2, y0)
                    pdf.multi_cell(colw_b[2], 4, desc, border=0, align="L")

                    # Columna 4: Calificación
                    x3 = x2 + colw_b[2]
                    pdf.rect(x3, y0, colw_b[3], estimated_height)
                    pdf.set_xy(x3, y0)
                    pdf.multi_cell(colw_b[3], 4, valor, border=0, align="C")

                    # Mover a la siguiente fila
                    pdf.set_xy(x0, y0 + estimated_height)

                    # Actualizar valores previos
                    prev_grupo = grupo
                    prev_subcat = subcat

        pdf.ln(3)

        # ---------- 6. Otros desafíos ----------
        pdf.h1(self.texts.get('section6_title', '6 Otros desafíos'))
        headers_o = [self.texts.get('challenge', 'Desafío'), self.texts.get('qualification', 'Calificación')]
        colw_o = [total_w * 0.82, total_w * 0.18]  # 82% para desafío, 18% para calificación

        if not self.other_challenges_data:
            pdf.table(headers_o, [[self.texts.get('not_available', 'No disponible'), '']], col_widths=colw_o, align=["L", "C"])
        else:
            # Helper para dibujar encabezados
            def draw_headers_other():
                pdf.set_style("table_header")
                pdf.set_fill_color(*pdf.colors["table_header_bg"])
                for i, h in enumerate(headers_o):
                    pdf.cell(colw_o[i], 6, h, border=1, ln=0, align="C", fill=True)
                pdf.ln(6)
                pdf.set_style("table_cell")

            # Dibujar encabezados iniciales
            draw_headers_other()

            # Renderizar filas con control de página
            for row in self.other_challenges_data:
                code = row.get('Codigo_Desafio', row.get('Challenge_Code', ''))
                name = self.other_challenges_texts.get(code, code)
                val = row.get('Valor_Importancia', row.get('Importance_Value', 'N/A'))

                # Calcular altura estimada de la fila
                pdf.set_style("table_cell")
                lines_name = pdf._split_text(name, colw_o[0])
                estimated_height = 4 * max(len(lines_name), 1)

                # Verificar espacio disponible
                space_left = pdf.h - pdf.get_y() - pdf.b_margin
                if space_left < estimated_height + 10:
                    pdf.add_page()
                    draw_headers_other()

                # Dibujar fila
                x0 = pdf.get_x()
                y0 = pdf.get_y()

                # Columna 1: Desafío
                pdf.rect(x0, y0, colw_o[0], estimated_height)
                pdf.set_xy(x0, y0)
                pdf.multi_cell(colw_o[0], 4, name, border=0, align="L")

                # Columna 2: Calificación
                x1 = x0 + colw_o[0]
                pdf.rect(x1, y0, colw_o[1], estimated_height)
                pdf.set_xy(x1, y0)
                pdf.multi_cell(colw_o[1], 4, str(val), border=0, align="C")

                # Mover a la siguiente fila
                pdf.set_xy(x0, y0 + estimated_height)

        pdf.ln(3)

        # ---------- 7. SbN seleccionadas ----------
        pdf.h1(self.texts.get('section7_title', '7 SbN seleccionadas'))
        headers_s = [self.texts.get('priority_order', 'Prioridad'), self.texts.get('section7_title', 'SbN')]
        colw_s = [total_w * 0.30, total_w * 0.70]  # 30% prioridad, 70% nombre

        if not self.selected_sbn:
            # Caso sin SbN: usa la tabla simple como fallback
            pdf.table(headers_s, [['', self.texts.get('no_selected_sbn', 'No hay SbN seleccionadas')]],
                      col_widths=colw_s, align=["C", "L"])
        else:
            # Helper para encabezados (idéntico patrón que sección 6)
            def draw_headers_sbn():
                pdf.set_style("table_header")
                pdf.set_fill_color(*pdf.colors["table_header_bg"])
                for i, h in enumerate(headers_s):
                    pdf.cell(colw_s[i], 6, h, border=1, ln=0, align="C", fill=True)
                pdf.ln(6)
                pdf.set_style("table_cell")

            # Dibujar encabezados iniciales
            draw_headers_sbn()

            # Render de filas con control de salto de página
            for sbn_id in self.selected_sbn:
                order = self.sbn_orders.get(sbn_id, 0)
                priority_text = f"{self.texts.get('priority_order', 'Prioridad')} {order}"
                sbn_name = self.sbn_solutions.get(str(sbn_id), f"SbN {sbn_id}")

                # Altura estimada por wrapping del nombre
                pdf.set_style("table_cell")
                lines_name = pdf._split_text(sbn_name, colw_s[1])
                estimated_height = 4 * max(len(lines_name), 1)

                # Verificar espacio disponible
                space_left = pdf.h - pdf.get_y() - pdf.b_margin
                if space_left < estimated_height + 10:
                    pdf.add_page()
                    draw_headers_sbn()

                # Dibujar fila (dos columnas)
                x0 = pdf.get_x()
                y0 = pdf.get_y()

                # Columna 1: Prioridad
                pdf.rect(x0, y0, colw_s[0], estimated_height)
                pdf.set_xy(x0, y0)
                pdf.multi_cell(colw_s[0], 4, str(priority_text), border=0, align="C")

                # Columna 2: SbN (wrapping)
                x1 = x0 + colw_s[0]
                pdf.rect(x1, y0, colw_s[1], estimated_height)
                pdf.set_xy(x1, y0)
                pdf.multi_cell(colw_s[1], 4, sbn_name, border=0, align="L")

                # Avanzar a la siguiente fila
                pdf.set_xy(x0, y0 + estimated_height)

        pdf.ln(3)

        # ---------- 8. Taxonomía CAF (relación con SbN seleccionadas) ----------
        pdf.h1(self.texts.get('section8_title', '8 Taxonomía CAF'))

        if self.selected_sbn and self.taxonomy_tree:
            # Columnas: SbN, Categoría, Subcategoría, Actividad
            headers_t = [
                self.texts.get('taxo_title', 'SbN'),
                self.texts.get('category_caf', 'Categoría'),
                self.texts.get('subcategory_caf', 'Subcategoría'),
                self.texts.get('activity_caf', 'Actividad')
            ]
            colw_t = [total_w * 0.18, total_w * 0.22, total_w * 0.25, total_w * 0.35]

            # Helper: encabezados de la tabla (igual patrón que secciones 6 y 7)
            def draw_headers_tax():
                pdf.set_style("table_header")
                pdf.set_fill_color(*pdf.colors["table_header_bg"])
                for i, h in enumerate(headers_t):
                    pdf.cell(colw_t[i], 6, h, border=1, ln=0, align="C", fill=True)
                pdf.ln(6)
                pdf.set_style("table_cell")

            # Dibujar encabezados iniciales
            draw_headers_tax()

            # Iterar jerarquía de Taxonomía (manteniendo límites de visibilidad actuales)
            for obj_amb, categorias in list(self.taxonomy_tree.items()):  # máx. 2 objetivos
                for cat, subcats in list(categorias.items()):  # máx. 2 categorías
                    # Filtrar subcategorías con acciones vinculadas a SbN seleccionadas
                    relevant_subcats = []
                    for subcat, acts in list(subcats.items()):  # máx. 2 subcategorías
                        rel = [a for a in acts if a.get('id') in self.selected_sbn]
                        if rel:
                            relevant_subcats.append((subcat, rel))

                    # Renderizar filas
                    for subcat, acts in relevant_subcats:
                        for act in acts:  # máx. 2 acciones
                            c1 = str(obj_amb)
                            c2 = str(cat)
                            c3 = str(subcat)
                            c0 = str(act.get('SbN', ''))

                            # Estimar alto por wrapping
                            lines0 = pdf._split_text(c0, colw_t[0])
                            lines1 = pdf._split_text(c1, colw_t[1])
                            lines2 = pdf._split_text(c2, colw_t[2])
                            lines3 = pdf._split_text(c3, colw_t[3])
                            n_lines = max(len(lines0), len(lines1), len(lines2), len(lines3), 1)
                            row_h = 4 * n_lines

                            # Control de salto de página
                            space_left = pdf.h - pdf.get_y() - pdf.b_margin
                            if space_left < row_h + 8:
                                pdf.add_page()
                                draw_headers_tax()

                            # Dibujar fila con rectángulos y multi_cell por columna
                            x0 = pdf.get_x()
                            y0 = pdf.get_y()

                            # Col 0
                            pdf.rect(x0, y0, colw_t[0], row_h)
                            pdf.set_xy(x0, y0)
                            pdf.multi_cell(colw_t[0], 4, c0, border=0, align="L")

                            # Col 1
                            x1 = x0 + colw_t[0]
                            pdf.rect(x1, y0, colw_t[1], row_h)
                            pdf.set_xy(x1, y0)
                            pdf.multi_cell(colw_t[1], 4, c1, border=0, align="L")

                            # Col 2
                            x2 = x1 + colw_t[1]
                            pdf.rect(x2, y0, colw_t[2], row_h)
                            pdf.set_xy(x2, y0)
                            pdf.multi_cell(colw_t[2], 4, c2, border=0, align="L")

                            # Col 3
                            x3 = x2 + colw_t[2]
                            pdf.rect(x3, y0, colw_t[3], row_h)
                            pdf.set_xy(x3, y0)
                            pdf.multi_cell(colw_t[3], 4, c3, border=0, align="L")

                            # Avanzar a la siguiente fila
                            pdf.set_xy(x0, y0 + row_h)
        else:
            pdf.p(self.texts.get('not_available', 'No disponible'))
        pdf.p(self.texts.get('footnote', ''))
        pdf.ln(3)

        # ---------- 9. Indicadores ----------
        pdf.h1(self.texts.get('section9_title', '9 Indicadores'))
        headers_i = [self.texts.get('sbn', 'SbN'), self.texts.get('indicator', 'Indicador'), self.texts.get('unit', 'Unidad')]
        colw_i = [total_w * 0.20, total_w * 0.50, total_w * 0.30]  # 20%, 50%, 30%
        if not self.selected_sbn:
            pdf.table(headers_i, [[self.texts.get('not_available', 'No disponible'), '', '']], col_widths=colw_i, align=["L", "L", "C"])
        else:
            # Helper para dibujar encabezados
            def draw_headers_indicators():
                pdf.set_style("table_header")
                pdf.set_fill_color(*pdf.colors["table_header_bg"])
                for i, h in enumerate(headers_i):
                    pdf.cell(colw_i[i], 6, h, border=1, ln=0, align="C", fill=True)
                pdf.ln(6)
                pdf.set_style("table_cell")

            # Dibujar encabezados iniciales
            draw_headers_indicators()

            # Renderizar filas con control de página y agrupación
            for sbn_id in self.selected_sbn:
                sbn_name = self.sbn_solutions.get(str(sbn_id), f'SbN {sbn_id}')
                indicators = self.indicators_data.get(str(sbn_id), [])

                if not indicators:
                    continue

                for idx, ind in enumerate(indicators):
                    ind_name = ind.get('nombre', '')
                    ind_unit = ind.get('unidad', '')

                    # Calcular altura estimada de la fila
                    pdf.set_style("table_cell")
                    lines_ind = pdf._split_text(ind_name, colw_i[1])
                    estimated_height = 4 * max(len(lines_ind), 1)

                    # Verificar espacio disponible
                    space_left = pdf.h - pdf.get_y() - pdf.b_margin
                    if space_left < estimated_height + 10:
                        pdf.add_page()
                        draw_headers_indicators()

                    # Determinar qué mostrar (agrupación: SbN solo en primera fila)
                    display_sbn = sbn_name if idx == 0 else ''

                    # Asegurar estilo normal para las celdas
                    pdf.set_style("table_cell")

                    # Dibujar fila
                    x0 = pdf.get_x()
                    y0 = pdf.get_y()

                    # Columna 1: SbN
                    pdf.rect(x0, y0, colw_i[0], estimated_height)
                    pdf.set_xy(x0, y0)
                    pdf.multi_cell(colw_i[0], 4, display_sbn, border=0, align="L")

                    # Columna 2: Indicador
                    x1 = x0 + colw_i[0]
                    pdf.rect(x1, y0, colw_i[1], estimated_height)
                    pdf.set_xy(x1, y0)
                    pdf.multi_cell(colw_i[1], 4, ind_name, border=0, align="L")

                    # Columna 3: Unidad
                    x2 = x1 + colw_i[1]
                    pdf.rect(x2, y0, colw_i[2], estimated_height)
                    pdf.set_xy(x2, y0)
                    pdf.multi_cell(colw_i[2], 4, ind_unit, border=0, align="C")

                    # Mover a la siguiente fila
                    pdf.set_xy(x0, y0 + estimated_height)

        pdf.ln(3)

        # ---------- 10. Anexos digitales ----------
        pdf.h1(self.texts.get('section10_title', '10 Anexos digitales'))
        pdf.set_style("h2")

        # Construir ruta a carpeta 03-SbN compatible con Windows
        sbn_folder_path = os.path.join(self.project_path, "03-SbN")
        # Convertir a formato file:/// para Windows (con barras normales)
        sbn_folder_url = "file:///" + sbn_folder_path.replace("\\", "/")

        # Anexo 10.1 con hipervínculo
        pdf.set_text_color(0, 0, 255)  # Azul para el enlace
        pdf.cell(0, 6, self.texts.get('section10_1', ''), ln=True, link=sbn_folder_url)

        # Anexo 10.2 con hipervínculo
        pdf.cell(0, 6, self.texts.get('section10_2', ''), ln=True, link=sbn_folder_url)
        pdf.set_text_color(0, 0, 0)  # Volver a negro

        # Exporta
        out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(out_dir, exist_ok=True)
        try:
            pdf.output(output_path)
            print(f"✅ Reporte principal generado: {output_path}")
        except Exception as e:
            print(f"Error al escribir PDF: {e}")
            return False

        # Generar fichas técnicas de SbN si está habilitado
        if generate_sbn_sheets:
            # Preguntar al usuario si desea generar las fichas
            title = get_text('messages.sbn_sheets_confirm_title')
            message = get_text('messages.sbn_sheets_confirm_message')

            user_wants_sheets = messagebox.askyesno(title, message)

            if user_wants_sheets:
                print("\n" + "="*60)
                print("📋 Generando fichas técnicas de SbN...")
                print("="*60)

                try:
                    # Obtener opción financiera del proyecto (si existe)
                    financial_option = self.project_data.get('project_info', {}).get(
                        'financial_option',
                        'investment_and_maintenance'
                    )

                    # Crear generador de fichas
                    sheets_gen = SbnSheetsGenerator(
                        project_folder=self.project_path,
                        language=self.language,
                        financial_option=financial_option
                    )

                    # Generar todas las fichas
                    sheets_success = sheets_gen.process_all()

                    if not sheets_success:
                        print("⚠️ Hubo errores al generar las fichas técnicas")
                    else:
                        # Si las fichas se generaron exitosamente, concatenar con el reporte
                        print("\n📑 Generando PDF Total (Reporte + Fichas)...")
                        concat_success = self.concatenate_report_and_sheets(output_path)

                        if not concat_success:
                            print("⚠️ No se pudo generar el PDF Total, pero los archivos individuales están disponibles")

                except Exception as e:
                    print(f"❌ Error al generar fichas técnicas: {e}")
                    import traceback
                    traceback.print_exc()
                    # No fallar el reporte completo si las fichas fallan
            else:
                print("\n⏭️ Usuario optó por omitir la generación de fichas técnicas de SbN")

        return True

    def concatenate_report_and_sheets(self, report_pdf_path: str) -> bool:
        """
        Concatena el reporte principal con todas las fichas de SbN en un PDF Total.

        Args:
            report_pdf_path: Ruta del PDF del reporte principal

        Returns:
            bool: True si fue exitoso
        """
        try:
            report_path = Path(report_pdf_path)

            # Verificar que el reporte principal existe
            if not report_path.exists():
                print(f"⚠️ No se encontró el reporte principal: {report_path}")
                return False

            # Ruta de la carpeta de fichas
            sheets_folder = Path(self.project_path) / "03-SbN"

            if not sheets_folder.exists():
                print(f"⚠️ No se encontró la carpeta de fichas: {sheets_folder}")
                return False

            # Buscar todas las fichas en orden (SbN_01.pdf a SbN_21.pdf)
            sheet_files = []
            for i in range(1, 22):  # SbN_01 a SbN_21
                sheet_name = f"SbN_{i}.pdf"
                sheet_path = sheets_folder / sheet_name
                if sheet_path.exists():
                    sheet_files.append(sheet_path)

            if not sheet_files:
                print("⚠️ No se encontraron fichas de SbN para concatenar")
                return False

            print(f"\n📑 Concatenando reporte con {len(sheet_files)} fichas de SbN...")

            # Crear nombre del PDF total
            # Ejemplo: "Reporte_Proyecto.pdf" → "Reporte_Proyecto_Total.pdf"
            total_pdf_name = report_path.stem + "_Total.pdf"
            total_pdf_path = report_path.parent / total_pdf_name

            # Crear escritor de PDF
            pdf_writer = PdfWriter()

            # 1. Agregar reporte principal
            print(f"  ✓ Agregando reporte principal: {report_path.name}")
            with open(report_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

            # 2. Agregar fichas de SbN en orden
            for sheet_path in sheet_files:
                print(f"  ✓ Agregando ficha: {sheet_path.name}")
                with open(sheet_path, 'rb') as pdf_file:
                    pdf_reader = PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)

            # 3. Guardar PDF compilado
            with open(total_pdf_path, 'wb') as output_file:
                pdf_writer.write(output_file)

            print(f"\n✅ PDF Total generado exitosamente:")
            print(f"   📄 {total_pdf_path}")
            print(f"   📊 Reporte principal + {len(sheet_files)} fichas de SbN")

            return True

        except Exception as e:
            print(f"❌ Error concatenando PDFs: {e}")
            import traceback
            traceback.print_exc()
            return False
