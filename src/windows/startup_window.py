# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from PIL import Image
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, set_language, get_available_languages, get_current_global_language, set_current_global_language
from ..utils.project_manager import ProjectManager
from ..utils.resource_path import get_resource_path
from src.utils.resource_path import get_resource_path

class StartupWindow(ctk.CTk):
    
    def __init__(self, window_manager=None):
        super().__init__()

        self.window_manager = window_manager
        self.title(get_text("startup.title"))
        self.geometry("550x520")  # Ancho, Alto  Aumentado para selector de idioma y disclaimer
        self.resizable(False, False)

        ThemeManager.configure_ctk()
        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        # Referencias a widgets que necesitan actualización de texto
        self.title_label = None
        self.subtitle_label = None
        self.language_label = None
        self.options_title = None
        self.new_project_btn = None
        self.open_project_btn = None
        self.recent_label = None
        self.no_recent_label = None
        self.language_combo = None
        self.disclaimer_label = None

        self._setup_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="y", expand=True, padx=40, pady=(30,10))

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", expand=True, pady=(10, 0))

        self._load_and_display_logos(header_frame)

        # Selector de idioma moderno
        language_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        language_frame.pack(fill="x", pady=(10, 0))

        self.language_label = ctk.CTkLabel(
            language_frame,
            text=get_text("startup.language_label"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.language_label.pack(side="left", padx=(20, 10), pady=15)

        # Contenedor para botones de idioma
        lang_buttons_frame = ctk.CTkFrame(language_frame, fg_color="transparent")
        lang_buttons_frame.pack(side="right", padx=(10, 20), pady=10)

        # Botones de idioma estilizados
        languages = get_available_languages()
        self.language_buttons = {}
        self.current_lang_selection = "es"

        for i, (code, info) in enumerate(languages.items()):
            btn = ctk.CTkButton(
                lang_buttons_frame,
                text=f"{info['flag']} {info['name']}",
                width=100,
                height=35,
                command=lambda c=code: self._on_language_select(c),
                font=ThemeManager.FONTS['body'],
                corner_radius=20,
                fg_color=ThemeManager.COLORS['accent_primary'] if code == "es" else ThemeManager.COLORS['bg_card'],
                hover_color=ThemeManager.COLORS['accent_secondary'],
                text_color='#FFFFFF' if code == "es" else ThemeManager.COLORS['text_secondary']
            )
            btn.pack(side="left", padx=5)
            self.language_buttons[code] = btn

        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(10, 1))

        self.title_label = ctk.CTkLabel(
            title_frame,
            text=get_text("startup.title"),
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.title_label.pack()

        self.subtitle_label = ctk.CTkLabel(
            title_frame,
            text=get_text("startup.subtitle"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.subtitle_label.pack(pady=(5, 3))
        
        options_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        options_frame.pack(fill="x", pady=(0, 20))

        self.options_title = ctk.CTkLabel(
            options_frame,
            text=get_text("startup.question"),
            **ThemeManager.get_label_style('heading')
        )
        self.options_title.pack(pady=(10, 5))

        buttons_container = ctk.CTkFrame(options_frame, fg_color="transparent")
        buttons_container.pack(pady=(0, 2))

        self.new_project_btn = ctk.CTkButton(
            buttons_container,
            text=get_text("startup.create_project"),
            width=280,
            height=50,
            command=self._create_new_project,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['heading'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.new_project_btn.pack(pady=5)

        self.open_project_btn = ctk.CTkButton(
            buttons_container,
            text=get_text("startup.open_project"),
            width=280,
            height=50,
            command=self._open_existing_project,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['heading'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.open_project_btn.pack(pady=(5,1))

        # Disclaimer
        disclaimer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        disclaimer_frame.pack(fill="x", pady=(1, 0))

        self.disclaimer_label = ctk.CTkLabel(
            disclaimer_frame,
            text=get_text("startup.disclaimer"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=470,
            justify="center"
        )
        self.disclaimer_label.pack(pady=(0, 0))

        '''
        recent_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        recent_frame.pack(fill="x")
        
        
        self.recent_label = ctk.CTkLabel(
            recent_frame,
            text=get_text("startup.recent_projects"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.recent_label.pack(pady=(0, 5))

        self.no_recent_label = ctk.CTkLabel(
            recent_frame,
            text=get_text("startup.no_recent"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_light']
        )
        self.no_recent_label.pack()
        '''
    def _load_and_display_logos(self, parent):
        try:
            caf_path = get_resource_path(os.path.join("icons", "Icon_CAF.png"))
            n4w_path = get_resource_path(os.path.join("icons", "Icon_N4W.png"))
            
            if os.path.exists(caf_path) and os.path.exists(n4w_path):
                caf_image = Image.open(caf_path)
                n4w_image = Image.open(n4w_path)

                caf_Size = (180, 50)
                n4w_Size = (230, 50)
                caf_image = caf_image.resize(caf_Size, Image.Resampling.LANCZOS)
                n4w_image = n4w_image.resize(n4w_Size, Image.Resampling.LANCZOS)
                
                caf_ctk_image = ctk.CTkImage(light_image=caf_image, dark_image=caf_image, size=caf_Size)
                n4w_ctk_image = ctk.CTkImage(light_image=n4w_image, dark_image=n4w_image, size=n4w_Size)
                
                logos_container = ctk.CTkFrame(parent, fg_color="transparent")
                logos_container.pack(pady=(0, 4))

                
                caf_label = ctk.CTkLabel(logos_container, image=caf_ctk_image, text="")
                caf_label.pack(side="left", padx=(0, 10))
                
                # center_spacer = ctk.CTkFrame(logos_container, fg_color="transparent", width=100)
                # center_spacer.pack(side="left")
                
                n4w_label = ctk.CTkLabel(logos_container, image=n4w_ctk_image, text="")
                n4w_label.pack(side="left", padx=(10, 0), pady=(2, 2))
                
        except Exception as e:
            pass
    
    def _create_new_project(self):
        # Paso 1: Seleccionar ubicación del proyecto
        from .project_location_dialog import ProjectLocationDialog
        current_lang = get_current_global_language()
        location_dialog = ProjectLocationDialog(self, language=current_lang)
        self.wait_window(location_dialog)
        
        if not (hasattr(location_dialog, 'result') and location_dialog.result):
            return  # Usuario canceló la selección de ubicación
        
        project_base_folder = location_dialog.result
        
        # Paso 2: Formulario de información del proyecto
        current_lang = get_current_global_language()
        dialog = NewProjectDialog(self, project_base_folder, language=current_lang)
        self.wait_window(dialog)
        
        if hasattr(dialog, 'result') and dialog.result:
            project_data = dialog.result
            self._launch_dashboard(project_data)
    
    def _open_existing_project(self):
        file_path = filedialog.askopenfilename(
            title=get_text("messages.open_project_dialog"),
            filetypes=[(get_text("file_types.json"), get_text("file_types.json_ext")),
                      (get_text("file_types.all"), get_text("file_types.all_ext"))]
        )

        if file_path:
            project_data = ProjectManager.load_project(file_path)
            if project_data:
                if ProjectManager.validate_project(project_data):
                    # Lanzar dashboard directamente - la BD global ya está configurada en .database_config
                    self._launch_dashboard(project_data, file_path)
                else:
                    messagebox.showerror(get_text("messages.error"), get_text("messages.invalid_project"))
            else:
                messagebox.showerror(get_text("messages.error"), get_text("messages.project_load_error"))
    
    def _launch_dashboard(self, project_data, project_path=None):
        from .dashboard_window import DashboardWindow

        # Cerrar la ventana startup
        self.destroy()

        current_lang = get_current_global_language()
        dashboard = DashboardWindow(self.window_manager, language=current_lang)
        if project_path:
            # Extraer carpeta del proyecto desde la ruta del JSON
            dashboard.current_project_path = os.path.dirname(project_path)
        dashboard.load_project(project_data)

        dashboard.mainloop()
    
    def _on_language_select(self, language_code):
        """Manejar selección de idioma con botones"""
        if language_code != self.current_lang_selection:
            # Actualizar selección visual
            self._update_language_buttons(language_code)

            # Cambiar idioma globalmente
            set_language(language_code)
            self.current_lang_selection = language_code

    def _update_language_buttons(self, selected_code):
        """Actualizar apariencia visual de los botones de idioma"""
        for code, btn in self.language_buttons.items():
            if code == selected_code:
                # Botón seleccionado
                btn.configure(
                    fg_color=ThemeManager.COLORS['accent_primary'],
                    text_color='#FFFFFF'
                )
            else:
                # Botón no seleccionado
                btn.configure(
                    fg_color=ThemeManager.COLORS['bg_card'],
                    text_color=ThemeManager.COLORS['text_secondary']
                )

    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        if hasattr(self, 'title_label') and self.title_label:
            # Actualizar título de la ventana
            self.title(get_text("startup.title"))

            # Actualizar widgets de texto
            self.title_label.configure(text=get_text("startup.title"))
            self.subtitle_label.configure(text=get_text("startup.subtitle"))
            self.language_label.configure(text=get_text("startup.language_label"))
            self.options_title.configure(text=get_text("startup.question"))
            self.new_project_btn.configure(text=get_text("startup.create_project"))
            self.open_project_btn.configure(text=get_text("startup.open_project"))
            #self.recent_label.configure(text=get_text("startup.recent_projects"))
            #self.no_recent_label.configure(text=get_text("startup.no_recent"))

            if hasattr(self, 'disclaimer_label') and self.disclaimer_label:
                self.disclaimer_label.configure(text=get_text("startup.disclaimer"))

            # Actualizar textos de botones de idioma
            if hasattr(self, 'language_buttons'):
                languages = get_available_languages()
                for code, btn in self.language_buttons.items():
                    if code in languages:
                        info = languages[code]
                        btn.configure(text=f"{info['flag']} {info['name']}")

    def _on_closing(self):
        self.destroy()

class NewProjectDialog(ctk.CTkToplevel):
    
    def __init__(self, parent, project_base_folder=None, language=None, project_data=None):
        super().__init__(parent)

        self.project_base_folder = project_base_folder
        self.project_data = project_data
        self.is_editing = project_data is not None

        # Sincronizar idioma antes de crear UI
        if language:
            set_current_global_language(language)

        title_key = "project_form.edit_title" if self.is_editing else "project_form.title"
        self.title(get_text(title_key))
        self.geometry("700x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        self.result = None

        # Referencias a widgets para actualización de texto
        self.title_label = None
        self.acronym_label = None
        self.acronym_entry = None
        self.name_label = None
        self.name_entry = None
        self.description_label = None
        self.description_entry = None
        self.location_label = None
        self.location_entry = None
        self.country_label = None
        self.country_combobox = None
        self.objective_label = None
        self.objective_entry = None
        self.taxonomy_section_label = None
        self.category_label = None
        self.category_combobox = None
        self.subcategory_label = None
        self.subcategory_combobox = None
        self.activity_label = None
        self.activity_combobox = None
        self.observations_label = None
        self.observations_entry = None
        self.cancel_btn = None
        self.create_btn = None

        # Datos de taxonomía
        self.taxonomy_data = {}
        self.taxonomy_id_map = {}  # Mapeo: ID -> (categoria, subcategoria, actividad)
        self.countries_dict = {}
        self.category_display_map = {}  # Mapeo: texto_truncado -> texto_completo
        self.subcategory_display_map = {}
        self.activity_display_map = {}

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir (después de crear los widgets)
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _setup_ui(self):
        # Frame principal con título
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 10))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text=get_text("project_form.title"),
            **ThemeManager.get_label_style('heading')
        )
        self.title_label.pack()

        # Frame scrollable para el formulario
        scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=ThemeManager.COLORS['accent_primary'],
            scrollbar_button_hover_color=ThemeManager.COLORS['accent_secondary']
        )
        scrollable_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        form_frame = ctk.CTkFrame(scrollable_frame, **ThemeManager.get_frame_style())
        form_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Acrónimo
        self.acronym_label = ctk.CTkLabel(form_frame, text=get_text("project_form.acronym_label"), **ThemeManager.get_label_style('body'))
        self.acronym_label.pack(anchor="w", padx=20, pady=(20, 5))
        self.acronym_entry = ctk.CTkEntry(form_frame, placeholder_text=get_text("project_form.acronym_placeholder"), **ThemeManager.get_entry_style())
        self.acronym_entry.pack(fill="x", padx=20, pady=(0, 15))

        # Nombre/Título del proyecto
        self.name_label = ctk.CTkLabel(form_frame, text=get_text("project_form.name_label"), **ThemeManager.get_label_style('body'))
        self.name_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text=get_text("project_form.name_placeholder"), **ThemeManager.get_entry_style())
        self.name_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        self.description_label = ctk.CTkLabel(form_frame, text=get_text("project_form.description_label"), **ThemeManager.get_label_style('body'))
        self.description_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.description_entry = ctk.CTkTextbox(
            form_frame, 
            height=80,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            border_width=1
        )
        self.description_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        self.location_label = ctk.CTkLabel(form_frame, text=get_text("project_form.location_label"), **ThemeManager.get_label_style('body'))
        self.location_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.location_entry = ctk.CTkEntry(form_frame, placeholder_text=get_text("project_form.location_placeholder"), **ThemeManager.get_entry_style())
        self.location_entry.pack(fill="x", padx=20, pady=(0, 15))

        # Selector de país
        self.country_label = ctk.CTkLabel(form_frame, text=get_text("project_form.country_label"), **ThemeManager.get_label_style('body'))
        self.country_label.pack(anchor="w", padx=20, pady=(0, 5))

        # Cargar lista de países desde Weight_Matrix.xlsx
        self.countries_dict = self._load_countries()
        country_names = list(self.countries_dict.keys())

        self.country_combobox = ctk.CTkComboBox(
            form_frame,
            values=country_names if country_names else ["No countries available"],
            state="readonly",
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            button_color=ThemeManager.COLORS['accent_primary'],
            button_hover_color=ThemeManager.COLORS['accent_secondary'],
            dropdown_fg_color=ThemeManager.COLORS['bg_card'],
            dropdown_hover_color=ThemeManager.COLORS['bg_secondary'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            dropdown_font=("Segoe UI", 9),
            height=28
        )
        self.country_combobox.pack(fill="x", padx=20, pady=(0, 15))
        if country_names:
            self.country_combobox.set(country_names[0])  # Seleccionar primer país por defecto

        # Configurar altura máxima del dropdown
        try:
            self.country_combobox._dropdown_menu.configure(height=200)
        except:
            pass

        self.objective_label = ctk.CTkLabel(form_frame, text=get_text("project_form.objective_label"), **ThemeManager.get_label_style('body'))
        self.objective_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.objective_entry = ctk.CTkTextbox(
            form_frame,
            height=120,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            border_width=1
        )
        self.objective_entry.pack(fill="x", padx=20, pady=(0, 15))

        # Sección Taxonomía CAF
        self.taxonomy_section_label = ctk.CTkLabel(
            form_frame,
            text=get_text("project_form.taxonomy_section"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.taxonomy_section_label.pack(anchor="w", padx=20, pady=(15, 5))

        # Info de taxonomía
        taxonomy_info_label = ctk.CTkLabel(
            form_frame,
            text=get_text("project_form.taxonomy_info"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=600
        )
        taxonomy_info_label.pack(anchor="w", padx=20, pady=(0, 10))

        # Cargar taxonomía
        self.taxonomy_data = self._load_taxonomy()

        # Categoría
        self.category_label = ctk.CTkLabel(form_frame, text=get_text("project_form.category_label"), **ThemeManager.get_label_style('body'))
        self.category_label.pack(anchor="w", padx=20, pady=(0, 5))

        # Preparar categorías truncadas para display
        select_text = get_text("project_form.select_category")
        categories_display = [select_text]
        self.category_display_map = {select_text: select_text}

        for cat in self.taxonomy_data.keys():
            truncated = self._truncate_text(cat, 60)
            categories_display.append(truncated)
            self.category_display_map[truncated] = cat

        self.category_combobox = ctk.CTkComboBox(
            form_frame,
            values=categories_display,
            state="readonly",
            command=self._on_category_selected,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            button_color=ThemeManager.COLORS['accent_primary'],
            button_hover_color=ThemeManager.COLORS['accent_secondary'],
            dropdown_fg_color=ThemeManager.COLORS['bg_card'],
            dropdown_hover_color=ThemeManager.COLORS['bg_secondary'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            dropdown_font=("Segoe UI", 8),
            height=28,
            width=600
        )
        self.category_combobox.pack(fill="x", padx=20, pady=(0, 15))
        self.category_combobox.set(select_text)

        # Configurar altura máxima del dropdown
        try:
            self.category_combobox._dropdown_menu.configure(height=250)
        except:
            pass

        # Subcategoría
        self.subcategory_label = ctk.CTkLabel(form_frame, text=get_text("project_form.subcategory_label"), **ThemeManager.get_label_style('body'))
        self.subcategory_label.pack(anchor="w", padx=20, pady=(0, 5))

        self.subcategory_combobox = ctk.CTkComboBox(
            form_frame,
            values=[get_text("project_form.select_subcategory")],
            state="disabled",
            command=self._on_subcategory_selected,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            button_color=ThemeManager.COLORS['accent_primary'],
            button_hover_color=ThemeManager.COLORS['accent_secondary'],
            dropdown_fg_color=ThemeManager.COLORS['bg_card'],
            dropdown_hover_color=ThemeManager.COLORS['bg_secondary'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            dropdown_font=("Segoe UI", 8),
            height=28,
            width=600
        )
        self.subcategory_combobox.pack(fill="x", padx=20, pady=(0, 15))
        self.subcategory_combobox.set(get_text("project_form.select_subcategory"))

        # Configurar altura máxima del dropdown
        try:
            self.subcategory_combobox._dropdown_menu.configure(height=250)
        except:
            pass

        # Actividad elegible
        self.activity_label = ctk.CTkLabel(form_frame, text=get_text("project_form.activity_label"), **ThemeManager.get_label_style('body'))
        self.activity_label.pack(anchor="w", padx=20, pady=(0, 5))

        self.activity_combobox = ctk.CTkComboBox(
            form_frame,
            values=[get_text("project_form.select_activity")],
            state="disabled",
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            button_color=ThemeManager.COLORS['accent_primary'],
            button_hover_color=ThemeManager.COLORS['accent_secondary'],
            dropdown_fg_color=ThemeManager.COLORS['bg_card'],
            dropdown_hover_color=ThemeManager.COLORS['bg_secondary'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            dropdown_font=("Segoe UI", 8),
            height=28,
            width=600
        )
        self.activity_combobox.pack(fill="x", padx=20, pady=(0, 15))
        self.activity_combobox.set(get_text("project_form.select_activity"))

        # Configurar altura máxima del dropdown
        try:
            self.activity_combobox._dropdown_menu.configure(height=250)
        except:
            pass

        # Observaciones
        self.observations_label = ctk.CTkLabel(form_frame, text=get_text("project_form.observations_label"), **ThemeManager.get_label_style('body'))
        self.observations_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.observations_entry = ctk.CTkTextbox(
            form_frame,
            height=80,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            border_width=1
        )
        self.observations_entry.pack(fill="x", padx=20, pady=(0, 25))

        # Botones fuera del scrollable frame (fijos en la parte inferior)
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text=get_text("project_form.cancel"),
            width=120,
            height=40,
            command=self._cancel,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.cancel_btn.pack(side="right", padx=(15, 0))
        
        button_text_key = "project_form.save" if self.is_editing else "project_form.create"
        self.create_btn = ctk.CTkButton(
            button_frame,
            text=get_text(button_text_key),
            width=150,
            height=40,
            command=self._create_project,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.create_btn.pack(side="right")

        # Pre-llenar campos si estamos editando
        if self.is_editing and self.project_data:
            project_info = self.project_data.get('project_info', {})
            self.acronym_entry.insert(0, project_info.get('acronym', ''))
            self.name_entry.insert(0, project_info.get('name', ''))
            self.description_entry.insert("1.0", project_info.get('description', ''))
            self.location_entry.insert(0, project_info.get('location', ''))
            self.objective_entry.insert("1.0", project_info.get('objective', ''))
            self.observations_entry.insert("1.0", project_info.get('observations', ''))

            # Cargar país si existe
            if 'country_code' in project_info and hasattr(self, 'country_combobox'):
                country_code = project_info.get('country_code')
                country_name = project_info.get('country_name', '')
                # Buscar y seleccionar el país en el combobox
                if country_name in self.countries_dict.keys():
                    self.country_combobox.set(country_name)

            # Cargar taxonomía CAF si existe
            caf_taxonomy_id = project_info.get('caf_taxonomy_id', '')
            caf_category = None
            caf_subcategory = None
            caf_activity = None

            print(f"\n=== DEBUG PRE-LLENADO TAXONOMÍA ===")
            print(f"ID guardado: {caf_taxonomy_id} (tipo: {type(caf_taxonomy_id).__name__})")
            print(f"IDs disponibles en mapa: {len(self.taxonomy_id_map)}")

            # Normalizar ID a string para búsqueda (JSON puede deserializar como int)
            if caf_taxonomy_id:
                caf_taxonomy_id = str(caf_taxonomy_id)
                print(f"ID normalizado: '{caf_taxonomy_id}'")
                # Debug: mostrar algunos IDs del mapa
                sample_ids = list(self.taxonomy_id_map.keys())[:5]
                print(f"IDs de ejemplo en mapa: {sample_ids}")
                print(f"¿ID '{caf_taxonomy_id}' en mapa?: {caf_taxonomy_id in self.taxonomy_id_map}")

            # Prioridad 1: Buscar por ID (multiidioma, proyectos nuevos)
            if caf_taxonomy_id and caf_taxonomy_id in self.taxonomy_id_map:
                caf_category, caf_subcategory, caf_activity = self.taxonomy_id_map[caf_taxonomy_id]
                print(f"✓ Taxonomía cargada por ID: {caf_taxonomy_id}")
                print(f"  Categoría: {caf_category[:50] if len(caf_category) > 50 else caf_category}")
                print(f"  Subcategoría: {caf_subcategory[:50] if len(caf_subcategory) > 50 else caf_subcategory}")
                print(f"  Actividad: {caf_activity[:50] if len(caf_activity) > 50 else caf_activity}")
            else:
                # Prioridad 2: Fallback a búsqueda por texto (retrocompatibilidad, proyectos viejos)
                caf_category = project_info.get('caf_category', '')
                caf_subcategory = project_info.get('caf_subcategory', '')
                caf_activity = project_info.get('caf_activity', '')
                if caf_category:
                    print(f"⚠️ Taxonomía cargada por texto (proyecto antiguo)")
                else:
                    print(f"✗ No se encontró ID ni datos de texto")

            # Si tenemos datos de taxonomía válidos, configurar los comboboxes
            print(f"Verificando categoría en taxonomy_data...")
            if caf_category and caf_category in self.taxonomy_data:
                print(f"✓ Categoría encontrada en taxonomy_data")
                # Buscar el valor truncado correspondiente en el mapeo
                cat_display = None
                for display, real in self.category_display_map.items():
                    if real == caf_category:
                        cat_display = display
                        break

                print(f"Display categoría: {cat_display[:50] if cat_display and len(cat_display) > 50 else cat_display}")

                if cat_display:
                    self.category_combobox.set(cat_display)
                    self._on_category_selected(cat_display)
                    print(f"✓ Categoría establecida en combobox")

                    print(f"Verificando subcategoría...")
                    if caf_subcategory and caf_subcategory in self.taxonomy_data.get(caf_category, {}):
                        print(f"✓ Subcategoría encontrada en taxonomy_data")
                        print(f"Mapeos de subcategoría disponibles: {len(self.subcategory_display_map)}")

                        # Buscar el valor truncado de subcategoría
                        subcat_display = None
                        for display, real in self.subcategory_display_map.items():
                            if real == caf_subcategory:
                                subcat_display = display
                                break

                        print(f"Display subcategoría: {subcat_display[:50] if subcat_display and len(subcat_display) > 50 else subcat_display}")

                        if subcat_display:
                            self.subcategory_combobox.set(subcat_display)
                            self._on_subcategory_selected(subcat_display)
                            print(f"✓ Subcategoría establecida en combobox")

                            print(f"Verificando actividad...")
                            if caf_activity:
                                print(f"Mapeos de actividad disponibles: {len(self.activity_display_map)}")

                                # Buscar el valor truncado de actividad
                                activity_display = None
                                for display, real in self.activity_display_map.items():
                                    if real == caf_activity:
                                        activity_display = display
                                        break

                                print(f"Display actividad: {activity_display[:50] if activity_display and len(activity_display) > 50 else activity_display}")

                                if activity_display:
                                    self.activity_combobox.set(activity_display)
                                    print(f"✓ Actividad establecida en combobox")
                                else:
                                    print(f"✗ No se encontró display para actividad")
                        else:
                            print(f"✗ No se encontró display para subcategoría")
                    else:
                        print(f"✗ Subcategoría '{caf_subcategory[:50] if caf_subcategory else 'N/A'}' no encontrada")
                else:
                    print(f"✗ No se encontró display para categoría")
            else:
                print(f"✗ Categoría no válida o no encontrada")

            print(f"=== FIN DEBUG ===\n")

    def _truncate_text(self, text, max_length):
        """Truncar texto largo para mostrar en dropdown"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _get_taxonomy_id(self, categoria, subcategoria, actividad):
        """
        Obtener ID de taxonomía para una combinación específica.
        Busca en el mapeo inverso de taxonomy_id_map.

        Args:
            categoria (str): Categoría completa
            subcategoria (str): Subcategoría completa
            actividad (str): Actividad completa

        Returns:
            str: ID de la taxonomía o None si no se encuentra
        """
        for tax_id, (cat, subcat, act) in self.taxonomy_id_map.items():
            if cat == categoria and subcat == subcategoria and act == actividad:
                return tax_id
        return None

    def _load_taxonomy(self):
        """
        Cargar taxonomía CAF desde archivo según idioma actual.
        Busca Taxonomia_CAF_{idioma}.csv según el idioma seleccionado (es, en, pt).
        Si no existe, usa español como fallback.

        Returns:
            dict: {Categoria: {Subcategoria: [Actividades]}}
        """
        try:
            import csv

            # Obtener idioma actual
            current_lang = get_current_global_language()

            # Construir nombre de archivo según idioma
            taxonomy_filename = f"Taxonomia_CAF_{current_lang}.csv"
            taxonomy_path = get_resource_path(os.path.join("locales", taxonomy_filename))

            # Si no existe el archivo del idioma, usar español como fallback
            if not os.path.exists(taxonomy_path):
                print(f"⚠️ No se encontró {taxonomy_filename}, usando español como fallback")
                taxonomy_filename = "Taxonomia_CAF_es.csv"
                taxonomy_path = get_resource_path(os.path.join("locales", taxonomy_filename))

                if not os.path.exists(taxonomy_path):
                    print(f"⚠️ No se encontró archivo de taxonomía")
                    return {}

            taxonomy = {}
            # Limpiar mapeo de IDs anterior
            self.taxonomy_id_map = {}

            # Intentar múltiples codificaciones (Windows puede guardar con diferentes encodings)
            encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            file_content = None
            encoding_used = None

            for encoding in encodings_to_try:
                try:
                    with open(taxonomy_path, 'r', encoding=encoding) as f:
                        file_content = f.read()
                        encoding_used = encoding
                        break
                except UnicodeDecodeError:
                    continue

            if file_content is None:
                print(f"⚠️ No se pudo leer {taxonomy_filename} con ninguna codificación")
                return {}

            print(f"✓ Archivo {taxonomy_filename} leído con codificación: {encoding_used}")

            # Procesar CSV desde el contenido leído
            import io
            reader = csv.DictReader(io.StringIO(file_content))

            # Mapeo de nombres de columnas en diferentes idiomas
            column_mappings = {
                'id': ['ID'],
                'categoria': ['Categoria', 'Category'],
                'subcategoria': ['Subcategoria', 'Subcategory'],
                'actividad': ['Actividad', 'Activity', 'Atividade']
            }

            # Detectar nombres de columnas reales del CSV
            if reader.fieldnames:
                col_names = {}
                for key, possible_names in column_mappings.items():
                    for name in possible_names:
                        if name in reader.fieldnames:
                            col_names[key] = name
                            break

                print(f"  Columnas detectadas: {col_names}")

                for row in reader:
                    tax_id = row.get(col_names.get('id', 'ID'), '').strip()
                    categoria = row.get(col_names.get('categoria', 'Categoria'), '').strip()
                    subcategoria = row.get(col_names.get('subcategoria', 'Subcategoria'), '').strip()
                    actividad = row.get(col_names.get('actividad', 'Actividad'), '').strip()

                    if not categoria or not subcategoria or not actividad:
                        continue

                    # Construir estructura jerárquica para navegación
                    if categoria not in taxonomy:
                        taxonomy[categoria] = {}

                    if subcategoria not in taxonomy[categoria]:
                        taxonomy[categoria][subcategoria] = []

                    if actividad not in taxonomy[categoria][subcategoria]:
                        taxonomy[categoria][subcategoria].append(actividad)

                    # Construir mapeo de ID para búsqueda multiidioma
                    if tax_id:
                        self.taxonomy_id_map[tax_id] = (categoria, subcategoria, actividad)

            print(f"✓ Cargadas {len(taxonomy)} categorías desde {taxonomy_filename}")
            for cat in taxonomy.keys():
                print(f"  - Categoría: {cat}")
            return taxonomy

        except Exception as e:
            print(f"⚠️ Error cargando taxonomía: {e}")
            return {}

    def _load_countries(self):
        """
        Cargar lista de países desde Weight_Matrix.xlsx

        Returns:
            dict: {country_name: (country_code, factor)}
        """
        try:
            import pandas as pd
            weight_matrix_path = get_resource_path(os.path.join("locales", "Weight_Matrix.xlsx"))

            # Si no existe y contiene src\, intentar sin src\
            if not os.path.exists(weight_matrix_path) and 'src' + os.sep in weight_matrix_path:
                weight_matrix_path = weight_matrix_path.replace('src' + os.sep, '')

            if not os.path.exists(weight_matrix_path):
                print(f"⚠️ No se encontró Weight_Matrix.xlsx")
                return {}

            # Leer hoja FactorCost
            df = pd.read_excel(weight_matrix_path, sheet_name="FactorCost")

            # Columna 0 = código, Columna 1 = nombre, Columna 2 = factor
            countries = {}
            for idx, row in df.iterrows():
                country_code = row.iloc[0]  # Primera columna = código numérico
                country_name = row.iloc[1] if len(row) > 1 else f"País {country_code}"
                country_factor = row.iloc[2] if len(row) > 2 else 1.0

                # Asegurar que el código sea numérico
                try:
                    country_code = int(country_code)
                    country_factor = float(country_factor)
                    countries[str(country_name)] = (country_code, country_factor)
                except (ValueError, TypeError):
                    continue

            print(f"✓ Cargados {len(countries)} países desde Weight_Matrix.xlsx")
            return countries

        except Exception as e:
            print(f"⚠️ Error cargando países: {e}")
            return {}

    def _on_category_selected(self, selected_category_display):
        """Manejar selección de categoría y habilitar subcategorías"""
        # Resetear subcategoría y actividad
        self.subcategory_combobox.configure(state="disabled")
        self.subcategory_combobox.set(get_text("project_form.select_subcategory"))
        self.activity_combobox.configure(state="disabled")
        self.activity_combobox.set(get_text("project_form.select_activity"))

        # Obtener categoría real desde el mapeo
        selected_category = self.category_display_map.get(selected_category_display, selected_category_display)

        # Si la categoría seleccionada es válida, habilitar subcategorías
        if selected_category and selected_category != get_text("project_form.select_category"):
            if selected_category in self.taxonomy_data:
                # Preparar subcategorías truncadas
                select_text = get_text("project_form.select_subcategory")
                subcategories_display = [select_text]
                self.subcategory_display_map = {select_text: select_text}

                for subcat in self.taxonomy_data[selected_category].keys():
                    truncated = self._truncate_text(subcat, 80)
                    subcategories_display.append(truncated)
                    self.subcategory_display_map[truncated] = subcat

                self.subcategory_combobox.configure(values=subcategories_display, state="readonly")

    def _on_subcategory_selected(self, selected_subcategory_display):
        """Manejar selección de subcategoría y habilitar actividades"""
        # Resetear actividad
        self.activity_combobox.configure(state="disabled")
        self.activity_combobox.set(get_text("project_form.select_activity"))

        # Obtener subcategoría real desde el mapeo
        selected_subcategory = self.subcategory_display_map.get(selected_subcategory_display, selected_subcategory_display)

        # Si la subcategoría seleccionada es válida, habilitar actividades
        if selected_subcategory and selected_subcategory != get_text("project_form.select_subcategory"):
            # Obtener categoría real desde el mapeo
            selected_category_display = self.category_combobox.get()
            selected_category = self.category_display_map.get(selected_category_display, selected_category_display)

            if selected_category in self.taxonomy_data:
                if selected_subcategory in self.taxonomy_data[selected_category]:
                    # Preparar actividades truncadas
                    select_text = get_text("project_form.select_activity")
                    activities_display = [select_text]
                    self.activity_display_map = {select_text: select_text}

                    for activity in self.taxonomy_data[selected_category][selected_subcategory]:
                        truncated = self._truncate_text(activity, 100)
                        activities_display.append(truncated)
                        self.activity_display_map[truncated] = activity

                    self.activity_combobox.configure(values=activities_display, state="readonly")

    def _create_project(self):
        acronym     = self.acronym_entry.get().strip()
        name        = self.name_entry.get().strip()
        description = self.description_entry.get("1.0", "end-1c").strip()
        location    = self.location_entry.get().strip()
        objective   = self.objective_entry.get("1.0", "end-1c").strip()
        observations = self.observations_entry.get("1.0", "end-1c").strip()

        # Obtener país seleccionado
        country_name = None
        country_code = None
        country_factor = None
        if hasattr(self, 'country_combobox'):
            country_name = self.country_combobox.get()
            country_data = self.countries_dict.get(country_name)
            if country_data:
                country_code, country_factor = country_data

        # Obtener taxonomía CAF seleccionada (valores de display)
        caf_category_display = self.category_combobox.get()
        caf_subcategory_display = self.subcategory_combobox.get()
        caf_activity_display = self.activity_combobox.get()

        # Obtener valores reales desde los mapeos
        caf_category = self.category_display_map.get(caf_category_display, caf_category_display)
        caf_subcategory = self.subcategory_display_map.get(caf_subcategory_display, caf_subcategory_display)
        caf_activity = self.activity_display_map.get(caf_activity_display, caf_activity_display)

        # Obtener ID de taxonomía para persistencia multiidioma
        caf_taxonomy_id = self._get_taxonomy_id(caf_category, caf_subcategory, caf_activity)

        # Validaciones
        if not name:
            messagebox.showerror(get_text("messages.error"), get_text("project_form.name_required"))
            return

        # Validar taxonomía CAF (todos los campos deben estar seleccionados)
        select_cat = get_text("project_form.select_category")
        select_subcat = get_text("project_form.select_subcategory")
        select_act = get_text("project_form.select_activity")

        if (caf_category == select_cat or
            caf_subcategory == select_subcat or
            caf_activity == select_act):
            messagebox.showerror(get_text("messages.error"), get_text("project_form.taxonomy_required"))
            return

        try:
            if self.is_editing:
                # Modo edición: actualizar project_data existente
                self.project_data['project_info'].update({
                    'acronym': acronym,
                    'name': name,
                    'description': description,
                    'location': location,
                    'objective': objective,
                    'country_code': country_code,
                    'country_name': country_name,
                    'country_factor': country_factor,
                    'caf_category': caf_category,
                    'caf_subcategory': caf_subcategory,
                    'caf_activity': caf_activity,
                    'caf_taxonomy_id': caf_taxonomy_id,
                    'observations': observations
                })
                self.result = self.project_data
                self.destroy()
            else:
                # Modo creación: crear nuevo proyecto
                if not self.project_base_folder:
                    messagebox.showerror(get_text("messages.error"), get_text("project_form.folder_required"))
                    return

                # Crear carpeta del proyecto
                project_folder = ProjectManager.create_project_folder(self.project_base_folder)

                # Crear template del proyecto
                project_data = ProjectManager.create_project_template()
                project_data['project_info'].update({
                    'acronym': acronym,
                    'name': name,
                    'description': description,
                    'location': location,
                    'objective': objective,
                    'country_code': country_code,
                    'country_name': country_name,
                    'country_factor': country_factor,
                    'caf_category': caf_category,
                    'caf_subcategory': caf_subcategory,
                    'caf_activity': caf_activity,
                    'caf_taxonomy_id': caf_taxonomy_id,
                    'observations': observations
                })

                # Establecer rutas de archivos
                project_data['files']['project_folder'] = project_folder
                # La BD global se obtiene directamente de .database_config, no se guarda en project.json

                project_json_path = ProjectManager.get_project_json_path(project_folder)

                # Guardar JSON inicial
                if not ProjectManager.save_project(project_data, project_json_path):
                    messagebox.showerror(get_text("messages.error"), get_text("project_form.creation_error"))
                    return

                # Establecer el resultado del diálogo
                self.result = project_data
                self.destroy()
                
        except Exception as e:
            messagebox.showerror(get_text("messages.error"), f"{get_text('project_form.creation_error')}: {str(e)}")

    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        if hasattr(self, 'title_label') and self.title_label:
            # Actualizar título de la ventana
            title_key = "project_form.edit_title" if self.is_editing else "project_form.title"
            self.title(get_text(title_key))

            # Actualizar widgets de texto
            self.title_label.configure(text=get_text("project_form.title"))

            if hasattr(self, 'acronym_label') and self.acronym_label:
                self.acronym_label.configure(text=get_text("project_form.acronym_label"))

            self.name_label.configure(text=get_text("project_form.name_label"))
            self.description_label.configure(text=get_text("project_form.description_label"))
            self.location_label.configure(text=get_text("project_form.location_label"))

            if hasattr(self, 'country_label') and self.country_label:
                self.country_label.configure(text=get_text("project_form.country_label"))

            self.objective_label.configure(text=get_text("project_form.objective_label"))

            if hasattr(self, 'taxonomy_section_label') and self.taxonomy_section_label:
                self.taxonomy_section_label.configure(text=get_text("project_form.taxonomy_section"))

            if hasattr(self, 'category_label') and self.category_label:
                self.category_label.configure(text=get_text("project_form.category_label"))

            if hasattr(self, 'subcategory_label') and self.subcategory_label:
                self.subcategory_label.configure(text=get_text("project_form.subcategory_label"))

            if hasattr(self, 'activity_label') and self.activity_label:
                self.activity_label.configure(text=get_text("project_form.activity_label"))

            if hasattr(self, 'observations_label') and self.observations_label:
                self.observations_label.configure(text=get_text("project_form.observations_label"))

            self.cancel_btn.configure(text=get_text("project_form.cancel"))

            button_text_key = "project_form.save" if self.is_editing else "project_form.create"
            self.create_btn.configure(text=get_text(button_text_key))

            # Actualizar placeholders
            if hasattr(self, 'acronym_entry') and self.acronym_entry:
                self.acronym_entry.configure(placeholder_text=get_text("project_form.acronym_placeholder"))

            self.name_entry.configure(placeholder_text=get_text("project_form.name_placeholder"))
            self.location_entry.configure(placeholder_text=get_text("project_form.location_placeholder"))

    def _cancel(self):
        self.destroy()