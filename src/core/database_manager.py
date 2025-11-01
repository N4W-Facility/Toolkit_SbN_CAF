import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

class DatabaseManager:
    """
    Singleton para manejar la configuración y validación de la base de datos.
    Guarda la ruta de la BD de forma transparente para el usuario.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Obtener ruta de AppData\Local para Windows
            local_appdata = os.getenv('LOCALAPPDATA')
            if not local_appdata:
                # Fallback si LOCALAPPDATA no está definido (muy raro en Windows)
                local_appdata = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')

            # Crear carpeta para la aplicación si no existe
            app_config_dir = os.path.join(local_appdata, 'SbN_Toolkit')
            os.makedirs(app_config_dir, exist_ok=True)

            # Ruta completa al archivo de configuración
            self.config_file = os.path.join(app_config_dir, '.database_config')
            self.db_path = None
            self.db_info = {}
            self._load_and_validate()
            DatabaseManager._initialized = True

    def _load_and_validate(self):
        """Carga configuración y valida automáticamente la base de datos"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.db_path = config_data.get('path', '')
                    self.db_info = config_data.get('info', {})

                if not self._validate_database():
                    self.db_path = None
                    self.db_info = {}

            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                self.db_path = None
                self.db_info = {}

    def _validate_database(self) -> bool:
        """Verifica que la base de datos existe y es válida"""
        if not self.db_path:
            return False

        db_path = Path(self.db_path)

        # Verificar que el directorio existe
        if not db_path.exists():
            return False

        # Verificar que es un directorio (asumiendo que la BD es una carpeta)
        if not db_path.is_dir():
            return False

        # Verificaciones adicionales de integridad de BD (opcional)
        # Aquí puedes agregar validaciones específicas para tu BD
        # Por ejemplo, verificar archivos clave, estructura, etc.

        return True

    def needs_database_selection(self) -> bool:
        """Retorna True si necesita que el usuario seleccione la base de datos"""
        return self.db_path is None

    def set_database_path(self, path: str, additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Establece y guarda nueva ruta de base de datos

        Args:
            path: Ruta a la base de datos
            additional_info: Información adicional sobre la BD (opcional)

        Returns:
            bool: True si se guardó exitosamente, False si la ruta no es válida
        """
        path = str(Path(path).resolve())  # Normalizar ruta

        # Verificar que la ruta existe
        if not os.path.exists(path):
            return False

        # Verificar que es un directorio
        if not os.path.isdir(path):
            return False

        self.db_path = path
        self.db_info = additional_info or {}

        # Guardar configuración
        config_data = {
            'path': self.db_path,
            'info': self.db_info,
            'last_updated': str(Path().absolute()),
            'version': '1.0'
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error al guardar configuración de BD: {e}")
            return False

    def get_database_path(self) -> Optional[str]:
        """Retorna la ruta actual de la base de datos"""
        return self.db_path

    def get_database_info(self) -> Dict[str, Any]:
        """Retorna información adicional de la base de datos"""
        return self.db_info.copy()

    def clear_database_config(self):
        """Limpia la configuración de la base de datos"""
        self.db_path = None
        self.db_info = {}

        if os.path.exists(self.config_file):
            try:
                os.remove(self.config_file)
            except Exception as e:
                print(f"Error al eliminar configuración: {e}")

    def is_database_configured(self) -> bool:
        """Retorna True si la base de datos está configurada y es válida"""
        return self.db_path is not None and self._validate_database()

    def reload_database_config(self):
        """Recarga la configuración desde el archivo"""
        self._load_and_validate()