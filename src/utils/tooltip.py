import customtkinter as ctk
from ..core.theme_manager import ThemeManager


class ToolTip:
    """
    Clase para crear tooltips (textos emergentes) en widgets de CustomTkinter.

    Uso:
        tooltip = ToolTip(widget, "Texto del tooltip")
    """

    def __init__(self, widget, text="", delay=500, wraplength=400):
        """
        Args:
            widget: Widget al que se asociará el tooltip
            text: Texto a mostrar en el tooltip
            delay: Milisegundos antes de mostrar (default 500ms)
            wraplength: Ancho máximo del texto antes de hacer wrap
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tooltip_window = None
        self.timer_id = None

        # Bind eventos del mouse
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Button-1>", self._on_leave)  # Ocultar al hacer click

    def _on_enter(self, event=None):
        """Cuando el mouse entra al widget"""
        self._cancel_timer()
        # Programar mostrar tooltip después del delay
        self.timer_id = self.widget.after(self.delay, self._show_tooltip)

    def _on_leave(self, event=None):
        """Cuando el mouse sale del widget"""
        self._cancel_timer()
        self._hide_tooltip()

    def _cancel_timer(self):
        """Cancela el timer de mostrar tooltip"""
        if self.timer_id:
            self.widget.after_cancel(self.timer_id)
            self.timer_id = None

    def _show_tooltip(self):
        """Muestra el tooltip"""
        if not self.text or self.tooltip_window:
            return

        # Crear ventana toplevel sin decoraciones
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)

        # Evitar que robe foco
        self.tooltip_window.attributes('-topmost', True)

        # Crear label con el texto
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            fg_color=ThemeManager.COLORS['bg_secondary'],
            text_color=ThemeManager.COLORS['text_primary'],
            corner_radius=6,
            padx=12,
            pady=8,
            font=ThemeManager.FONTS['caption'],
            wraplength=self.wraplength,
            justify="left"
        )
        label.pack()

        # Posicionar tooltip cerca del cursor
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10

        # Ajustar si se sale de la pantalla
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        # Esperar a que se actualice el tamaño del tooltip
        self.tooltip_window.update_idletasks()
        tooltip_width = self.tooltip_window.winfo_width()
        tooltip_height = self.tooltip_window.winfo_height()

        # Ajustar posición horizontal si se sale
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 10

        # Ajustar posición vertical si se sale
        if y + tooltip_height > screen_height:
            y = self.widget.winfo_pointery() - tooltip_height - 10

        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        """Oculta el tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, new_text):
        """
        Actualiza el texto del tooltip.
        Útil cuando cambia el idioma.
        """
        self.text = new_text
        # Si el tooltip está visible, ocultarlo (se volverá a mostrar con nuevo texto)
        if self.tooltip_window:
            self._hide_tooltip()
