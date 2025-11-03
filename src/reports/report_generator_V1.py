import json
import csv
import os
from datetime import datetime
from fpdf import FPDF
from src.utils.resource_path import get_resource_path

class ReportGenerator:
    def __init__(self, project_path, language='es'):
        self.project_path = project_path
        self.language = language
        self.project_data = {}
        self.selected_sbn = []
        self.water_security_data = []
        self.barriers_data = []
        self.other_challenges_data = []
        self.indicators_data = {}
        self.taxonomy_tree = {}
        self.texts = {}

    def load_data(self):
        """Cargar todos los datos"""
        # Textos multiidioma
        locale_path = get_resource_path(os.path.join('locales', f'{self.language}.json'))
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
                    self.selected_sbn = [int(row['sbn_id']) for row in reader if row['selected'].lower() == 'true']
            except:
                pass
        if not self.selected_sbn and not os.path.exists(sbn_csv):
            self._create_default_sbn_csv()

        # Water security
        water_csv = self._find_csv('DF_WS')
        if water_csv:
            with open(water_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.water_security_data = list(reader)

        # Barriers
        barriers_csv = self._find_csv('Barriers')
        if barriers_csv:
            with open(barriers_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.barriers_data = list(reader)

        # Other challenges
        other_csv = self._find_csv('D_O')
        if other_csv:
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

    def _find_csv(self, *names):
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
        except:
            pass

    def generate_pdf(self, output_path):
        self.load_data()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        project_info = self.project_data.get('project_info', {})

        # Título
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(25, 118, 210)
        pdf.cell(0, 10, f"{self.texts.get('title', 'Reporte final')} {project_info.get('name', '')}", ln=True)
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, datetime.now().strftime('%d/%m/%Y'), ln=True)
        pdf.ln(5)

        # 1. Introducción
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('intro_title', '1 Introduccion'), ln=True)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, self.texts.get('intro_text', ''))
        pdf.ln(3)

        # 2. Descripción general
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section2_title', '2 Descripcion general'), ln=True)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(0, 0, 0)

        data = [
            (self.texts.get('project_title', 'Nombre'), project_info.get('name', self.texts.get('not_specified'))),
            (self.texts.get('description', 'Descripcion'), (project_info.get('description', self.texts.get('not_specified')) or self.texts.get('not_specified'))[:60]),
            (self.texts.get('location', 'Localizacion'), project_info.get('location', self.texts.get('not_specified'))),
            (self.texts.get('objectives', 'Objetivos'), project_info.get('objective', self.texts.get('not_specified'))[:60])
        ]

        for label, value in data:
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(60, 6, label, border=1)
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 6, str(value), border=1, ln=True)
        pdf.ln(5)

        # 3. Caracterización cuenca
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section3_title', '3 Caracterizacion cuenca'), ln=True)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(66, 165, 245)
        pdf.cell(0, 6, self.texts.get('section3_1', '3.1 MAPA'), ln=True)

        # Imagen
        img_path = os.path.join(self.project_path, '01-Watershed', 'Watershed.jpg')
        if os.path.exists(img_path):
            pdf.set_font('Arial', 'I', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 5, self.texts.get('figure1', 'Figura 1.'), ln=True)
            try:
                pdf.image(img_path, x=10, w=190)
                pdf.ln(3)
            except:
                pass

        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(66, 165, 245)
        pdf.cell(0, 6, self.texts.get('section3_2', '3.2 CARACTERIZACION'), ln=True)

        watershed = self.project_data.get('watershed_data', {})
        morph = watershed.get('morphometry', {})
        climate = watershed.get('climate', {})

        wdata = [
            (self.texts.get('area'), str(morph.get('area', 'N/A'))),
            (self.texts.get('perimeter'), str(morph.get('perimeter', 'N/A'))),
            (self.texts.get('min_elevation'), str(morph.get('min_elevation', 'N/A'))),
            (self.texts.get('max_elevation'), str(morph.get('max_elevation', 'N/A'))),
            (self.texts.get('avg_slope'), str(morph.get('avg_slope', 'N/A'))),
            (self.texts.get('precipitation'), str(climate.get('precipitation', 'N/A'))),
            (self.texts.get('temperature'), str(climate.get('temperature', 'N/A')))
        ]

        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(0, 0, 0)
        for label, value in wdata:
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(90, 5, label, border=1)
            pdf.set_font('Arial', '', 8)
            pdf.cell(0, 5, value, border=1, ln=True)
        pdf.ln(5)

        # 4. Desafíos seguridad hídrica
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section4_title', '4 Desafios seguridad hidrica'), ln=True)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(120, 6, self.texts.get('challenge', 'Desafio'), border=1)
        pdf.cell(0, 6, self.texts.get('qualification', 'Calificacion'), border=1, ln=True)

        pdf.set_font('Arial', '', 8)
        if not self.water_security_data:
            pdf.cell(120, 5, self.texts.get('not_available', 'No disponible'), border=1)
            pdf.cell(0, 5, '', border=1, ln=True)
        else:
            for row in self.water_security_data[:4]:  # Max 4
                code = row.get('Codigo_Desafio', row.get('Challenge_Code', ''))
                challenge_name = self.water_challenges_texts.get(code, code)
                value = row.get('Valor_Importancia', row.get('Importance_Value', 'N/A'))
                pdf.cell(120, 5, challenge_name[:60], border=1)
                pdf.cell(0, 5, str(value), border=1, ln=True)
        pdf.ln(5)

        # 5. Barreras
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section5_title', '5 Barreras'), ln=True)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 6, self.texts.get('barrier_type', 'Tipo'), border=1)
        pdf.cell(80, 6, self.texts.get('barrier', 'Barrera'), border=1)
        pdf.cell(0, 6, self.texts.get('qualification', 'Calif'), border=1, ln=True)

        pdf.set_font('Arial', '', 7)
        if not self.barriers_data:
            pdf.cell(60, 4, self.texts.get('not_available', 'No disponible'), border=1)
            pdf.cell(80, 4, '', border=1)
            pdf.cell(0, 4, '', border=1, ln=True)
        else:
            # Agrupar barreras
            barriers_by_group = {}
            for row in self.barriers_data:
                group = row.get('Codigo_Grupo', row.get('Group_Code', ''))
                if group not in barriers_by_group:
                    barriers_by_group[group] = []
                barriers_by_group[group].append(row)

            for group_code in sorted(barriers_by_group.keys())[:5]:  # Max 5 grupos
                group_name = self.barrier_groups_texts.get(group_code, group_code)
                barriers = barriers_by_group[group_code][:3]  # Max 3 por grupo
                for i, barrier in enumerate(barriers):
                    if i == 0:
                        pdf.cell(60, 4, group_name[:30], border=1)
                    else:
                        pdf.cell(60, 4, '', border=1)
                    pdf.cell(80, 4, barrier.get('Codigo_Barreira', barrier.get('Barrier_Code', ''))[:40], border=1)
                    pdf.cell(0, 4, str(barrier.get('Valor_Numerico', barrier.get('Numeric_Value', ''))), border=1, ln=True)
        pdf.ln(5)

        # 6. Otros desafíos
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section6_title', '6 Otros desafios'), ln=True)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(140, 6, self.texts.get('challenge', 'Desafio'), border=1)
        pdf.cell(0, 6, self.texts.get('qualification', 'Calif'), border=1, ln=True)

        pdf.set_font('Arial', '', 7)
        if not self.other_challenges_data:
            pdf.cell(140, 4, self.texts.get('not_available', 'No disponible'), border=1)
            pdf.cell(0, 4, '', border=1, ln=True)
        else:
            for row in self.other_challenges_data[:9]:  # Max 9
                code = row.get('Codigo_Desafio', row.get('Challenge_Code', ''))
                challenge_name = self.other_challenges_texts.get(code, code)
                value = row.get('Valor_Importancia', row.get('Importance_Value', 'N/A'))
                pdf.cell(140, 4, challenge_name[:70], border=1)
                pdf.cell(0, 4, str(value), border=1, ln=True)
        pdf.ln(5)

        # 7. SbN priorizadas
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section7_title', '7 SbN priorizadas'), ln=True)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(30, 6, self.texts.get('priority_order', 'Prioridad'), border=1)
        pdf.cell(0, 6, 'SbN', border=1, ln=True)

        if not self.selected_sbn:
            pdf.set_font('Arial', '', 8)
            pdf.cell(30, 5, '', border=1)
            pdf.cell(0, 5, self.texts.get('no_selected_sbn', 'No hay SbN seleccionadas'), border=1, ln=True)
        else:
            pdf.set_font('Arial', '', 8)
            for i, sbn_id in enumerate(self.selected_sbn[:10], 1):  # Max 10
                pdf.cell(30, 5, str(i), border=1)
                pdf.cell(0, 5, self.sbn_solutions.get(str(sbn_id), f'SbN {sbn_id}'), border=1, ln=True)
        pdf.ln(5)

        # 8. Taxonomía CAF
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section8_title', '8 Taxonomia CAF'), ln=True)

        pdf.set_font('Arial', '', 7)
        pdf.set_text_color(0, 0, 0)
        if self.selected_sbn and self.taxonomy_tree:
            for obj_amb, categorias in list(self.taxonomy_tree.items())[:2]:  # Max 2 objetivos
                for cat, subcats in list(categorias.items())[:2]:  # Max 2 categorías
                    for subcat, acts in list(subcats.items())[:2]:  # Max 2 subcategorías
                        relevant = [a for a in acts if a.get('id') in self.selected_sbn]
                        if relevant:
                            pdf.set_font('Arial', 'B', 8)
                            pdf.cell(0, 4, obj_amb[:80], ln=True, border=1)
                            pdf.set_font('Arial', '', 7)
                            pdf.cell(10, 3, '', border=0)
                            pdf.cell(0, 3, cat[:70], ln=True, border=1)
                            for act in relevant[:2]:  # Max 2 actividades
                                pdf.cell(20, 3, '', border=0)
                                pdf.cell(0, 3, act.get('SbN', '')[:60], ln=True, border=1)
        pdf.ln(5)

        # 9. Indicadores
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section9_title', '9 Indicadores'), ln=True)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 5, 'SbN', border=1)
        pdf.cell(100, 5, self.texts.get('indicator', 'Indicador'), border=1)
        pdf.cell(0, 5, self.texts.get('unit', 'Unidad'), border=1, ln=True)

        if not self.selected_sbn:
            pdf.set_font('Arial', '', 7)
            pdf.cell(0, 4, self.texts.get('no_selected_sbn'), border=1, ln=True)
        else:
            pdf.set_font('Arial', '', 7)
            for sbn_id in self.selected_sbn[:5]:  # Max 5 SbN
                sbn_name = self.sbn_solutions.get(str(sbn_id), f'SbN {sbn_id}')
                indicators = self.indicators_data.get(str(sbn_id), [])
                for i, ind in enumerate(indicators[:2]):  # Max 2 indicadores
                    if i == 0:
                        pdf.cell(50, 4, sbn_name[:30], border=1)
                    else:
                        pdf.cell(50, 4, '', border=1)
                    pdf.cell(100, 4, ind.get('nombre', '')[:50], border=1)
                    pdf.cell(0, 4, ind.get('unidad', ''), border=1, ln=True)
        pdf.ln(5)

        # 10. Anexos
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(33, 150, 243)
        pdf.cell(0, 8, self.texts.get('section10_title', '10 Anexos digitales'), ln=True)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(66, 165, 245)
        pdf.cell(0, 6, self.texts.get('section10_1', ''), ln=True)
        pdf.cell(0, 6, self.texts.get('section10_2', ''), ln=True)

        try:
            pdf.output(output_path)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
