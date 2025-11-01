# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from PIL import Image
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, set_language, get_available_languages, get_current_global_language, set_current_global_language
from ..utils.project_manager import ProjectManager
from ..utils.resource_path import get_resource_path

class StartupWindow(ctk.CTk):
    
    def __init__(self, window_manager=None):
        super().__init__()

        self.window_manager = window_manager
        self.title(get_text("startup.title"))
        self.geometry("550x500")  # Ancho, Alto  Aumentado para el selector de idioma
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
        buttons_container.pack(pady=(0, 25))

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
        self.open_project_btn.pack(pady=5)

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

                caf_Size = (180, 60)
                n4w_Size = (230, 55)
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
        self.geometry("600x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        self.result = None

        # Referencias a widgets para actualización de texto
        self.title_label = None
        self.name_label = None
        self.description_label = None
        self.location_label = None
        self.objective_label = None
        self.cancel_btn = None
        self.create_btn = None
        self.name_entry = None
        self.description_entry = None
        self.location_entry = None
        self.objective_entry = None

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir (después de crear los widgets)
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        self.title_label = ctk.CTkLabel(
            main_frame,
            text=get_text("project_form.title"),
            **ThemeManager.get_label_style('heading')
        )
        self.title_label.pack(pady=(0, 20))
        
        form_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        form_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.name_label = ctk.CTkLabel(form_frame, text=get_text("project_form.name_label"), **ThemeManager.get_label_style('body'))
        self.name_label.pack(anchor="w", padx=20, pady=(20, 5))
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
        
        self.objective_label = ctk.CTkLabel(form_frame, text=get_text("project_form.objective_label"), **ThemeManager.get_label_style('body'))
        self.objective_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.objective_entry = ctk.CTkTextbox(
            form_frame, 
            height=100,
            fg_color=ThemeManager.COLORS['bg_card'],
            border_color=ThemeManager.COLORS['border'],
            text_color=ThemeManager.COLORS['text_primary'],
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            border_width=1
        )
        self.objective_entry.pack(fill="x", padx=20, pady=(0, 25))
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
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
            self.name_entry.insert(0, project_info.get('name', ''))
            self.description_entry.insert("1.0", project_info.get('description', ''))
            self.location_entry.insert(0, project_info.get('location', ''))
            self.objective_entry.insert("1.0", project_info.get('objective', ''))
    
    def _create_project(self):
        name        = self.name_entry.get().strip()
        description = self.description_entry.get("1.0", "end-1c").strip()
        location    = self.location_entry.get().strip()
        objective   = self.objective_entry.get("1.0", "end-1c").strip()

        if not name:
            messagebox.showerror(get_text("messages.error"), get_text("project_form.name_required"))
            return

        try:
            if self.is_editing:
                # Modo edición: actualizar project_data existente
                self.project_data['project_info'].update({
                    'name': name,
                    'description': description,
                    'location': location,
                    'objective': objective
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
                    'name': name,
                    'description': description,
                    'location': location,
                    'objective': objective
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
            self.title(get_text("project_form.title"))

            # Actualizar widgets de texto
            self.title_label.configure(text=get_text("project_form.title"))
            self.name_label.configure(text=get_text("project_form.name_label"))
            self.description_label.configure(text=get_text("project_form.description_label"))
            self.location_label.configure(text=get_text("project_form.location_label"))
            self.objective_label.configure(text=get_text("project_form.objective_label"))
            self.cancel_btn.configure(text=get_text("project_form.cancel"))
            self.create_btn.configure(text=get_text("project_form.create"))

            # Actualizar placeholders
            self.name_entry.configure(placeholder_text=get_text("project_form.name_placeholder"))
            self.location_entry.configure(placeholder_text=get_text("project_form.location_placeholder"))

    def _cancel(self):
        self.destroy()