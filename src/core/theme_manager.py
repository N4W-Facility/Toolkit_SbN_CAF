import customtkinter as ctk
from src.utils.screen_adapter import get_screen_adapter

class ThemeManager:
    
    COLORS = {
        'bg_primary': '#FFFFFF',
        'bg_secondary': '#E7E7E7',
        'bg_tertiary': '#FFFFFF',
        'bg_sidebar': '#F2F2F2',
        'bg_card': '#FFFFFF',
        'accent_primary': '#2196F3',
        'accent_secondary': '#1976D2',
        'accent_hover': '#1976D2',
        'text_primary': '#1A1A1A',
        'text_secondary': '#666666',
        'text_light': '#999999',
        'border': '#E0E0E0',
        'success': '#4CAF50',
        'success_hover': '#388E3C',
        'warning': '#FF9800',
        'error': '#F44336',
        'error_hover': '#D32F2F',
        'hover': '#E3F2FD',
        'info': '#1A1A1A'
    }
    
    FONTS = {
        'title': ("Segoe UI", 24, "bold"),
        'subtitle': ("Segoe UI", 18, "bold"),
        'heading': ("Segoe UI", 16, "bold"),
        'body': ("Segoe UI", 12),
        'caption': ("Segoe UI", 10),
        'button': ("Segoe UI", 12, "bold")
    }
    
    DIMENSIONS = {
        'sidebar_width': 300,
        'header_height': 60,
        'footer_height': 80,
        'card_padding': 15,
        'button_height': 35,
        'corner_radius': 8,
        'border_width': 1
    }
    
    @classmethod
    def configure_ctk(cls):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
    
    @classmethod
    def get_button_style(cls):
        return {
            'fg_color': cls.COLORS['accent_primary'],
            'hover_color': cls.COLORS['accent_secondary'],
            'text_color': '#FFFFFF',
            'font': cls.FONTS['button'],
            'corner_radius': cls.DIMENSIONS['corner_radius'],
            'height': cls.DIMENSIONS['button_height']
        }
    
    @classmethod
    def get_frame_style(cls):
        return {
            'fg_color': cls.COLORS['bg_card'],
            'border_color': cls.COLORS['border'],
            'border_width': cls.DIMENSIONS['border_width'],
            'corner_radius': cls.DIMENSIONS['corner_radius']
        }
    
    @classmethod
    def get_entry_style(cls):
        return {
            'fg_color': cls.COLORS['bg_card'],
            'border_color': cls.COLORS['border'],
            'text_color': cls.COLORS['text_primary'],
            'font': cls.FONTS['body'],
            'corner_radius': cls.DIMENSIONS['corner_radius']
        }
    
    @classmethod
    def get_label_style(cls, style_type='body'):
        return {
            'text_color': cls.COLORS['text_primary'],
            'font': cls.FONTS[style_type]
        }

    @classmethod
    def get_adaptive_button_width(cls, button_type='normal'):
        """
        Obtiene el ancho adaptativo para un botón según el tamaño de pantalla.

        Args:
            button_type: Tipo de botón ('small', 'normal', 'large', 'wide')

        Returns:
            Ancho del botón en píxeles
        """
        adapter = get_screen_adapter()
        return adapter.get_button_width(button_type)

    @classmethod
    def get_adaptive_button_style(cls, button_type='normal'):
        """
        Obtiene el estilo completo de botón con ancho adaptativo.

        Args:
            button_type: Tipo de botón ('small', 'normal', 'large', 'wide')

        Returns:
            Diccionario con estilos de botón incluyendo width adaptativo
        """
        style = cls.get_button_style()
        style['width'] = cls.get_adaptive_button_width(button_type)
        return style

    @classmethod
    def get_window_dimensions(cls, desired_width, desired_height,
                            width_percent=0.75, height_percent=0.80,
                            min_width=600, min_height=500,
                            max_width=None, max_height=None):
        """
        Calcula dimensiones adaptativas para una ventana.

        Args:
            desired_width: Ancho deseado en píxeles
            desired_height: Alto deseado en píxeles
            width_percent: Porcentaje máximo del ancho de pantalla
            height_percent: Porcentaje máximo del alto de pantalla
            min_width: Ancho mínimo
            min_height: Alto mínimo
            max_width: Ancho máximo (None = sin límite)
            max_height: Alto máximo (None = sin límite)

        Returns:
            Tupla (width, height)
        """
        adapter = get_screen_adapter()
        return adapter.get_window_dimensions(
            desired_width, desired_height,
            width_percent, height_percent,
            min_width, min_height,
            max_width, max_height
        )

    @classmethod
    def get_adaptive_panel_width(cls, desired_width, parent_width=None,
                                 width_percent=0.30, min_width=300, max_width=500):
        """
        Calcula el ancho adaptativo para un panel lateral.

        Args:
            desired_width: Ancho deseado en píxeles
            parent_width: Ancho de la ventana padre (None = usar ancho de pantalla)
            width_percent: Porcentaje del ancho del padre
            min_width: Ancho mínimo
            max_width: Ancho máximo

        Returns:
            Ancho calculado en píxeles
        """
        adapter = get_screen_adapter()
        return adapter.get_panel_width(
            desired_width, parent_width,
            width_percent, min_width, max_width
        )