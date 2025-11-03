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
  - SbN_Select.csv                   -> columnas: sbn_id, selected
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

from fpdf import FPDF
from src.utils.resource_path import get_resource_path

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

        # Tipografía base (core, no requiere TTF)
        self.base_family = "helvetica"
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
        self.water_security_data: List[Dict[str, Any]] = []
        self.barriers_data: List[Dict[str, Any]] = []
        self.other_challenges_data: List[Dict[str, Any]] = []
        self.indicators_data: Dict[str, Any] = {}
        self.taxonomy_tree: Dict[str, Any] = {}
        self.texts: Dict[str, str] = {}
        self.water_challenges_texts: Dict[str, str] = {}
        self.other_challenges_texts: Dict[str, str] = {}
        self.barrier_groups_texts: Dict[str, str] = {}
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

        # project.json
        project_json = os.path.join(self.project_path, 'project.json')
        if os.path.exists(project_json):
            with open(project_json, 'r', encoding='utf-8') as f:
                self.project_data = json.load(f)

        # SbN seleccionadas
        sbn_csv = os.path.join(self.project_path, 'SbN_Select.csv')
        if os.path.exists(sbn_csv):
            try:
                with open(sbn_csv, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.selected_sbn = [int(row['sbn_id']) for row in reader if str(row.get('selected', '')).lower() == 'true']
            except Exception:
                # si falla lectura, crea CSV por defecto
                self._create_default_sbn_csv()
        else:
            self._create_default_sbn_csv()

        # Seguridad hídrica
        water_csv = self._find_csv('DF_WS')
        if water_csv and os.path.exists(water_csv):
            with open(water_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.water_security_data = list(reader)

        # Barreras
        barriers_csv = self._find_csv('Barriers')
        if barriers_csv and os.path.exists(barriers_csv):
            with open(barriers_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.barriers_data = list(reader)

        # Otros desafíos (nombres alternativos para mayor robustez)
        other_csv = self._find_csv('D_O')
        if other_csv and os.path.exists(other_csv):
            with open(other_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.other_challenges_data = list(reader)

        # Indicadores
        ind_path = get_resource_path(os.path.join('utilities', 'indicators', f'{self.language}.json'))
        if os.path.exists(ind_path):
            with open(ind_path, 'r', encoding='utf-8') as f:
                self.indicators_data = json.load(f)

        # Taxonomía CAF
        tax_path = get_resource_path(os.path.join('locales', 'CAF_taxonomy_tree.json'))
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

    def _create_default_sbn_csv(self):
        csv_path = os.path.join(self.project_path, 'SbN_Select.csv')
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['sbn_id', 'selected'])
                for i in range(1, 22):
                    writer.writerow([i, False])
        except Exception:
            pass

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
    def generate_pdf(self, output_path: str) -> bool:
        self.load_data()
        pdf = StyledPDF()
        pdf.add_page()

        # ---------- Portada ----------
        title_text = self.texts.get('title', 'Reporte final')
        project_info = self.project_data.get('project_info', {})
        name = project_info.get('name', '')
        if name:
            title_text = f"{title_text} - {name}"

        pdf.set_style("title")
        pdf.cell(0, 10, title_text, ln=True)
        pdf.set_style("subtitle")
        pdf.cell(0, 5, datetime.now().strftime("%d/%m/%Y"), ln=True)
        pdf.ln(2)
        pdf.hr()

        # ---------- 1. Introducción ----------
        pdf.h1(self.texts.get('intro_title', '1 Introducción'))
        pdf.p(self.texts.get('intro_text', ''))

        # ---------- 2. Descripción general ----------
        pdf.h1(self.texts.get('section2_title', '2 Descripción general'))
        total_w = pdf.w - pdf.l_margin - pdf.r_margin
        col_widths = [60, total_w - 60]

        data_pairs = [
            (self.texts.get('project_title', 'Nombre del proyecto'), name or self.texts.get('not_specified', 'No especificado')),
            (self.texts.get('description', 'Descripción'), (project_info.get('description', self.texts.get('not_specified')) or self.texts.get('not_specified'))[:60]),
            (self.texts.get('location', 'Localización'), project_info.get('location', self.texts.get('not_specified', 'No especificado'))),
            (self.texts.get('objectives', 'Objetivos'), project_info.get('objective', self.texts.get('not_specified', 'No especificado'))[:60]),
        ]
        pdf.table([self.texts.get('field', 'Campo'), self.texts.get('value', 'Valor')],
                  self._pair_list_to_rows(data_pairs),
                  col_widths=col_widths, align=["L", "L"])
        pdf.ln(2)

        # ---------- 3. Caracterización de la cuenca ----------
        pdf.h1(self.texts.get('section3_title', '3 Caracterización de la cuenca'))

        # 3.1 Mapa
        pdf.h2(self.texts.get('section3_1', '3.1 Mapa de referencia'))
        map_path = self._auto_map_path()
        if map_path:
            pdf.caption(self.texts.get('figure1', 'Figura 1. Delimitación de la cuenca.'))
            usable_w = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.image(map_path, x=pdf.l_margin, w=usable_w)
            pdf.ln(2)
        else:
            pdf.caption(self.texts.get('figure1_missing', 'No se encontró la imagen. Continúa el informe sin el mapa.'))

        # 3.2 Métricas morfología/clima (si existen en project.json)
        pdf.h2(self.texts.get('section3_2', '3.2 Caracterización'))
        watershed = self.project_data.get('watershed_data', {})
        morph = watershed.get('morphometry', {})
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
        colw = [140, total_w - 140] if total_w > 160 else [110, total_w - 110]

        rows = []
        if self.water_security_data:
            # muestra hasta 4 filas
            for row in self.water_security_data[:4]:
                code = row.get('Codigo_Desafio', row.get('Challenge_Code', ''))
                name = self.water_challenges_texts.get(code, code)
                val = row.get('Valor_Importancia', row.get('Importance_Value', 'N/A'))
                rows.append([name, str(val)])
        else:
            rows.append([self.texts.get('not_available', 'No disponible'), ''])

        pdf.table(headers, rows, col_widths=colw, align=["L", "C"])
        pdf.ln(3)

        # ---------- 5. Barreras ----------
        pdf.h1(self.texts.get('section5_title', '5 Barreras'))
        headers_b = [self.texts.get('barrier_group', 'Grupo de barrera'),
                     self.texts.get('barrier_code', 'Código'),
                     self.texts.get('value', 'Valor')]
        colw_b = [60, 80, total_w - 140]

        if not self.barriers_data:
            pdf.table(headers_b, [[self.texts.get('not_available', 'No disponible'), '', '']], col_widths=colw_b, align=["L", "L", "C"])
        else:
            # Agrupar por grupo y imprimir 5 grupos x 3 ítems (para evitar desbordes)
            groups: Dict[str, List[Dict[str, Any]]] = {}
            for r in self.barriers_data:
                grp_code = r.get('Codigo_Grupo', r.get('Group_Code', ''))
                groups.setdefault(grp_code, []).append(r)

            # orden estable por clave
            printed_rows = []
            for gidx, (grp, items) in enumerate(list(groups.items())[:5]):
                group_name = self.barrier_groups_texts.get(grp, grp)
                items = items[:3]
                for i, it in enumerate(items):
                    code = it.get('Codigo_Barreira', it.get('Barrier_Code', ''))
                    val = it.get('Valor_Numerico', it.get('Numeric_Value', ''))
                    if i == 0:
                        printed_rows.append([group_name, code, str(val)])
                    else:
                        printed_rows.append(['', code, str(val)])

            pdf.table(headers_b, printed_rows, col_widths=colw_b, align=["L", "L", "C"])
        pdf.ln(3)

        # ---------- 6. Otros desafíos ----------
        pdf.h1(self.texts.get('section6_title', '6 Otros desafíos'))
        headers_o = [self.texts.get('challenge', 'Desafío'), self.texts.get('qualification', 'Calificación')]
        colw_o = [140, total_w - 140] if total_w > 160 else [110, total_w - 110]

        rows_o = []
        if self.other_challenges_data:
            for row in self.other_challenges_data[:9]:
                code = row.get('Codigo_Desafio', row.get('Challenge_Code', ''))
                name = self.other_challenges_texts.get(code, code)
                val = row.get('Valor_Importancia', row.get('Importance_Value', 'N/A'))
                rows_o.append([name, str(val)])
        else:
            rows_o.append([self.texts.get('not_available', 'No disponible'), ''])

        pdf.table(headers_o, rows_o, col_widths=colw_o, align=["L", "C"])
        pdf.ln(3)

        # ---------- 7. SbN seleccionadas ----------
        pdf.h1(self.texts.get('section7_title', '7 SbN seleccionadas'))
        headers_s = [self.texts.get('num', '#'), self.texts.get('sbn', 'SbN')]
        colw_s = [30, total_w - 30]
        rows_s = []
        if not self.selected_sbn:
            rows_s.append(['', self.texts.get('no_selected_sbn', 'No hay SbN seleccionadas')])
        else:
            for i, sbn_id in enumerate(self.selected_sbn[:10], 1):  # máximo 10 para no desbordar
                rows_s.append([str(i), self.sbn_solutions.get(str(sbn_id), f'SbN {sbn_id}')])
        pdf.table(headers_s, rows_s, col_widths=colw_s, align=["C", "L"])
        pdf.ln(3)

        # ---------- 8. Taxonomía CAF (relación con SbN seleccionadas) ----------
        pdf.add_page()
        pdf.h1(self.texts.get('section8_title', '8 Taxonomía CAF'))
        if self.selected_sbn and self.taxonomy_tree:
            # máximo 2 objetivos x 2 categorías x 2 subcategorías para mantener legibilidad
            for obj_amb, categorias in list(self.taxonomy_tree.items())[:2]:
                for cat, subcats in list(categorias.items())[:2]:
                    relevant_subcats = []
                    for subcat, acts in list(subcats.items())[:2]:
                        rel = [a for a in acts if a.get('id') in self.selected_sbn]
                        if rel:
                            relevant_subcats.append((subcat, rel))
                    if relevant_subcats:
                        pdf.set_style("table_header")
                        pdf.cell(0, 6, obj_amb[:90], ln=True, border=1)
                        pdf.set_style("table_cell")
                        pdf.cell(10, 5, "", border=0)
                        pdf.cell(0, 5, cat[:80], ln=True, border=1)
                        for subcat, acts in relevant_subcats:
                            for act in acts[:2]:
                                pdf.cell(20, 4, "", border=0)
                                pdf.cell(0, 4, f"{subcat[:40]}: {act.get('SbN','')[:60]}", ln=True, border=1)
        else:
            pdf.p(self.texts.get('not_available', 'No disponible'))
        pdf.ln(3)

        # ---------- 9. Indicadores ----------
        pdf.h1(self.texts.get('section9_title', '9 Indicadores'))
        headers_i = ['SbN', self.texts.get('indicator', 'Indicador'), self.texts.get('unit', 'Unidad')]
        colw_i = [50, 100, total_w - 150]
        rows_i = []
        if not self.selected_sbn:
            rows_i.append([self.texts.get('not_available', 'No disponible'), '', ''])
        else:
            for sbn_id in self.selected_sbn[:5]:
                sbn_name = self.sbn_solutions.get(str(sbn_id), f'SbN {sbn_id}')
                indicators = self.indicators_data.get(str(sbn_id), [])
                for i, ind in enumerate(indicators[:2]):
                    if i == 0:
                        rows_i.append([sbn_name, ind.get('nombre', ''), ind.get('unidad', '')])
                    else:
                        rows_i.append(['', ind.get('nombre', ''), ind.get('unidad', '')])
        pdf.table(headers_i, rows_i, col_widths=colw_i, align=["L", "L", "C"])
        pdf.ln(3)

        # ---------- 10. Anexos digitales ----------
        pdf.h1(self.texts.get('section10_title', '10 Anexos digitales'))
        pdf.set_style("h2")
        pdf.cell(0, 6, self.texts.get('section10_1', ''), ln=True)
        pdf.cell(0, 6, self.texts.get('section10_2', ''), ln=True)

        # Exporta
        out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(out_dir, exist_ok=True)
        try:
            pdf.output(output_path)
            return True
        except Exception as e:
            print(f"Error al escribir PDF: {e}")
            return False
