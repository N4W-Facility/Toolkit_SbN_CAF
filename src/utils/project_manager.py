import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from .sbn_prioritization import SbNPrioritization

class ProjectManager:
    
    @staticmethod
    def create_project_template() -> Dict[str, Any]:
        return {
            "project_info": {
                "name": "",
                "acronym": "",
                "description": "",
                "location": "",
                "objective": "",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "last_modified": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0"
            },
            "files": {
                "watershed_shapefile": "",
                "dem_raster": "",
                "project_folder": ""
            },
            "watershed_data": {
                "coordinates": {
                    "latitude": None,
                    "longitude": None
                },
                "morphometry": {
                    "area": None,
                    "perimeter": None,
                    "min_elevation": None,
                    "max_elevation": None,
                    "avg_slope": None
                },
                "climate": {
                    "precipitation": None,
                    "temperature": None
                },
                "hydrology": {
                    "avg_flow": None,
                    "flood_risk": "",
                    "water_stress": ""
                },
                "nutrients": {
                    "sediments": None,
                    "phosphorus": None,
                    "nitrogen": None
                }
            },
            "sbn_analysis": {
                "selected_solutions": [],
                "scenarios": [],
                "results": {}
            },
            "workflow_progress": {
                "cuenca": {"completed": False, "data": None, "order": 1, "enabled": True},
                "barreras": {"completed": False, "data": None, "order": 2, "enabled": False},
                "water_security": {"completed": False, "data": None, "order": 3, "enabled": False},
                "other_challenges": {"completed": False, "data": None, "order": 4, "enabled": False},
                "sbn": {"completed": False, "data": None, "order": 5, "enabled": False},
                "reporte": {"completed": False, "data": None, "order": 6, "enabled": False}
            }
        }
    
    @staticmethod
    def save_project(project_data: Dict[str, Any], file_path: str) -> bool:
        try:
            project_data["project_info"]["last_modified"] = datetime.now().strftime("%Y-%m-%d")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def load_project(file_path: str) -> Optional[Dict[str, Any]]:
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Actualizar la ruta del proyecto a la ubicación real del JSON
            actual_project_folder = os.path.dirname(file_path)
            # Normalizar para formato Windows
            actual_project_folder = os.path.normpath(actual_project_folder)

            if 'files' not in project_data:
                project_data['files'] = {}

            project_data['files']['project_folder'] = actual_project_folder

            # Guardar inmediatamente el JSON con la ruta actualizada
            ProjectManager.save_project(project_data, file_path)

            return project_data
        except Exception as e:
            return None
    
    @staticmethod
    def create_project_folder(base_path: str) -> str:
        project_folder = os.path.join(base_path)
        
        folders = [
            project_folder,
            os.path.join(project_folder, "01-Watershed"),
            os.path.join(project_folder, "02-Rasters"),
            os.path.join(project_folder, "03-SbN")
        ]
        
        for folder in folders:
            os.makedirs(folder, exist_ok=True)

        # Copiar template de SbN_Prioritization.csv al nuevo proyecto
        try:
            SbNPrioritization.copy_template_to_project(project_folder)
        except Exception as e:
            print(f"Warning: No se pudo copiar SbN_Prioritization.csv template: {e}")

        return project_folder
    
    @staticmethod
    def validate_project(project_data: Dict[str, Any]) -> bool:
        required_keys = ["project_info", "files", "watershed_data", "sbn_analysis"]
        return all(key in project_data for key in required_keys)
    
    @staticmethod
    def get_project_json_path(project_folder: str) -> str:
        return os.path.join(project_folder, "project.json")
    
    @staticmethod
    def update_project_data(project_data: Dict[str, Any], section: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if section in project_data:
            if isinstance(project_data[section], dict) and isinstance(data, dict):
                project_data[section].update(data)
            else:
                project_data[section] = data
        
        project_data["project_info"]["last_modified"] = datetime.now().strftime("%Y-%m-%d")
        return project_data