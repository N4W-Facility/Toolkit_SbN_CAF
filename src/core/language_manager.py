
# -*- coding: utf-8 -*-
import json
import os
from typing import Dict, List, Callable, Any
from src.utils.resource_path import get_resource_path

# Variable global como fuente de verdad del idioma actual
CURRENT_LANGUAGE = "es"

class LanguageManager:
    """
    Singleton para manejar la internacionalización de la aplicación.
    Soporta Español, Inglés y Portugués.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            global CURRENT_LANGUAGE
            self._current_language = CURRENT_LANGUAGE  # Sincronizar con variable global
            self._translations: Dict[str, Dict] = {}
            self._subscribers: List[Callable] = []
            self._available_languages = {
                'es': {'name': 'Español', 'flag': '🇪🇸'},
                'en': {'name': 'English', 'flag': '🇺🇸'},
                'pt': {'name': 'Português', 'flag': '🇧🇷'}
            }
            self._load_all_translations()
            LanguageManager._initialized = True

    def _load_all_translations(self):
        """Cargar todos los archivos de traducción"""
        for lang_code in self._available_languages.keys():
            file_path = get_resource_path(os.path.join('locales', f'{lang_code}.json'))
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation file {file_path}: {e}")
                    self._translations[lang_code] = {}
            else:
                print(f"Translation file not found: {file_path}")
                self._translations[lang_code] = {}

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Obtener lista de idiomas disponibles"""
        return self._available_languages.copy()

    def get_current_language(self) -> str:
        """Obtener el idioma actual"""
        global CURRENT_LANGUAGE
        return CURRENT_LANGUAGE

    def set_language(self, language_code: str):
        """Cambiar el idioma actual"""
        if language_code in self._available_languages:
            global CURRENT_LANGUAGE
            if CURRENT_LANGUAGE != language_code:
                CURRENT_LANGUAGE = language_code
                self._current_language = language_code
                self._save_language_preference()
                self._notify_subscribers()
        else:
            raise ValueError(f"Language '{language_code}' not supported")

    def get(self, key: str, fallback: str = None) -> str:
        """
        Obtener texto traducido usando notación de puntos.
        Ejemplo: get('startup.title') -> obtiene translations['startup']['title']
        """
        global CURRENT_LANGUAGE
        keys = key.split('.')
        current_dict = self._translations.get(CURRENT_LANGUAGE, {})

        # Navegar por la estructura anidada
        for k in keys:
            if isinstance(current_dict, dict) and k in current_dict:
                current_dict = current_dict[k]
            else:
                # Si no se encuentra, intentar con español como fallback
                if self._current_language != 'es':
                    fallback_dict = self._translations.get('es', {})
                    for k in keys:
                        if isinstance(fallback_dict, dict) and k in fallback_dict:
                            fallback_dict = fallback_dict[k]
                        else:
                            fallback_dict = None
                            break
                    if isinstance(fallback_dict, str):
                        return fallback_dict

                # Si tampoco está en español, devolver fallback o la clave
                return fallback if fallback is not None else f"[{key}]"

        return current_dict if isinstance(current_dict, str) else f"[{key}]"

    def subscribe(self, callback: Callable):
        """Suscribirse a cambios de idioma"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Desuscribirse de cambios de idioma"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self):
        """Notificar a todos los suscriptores del cambio de idioma"""
        for callback in self._subscribers:
            try:
                callback()
            except Exception as e:
                print(f"Error notifying language change subscriber: {e}")

    def _save_language_preference(self):
        """Guardar la preferencia de idioma (simplificado por ahora)"""
        # TODO: Implementar persistencia en archivo de configuración
        pass

    def _load_language_preference(self):
        """Cargar la preferencia de idioma guardada"""
        # TODO: Implementar carga desde archivo de configuración
        pass

# Instancia global del manager
language_manager = LanguageManager()

# Funciones globales para manejar idioma
def get_current_global_language() -> str:
    """Obtener idioma actual desde variable global"""
    global CURRENT_LANGUAGE
    return CURRENT_LANGUAGE

def set_current_global_language(language_code: str):
    """Establecer idioma actual en variable global"""
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = language_code

# Funciones de conveniencia (mantienen compatibilidad)
def get_text(key: str, fallback: str = None) -> str:
    """Función de conveniencia para obtener texto traducido"""
    return language_manager.get(key, fallback)

def set_language(language_code: str):
    """Función de conveniencia para cambiar idioma"""
    language_manager.set_language(language_code)

def get_current_language() -> str:
    """Función de conveniencia para obtener idioma actual"""
    return get_current_global_language()

def subscribe_to_language_changes(callback: Callable):
    """Función de conveniencia para suscribirse a cambios"""
    language_manager.subscribe(callback)

def get_available_languages() -> Dict[str, Dict[str, str]]:
    """Función de conveniencia para obtener idiomas disponibles"""
    return language_manager.get_available_languages()