import customtkinter as ctk
from tkinter import messagebox
import os
import csv
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes

class SbNSelectionWindow(ctk.CTkToplevel):
    """Ventana para seleccionar SbN que se incluirán en el reporte"""

    def __init__(self, parent, project_path=None, callback=None):
        super().__init__(parent)

        self.parent = parent
        self.project_path = project_path
        self.callback = callback  # Función a llamar después de guardar

        self.title(get_text("sbn_selection.title"))
        self.geometry("600x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Lista de SbN con iconos
        self.sbn_list = [
            {'id': 1, 'icon': '🌲'},
            {'id': 2, 'icon': '🌱'},
            {'id': 3, 'icon': '🌿'},
            {'id': 4, 'icon': '🔄'},
            {'id': 5, 'icon': '🏞️'},
            {'id': 6, 'icon': '🌊'},
            {'id': 7, 'icon': '💧'},
            {'id': 8, 'icon': '🌾'},
            {'id': 9, 'icon': '🌿'},
            {'id': 10, 'icon': '🏞️'},
            {'id': 11, 'icon': '🦆'},
            {'id': 12, 'icon': '🌧️'},
            {'id': 13, 'icon': '🚰'},
            {'id': 14, 'icon': '🌳'},
            {'id': 15, 'icon': '🏞️'},
            {'id': 16, 'icon': '🧱'},
            {'id': 17, 'icon': '🌲'},
            {'id': 18, 'icon': '🏠'},
            {'id': 19, 'icon': '🚴'},
            {'id': 20, 'icon': '🌾'},
            {'id': 21, 'icon': '💧'}
        ]

        # Diccionario para guardar los checkboxes
        self.checkboxes = {}
        self.checkbox_vars = {}

        # Referencias a widgets para actualización de texto
        self.widget_refs = {}

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()
        self._load_selection()

        # Sincronizar con el idioma actual
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        """Configurar la interfaz de usuario"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        title_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack()
        self.widget_refs['title'] = title_label

        description_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=550
        )
        description_label.pack(pady=(5, 0))
        self.widget_refs['description'] = description_label

        # Frame con scroll para los checkboxes
        scrollable_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color=ThemeManager.COLORS['bg_secondary'],
            corner_radius=10
        )
        scrollable_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Botón "Seleccionar todas"
        select_all_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        select_all_frame.pack(fill="x", padx=10, pady=(10, 5))

        select_all_btn = ctk.CTkButton(
            select_all_frame,
            text="",
            command=self._select_all,
            font=ThemeManager.FONTS['body'],
            fg_color=ThemeManager.COLORS['accent_secondary'],
            hover_color=ThemeManager.COLORS['accent_primary'],
            width=120
        )
        select_all_btn.pack(side="left", padx=5)
        self.widget_refs['select_all'] = select_all_btn

        deselect_all_btn = ctk.CTkButton(
            select_all_frame,
            text="",
            command=self._deselect_all,
            font=ThemeManager.FONTS['body'],
            fg_color=ThemeManager.COLORS['accent_secondary'],
            hover_color=ThemeManager.COLORS['accent_primary'],
            width=120
        )
        deselect_all_btn.pack(side="left", padx=5)
        self.widget_refs['deselect_all'] = deselect_all_btn

        # Crear checkboxes para cada SbN
        for sbn in self.sbn_list:
            sbn_id = sbn['id']
            var = ctk.BooleanVar(value=False)
            self.checkbox_vars[sbn_id] = var

            checkbox = ctk.CTkCheckBox(
                scrollable_frame,
                text=f"{sbn['icon']} {get_text(f'sbn_solutions.{sbn_id}')}",
                variable=var,
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['text_primary'],
                fg_color=ThemeManager.COLORS['accent_primary'],
                hover_color=ThemeManager.COLORS['accent_secondary'],
                checkmark_color=ThemeManager.COLORS['text_primary']
            )
            checkbox.pack(fill="x", padx=10, pady=5)
            self.checkboxes[sbn_id] = checkbox

        # Botones de acción
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="",
            command=self._on_closing,
            font=ThemeManager.FONTS['body'],
            fg_color=ThemeManager.COLORS['error'],
            hover_color="#D32F2F",
            width=150
        )
        cancel_btn.pack(side="left", padx=5)
        self.widget_refs['cancel'] = cancel_btn

        save_btn = ctk.CTkButton(
            button_frame,
            text="",
            command=self._save_and_continue,
            font=ThemeManager.FONTS['body'],
            fg_color=ThemeManager.COLORS['success'],
            hover_color="#388E3C",
            width=150
        )
        save_btn.pack(side="right", padx=5)
        self.widget_refs['save'] = save_btn

    def _update_texts(self):
        """Actualizar todos los textos según el idioma actual"""
        self.title(get_text("sbn_selection.title"))
        self.widget_refs['title'].configure(text=get_text("sbn_selection.main_title"))
        self.widget_refs['description'].configure(text=get_text("sbn_selection.description"))
        self.widget_refs['select_all'].configure(text=get_text("sbn_selection.select_all"))
        self.widget_refs['deselect_all'].configure(text=get_text("sbn_selection.deselect_all"))
        self.widget_refs['cancel'].configure(text=get_text("sbn_selection.cancel"))
        self.widget_refs['save'].configure(text=get_text("sbn_selection.save"))

        # Actualizar textos de checkboxes
        for sbn_id, checkbox in self.checkboxes.items():
            icon = next(s['icon'] for s in self.sbn_list if s['id'] == sbn_id)
            checkbox.configure(text=f"{icon} {get_text(f'sbn_solutions.{sbn_id}')}")

    def _select_all(self):
        """Seleccionar todas las SbN"""
        for var in self.checkbox_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Deseleccionar todas las SbN"""
        for var in self.checkbox_vars.values():
            var.set(False)

    def _load_selection(self):
        """Cargar la selección guardada desde el CSV si existe, o crear uno por defecto"""
        if not self.project_path:
            return

        csv_path = os.path.join(self.project_path, "SbN_Select.csv")

        # Si no existe, crear archivo por defecto con todas las SbN deseleccionadas
        if not os.path.exists(csv_path):
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['sbn_id', 'selected'])
                    for sbn_id in range(1, 22):  # 21 SbN
                        writer.writerow([sbn_id, False])
                print(f"Created default SbN_Select.csv")
            except Exception as e:
                print(f"Error creating default SbN selection: {e}")
            return

        # Cargar selección existente
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sbn_id = int(row['sbn_id'])
                    selected = row['selected'].lower() == 'true'
                    if sbn_id in self.checkbox_vars:
                        self.checkbox_vars[sbn_id].set(selected)
        except Exception as e:
            print(f"Error loading SbN selection: {e}")

    def _save_selection(self):
        """Guardar la selección en el CSV"""
        if not self.project_path:
            messagebox.showerror(
                get_text("messages.error"),
                get_text("sbn_selection.no_project_path")
            )
            return False

        csv_path = os.path.join(self.project_path, "SbN_Select.csv")

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['sbn_id', 'selected'])

                for sbn_id in sorted(self.checkbox_vars.keys()):
                    selected = self.checkbox_vars[sbn_id].get()
                    writer.writerow([sbn_id, selected])

            return True
        except Exception as e:
            messagebox.showerror(
                get_text("messages.error"),
                f"{get_text('sbn_selection.save_error')}\n{str(e)}"
            )
            return False

    def _save_and_continue(self):
        """Guardar y continuar con el reporte"""
        # Verificar que al menos una SbN esté seleccionada
        selected_count = sum(1 for var in self.checkbox_vars.values() if var.get())

        if selected_count == 0:
            messagebox.showwarning(
                get_text("messages.warning"),
                get_text("sbn_selection.no_selection")
            )
            return

        if self._save_selection():
            messagebox.showinfo(
                get_text("messages.success"),
                get_text("sbn_selection.save_success").format(selected_count)
            )

            # Llamar al callback si existe (para generar el reporte)
            if self.callback:
                self.callback()

            self.destroy()

    def _on_closing(self):
        """Manejar el cierre de la ventana"""
        self.destroy()
