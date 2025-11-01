import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, get_current_global_language, set_current_global_language
from ..utils.project_manager import ProjectManager

class ProjectLocationDialog(ctk.CTkToplevel):
    
    def __init__(self, parent, language=None):
        super().__init__(parent)

        # Sincronizar idioma antes de crear UI
        if language:
            set_current_global_language(language)

        self.title(get_text("location_dialog.title"))
        self.geometry("600x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        self.result = None
        self.selected_folder = None
        self.widget_refs = {}

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 25))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack()
        self.widget_refs['title'] = title_label

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        subtitle_label.pack(pady=(5, 0))
        self.widget_refs['subtitle'] = subtitle_label
        
        content_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        content_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        instructions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        instructions_frame.pack(fill="x", padx=25, pady=(25, 20))
        
        instructions_title = ctk.CTkLabel(
            instructions_frame,
            text="",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        instructions_title.pack(anchor="w", pady=(0, 10))
        self.widget_refs['info_title'] = instructions_title
        
        # Crear labels para las instrucciones
        for i in range(1, 5):
            inst_label = ctk.CTkLabel(
                instructions_frame,
                text="",
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['text_secondary']
            )
            inst_label.pack(anchor="w", pady=2)
            self.widget_refs[f'instruction_{i}'] = inst_label
        
        selection_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        selection_frame.pack(fill="x", padx=25, pady=(20, 25))
        
        base_folder_label = ctk.CTkLabel(
            selection_frame,
            text="",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_primary']
        )
        base_folder_label.pack(anchor="w", pady=(0, 5))
        self.widget_refs['base_folder'] = base_folder_label
        
        folder_display_frame = ctk.CTkFrame(selection_frame, **ThemeManager.get_frame_style())
        folder_display_frame.pack(fill="x", pady=(0, 15))
        
        self.folder_label = ctk.CTkLabel(
            folder_display_frame,
            text="",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_light'],
            wraplength=500
        )
        self.folder_label.pack(padx=15, pady=15)
        # Guardar referencia para actualizar el texto de "ninguna carpeta"
        self.widget_refs['none_selected'] = self.folder_label
        
        button_container = ctk.CTkFrame(selection_frame, fg_color="transparent")
        button_container.pack(fill="x")
        
        browse_btn = ctk.CTkButton(
            button_container,
            text="",
            width=200,
            height=40,
            command=self._browse_folder,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        browse_btn.pack()
        self.widget_refs['browse_button'] = browse_btn
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="",
            width=120,
            height=40,
            command=self._cancel,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        cancel_btn.pack(side="right", padx=(15, 0))
        self.widget_refs['cancel_button'] = cancel_btn

        self.continue_btn = ctk.CTkButton(
            button_frame,
            text="",
            width=150,
            height=40,
            command=self._continue,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="disabled"
        )
        self.continue_btn.pack(side="right")
        self.widget_refs['continue_button'] = self.continue_btn
    
    def _browse_folder(self):
        folder_path = filedialog.askdirectory(
            title=get_text("location_dialog.title"),
            mustexist=True
        )
        
        if folder_path:
            # Verificar permisos de escritura
            if not os.access(folder_path, os.W_OK):
                messagebox.showerror(
                    get_text("location_dialog.permission_error_title"),
                    get_text("location_dialog.permission_error_message")
                )
                return
            
            self.selected_folder = folder_path
            
            # Mostrar carpeta seleccionada (truncar si es muy larga)
            display_path = folder_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            
            self.folder_label.configure(
                text=f"📁 {display_path}",
                text_color=ThemeManager.COLORS['text_primary']
            )
            
            # Habilitar botón continuar
            self.continue_btn.configure(state="normal")
    
    def _continue(self):
        if not self.selected_folder:
            messagebox.showwarning(
                get_text("location_dialog.warning_title"),
                get_text("location_dialog.warning_message")
            )
            return
        
        self.result = self.selected_folder
        self.destroy()
    
    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        try:
            # Actualizar título de la ventana
            self.title(get_text("location_dialog.title"))

            # Actualizar título y subtítulo
            if 'title' in self.widget_refs:
                self.widget_refs['title'].configure(text=get_text("location_dialog.main_title"))

            if 'subtitle' in self.widget_refs:
                self.widget_refs['subtitle'].configure(text=get_text("location_dialog.subtitle"))

            # Actualizar título de información
            if 'info_title' in self.widget_refs:
                self.widget_refs['info_title'].configure(text=get_text("location_dialog.info_title"))

            # Actualizar instrucciones
            for i in range(1, 5):
                if f'instruction_{i}' in self.widget_refs:
                    self.widget_refs[f'instruction_{i}'].configure(text=get_text(f"location_dialog.instruction_{i}"))

            # Actualizar label de carpeta base
            if 'base_folder' in self.widget_refs:
                self.widget_refs['base_folder'].configure(text=get_text("location_dialog.base_folder"))

            # Actualizar texto de "ninguna carpeta seleccionada" solo si no hay carpeta seleccionada
            if 'none_selected' in self.widget_refs and not self.selected_folder:
                self.widget_refs['none_selected'].configure(text=get_text("location_dialog.none_selected"))

            # Actualizar botón de examinar
            if 'browse_button' in self.widget_refs:
                self.widget_refs['browse_button'].configure(text=get_text("location_dialog.browse_button"))

            # Actualizar botones
            if 'cancel_button' in self.widget_refs:
                self.widget_refs['cancel_button'].configure(text=get_text("location_dialog.cancel"))

            if 'continue_button' in self.widget_refs:
                self.widget_refs['continue_button'].configure(text=get_text("location_dialog.continue"))

        except Exception as e:
            # Fail silently si no se pueden actualizar los textos
            print(f"Error actualizando textos: {e}")

    def _cancel(self):
        self.destroy()