import customtkinter as ctk
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes


class DatabaseProcessingDialog(ctk.CTkToplevel):
    """
    Ventana modal para mostrar el progreso del procesamiento de la base de datos.
    Bloquea la interacción con toda la aplicación durante el procesamiento.
    """

    def __init__(self, parent, total_rasters):
        super().__init__(parent)

        self.total_rasters = total_rasters
        self.current_index = 0
        self.current_raster_name = ""
        self.is_processing = True

        # Referencias a widgets para actualización
        self.widget_refs = {}

        # Configurar ventana
        self.title(get_text("database_processing.processing_title"))
        self.geometry("500x250")
        self.resizable(False, False)
        self.transient(parent)
        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Centrar ventana
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (250 // 2)
        self.geometry(f"500x250+{x}+{y}")

        # No permitir cerrar la ventana durante el procesamiento
        self.protocol("WM_DELETE_WINDOW", self._on_closing_attempt)

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Renderizar ventana antes de continuar
        self.update()
        self.grab_set()  # Bloquear interacción con otras ventanas

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # Mensaje principal
        self.widget_refs['main_message'] = ctk.CTkLabel(
            main_frame,
            text=get_text("database_processing.processing_message"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_primary'],
            justify="center"
        )
        self.widget_refs['main_message'].pack(pady=(10, 20))

        # Frame para información de raster actual
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 15))

        # Label "Procesando:"
        self.widget_refs['processing_label'] = ctk.CTkLabel(
            info_frame,
            text=get_text("database_processing.current_raster"),
            font=ThemeManager.FONTS['button'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.widget_refs['processing_label'].pack(anchor="w")

        # Nombre del raster actual
        self.widget_refs['raster_name'] = ctk.CTkLabel(
            info_frame,
            text="---",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.widget_refs['raster_name'].pack(anchor="w", pady=(5, 0))

        # Barra de progreso determinada
        self.progress_bar = ctk.CTkProgressBar(
            main_frame,
            mode="determinate",
            width=400,
            height=20
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)  # Iniciar en 0%

        # Label de progreso (X de Y rasters)
        self.widget_refs['progress_label'] = ctk.CTkLabel(
            main_frame,
            text=get_text("database_processing.progress_label").format(0, self.total_rasters),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.widget_refs['progress_label'].pack(pady=(5, 0))

    def update_progress(self, raster_name, index):
        """
        Actualiza el progreso del procesamiento

        Args:
            raster_name: Nombre del raster que se está procesando
            index: Índice del raster actual (0-based)
        """
        self.current_raster_name = raster_name
        self.current_index = index + 1  # Convertir a 1-based para mostrar

        # Actualizar nombre del raster
        self.widget_refs['raster_name'].configure(text=raster_name)

        # Actualizar barra de progreso
        progress_value = self.current_index / self.total_rasters
        self.progress_bar.set(progress_value)

        # Actualizar label de progreso
        self.widget_refs['progress_label'].configure(
            text=get_text("database_processing.progress_label").format(
                self.current_index,
                self.total_rasters
            )
        )

        # Forzar actualización de la ventana
        self.update()

    def finish_processing(self):
        """Marca el procesamiento como finalizado y permite cerrar la ventana"""
        self.is_processing = False
        self.grab_release()

    def _on_closing_attempt(self):
        """Maneja el intento de cerrar la ventana durante el procesamiento"""
        if self.is_processing:
            # No permitir cerrar durante el procesamiento
            # Opcionalmente mostrar un mensaje
            pass
        else:
            self.destroy()

    def _update_texts(self):
        """Actualiza todos los textos cuando cambia el idioma"""

        # Actualizar título de la ventana
        if self.winfo_exists():
            self.title(get_text("database_processing.processing_title"))

        # Actualizar labels
        if 'main_message' in self.widget_refs:
            self.widget_refs['main_message'].configure(
                text=get_text("database_processing.processing_message")
            )
        if 'processing_label' in self.widget_refs:
            self.widget_refs['processing_label'].configure(
                text=get_text("database_processing.current_raster")
            )
        if 'progress_label' in self.widget_refs:
            self.widget_refs['progress_label'].configure(
                text=get_text("database_processing.progress_label").format(
                    self.current_index if self.current_index > 0 else 0,
                    self.total_rasters
                )
            )
