import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from ..core.database_manager import DatabaseManager
from ..core.theme_manager import ThemeManager

class DatabaseSelectionDialog:
    """
    Diálogo para seleccionar la ubicación de la base de datos.
    Se muestra solo cuando no se ha configurado una BD válida.
    Incluye textos en español, inglés y portugués.
    """

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.selected_path = None
        self.dialog_result = False

        # Configurar tema
        ThemeManager.configure_ctk()

        self._create_dialog()

    def _create_dialog(self):
        """Crea el diálogo de selección de base de datos"""

        # Ventana principal
        self.root = ctk.CTk()
        self.root.title("SbN Toolkit")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        self.root.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Centrar ventana
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.root.winfo_screenheight() // 2) - (650 // 2)
        self.root.geometry(f"500x650+{x}+{y}")

        # Prevenir cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Frame principal
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)

        # Header con título
        self._create_header(main_frame)

        # Mensajes multiidioma
        self._create_multilingual_messages(main_frame)

        # Área de selección
        self._create_selection_area(main_frame)

        # Botones de acción
        self._create_action_buttons(main_frame)

    def _create_header(self, parent):
        """Crea el header del diálogo"""

        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 30))

        # Título principal
        title_label = ctk.CTkLabel(
            header_frame,
            text="Database Configuration",
            **ThemeManager.get_label_style('title')
        )
        title_label.pack(pady=(0, 10))

        # Subtítulo
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Configure your spatial database location",
            font=ThemeManager.FONTS['subtitle'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        subtitle_label.pack()

    def _create_multilingual_messages(self, parent):
        """Crea los mensajes en los tres idiomas"""

        # Card contenedor
        messages_card = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        messages_card.pack(fill="x", pady=(0, 25))

        # Header de la card
        card_header = ctk.CTkLabel(
            messages_card,
            text="Select your spatial database folder",
            **ThemeManager.get_label_style('heading')
        )
        card_header.pack(pady=(20, 15))

        # Mensajes por idioma
        languages = [
            ("🇪🇸", "Por favor, seleccione la ubicación de la base de datos espacial"),
            ("🇺🇸", "Please select the spatial database location"),
            ("🇧🇷", "Por favor, selecione a localização da base de dados espacial")
        ]

        for flag, text in languages:
            lang_frame = ctk.CTkFrame(messages_card, fg_color="transparent")
            lang_frame.pack(fill="x", padx=20, pady=3)

            flag_label = ctk.CTkLabel(
                lang_frame,
                text=flag,
                font=ctk.CTkFont(size=16)
            )
            flag_label.pack(side="left", padx=(0, 10))

            text_label = ctk.CTkLabel(
                lang_frame,
                text=text,
                **ThemeManager.get_label_style('body'),
                anchor="w"
            )
            text_label.pack(side="left", fill="x", expand=True)

        # Espaciado inferior
        ctk.CTkLabel(messages_card, text="").pack(pady=(5, 15))

    def _create_selection_area(self, parent):
        """Crea el área de selección de carpeta"""

        # Card para selección
        selection_card = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        selection_card.pack(fill="x", pady=(0, 25))

        # Título de la sección
        section_title = ctk.CTkLabel(
            selection_card,
            text="Database Folder",
            **ThemeManager.get_label_style('heading')
        )
        section_title.pack(pady=(20, 15))

        # Frame para la ruta
        path_container = ctk.CTkFrame(selection_card, fg_color=ThemeManager.COLORS['bg_secondary'])
        path_container.pack(fill="x", padx=20, pady=(0, 15))

        # Entry para mostrar ruta
        entry_style = ThemeManager.get_entry_style()
        self.path_entry = ctk.CTkEntry(
            path_container,
            placeholder_text="No folder selected yet...",
            state="readonly",
            height=40,
            **entry_style
        )
        self.path_entry.pack(fill="x", padx=15, pady=15)

        # Frame para botones lado a lado
        buttons_row = ctk.CTkFrame(selection_card, fg_color="transparent")
        buttons_row.pack(fill="x", padx=20, pady=(0, 20))

        # Botón de selección
        button_style = ThemeManager.get_button_style()
        button_style['height'] = 45
        self.select_button = ctk.CTkButton(
            buttons_row,
            text="📁  Select Folder",
            command=self._select_database_path,
            **button_style
        )
        self.select_button.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Botón continuar (inicialmente deshabilitado)
        continue_style = ThemeManager.get_button_style()
        continue_style['height'] = 45
        continue_style['fg_color'] = ThemeManager.COLORS['success']
        continue_style['hover_color'] = '#45A049'

        self.continue_button = ctk.CTkButton(
            buttons_row,
            text="✓ Continue",
            state="disabled",
            command=self._continue_application,
            **continue_style
        )
        self.continue_button.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _create_action_buttons(self, parent):
        """Crea información adicional"""

        # Información adicional
        info_frame = ctk.CTkFrame(parent, fg_color=ThemeManager.COLORS['bg_secondary'])
        info_frame.pack(fill="x", pady=(20, 0))

        info_label = ctk.CTkLabel(
            info_frame,
            text="The application requires access to a spatial database to function properly.\n"
                 "Please select the folder containing your spatial data files.",
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=400
        )
        info_label.pack(pady=15)

    def _select_database_path(self):
        """Abre el diálogo para seleccionar la carpeta de la base de datos"""

        selected_folder = filedialog.askdirectory(
            title="Select Database Folder / Seleccionar Carpeta de Base de Datos / Selecionar Pasta da Base de Dados",
            mustexist=True
        )

        if selected_folder:
            # Normalizar ruta
            selected_folder = os.path.normpath(selected_folder)

            # Actualizar entry
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected_folder)
            self.path_entry.configure(state="readonly")

            # Guardar ruta seleccionada
            self.selected_path = selected_folder

            # Habilitar botón continuar
            self.continue_button.configure(state="normal")

    def _continue_application(self):
        """Guarda la configuración y continúa con la aplicación"""

        if self.selected_path:
            # Intentar guardar en DatabaseManager
            success = self.db_manager.set_database_path(self.selected_path)

            if success:
                self.dialog_result = True
                self.root.quit()
                self.root.destroy()
            else:
                # Mostrar error
                messagebox.showerror(
                    "Error",
                    "Error al configurar la base de datos.\n"
                    "Error configuring database.\n"
                    "Erro ao configurar a base de dados."
                )
        else:
            messagebox.showwarning(
                "Warning / Advertencia / Aviso",
                "Por favor seleccione una ruta válida.\n"
                "Please select a valid path.\n"
                "Por favor, selecione um caminho válido."
            )

    def _on_closing(self):
        """Maneja el intento de cerrar la ventana"""

        result = messagebox.askyesno(
            "Exit / Salir / Sair",
            "¿Desea salir de la aplicación?\n"
            "Do you want to exit the application?\n"
            "Deseja sair da aplicação?\n\n"
            "La aplicación requiere una base de datos para funcionar.\n"
            "The application requires a database to function.\n"
            "A aplicação requer uma base de dados para funcionar."
        )

        if result:
            self.root.quit()
            self.root.destroy()

    def show(self):
        """Muestra el diálogo y retorna True si se configuró exitosamente"""

        self.root.mainloop()
        return self.dialog_result

def show_database_selection_dialog():
    """
    Función de conveniencia para mostrar el diálogo de selección de BD.
    Retorna True si se configuró exitosamente la base de datos.
    """

    dialog = DatabaseSelectionDialog()
    return dialog.show()

def check_and_configure_database():
    """
    Verifica si la base de datos está configurada.
    Si no lo está, muestra el diálogo de selección.
    Retorna True si la BD está lista para usar.
    """

    db_manager = DatabaseManager()

    if db_manager.needs_database_selection():
        return show_database_selection_dialog()

    return True