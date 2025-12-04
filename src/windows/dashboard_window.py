import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from PIL import Image
from CTkToolTip import CTkToolTip
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, get_current_global_language, set_current_global_language
from ..utils.project_manager import ProjectManager
from ..utils.resource_path import get_resource_path
from .barriers_window import BarriersWindow
from .water_security_window import WaterSecurityWindow
from .other_challenges_window import OtherChallengesWindow
from .sbn_window import SbNWindow
from .sbn_selection_window import SbNSelectionWindow
from .sbn_prioritization_config_dialog import SbnPrioritizationConfigDialog
from .startup_window import NewProjectDialog
from ..reports.report_generator import ReportGenerator

# Tamaño delos iconos
caf_size = (200, 45)
n4w_size = (210, 45)

class DashboardWindow(ctk.CTk):

    def __init__(self, window_manager=None, language=None):
        super().__init__()

        self.window_manager = window_manager
        self.project_data = None
        self.current_project_path = None

        # Sincronizar idioma antes de crear UI
        if language:
            set_current_global_language(language)

        self.title(get_text("dashboard.title"))
        self.geometry("1000x750")
        self.resizable(True, True)

        ThemeManager.configure_ctk()
        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Referencias a widgets para actualización de texto
        self.project_title_label = None
        self.info_labels = {}
        self.workflow_buttons = {}
        self.widget_refs = {}

        # Referencias a botones y tooltips
        self.edit_btn = None
        self.new_project_btn = None
        self.db_update_btn = None
        self.tooltips = {}

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir
        self._update_texts()


        # Estado del flujo de trabajo con secuencia
        self.workflow_steps = {
            'cuenca': {'completed': False, 'data': None, 'order': 1, 'enabled': True},
            'barreras': {'completed': False, 'data': None, 'order': 2, 'enabled': False},
            'water_security': {'completed': False, 'data': None, 'order': 3, 'enabled': False},
            'other_challenges': {'completed': False, 'data': None, 'order': 4, 'enabled': False},
            'sbn': {'completed': False, 'data': None, 'order': 5, 'enabled': False},
            'reporte': {'completed': False, 'data': None, 'order': 6, 'enabled': False}
        }

        self.protocol("WM_DELETE_WINDOW", self._on_closing)


    def _setup_ui(self):
        # Frame principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header con logos y título
        self._create_header(main_container)

        # Layout principal: información del proyecto a la izquierda, botones del flujo al centro
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Panel de información del proyecto (izquierda) - más ancho
        project_info_frame = ctk.CTkFrame(content_frame, width=450, **ThemeManager.get_frame_style())
        project_info_frame.pack(side="left", fill="y", padx=(0, 10))
        project_info_frame.pack_propagate(False)

        # Panel central con botones del flujo principal - dinámico
        workflow_frame = ctk.CTkFrame(content_frame, **ThemeManager.get_frame_style())
        workflow_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # Configurar cada panel
        self._create_project_info_panel(project_info_frame)
        self._create_workflow_panel(workflow_frame)

    def _create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent", height=100)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        # Logos
        self._load_and_display_logos(header_frame)

        # Título y subtítulo
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(expand=True)

        self.widget_refs['main_title'] = ctk.CTkLabel(
            title_frame,
            text=get_text("dashboard.title"),
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.widget_refs['main_title'].pack()

        self.project_title_label = ctk.CTkLabel(
            title_frame,
            text=get_text("dashboard.subtitle"),
            font=ThemeManager.FONTS['subtitle'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.project_title_label.pack(pady=(5, 0))

    def _create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent", height=100)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        # Configurar grid con 3 columnas
        header_frame.grid_columnconfigure(0, weight=0)  # Izquierda - logo CAF
        header_frame.grid_columnconfigure(1, weight=1)  # Centro - título
        header_frame.grid_columnconfigure(2, weight=0)  # Derecha - logo N4W

        # === COLUMNA IZQUIERDA - Logo CAF ===
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=20, sticky="w")

        try:
            caf_path = get_resource_path(os.path.join("icons", "Icon_CAF.png"))

            if os.path.exists(caf_path):
                caf_image = Image.open(caf_path)
                caf_image = caf_image.resize(caf_size, Image.Resampling.LANCZOS)
                caf_ctk_image = ctk.CTkImage(light_image=caf_image, dark_image=caf_image, size=caf_size)
                caf_label = ctk.CTkLabel(left_frame, image=caf_ctk_image, text="")
                caf_label.pack()
                # Guardar referencia para evitar garbage collection
                caf_label.image = caf_ctk_image
        except Exception as e:
            pass

        # === COLUMNA CENTRO - Título y subtítulo ===
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="nsew")

        self.widget_refs['main_title'] = ctk.CTkLabel(
            title_frame,
            text=get_text("dashboard.title"),
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.widget_refs['main_title'].pack(expand=True)

        # self.project_title_label = ctk.CTkLabel(
        #     title_frame,
        #     text=get_text("dashboard.subtitle"),
        #     font=ThemeManager.FONTS['subtitle'],
        #     text_color=ThemeManager.COLORS['text_secondary']
        # )
        # self.project_title_label.pack(pady=(5, 0))

        # === COLUMNA DERECHA - Logo N4W ===
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.grid(row=0, column=2, padx=20, sticky="e")

        try:
            n4w_path = get_resource_path(os.path.join("icons", "Icon_N4W.png"))

            if os.path.exists(n4w_path):
                n4w_image = Image.open(n4w_path)
                n4w_image = n4w_image.resize(n4w_size, Image.Resampling.LANCZOS)
                n4w_ctk_image = ctk.CTkImage(light_image=n4w_image, dark_image=n4w_image, size=n4w_size)
                n4w_label = ctk.CTkLabel(right_frame, image=n4w_ctk_image, text="")
                n4w_label.pack()
                # Guardar referencia para evitar garbage collection
                n4w_label.image = n4w_ctk_image
        except Exception as e:
            pass

    def _load_and_display_logos_old(self, parent):
        try:
            caf_path = get_resource_path(os.path.join("icons", "Icon_CAF.png"))
            n4w_path = get_resource_path(os.path.join("icons", "Icon_N4W.png"))

            if os.path.exists(caf_path) and os.path.exists(n4w_path):
                caf_image = Image.open(caf_path)
                n4w_image = Image.open(n4w_path)

                caf_image = caf_image.resize(caf_size, Image.Resampling.LANCZOS)
                n4w_image = n4w_image.resize(n4w_size, Image.Resampling.LANCZOS)

                caf_ctk_image = ctk.CTkImage(light_image=caf_image, dark_image=caf_image, size=caf_size)
                n4w_ctk_image = ctk.CTkImage(light_image=n4w_image, dark_image=n4w_image, size=n4w_size)

                logos_frame = ctk.CTkFrame(parent, fg_color="transparent")
                logos_frame.pack(side="top", pady=(10, 0))

                caf_label = ctk.CTkLabel(logos_frame, image=caf_ctk_image, text="")
                caf_label.pack(side="left", padx=(0, 30))

                n4w_label = ctk.CTkLabel(logos_frame, image=n4w_ctk_image, text="")
                n4w_label.pack(side="left", padx=(30, 0))
        except Exception as e:
            pass

    def _create_project_info_panel(self, parent):
        # Frame para título y botón editar
        title_frame = ctk.CTkFrame(parent, fg_color="transparent")
        title_frame.pack(pady=(20, 15), padx=15, fill="x")

        # Título del panel
        self.widget_refs['project_info_title'] = ctk.CTkLabel(
            title_frame,
            text=get_text("dashboard.project_info"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.widget_refs['project_info_title'].pack(side="left")

        # Botón editar (pequeño)
        self.edit_btn = ctk.CTkButton(
            title_frame,
            text="✏️",
            width=30,
            height=30,
            command=self._edit_project_info,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=15
        )
        self.edit_btn.pack(side="left", padx=5)

        # Botón nuevo proyecto (pequeño)
        self.new_project_btn = ctk.CTkButton(
            title_frame,
            text="📂",
            width=30,
            height=30,
            command=self._load_new_project,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=15
        )
        self.new_project_btn.pack(side="left", padx=5)

        # Botón actualizar base de datos (pequeño)
        self.db_update_btn = ctk.CTkButton(
            title_frame,
            text="🗄️",
            width=30,
            height=30,
            command=self._update_database_config,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=15
        )
        self.db_update_btn.pack(side="left", padx=5)

        # Crear tooltips para los botones
        self.tooltips['edit_project'] = CTkToolTip(
            self.edit_btn,
            message=get_text("dashboard.tooltips.edit_project"),
            delay=0.5,
            bg_color=ThemeManager.COLORS['bg_card'],
            text_color=ThemeManager.COLORS['text_primary'],
            corner_radius=5
        )
        self.tooltips['load_project'] = CTkToolTip(
            self.new_project_btn,
            message=get_text("dashboard.tooltips.load_project"),
            delay=0.5,
            bg_color=ThemeManager.COLORS['bg_card'],
            text_color=ThemeManager.COLORS['text_primary'],
            corner_radius=5
        )
        self.tooltips['change_database'] = CTkToolTip(
            self.db_update_btn,
            message=get_text("dashboard.tooltips.change_database"),
            delay=0.5,
            bg_color=ThemeManager.COLORS['bg_card'],
            text_color=ThemeManager.COLORS['text_primary'],
            corner_radius=5
        )

        # Scroll frame para la información
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # Campos de información del proyecto
        self.info_labels = {}
        self.info_field_labels = {}  # Para guardar los labels de los nombres de campo
        # info_fields = [
        #     ("name", "dashboard.name"),
        #     ("description", "dashboard.description"),
        #     ("location", "dashboard.location"),
        #     ("objective", "dashboard.objective")
        # ]
        info_fields = [
            ("name", "dashboard.name"),
            ("country_name", "dashboard.country"),
            ("location", "dashboard.location")
        ]

        for field_name, translation_key in info_fields:
            # Label del campo
            field_label = ctk.CTkLabel(
                scroll_frame,
                text=get_text(translation_key),
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['accent_primary'],
                anchor="w"
            )
            field_label.pack(fill="x", pady=(5, 5))
            self.info_field_labels[field_name] = field_label  # Guardar referencia

            # Valor del campo
            value_label = ctk.CTkLabel(
                scroll_frame,
                text=get_text("dashboard.not_available"),
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['text_secondary'],
                anchor="w",
                wraplength=300,
                justify="left"
            )
            value_label.pack(fill="x", pady=(0, 10), padx=(10, 0))

            self.info_labels[field_name] = value_label

        # # Separador
        # separator = ctk.CTkFrame(scroll_frame, height=2, fg_color=ThemeManager.COLORS['border'])
        # separator.pack(fill="x", pady=20)
        #
        # # Estado del proyecto
        # self.status_field_label = ctk.CTkLabel(
        #     scroll_frame,
        #     text=get_text("dashboard.project_status"),
        #     font=ThemeManager.FONTS['body'],
        #     text_color=ThemeManager.COLORS['accent_primary'],
        #     anchor="w"
        # )
        # self.status_field_label.pack(fill="x", pady=(0, 5))

        # self.status_info_label = ctk.CTkLabel(
        #     scroll_frame,
        #     text=get_text("dashboard.project_created"),
        #     font=ThemeManager.FONTS['caption'],
        #     text_color=ThemeManager.COLORS['text_light'],
        #     anchor="w"
        # )
        # self.status_info_label.pack(fill="x", padx=(10, 0))

        # Agregar secciones técnicas
        self._add_technical_sections(scroll_frame)

    def _add_technical_sections(self, parent):
        """Agregar secciones de información técnica de cuenca y SbN"""
        # Separador
        separator2 = ctk.CTkFrame(parent, height=2, fg_color=ThemeManager.COLORS['border'])
        separator2.pack(fill="x", pady=20)

        # Información de cuenca
        self.watershed_title = ctk.CTkLabel(
            parent,
            text=get_text("technical.watershed_info"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary'],
            anchor="w"
        )
        self.watershed_title.pack(fill="x", pady=(0, 10))

        # Frame contenedor para los datos de cuenca
        watershed_container = ctk.CTkFrame(parent, fg_color=ThemeManager.COLORS['bg_secondary'])
        watershed_container.pack(fill="x", pady=(0, 15), padx=10)

        # Inicializar diccionario para labels técnicos
        self.technical_labels = {}

        # Morfometría
        self._create_technical_section(watershed_container, get_text("technical.morphometry"), [
            (get_text("technical.area"), "morphometry_area", "km²"),
            (get_text("technical.perimeter"), "morphometry_perimeter", "km"),
            (get_text("technical.min_elevation"), "morphometry_min_elevation", "m"),
            (get_text("technical.max_elevation"), "morphometry_max_elevation", "m"),
            (get_text("technical.avg_slope"), "morphometry_avg_slope", "%")
        ])

        # Clima
        self._create_technical_section(watershed_container, get_text("technical.climate"), [
            (get_text("technical.precipitation"), "climate_precipitation", "mm/año"),
            (get_text("technical.temperature"), "climate_temperature", "°C")
        ])

        # Hidrología
        self._create_technical_section(watershed_container, get_text("technical.hydrology"), [
            (get_text("technical.avg_flow"), "hydrology_avg_flow", "m³/s"),
            (get_text("technical.flood_risk"), "hydrology_flood_risk", ""),
            (get_text("technical.water_stress"), "hydrology_water_stress", "")
        ])

        # Nutrientes
        self._create_technical_section(watershed_container, get_text("technical.nutrients"), [
            (get_text("technical.sediments"), "nutrients_sediments", "mg/L"),
            (get_text("technical.phosphorus"), "nutrients_phosphorus", "mg/L"),
            (get_text("technical.nitrogen"), "nutrients_nitrogen", "mg/L")
        ])

        # # Separador antes de SbN
        # separator3 = ctk.CTkFrame(parent, height=2, fg_color=ThemeManager.COLORS['border'])
        # separator3.pack(fill="x", pady=20)
        #
        # # Información de análisis SbN
        # self.sbn_title = ctk.CTkLabel(
        #     parent,
        #     text=get_text("technical.sbn_analysis"),
        #     font=ThemeManager.FONTS['body'],
        #     text_color=ThemeManager.COLORS['accent_primary'],
        #     anchor="w"
        # )
        # self.sbn_title.pack(fill="x", pady=(0, 10))
        #
        # # Frame contenedor para datos SbN
        # sbn_container = ctk.CTkFrame(parent, fg_color=ThemeManager.COLORS['bg_secondary'])
        # sbn_container.pack(fill="x", pady=(0, 15), padx=10)
        #
        # # Información SbN
        # self._create_technical_section(sbn_container, get_text("technical.analysis_status"), [
        #     (get_text("technical.solutions_count"), "sbn_solutions_count", ""),
        #     (get_text("technical.scenarios_count"), "sbn_scenarios_count", ""),
        #     (get_text("technical.results_available"), "sbn_results_available", "")
        # ])

    def _create_technical_section(self, parent, title, fields):
        """Crear una sección técnica con título y campos"""
        # Título de la subsección
        section_title = ctk.CTkLabel(
            parent,
            text=title,
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['accent_primary'],
            anchor="w"
        )
        section_title.pack(fill="x", pady=(10, 5), padx=15)

        # Campos de la sección
        for display_name, field_key, unit in fields:
            field_frame = ctk.CTkFrame(parent, fg_color="transparent")
            field_frame.pack(fill="x", padx=20, pady=2)

            # Nombre del campo
            name_label = ctk.CTkLabel(
                field_frame,
                text=f"{display_name}:",
                font=ThemeManager.FONTS['caption'],
                text_color=ThemeManager.COLORS['text_secondary'],
                anchor="w",
                width=120
            )
            name_label.pack(side="left")

            # Valor del campo
            value_label = ctk.CTkLabel(
                field_frame,
                text=get_text("technical.not_available"),
                font=ThemeManager.FONTS['caption'],
                text_color=ThemeManager.COLORS['text_light'],
                anchor="w"
            )
            value_label.pack(side="left", padx=(10, 0))

            # Unidad
            if unit:
                unit_label = ctk.CTkLabel(
                    field_frame,
                    text=unit,
                    font=ThemeManager.FONTS['caption'],
                    text_color=ThemeManager.COLORS['text_light'],
                    anchor="w"
                )
                unit_label.pack(side="right")

            # Guardar referencia al label de valor
            self.technical_labels[field_key] = value_label

        # Espacio al final de la sección
        ctk.CTkLabel(parent, text="", height=5).pack()

    def _create_workflow_panel(self, parent):
        # Título del panel
        self.widget_refs['workflow_title'] = ctk.CTkLabel(
            parent,
            text=get_text("dashboard.workflow"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.widget_refs['workflow_title'].pack(pady=(10, 0))

        # Frame scrollable para el contenido del workflow
        scrollable_workflow = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=ThemeManager.COLORS['text_light'],
            scrollbar_button_hover_color=ThemeManager.COLORS['text_secondary']
        )
        scrollable_workflow.pack(fill="both", expand=True, padx=5, pady=(10, 5))

        # Contenedor para la matriz de botones
        matrix_container = ctk.CTkFrame(scrollable_workflow, fg_color="transparent")
        matrix_container.pack(expand=False, padx=15, pady=(0, 5))

        # Botones del flujo de trabajo
        self.workflow_buttons = {}

        # Definir los 6 botones en orden para matriz 2x3
        workflow_steps = [
            ("cuenca", get_text("workflow.watershed"), self._open_cuenca),
            ("barreras", get_text("workflow.barriers"), self._open_barreras),
            ("water_security", get_text("workflow.water_security"), self._open_water_security),
            ("other_challenges", get_text("workflow.other_challenges"), self._open_other_challenges),
            ("sbn", get_text("workflow.sbn"), self._open_sbn),
            ("reporte", get_text("workflow.report"), self._open_reporte)
        ]

        # Crear matriz 2x3 (2 filas, 3 columnas)
        for row in range(2):
            row_frame = ctk.CTkFrame(matrix_container, fg_color="transparent")
            row_frame.pack(pady=5)

            for col in range(3):
                index = row * 3 + col
                if index < len(workflow_steps):
                    step_id, text, command = workflow_steps[index]

                    # Frame para cada botón
                    btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                    btn_frame.pack(side="left", padx=5)

                    # Deshabilitar todos excepto cuenca
                    is_disabled = step_id != "cuenca"

                    # Botón compacto
                    btn = ctk.CTkButton(
                        btn_frame,
                        text=text,
                        width=140,
                        height=50,
                        command=command,
                        fg_color=ThemeManager.COLORS['accent_primary'],
                        hover_color=ThemeManager.COLORS['accent_secondary'],
                        text_color='#FFFFFF',
                        font=ThemeManager.FONTS['body'],
                        corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
                        state="disabled" if is_disabled else "normal"
                    )
                    btn.pack(pady=2)

                    # Indicador de estado compacto
                    status_label = ctk.CTkLabel(
                        btn_frame,
                        text=get_text("workflow.pending"),
                        font=ThemeManager.FONTS['caption'],
                        text_color=ThemeManager.COLORS['text_light']
                    )
                    status_label.pack(pady=(2, 5))

                    self.workflow_buttons[step_id] = {
                        'button': btn,
                        'status': status_label,
                        'frame': btn_frame
                    }

        # Panel de imagen de la cuenca debajo de los botones
        self._create_image_panel(scrollable_workflow)

    def _create_image_panel(self, parent):
        """Crear panel para mostrar la imagen de la cuenca"""
        # Título de la sección
        self.image_title = ctk.CTkLabel(
            parent,
            text=get_text("technical.watershed_image"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.image_title.pack(pady=(5, 5))

        # Frame contenedor para la imagen
        self.image_frame = ctk.CTkFrame(parent, fg_color=ThemeManager.COLORS['bg_secondary'])
        self.image_frame.pack(pady=(5, 10), padx=20, fill="x")

        # Label para mostrar la imagen
        self.image_label = ctk.CTkLabel(
            self.image_frame,
            text="",
            width=400,
            height=300
        )
        self.image_label.pack(pady=15)

        # Texto de estado cuando no hay imagen
        self.no_image_label = ctk.CTkLabel(
            self.image_frame,
            text=get_text("technical.no_image_available"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_light']
        )
        self.no_image_label.pack(pady=15)

        # Inicialmente mostrar mensaje de no imagen
        self.image_label.pack_forget()

    def load_project(self, project_data):
        """Cargar datos del proyecto en el dashboard"""
        self.project_data = project_data
        # La BD global se obtiene de .database_config, no del proyecto

        # Actualizar título con texto traducido
        project_name = project_data.get('project_info', {}).get('name', get_text('dashboard.not_available'))
        #self.project_title_label.configure(text=f"Proyecto: {project_name}")

        # Actualizar información del proyecto con textos traducidos
        project_info = project_data.get('project_info', {})
        for field_name, label in self.info_labels.items():
            value = project_info.get(field_name, get_text('dashboard.not_specified'))
            if isinstance(value, str) and value.strip():
                label.configure(text=value, text_color=ThemeManager.COLORS['text_primary'])
            else:
                label.configure(text=get_text('dashboard.not_specified'), text_color=ThemeManager.COLORS['text_light'])

        # Restaurar estado del workflow si existe en project_data
        if 'workflow_progress' in project_data:
            saved_progress = project_data['workflow_progress']
            for step_id, step_data in saved_progress.items():
                if step_id in self.workflow_steps:
                    # Restaurar completed y data, mantener order y enabled de valores por defecto
                    self.workflow_steps[step_id]['completed'] = step_data.get('completed', False)
                    self.workflow_steps[step_id]['data'] = step_data.get('data', None)

        # Actualizar estado del flujo de trabajo
        self._update_workflow_status()

        # Cargar imagen de la cuenca si existe
        self._load_watershed_image()

        # Actualizar información técnica
        self._update_technical_info()

        # Habilitar botones si existe el archivo Watershed.shp
        from pathlib import Path
        # La secuencia de botones se actualiza en _update_workflow_status()

    def _update_workflow_status(self):
        """Actualizar el estado visual del flujo de trabajo basado ÚNICAMENTE en el estado guardado"""
        if not self.project_data:
            return

        # Actualizar UI basándose únicamente en self.workflow_steps (que viene de workflow_progress en JSON)
        # NO validar archivos - el workflow se controla 100% por clics del usuario en los botones

        for step_id, step_data in self.workflow_steps.items():
            completed = step_data.get('completed', False)
            status_text = get_text("workflow.completed") if completed else get_text("workflow.pending")
            self._update_step_status(step_id, completed, status_text)

        # Actualizar UI del workflow
        self._update_workflow_ui()

        # Actualizar secuencia de botones habilitados
        self._update_buttons_sequence()

    def _update_buttons_sequence(self):
        """Actualizar qué botones están habilitados según secuencia de workflow"""
        # Verificar que la ventana no esté destruida
        try:
            if not self.winfo_exists():
                return
        except:
            return

        # Ordenar pasos por orden
        sorted_steps = sorted(self.workflow_steps.items(), key=lambda x: x[1]['order'])

        # Encontrar el primer paso no completado
        next_step_found = False
        for step_id, step_data in sorted_steps:
            if step_data['completed']:
                # Pasos completados: habilitados (para poder editar)
                step_data['enabled'] = True
            elif not next_step_found:
                # Primer paso no completado: habilitado
                step_data['enabled'] = True
                next_step_found = True
            else:
                # Pasos futuros: deshabilitados
                step_data['enabled'] = False

        # Aplicar estado a botones
        for step_id, step_data in self.workflow_steps.items():
            if step_id in self.workflow_buttons:
                button = self.workflow_buttons[step_id]['button']
                try:
                    # Verificar que el botón todavía existe
                    if button.winfo_exists():
                        if step_data['enabled']:
                            button.configure(state="normal")
                        else:
                            button.configure(state="disabled")
                except:
                    # El widget fue destruido, ignorar
                    pass

    def _update_step_status(self, step_id, completed, status_text):
        """Actualizar el estado visual de un paso específico"""
        # Verificar que la ventana no esté destruida
        try:
            if not self.winfo_exists():
                return
        except:
            return

        if step_id in self.workflow_buttons:
            button_info = self.workflow_buttons[step_id]
            try:
                # Verificar que los widgets existen antes de configurar
                if button_info['status'].winfo_exists():
                    button_info['status'].configure(text=status_text)

                    if completed:
                        button_info['status'].configure(text_color=ThemeManager.COLORS['success'])
                        # Opcional: cambiar color del botón para indicar completado
                        if button_info['button'].winfo_exists():
                            button_info['button'].configure(fg_color=ThemeManager.COLORS['success'])
                    else:
                        button_info['status'].configure(text_color=ThemeManager.COLORS['text_light'])
            except:
                # Los widgets fueron destruidos, ignorar
                pass

    def _load_watershed_image(self):
        """Cargar y mostrar imagen de la cuenca si existe"""
        try:
            print("DEBUG: _load_watershed_image iniciado")

            if not self.project_data:
                print("DEBUG: No hay project_data")
                self._show_no_image()
                return

            from pathlib import Path

            # Construir ruta directa a la imagen en 01-Watershed/Watershed.jpg
            project_folder = Path(self.project_data.get('files', {}).get('project_folder'))
            print(f"DEBUG: project_folder = {project_folder}")

            if not project_folder:
                print("DEBUG: No hay project_folder")
                self._show_no_image()
                return

            image_path = os.path.join(project_folder, "01-Watershed", "Watershed.jpg")
            print(f"DEBUG: Buscando imagen en: {image_path}")
            print(f"DEBUG: Archivo existe? {os.path.exists(image_path)}")

            if not os.path.exists(image_path):
                print("DEBUG: Imagen no existe")
                self._show_no_image()
                return

            print("DEBUG: Cargando imagen...")
            # Cargar y redimensionar imagen
            pil_image = Image.open(image_path)

            # Redimensionar manteniendo proporción para que quepa en 400x300
            pil_image.thumbnail((400, 300), Image.Resampling.LANCZOS)

            # Convertir a CTkImage
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=pil_image.size
            )

            print("DEBUG: Ocultando no_image_label")
            # Ocultar mensaje y mostrar imagen
            self.no_image_label.pack_forget()

            print("DEBUG: Configurando y mostrando image_label")
            # Mostrar imagen
            self.image_label.configure(image=ctk_image, text="")
            self.image_label.image = ctk_image  # Mantener referencia
            self.image_label.pack(pady=15)

            print("DEBUG: Imagen cargada exitosamente")

        except Exception as e:
            print(f"DEBUG: Error - {e}")
            import traceback
            traceback.print_exc()
            self._show_no_image()

    def _show_no_image(self):
        """Mostrar mensaje cuando no hay imagen disponible"""
        self.image_label.pack_forget()
        self.no_image_label.pack(pady=15)

    def _update_technical_info(self):
        """Actualizar información técnica desde los datos del proyecto"""
        if not self.project_data or not hasattr(self, 'technical_labels'):
            return

        try:
            # Obtener datos de cuenca
            watershed_data = self.project_data.get('watershed_data', {})

            # Actualizar morfometría
            morphometry = watershed_data.get('morphometry', {})
            self._update_technical_field('morphometry_area', morphometry.get('area'))
            self._update_technical_field('morphometry_perimeter', morphometry.get('perimeter'))
            self._update_technical_field('morphometry_min_elevation', morphometry.get('min_elevation'))
            self._update_technical_field('morphometry_max_elevation', morphometry.get('max_elevation'))
            self._update_technical_field('morphometry_avg_slope', morphometry.get('avg_slope'))

            # Actualizar clima
            climate = watershed_data.get('climate', {})
            self._update_technical_field('climate_precipitation', climate.get('precipitation'))
            self._update_technical_field('climate_temperature', climate.get('temperature'))

            # Actualizar hidrología
            hydrology = watershed_data.get('hydrology', {})
            self._update_technical_field('hydrology_avg_flow', hydrology.get('avg_flow'))
            self._update_technical_field('hydrology_flood_risk', hydrology.get('flood_risk'))
            self._update_technical_field('hydrology_water_stress', hydrology.get('water_stress'))

            # Actualizar nutrientes
            nutrients = watershed_data.get('nutrients', {})
            self._update_technical_field('nutrients_sediments', nutrients.get('sediments'))
            self._update_technical_field('nutrients_phosphorus', nutrients.get('phosphorus'))
            self._update_technical_field('nutrients_nitrogen', nutrients.get('nitrogen'))

            # # Actualizar análisis SbN
            # sbn_analysis = self.project_data.get('sbn_analysis', {})
            # solutions_count = len(sbn_analysis.get('selected_solutions', []))
            # scenarios_count = len(sbn_analysis.get('scenarios', []))
            # results_available = "Sí" if sbn_analysis.get('results') else "No"
            #
            # self._update_technical_field('sbn_solutions_count', solutions_count if solutions_count > 0 else None)
            # self._update_technical_field('sbn_scenarios_count', scenarios_count if scenarios_count > 0 else None)
            # self._update_technical_field('sbn_results_available', results_available if sbn_analysis.get('results') else None)

        except Exception as e:
            print(f"Error al actualizar información técnica: {str(e)}")

    def _update_technical_field(self, field_key, value):
        """Actualizar un campo técnico específico"""
        if field_key not in self.technical_labels:
            return

        label = self.technical_labels[field_key]

        if value is None or value == "" or value == []:
            label.configure(text=get_text("technical.not_available"), text_color=ThemeManager.COLORS['text_light'])
        else:
            # Traducir categorías de importancia si es necesario
            category_keys = ['very_low', 'low', 'medium', 'high', 'very_high']
            if isinstance(value, str) and value in category_keys:
                formatted_value = get_text(f"water_security.importance_levels.{value}")
            # Formatear números
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
            else:
                formatted_value = str(value)

            label.configure(text=formatted_value, text_color=ThemeManager.COLORS['text_primary'])

    # Métodos para abrir cada módulo del flujo de trabajo
    def _edit_project_info(self):
        """Abrir diálogo para editar información del proyecto"""
        current_lang = get_current_global_language()
        edit_dialog = NewProjectDialog(self, language=current_lang, project_data=self.project_data)
        self.wait_window(edit_dialog)

        if hasattr(edit_dialog, 'result') and edit_dialog.result:
            self.project_data = edit_dialog.result
            self.load_project(self.project_data)
            self._save_project()

    def _load_new_project(self):
        """Cargar otro proyecto (volver a startup window)"""
        # Preguntar si quiere guardar antes de cambiar de proyecto
        if self.project_data:
            result = messagebox.askyesnocancel(
                get_text("messages.warning"),
                get_text("messages.save_before_close")
            )
            if result is True:  # Sí, guardar
                self._save_project()
            elif result is None:  # Cancelar
                return
            # Si es False (No), continuar sin guardar

        # Destruir dashboard actual
        self.destroy()

        # Abrir StartupWindow
        from .startup_window import StartupWindow
        current_lang = get_current_global_language()
        startup = StartupWindow(self.window_manager)
        startup.mainloop()

    def _update_database_config(self):
        """Abrir diálogo para actualizar la configuración de la base de datos global"""
        from .database_selection_dialog import DatabaseSelectionDialog
        from ..core.database_manager import DatabaseManager

        # Abrir diálogo de selección de BD
        dialog = DatabaseSelectionDialog()
        result = dialog.show()

        if result:
            # Actualización exitosa
            db_manager = DatabaseManager()
            new_db_path = db_manager.get_database_path()

            messagebox.showinfo(
                "Success / Éxito / Sucesso",
                f"Database updated successfully!\n¡Base de datos actualizada exitosamente!\nBase de dados atualizada com sucesso!\n\nNew path / Nueva ruta / Novo caminho:\n{new_db_path}"
            )

    def _enable_all_buttons(self):
        """Habilitar todos los botones del workflow"""
        for step_id, widgets in self.workflow_buttons.items():
            widgets['button'].configure(state="normal")

    def _open_cuenca(self):
        """Abrir módulo de delimitación de cuenca"""
        from .watershed_delimitation_folium import WatershedDelimitationFolium
        from pathlib import Path

        # Verificar si existe el shapefile de cuenca
        watershed_shp = None
        if self.project_data and 'files' in self.project_data:
            project_folder = self.project_data['files'].get('project_folder')
            if project_folder:
                watershed_shp_path = Path(project_folder) / "01-Watershed" / "Watershed.shp"
                if watershed_shp_path.exists():
                    watershed_shp = str(watershed_shp_path)

        current_lang = get_current_global_language()
        delimitation_window = WatershedDelimitationFolium(
            self,
            self.project_data,
            language=current_lang,
            watershed_shapefile=watershed_shp,
            current_project_path=self.current_project_path
        )
        self.wait_window(delimitation_window)

        if hasattr(delimitation_window, 'result') and delimitation_window.result:
            self.project_data = delimitation_window.result
            self.update_workflow_step('cuenca', True)  # Marcar cuenca como completado
            self._load_watershed_image()  # Recargar imagen
            self._update_technical_info()  # Actualizar información técnica
            self._save_project()  # Guardar automáticamente

    def _open_barreras(self):
        """Abrir módulo de barreras"""
        try:
            barriers_window = BarriersWindow(
                window_manager=self,
                project_path=self.current_project_path
            )
            self.wait_window(barriers_window)
            self._save_project()
        except Exception as e:
            messagebox.showerror(
                get_text("errors.generic_title"),
                f"Error al abrir la ventana de barreras: {str(e)}"
            )

    def _open_water_security(self):
        """Abrir módulo de desafíos de seguridad hídrica"""
        try:
            water_security_window = WaterSecurityWindow(
                parent=self,
                window_manager=self,
                project_path=self.current_project_path
            )
            self.wait_window(water_security_window)
            self._save_project()
        except Exception as e:
            messagebox.showerror(
                get_text("errors.generic_title"),
                f"Error al abrir la ventana de seguridad hídrica: {str(e)}"
            )

    def _open_other_challenges(self):
        """Abrir módulo de otros desafíos"""
        if not self.project_data or not self.current_project_path:
            messagebox.showwarning(get_text("messages.warning"), get_text("messages.no_active_project"))
            return

        window = OtherChallengesWindow(parent=self, window_manager=self, project_path=self.current_project_path)
        self.wait_window(window)
        self._save_project()

    def _open_sbn(self):
        """Abrir módulo de SbN"""
        if not self.project_data or not self.current_project_path:
            messagebox.showwarning(get_text("messages.warning"), get_text("messages.no_active_project"))
            return

        try:
            # Paso 1: Abrir ventana de configuración de priorización
            config_dialog = SbnPrioritizationConfigDialog(
                parent=self,
                project_data=self.project_data
            )
            self.wait_window(config_dialog)

            # Si el usuario canceló, no continuar
            if not config_dialog.result:
                print("⭕ Usuario canceló la configuración de SbN")
                return

            # Guardar configuración en project_data
            if 'sbn_analysis' not in self.project_data:
                self.project_data['sbn_analysis'] = {}

            if 'prioritization_config' not in self.project_data['sbn_analysis']:
                self.project_data['sbn_analysis']['prioritization_config'] = {}

            self.project_data['sbn_analysis']['prioritization_config'] = config_dialog.result

            # Guardar cambios en project.json
            self._save_project()

            print(f"✓ Configuración guardada: {len(config_dialog.result['selected_sbn_codes'])} SbN, " +
                  f"opción financiera: {config_dialog.result['financial_option']}")

            # Paso 2: Procesar costos ajustados por país
            from ..core.cost_processor import CostProcessor

            project_folder = self.project_data.get('files', {}).get('project_folder')
            country_code = self.project_data.get('project_info', {}).get('country_code')
            financial_option = config_dialog.result['financial_option']

            if project_folder:
                print("📊 Procesando costos ajustados por país...")
                processor = CostProcessor(project_folder, country_code)
                success = processor.process_all(financial_option)

                if not success:
                    print("⚠️ Advertencia: El procesamiento de costos tuvo errores")
                    messagebox.showwarning(
                        get_text("messages.warning"),
                        "El ajuste de costos por país tuvo errores. Se continuará con los datos disponibles."
                    )

                # Paso 2.5: Actualizar priorización con las matrices recategorizadas
                # Esto asegura que SbN_Prioritization.csv tenga scores correctos ANTES de abrir la ventana
                print("🔄 Actualizando priorización de SbN con matrices recategorizadas...")
                from ..utils.sbn_prioritization import SbNPrioritization

                # Actualizar scores de Water Security si existe DF_WS.csv
                SbNPrioritization.update_water_security(project_folder)

                # Actualizar scores de Other Challenges si existe D_O.csv
                SbNPrioritization.update_other_challenges(project_folder)

                print("✓ Priorización actualizada correctamente")

                # Paso 2.6: Compilar áreas y costos
                print("📋 Compilando áreas y costos...")
                from ..core.area_calculator import compile_area_and_costs
                compile_success = compile_area_and_costs(project_folder)

                if not compile_success:
                    print("⚠️ No se pudo compilar Area_Cost_Compiler.csv")
                    print("   Posibles causas:")
                    print("   - Area.csv no existe (ejecutar delimitación de cuenca primero)")
                    print("   - Cost.csv no existe (se acaba de generar, verificar errores)")

            # Paso 3: Abrir ventana de SbN con la configuración
            window = SbNWindow(
                parent=self,
                project_data=self.project_data,
                project_path=self.current_project_path,
                window_manager=self,
                language=get_current_global_language()
            )

            # Habilitar botón de reporte apenas se abre la ventana de SbN
            print("🔍 DEBUG: Habilitando botón de reporte...")
            print(f"🔍 DEBUG: workflow_buttons tiene 'reporte'? {'reporte' in self.workflow_buttons}")

            self.workflow_steps['reporte']['enabled'] = True

            if 'reporte' in self.workflow_buttons:
                reporte_btn = self.workflow_buttons['reporte']['button']
                reporte_btn.configure(
                    state="normal",
                    fg_color=ThemeManager.COLORS['accent_primary']
                )
                # Forzar actualización visual
                reporte_btn.update_idletasks()
                self.update_idletasks()
                print("✓ Botón de reporte habilitado y actualizado")
            else:
                print("❌ ERROR: 'reporte' no está en workflow_buttons")
                print(f"🔍 DEBUG: Keys en workflow_buttons: {list(self.workflow_buttons.keys())}")

            self.wait_window(window)

            # Marcar SbN como completado después de cerrar la ventana
            self.workflow_steps['sbn']['completed'] = True
            self._update_step_status('sbn', True, get_text("workflow.completed"))
            print("✓ Paso SbN marcado como completado")

            # Actualizar workflow después de cerrar
            # _update_workflow_status ya actualiza los colores según el estado
            self._update_workflow_status()
            # _save_project guardará automáticamente workflow_progress = self.workflow_steps
            self._save_project()

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                get_text("messages.error"),
                f"Error al abrir la ventana de SbN: {str(e)}"
            )

    def _open_reporte(self):
        """Abrir módulo de reporte"""
        if not self.current_project_path:
            messagebox.showerror(
                get_text("messages.error"),
                get_text("messages.no_project_folder")
            )
            return

        # Generar reporte directamente (priorización ya establecida en sbn_prioritization_config_dialog)
        self._generate_report()

    def _generate_report(self):
        """Generar el reporte PDF"""
        # Solicitar ubicación para guardar el PDF
        output_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"Reporte_{self.project_data.get('project_info', {}).get('name', 'Proyecto')}.pdf"
        )

        if not output_file:
            return

        try:
            # Obtener idioma actual
            language = get_current_global_language()

            # Generar reporte
            generator = ReportGenerator(self.current_project_path, language)
            success = generator.generate_pdf(output_file)

            if success:
                # Marcar reporte como completado después de generar exitosamente el PDF
                self.update_workflow_step('reporte', True)
                self._save_project()
                messagebox.showinfo(
                    get_text("messages.success"),
                    get_text("messages.report_generated_success").format(output_file)
                )
            else:
                messagebox.showerror(
                    get_text("messages.error"),
                    get_text("messages.report_generation_error")
                )
        except Exception as e:
            messagebox.showerror(
                get_text("messages.error"),
                get_text("messages.report_generation_error_detail").format(str(e))
            )

    def _save_project(self):
        """Guardar proyecto actual"""
        if not self.project_data:
            messagebox.showwarning(get_text("messages.warning"), get_text("messages.no_project_data"))
            return

        try:
            # Guardar estado del workflow en project_data
            self.project_data['workflow_progress'] = self.workflow_steps

            if self.current_project_path:
                # Guardar en ubicación existente
                project_json_path = os.path.join(self.current_project_path, 'project.json')
                success = ProjectManager.save_project(self.project_data, project_json_path)
                if success:
                    messagebox.showinfo(get_text("messages.success"), get_text("messages.project_saved"))
                else:
                    messagebox.showerror(get_text("messages.error"), get_text("messages.project_save_error"))
            else:
                # Guardar como nuevo (debería tener una ruta por defecto)
                project_folder = self.project_data.get('files', {}).get('project_folder')
                if project_folder:
                    project_json_path = ProjectManager.get_project_json_path(project_folder)
                    success = ProjectManager.save_project(self.project_data, project_json_path)
                    if success:
                        self.current_project_path = project_folder
                        messagebox.showinfo(get_text("messages.success"), get_text("messages.project_saved"))
                    else:
                        messagebox.showerror(get_text("messages.error"), get_text("messages.project_save_error"))
                else:
                    messagebox.showerror(get_text("messages.error"), get_text("messages.no_project_folder"))
        except Exception as e:
            messagebox.showerror(get_text("messages.error"), f"{get_text('messages.project_save_error')}: {str(e)}")

    def _export_project(self):
        """Exportar datos del proyecto"""
        messagebox.showinfo(get_text("messages.in_development"), get_text("messages.export_function"))

    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        try:
            # Actualizar título de la ventana
            self.title(get_text("dashboard.title"))

            # Actualizar widget referencias principales
            if hasattr(self, 'widget_refs') and self.widget_refs:
                if 'main_title' in self.widget_refs:
                    self.widget_refs['main_title'].configure(text=get_text("dashboard.title"))

                if 'project_info_title' in self.widget_refs:
                    self.widget_refs['project_info_title'].configure(text=get_text("dashboard.project_info"))

                if 'workflow_title' in self.widget_refs:
                    self.widget_refs['workflow_title'].configure(text=get_text("dashboard.workflow"))

            # Actualizar título del proyecto
            if hasattr(self, 'project_title_label') and self.project_title_label:
                if self.project_data:
                    project_name = self.project_data.get('project_info', {}).get('name', get_text("dashboard.not_available"))
                    self.project_title_label.configure(text=f"Proyecto: {project_name}")
                else:
                    self.project_title_label.configure(text=get_text("dashboard.subtitle"))

            # Actualizar botones del workflow
            if hasattr(self, 'workflow_buttons') and self.workflow_buttons:
                workflow_translations = {
                    'cuenca': get_text("workflow.watershed"),
                    'barreras': get_text("workflow.barriers"),
                    'water_security': get_text("workflow.water_security"),
                    'other_challenges': get_text("workflow.other_challenges"),
                    'sbn': get_text("workflow.sbn"),
                    'reporte': get_text("workflow.report")
                }

                for step_id, widgets in self.workflow_buttons.items():
                    if 'button' in widgets and step_id in workflow_translations:
                        widgets['button'].configure(text=workflow_translations[step_id])

                    # Actualizar descripciones y estados
                    if 'status' in widgets:
                        # Mantener el estado actual pero con texto traducido
                        current_status_text = widgets['status'].cget("text")
                        if "✅" in current_status_text:
                            widgets['status'].configure(text=get_text("workflow.completed"))
                        elif "⏳" in current_status_text:
                            widgets['status'].configure(text=get_text("workflow.pending"))

            # Actualizar labels de información del proyecto
            if hasattr(self, 'info_field_labels') and self.info_field_labels:
                field_translations = {
                    'name': get_text("dashboard.name"),
                    'country_name': get_text("dashboard.country"),
                    'location': get_text("dashboard.location"),
                }
                # Actualizar las etiquetas de los campos
                for field_name, label in self.info_field_labels.items():
                    if field_name in field_translations:
                        label.configure(text=field_translations[field_name])

            # # Actualizar etiqueta de estado del proyecto
            # if hasattr(self, 'status_field_label'):
            #     self.status_field_label.configure(text=get_text("dashboard.project_status"))

            # Actualizar títulos de secciones técnicas
            if hasattr(self, 'watershed_title'):
                self.watershed_title.configure(text=get_text("technical.watershed_info"))
            # if hasattr(self, 'sbn_title'):
            #     self.sbn_title.configure(text=get_text("technical.sbn_analysis"))
            if hasattr(self, 'image_title'):
                self.image_title.configure(text=get_text("technical.watershed_image"))
            if hasattr(self, 'no_image_label'):
                self.no_image_label.configure(text=get_text("technical.no_image_available"))

            # Actualizar información del proyecto sin llamar load_project para evitar recursión
            if self.project_data:
                project_info = self.project_data.get('project_info', {})
                for field_name, label in self.info_labels.items():
                    value = project_info.get(field_name, get_text('dashboard.not_specified'))
                    if isinstance(value, str) and value.strip():
                        label.configure(text=value, text_color=ThemeManager.COLORS['text_primary'])
                    else:
                        label.configure(text=get_text('dashboard.not_specified'), text_color=ThemeManager.COLORS['text_light'])

            # Actualizar valores de información técnica con traducciones
            if hasattr(self, '_update_technical_info'):
                self._update_technical_info()

            # Actualizar tooltips
            if hasattr(self, 'tooltips') and self.tooltips:
                if 'edit_project' in self.tooltips:
                    self.tooltips['edit_project'].configure(message=get_text("dashboard.tooltips.edit_project"))
                if 'load_project' in self.tooltips:
                    self.tooltips['load_project'].configure(message=get_text("dashboard.tooltips.load_project"))
                if 'change_database' in self.tooltips:
                    self.tooltips['change_database'].configure(message=get_text("dashboard.tooltips.change_database"))

        except Exception as e:
            print(f"Error updating Dashboard texts: {e}")

    def _update_workflow_ui(self):
        """Actualiza la UI del workflow cuando cambian los estados"""
        try:
            for step_id, step_data in self.workflow_steps.items():
                if step_id in self.workflow_buttons:
                    widgets = self.workflow_buttons[step_id]

                    # Actualizar texto del estado
                    if step_data['completed']:
                        widgets['status'].configure(
                            text=get_text("workflow.completed"),
                            text_color=ThemeManager.COLORS['success']
                        )
                        # Cambiar color del botón para indicar completado
                        widgets['button'].configure(
                            fg_color=ThemeManager.COLORS['success'],
                            hover_color=ThemeManager.COLORS['success_hover']
                        )
                    else:
                        widgets['status'].configure(
                            text=get_text("workflow.pending"),
                            text_color=ThemeManager.COLORS['text_light']
                        )
                        # Color normal del botón
                        widgets['button'].configure(
                            fg_color=ThemeManager.COLORS['accent_primary'],
                            hover_color=ThemeManager.COLORS['accent_secondary']
                        )
        except Exception as e:
            print(f"Error updating workflow UI: {e}")

    def update_workflow_step(self, step_id, completed, data=None):
        """Actualizar el estado de un paso del workflow"""
        # Verificar que la ventana no esté destruida
        try:
            if not self.winfo_exists():
                return
        except:
            return

        if step_id in self.workflow_steps:
            self.workflow_steps[step_id]['completed'] = completed
            self.workflow_steps[step_id]['data'] = data
            self._update_workflow_ui()
            self._update_buttons_sequence()  # Actualizar habilitación secuencial de botones

    def reset_workflow_on_new_delineation(self):
        """
        Resetear el workflow cuando se delimita una nueva cuenca.
        Esto pone TODOS los pasos (incluyendo cuenca) como pendientes y deshabilitados.
        Solo cuenca quedará habilitado para poder guardar la delimitación.
        """
        # Verificar que la ventana no esté destruida
        try:
            if not self.winfo_exists():
                return
        except:
            return

        # Resetear TODOS los pasos incluyendo 'cuenca'
        # Cuenca se marcará como no completado hasta que el usuario haga "Guardar y Cerrar"
        for step_id in self.workflow_steps.keys():
            self.workflow_steps[step_id]['completed'] = False
            self.workflow_steps[step_id]['data'] = None
            if step_id == 'cuenca':
                # Cuenca queda habilitado para poder acceder y guardar
                self.workflow_steps[step_id]['enabled'] = True
            else:
                # Todos los demás deshabilitados
                self.workflow_steps[step_id]['enabled'] = False

        # Guardar en project_data si existe
        if self.project_data:
            self.project_data['workflow_progress'] = {
                step_id: {
                    'completed': step_data['completed'],
                    'data': step_data['data']
                }
                for step_id, step_data in self.workflow_steps.items()
            }

            # Guardar proyecto
            if self.current_project_path:
                from ..utils.project_manager import ProjectManager
                import os
                project_json_path = os.path.join(self.current_project_path, 'project.json')
                ProjectManager.save_project(self.project_data, project_json_path)

        # Actualizar UI
        self._update_workflow_status()

    def _on_closing(self):
        """Manejar cierre de ventana"""
        # Preguntar si quiere guardar antes de cerrar
        if self.project_data:
            result = messagebox.askyesnocancel(
                get_text("messages.close_dashboard"),
                get_text("messages.save_before_close")
            )
            if result is True:  # Sí
                self._save_project()
                self._cleanup_and_destroy()
            elif result is False:  # No
                self._cleanup_and_destroy()
            # Si es None (Cancel), no hace nada
        else:
            self._cleanup_and_destroy()

    def _cleanup_and_destroy(self):
        """Limpiar recursos antes de destruir la ventana"""
        try:
            # Destruir todas las ventanas hijas (Toplevel) que puedan estar abiertas
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    widget.destroy()

            # Limpiar referencias
            self.project_data = None
            self.current_project_path = None

            # Destruir la ventana principal
            self.destroy()

            # Forzar salida de la aplicación si es la última ventana
            import sys
            if len(self.winfo_toplevel().winfo_children()) == 0:
                sys.exit(0)
        except Exception as e:
            # Si hay algún error en la limpieza, forzar cierre de todas formas
            import sys
            sys.exit(0)