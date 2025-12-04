# -*- coding: utf-8 -*-
"""
Screen Adapter Utility
Detecta el tamaño de pantalla y calcula dimensiones adaptativas para ventanas y componentes.
Compatible con Windows.
"""

import tkinter as tk
from typing import Tuple, Dict


class ScreenAdapter:
    """Gestor de adaptación de pantalla para la aplicación."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton para mantener una única instancia."""
        if cls._instance is None:
            cls._instance = super(ScreenAdapter, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializa el adaptador de pantalla."""
        if not ScreenAdapter._initialized:
            self.screen_width = 1920
            self.screen_height = 1080
            self.dpi_scale = 1.0
            self._detect_screen_size()
            ScreenAdapter._initialized = True

    def _detect_screen_size(self):
        """Detecta el tamaño de la pantalla principal en Windows."""
        try:
            # Crear ventana temporal para obtener dimensiones de pantalla
            root = tk.Tk()
            root.withdraw()  # Ocultar ventana

            # Obtener dimensiones de pantalla
            self.screen_width = root.winfo_screenwidth()
            self.screen_height = root.winfo_screenheight()

            # Obtener DPI scaling (importante en Windows con scaling 125%, 150%, etc.)
            try:
                self.dpi_scale = root.tk.call('tk', 'scaling')
            except:
                self.dpi_scale = 1.0

            root.destroy()

            print(f"✓ Pantalla detectada: {self.screen_width}x{self.screen_height} (DPI scale: {self.dpi_scale:.2f})")

        except Exception as e:
            print(f"⚠️ Error detectando pantalla, usando valores por defecto: {e}")
            self.screen_width = 1920
            self.screen_height = 1080
            self.dpi_scale = 1.0

    def get_window_dimensions(self,
                             desired_width: int,
                             desired_height: int,
                             width_percent: float = 0.75,
                             height_percent: float = 0.80,
                             min_width: int = 600,
                             min_height: int = 500,
                             max_width: int = None,
                             max_height: int = None) -> Tuple[int, int]:
        """
        Calcula dimensiones adaptativas para una ventana.

        Args:
            desired_width: Ancho deseado en píxeles
            desired_height: Alto deseado en píxeles
            width_percent: Porcentaje máximo del ancho de pantalla (0.0-1.0)
            height_percent: Porcentaje máximo del alto de pantalla (0.0-1.0)
            min_width: Ancho mínimo permitido
            min_height: Alto mínimo permitido
            max_width: Ancho máximo permitido (None = sin límite)
            max_height: Alto máximo permitido (None = sin límite)

        Returns:
            Tupla (width, height) con las dimensiones calculadas
        """
        # Calcular dimensiones máximas basadas en pantalla
        max_allowed_width = int(self.screen_width * width_percent)
        max_allowed_height = int(self.screen_height * height_percent)

        # Determinar ancho
        width = min(desired_width, max_allowed_width)
        if max_width:
            width = min(width, max_width)
        width = max(width, min_width)

        # Determinar alto
        height = min(desired_height, max_allowed_height)
        if max_height:
            height = min(height, max_height)
        height = max(height, min_height)

        return (width, height)

    def get_panel_width(self,
                       desired_width: int,
                       parent_width: int = None,
                       width_percent: float = 0.30,
                       min_width: int = 300,
                       max_width: int = 500) -> int:
        """
        Calcula el ancho adaptativo para un panel lateral.

        Args:
            desired_width: Ancho deseado en píxeles
            parent_width: Ancho de la ventana padre (None = usar ancho de pantalla)
            width_percent: Porcentaje del ancho del padre (0.0-1.0)
            min_width: Ancho mínimo permitido
            max_width: Ancho máximo permitido

        Returns:
            Ancho calculado en píxeles
        """
        if parent_width is None:
            parent_width = self.screen_width

        # Calcular como porcentaje del padre
        calculated_width = int(parent_width * width_percent)

        # Aplicar límites
        width = max(min_width, min(calculated_width, max_width))

        return width

    def get_button_width(self, button_type: str = 'normal') -> int:
        """
        Calcula el ancho adaptativo para botones según el tamaño de pantalla.

        Args:
            button_type: Tipo de botón ('small', 'normal', 'large', 'wide')

        Returns:
            Ancho del botón en píxeles
        """
        # Definir anchos base según tipo
        base_widths = {
            'small': 100,
            'normal': 120,
            'large': 150,
            'wide': 200
        }

        base_width = base_widths.get(button_type, 120)

        # Ajustar según resolución de pantalla
        if self.screen_width >= 1920:
            # Pantallas grandes (Full HD o superior)
            multiplier = 1.2
        elif self.screen_width >= 1600:
            # Pantallas medianas-grandes
            multiplier = 1.1
        elif self.screen_width >= 1366:
            # Pantallas medianas (laptop estándar)
            multiplier = 1.0
        else:
            # Pantallas pequeñas
            multiplier = 0.9

        return int(base_width * multiplier)

    def is_small_screen(self) -> bool:
        """
        Determina si la pantalla se considera pequeña.

        Returns:
            True si la pantalla es pequeña (menor a 1366x768)
        """
        return self.screen_width < 1366 or self.screen_height < 768

    def is_large_screen(self) -> bool:
        """
        Determina si la pantalla se considera grande.

        Returns:
            True si la pantalla es grande (1920x1080 o superior)
        """
        return self.screen_width >= 1920 and self.screen_height >= 1080

    def get_screen_category(self) -> str:
        """
        Categoriza el tamaño de pantalla.

        Returns:
            Categoría: 'small', 'medium', 'large', o 'xlarge'
        """
        if self.screen_width < 1366 or self.screen_height < 768:
            return 'small'
        elif self.screen_width < 1600 or self.screen_height < 900:
            return 'medium'
        elif self.screen_width < 2560 or self.screen_height < 1440:
            return 'large'
        else:
            return 'xlarge'

    def get_info(self) -> Dict[str, any]:
        """
        Obtiene información completa sobre la pantalla.

        Returns:
            Diccionario con información de pantalla
        """
        return {
            'width': self.screen_width,
            'height': self.screen_height,
            'dpi_scale': self.dpi_scale,
            'category': self.get_screen_category(),
            'is_small': self.is_small_screen(),
            'is_large': self.is_large_screen()
        }


# Instancia global singleton
_screen_adapter = None

def get_screen_adapter() -> ScreenAdapter:
    """
    Obtiene la instancia global del ScreenAdapter.

    Returns:
        Instancia de ScreenAdapter
    """
    global _screen_adapter
    if _screen_adapter is None:
        _screen_adapter = ScreenAdapter()
    return _screen_adapter
