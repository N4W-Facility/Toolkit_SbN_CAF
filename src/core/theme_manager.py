import customtkinter as ctk

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
        'hover': '#E3F2FD'
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