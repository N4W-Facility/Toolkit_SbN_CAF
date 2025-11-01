import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from ..core.database_manager import DatabaseManager
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes

class DatabaseConfirmationDialog:
    """
    Diálogo para confirmar o cambiar la ubicación de la base de datos existente.
    Muestra la ruta actual y permite OK o Cambiar.
    Incluye textos en español, inglés y portugués.
    """

    def __init__(self, current_path):
        self.current_path = current_path
        self.selected_path = current_path
        self.dialog_result = False  # True si confirmó, False si canceló
        self.path_changed = False   # True si cambió la ruta

        # Referencias a widgets para actualización de texto
        self.widget_refs = {}

        # Configurar tema
        ThemeManager.configure_ctk()

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._create_dialog()

    def _create_dialog(self):
        """Crea el diálogo de confirmación de base de datos"""

        # Ventana principal
        self.root = ctk.CTk()
        self.root.title(get_text("database_confirmation.title"))
        self.root.geometry("550x600")
        self.root.resizable(False, False)
        self.root.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Centrar ventana
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f"550x600+{x}+{y}")

        # Prevenir cierre de ventana sin confirmación
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Frame principal
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)

        # Header con título
        self._create_header(main_frame)

        # Mensajes multiidioma
        self._create_multilingual_messages(main_frame)

        # Área de ruta actual
        self._create_current_path_area(main_frame)

        # Botones de acción
        self._create_action_buttons(main_frame)

    def _create_header(self, parent):
        """Crea el header del diálogo"""

        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 30))

        # Título principal
        self.widget_refs['title_label'] = ctk.CTkLabel(
            header_frame,
            text=get_text("database_confirmation.main_title"),
            **ThemeManager.get_label_style('title')
        )
        self.widget_refs['title_label'].pack(pady=(0, 10))

        # Subtítulo
        self.widget_refs['subtitle_label'] = ctk.CTkLabel(
            header_frame,
            text=get_text("database_confirmation.subtitle"),
            font=ThemeManager.FONTS['subtitle'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.widget_refs['subtitle_label'].pack()

    def _create_multilingual_messages(self, parent):
        """Crea los mensajes en el idioma actual"""

        # Card contenedor
        messages_card = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        messages_card.pack(fill="x", pady=(0, 25))

        # Header de la card
        self.widget_refs['card_header'] = ctk.CTkLabel(
            messages_card,
            text=get_text("database_confirmation.current_location_title"),
            **ThemeManager.get_label_style('heading')
        )
        self.widget_refs['card_header'].pack(pady=(20, 15))

        # Mensaje en el idioma actual
        self.widget_refs['message_label'] = ctk.CTkLabel(
            messages_card,
            text=get_text("database_confirmation.message"),
            **ThemeManager.get_label_style('body'),
            anchor="w"
        )
        self.widget_refs['message_label'].pack(fill="x", padx=20, pady=(0, 15))

    def _create_current_path_area(self, parent):
        """Crea el área que muestra la ruta actual"""

        # Card para ruta actual
        path_card = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        path_card.pack(fill="x", pady=(0, 25))

        # Título de la sección
        self.widget_refs['section_title'] = ctk.CTkLabel(
            path_card,
            text=get_text("database_confirmation.path_section_title"),
            **ThemeManager.get_label_style('heading')
        )
        self.widget_refs['section_title'].pack(pady=(20, 15))

        # Frame para la ruta
        path_container = ctk.CTkFrame(path_card, fg_color=ThemeManager.COLORS['bg_secondary'])
        path_container.pack(fill="x", padx=20, pady=(0, 15))

        # Entry para mostrar ruta (solo lectura)
        entry_style = ThemeManager.get_entry_style()
        self.path_entry = ctk.CTkEntry(
            path_container,
            state="readonly",
            **entry_style
        )
        self.path_entry.pack(fill="x", padx=15, pady=15)

        # Mostrar ruta actual
        self.path_entry.configure(state="normal")
        self.path_entry.delete(0, 'end')
        self.path_entry.insert(0, self.current_path)
        self.path_entry.configure(state="readonly")

        # Botón para cambiar ruta
        change_style = ThemeManager.get_button_style()
        self.widget_refs['change_button'] = ctk.CTkButton(
            path_card,
            text=get_text("database_confirmation.change_button"),
            command=self._browse_folder,
            **change_style,
            width=250
        )
        self.widget_refs['change_button'].pack(pady=(0, 20))

        # Estado de validación
        self.status_label = ctk.CTkLabel(
            path_card,
            text=get_text("database_confirmation.valid_location"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['success']
        )
        self.status_label.pack(pady=(0, 15))

    def _create_action_buttons(self, parent):
        """Crea los botones de acción"""

        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 5))

        # Botón Cancelar
        cancel_style = ThemeManager.get_button_style()
        self.widget_refs['cancel_button'] = ctk.CTkButton(
            button_frame,
            text=get_text("database_confirmation.cancel_button"),
            command=self._on_cancel,
            **cancel_style,
            width=200
        )
        self.widget_refs['cancel_button'].pack(side="left", padx=(0, 10))

        # Botón OK/Confirmar
        ok_style = ThemeManager.get_button_style()
        ok_style['fg_color'] = ThemeManager.COLORS['success']
        ok_style['hover_color'] = '#45A049'
        self.ok_button = ctk.CTkButton(
            button_frame,
            text=get_text("database_confirmation.ok_button"),
            command=self._on_ok,
            **ok_style,
            width=200
        )
        self.ok_button.pack(side="right")

    def _browse_folder(self):
        """Abre el explorador para seleccionar una carpeta"""

        folder_path = filedialog.askdirectory(
            title=get_text("database_confirmation.select_folder_title"),
            initialdir=self.selected_path if self.selected_path else os.path.expanduser("~")
        )

        if folder_path:
            self.selected_path = folder_path
            self.path_changed = True

            # Actualizar entry
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, folder_path)
            self.path_entry.configure(state="readonly")

            # Validar ruta
            if os.path.exists(folder_path):
                self.status_label.configure(
                    text=get_text("database_confirmation.valid_location"),
                    text_color=ThemeManager.COLORS['success']
                )
                self.ok_button.configure(state="normal")
            else:
                self.status_label.configure(
                    text=get_text("database_confirmation.invalid_location"),
                    text_color=ThemeManager.COLORS['error']
                )
                self.ok_button.configure(state="disabled")

    def _on_ok(self):
        """Confirmar y cerrar el diálogo"""

        if not self.selected_path or not os.path.exists(self.selected_path):
            messagebox.showerror(
                get_text("database_confirmation.invalid_path_title"),
                get_text("database_confirmation.invalid_path_message")
            )
            return

        self.dialog_result = True
        self.root.quit()
        self.root.destroy()

    def _on_cancel(self):
        """Cancelar y cerrar el diálogo"""

        result = messagebox.askyesno(
            get_text("database_confirmation.cancel_confirm_title"),
            get_text("database_confirmation.cancel_confirm_message")
        )

        if result:
            self.dialog_result = False
            self.root.quit()
            self.root.destroy()

    def _update_texts(self):
        """Actualiza todos los textos cuando cambia el idioma"""

        # Actualizar título de la ventana
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.title(get_text("database_confirmation.title"))

        # Actualizar labels
        if 'title_label' in self.widget_refs:
            self.widget_refs['title_label'].configure(text=get_text("database_confirmation.main_title"))
        if 'subtitle_label' in self.widget_refs:
            self.widget_refs['subtitle_label'].configure(text=get_text("database_confirmation.subtitle"))
        if 'card_header' in self.widget_refs:
            self.widget_refs['card_header'].configure(text=get_text("database_confirmation.current_location_title"))
        if 'message_label' in self.widget_refs:
            self.widget_refs['message_label'].configure(text=get_text("database_confirmation.message"))
        if 'section_title' in self.widget_refs:
            self.widget_refs['section_title'].configure(text=get_text("database_confirmation.path_section_title"))

        # Actualizar botones
        if 'change_button' in self.widget_refs:
            self.widget_refs['change_button'].configure(text=get_text("database_confirmation.change_button"))
        if 'cancel_button' in self.widget_refs:
            self.widget_refs['cancel_button'].configure(text=get_text("database_confirmation.cancel_button"))
        if hasattr(self, 'ok_button'):
            self.ok_button.configure(text=get_text("database_confirmation.ok_button"))

        # Actualizar status label (solo si es válido)
        if hasattr(self, 'status_label') and hasattr(self, 'selected_path'):
            if os.path.exists(self.selected_path):
                self.status_label.configure(text=get_text("database_confirmation.valid_location"))
            else:
                self.status_label.configure(text=get_text("database_confirmation.invalid_location"))

    def show(self):
        """Muestra el diálogo y espera resultado"""
        self.root.mainloop()
        return self.dialog_result, self.selected_path, self.path_changed
