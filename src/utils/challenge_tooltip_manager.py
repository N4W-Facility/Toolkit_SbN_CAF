import os
import pandas as pd
from ..core.language_manager import get_current_language
from .resource_path import get_resource_path


class ChallengeTooltipManager:
    """
    Gestor de tooltips para desafíos de seguridad hídrica y otros desafíos.
    Carga descripciones desde CSV según el idioma actual.
    """

    _instance = None
    _tooltips_data = None

    def __new__(cls):
        """Singleton para evitar cargar CSV múltiples veces"""
        if cls._instance is None:
            cls._instance = super(ChallengeTooltipManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializa el gestor"""
        if self._tooltips_data is None:
            self.load_tooltips()

    def load_tooltips(self):
        """Carga tooltips desde CSV según idioma actual"""
        try:
            # Obtener idioma actual
            current_lang = get_current_language()

            # Construir nombre del archivo CSV (Windows path)
            csv_filename = f"TooltipsChallenges_{current_lang}.csv"
            csv_path = get_resource_path(os.path.join('locales', csv_filename))

            if not os.path.exists(csv_path):
                print(f"⚠️ Archivo de tooltips no encontrado: {csv_path}")
                self._tooltips_data = {}
                return

            # Leer CSV con pandas
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # Convertir a diccionario {Code: Description}
            self._tooltips_data = {}
            for _, row in df.iterrows():
                code = str(row['Code']).strip() if pd.notna(row['Code']) else None
                desc = str(row['Description']).strip() if pd.notna(row['Description']) else None

                if code and desc:
                    self._tooltips_data[code] = desc

            print(f"✓ Tooltips de desafíos cargados: {len(self._tooltips_data)} descripciones ({current_lang})")

        except Exception as e:
            print(f"⚠️ Error cargando tooltips de desafíos: {e}")
            self._tooltips_data = {}

    def get_tooltip(self, challenge_code):
        """
        Obtiene el tooltip para un código de desafío.

        Args:
            challenge_code: Código del desafío (ej: 'WS01', 'OC03')

        Returns:
            str: Descripción del tooltip, o None si no existe
        """
        if self._tooltips_data is None:
            self.load_tooltips()

        return self._tooltips_data.get(challenge_code)

    def reload_tooltips(self):
        """Recarga tooltips (útil cuando cambia el idioma)"""
        self._tooltips_data = None
        self.load_tooltips()

    def get_all_tooltips(self):
        """Retorna todos los tooltips cargados"""
        if self._tooltips_data is None:
            self.load_tooltips()

        return self._tooltips_data.copy()


# Función de conveniencia para obtener tooltip directamente
def get_challenge_tooltip(challenge_code):
    """
    Obtiene el tooltip de un desafío.

    Args:
        challenge_code: Código del desafío (ej: 'WS01', 'OC03')

    Returns:
        str: Descripción del tooltip
    """
    manager = ChallengeTooltipManager()
    return manager.get_tooltip(challenge_code)
