import customtkinter as ctk
from ..core.theme_manager import ThemeManager

class ProjectInfoPanel(ctk.CTkScrollableFrame):
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.project_data = {}
        self._setup_ui()
    
    def _setup_ui(self):
        self._create_project_section()
        self._create_characteristics_section()
    
    def _create_project_section(self):
        project_frame = ctk.CTkFrame(self, **ThemeManager.get_frame_style())
        project_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        title_label = ctk.CTkLabel(
            project_frame,
            text="INFORMACIÓN PROYECTO",
            **ThemeManager.get_label_style('heading')
        )
        title_label.pack(pady=(15, 10), padx=15, anchor="w")
        
        self.name_label = ctk.CTkLabel(
            project_frame,
            text="• Nombre: Sin proyecto",
            **ThemeManager.get_label_style('body')
        )
        self.name_label.pack(pady=2, padx=20, anchor="w")
        
        self.description_label = ctk.CTkLabel(
            project_frame,
            text="• Descripción: No disponible",
            **ThemeManager.get_label_style('body'),
            wraplength=250
        )
        self.description_label.pack(pady=2, padx=20, anchor="w")
        
        self.location_label = ctk.CTkLabel(
            project_frame,
            text="• Localización: No disponible",
            **ThemeManager.get_label_style('body')
        )
        self.location_label.pack(pady=2, padx=20, anchor="w")
        
        self.objective_label = ctk.CTkLabel(
            project_frame,
            text="• Objetivo: No disponible",
            **ThemeManager.get_label_style('body'),
            wraplength=250
        )
        self.objective_label.pack(pady=(2, 15), padx=20, anchor="w")
    
    def _create_characteristics_section(self):
        char_frame = ctk.CTkFrame(self, **ThemeManager.get_frame_style())
        char_frame.pack(fill="x", padx=15, pady=10)
        
        title_label = ctk.CTkLabel(
            char_frame,
            text="CARACTERÍSTICAS CUENCA",
            **ThemeManager.get_label_style('heading')
        )
        title_label.pack(pady=(15, 10), padx=15, anchor="w")
        
        self._create_subsection(char_frame, "📊 Morfometría", [
            ("• Área:", "--- km²"),
            ("• Perímetro:", "--- km"),
            ("• Elevación mín:", "--- m.s.n.m"),
            ("• Elevación máx:", "--- m.s.n.m"),
            ("• Pendiente prom:", "--- %")
        ])
        
        self._create_subsection(char_frame, "🌧️ Clima", [
            ("• Precipitación:", "--- mm/año"),
            ("• Temperatura:", "--- °C")
        ])
        
        self._create_subsection(char_frame, "💧 Hidrología", [
            ("• Caudal prom:", "--- m³/s"),
            ("• Riesgo inundación:", "---"),
            ("• Estrés hídrico:", "---")
        ])
        
        self._create_subsection(char_frame, "🌱 Nutrientes", [
            ("• Sedimentos:", "--- ton/ha.año"),
            ("• Fósforo:", "--- kg/ha.año"),
            ("• Nitrógeno:", "--- kg/ha.año")
        ])
    
    def _create_subsection(self, parent, title, items):
        subsection_frame = ctk.CTkFrame(parent, fg_color="transparent")
        subsection_frame.pack(fill="x", padx=15, pady=5)
        
        title_label = ctk.CTkLabel(
            subsection_frame,
            text=title,
            **ThemeManager.get_label_style('body'),
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack(pady=(5, 2), anchor="w")
        
        for label_text, value_text in items:
            item_frame = ctk.CTkFrame(subsection_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=1)
            
            label = ctk.CTkLabel(
                item_frame,
                text=label_text,
                **ThemeManager.get_label_style('body')
            )
            label.pack(side="left")
            
            value = ctk.CTkLabel(
                item_frame,
                text=value_text,
                **ThemeManager.get_label_style('body'),
                text_color=ThemeManager.COLORS['text_secondary']
            )
            value.pack(side="right")
            
            setattr(self, f"{label_text.replace('• ', '').replace(':', '').replace(' ', '_').lower()}_value", value)
    
    def update_project_info(self, project_data):
        self.project_data = project_data
        
        self.name_label.configure(text=f"• Nombre: {project_data.get('name', 'Sin proyecto')}")
        self.description_label.configure(text=f"• Descripción: {project_data.get('description', 'No disponible')}")
        self.location_label.configure(text=f"• Localización: {project_data.get('location', 'No disponible')}")
        self.objective_label.configure(text=f"• Objetivo: {project_data.get('objective', 'No disponible')}")
    
    def update_watershed_data(self, watershed_data):
        if 'morphometry' in watershed_data:
            morph = watershed_data['morphometry']
            self.área_value.configure(text=f"{morph.get('area', '---')} km²")
            self.perímetro_value.configure(text=f"{morph.get('perimeter', '---')} km")
            self.elevación_mín_value.configure(text=f"{morph.get('min_elevation', '---')} m.s.n.m")
            self.elevación_máx_value.configure(text=f"{morph.get('max_elevation', '---')} m.s.n.m")
            self.pendiente_prom_value.configure(text=f"{morph.get('avg_slope', '---')} %")
        
        if 'climate' in watershed_data:
            climate = watershed_data['climate']
            self.precipitación_value.configure(text=f"{climate.get('precipitation', '---')} mm/año")
            self.temperatura_value.configure(text=f"{climate.get('temperature', '---')} °C")
        
        if 'hydrology' in watershed_data:
            hydro = watershed_data['hydrology']
            self.caudal_prom_value.configure(text=f"{hydro.get('avg_flow', '---')} m³/s")
            self.riesgo_inundación_value.configure(text=f"{hydro.get('flood_risk', '---')}")
            self.estrés_hídrico_value.configure(text=f"{hydro.get('water_stress', '---')}")
        
        if 'nutrients' in watershed_data:
            nutrients = watershed_data['nutrients']
            self.sedimentos_value.configure(text=f"{nutrients.get('sediments', '---')} ton/ha.año")
            self.fósforo_value.configure(text=f"{nutrients.get('phosphorus', '---')} kg/ha.año")
            self.nitrógeno_value.configure(text=f"{nutrients.get('nitrogen', '---')} kg/ha.año")