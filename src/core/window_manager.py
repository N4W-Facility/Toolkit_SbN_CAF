import customtkinter as ctk
from typing import Dict, Any, Optional

class WindowManager:
    
    def __init__(self):
        self.windows: Dict[str, ctk.CTkToplevel] = {}
        self.main_window: Optional[ctk.CTk] = None
        self.current_project_data: Dict[str, Any] = {}
    
    def set_main_window(self, window: ctk.CTk):
        self.main_window = window
    
    def open_window(self, window_name: str, window_class, **kwargs):
        if window_name in self.windows:
            self.windows[window_name].lift()
            return self.windows[window_name]
        
        new_window = window_class(self, **kwargs)
        self.windows[window_name] = new_window
        return new_window
    
    def close_window(self, window_name: str):
        if window_name in self.windows:
            self.windows[window_name].destroy()
            del self.windows[window_name]
    
    def close_all_windows(self):
        for window in list(self.windows.values()):
            window.destroy()
        self.windows.clear()
    
    def set_project_data(self, data: Dict[str, Any]):
        self.current_project_data = data
    
    def get_project_data(self) -> Dict[str, Any]:
        return self.current_project_data
    
    def update_project_data(self, key: str, value: Any):
        self.current_project_data[key] = value
    
    def navigate_to(self, window_name: str, **kwargs):
        if self.main_window:
            for window in self.windows.values():
                window.withdraw()

        return self.open_window(window_name, **kwargs)

    def update_workflow_step(self, step_name: str, completed: bool, data: Any = None):
        """Actualiza el estado de un paso del workflow"""
        if hasattr(self.main_window, 'workflow_steps'):
            self.main_window.workflow_steps[step_name] = {
                'completed': completed,
                'data': data
            }
            # Actualizar UI del dashboard si es necesario
            if hasattr(self.main_window, '_update_workflow_ui'):
                self.main_window._update_workflow_ui()