import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
import os
from datetime import datetime
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes


class OtherChallengesWindow(ctk.CTk):

    def __init__(self, window_manager=None, project_path=None):
        super().__init__()

        self.window_manager = window_manager
        self.project_path = project_path
        print(f"DEBUG: OtherChallengesWindow recibió project_path: {project_path}")

        # Configuración de la ventana
        self.title(get_text("other_challenges.title"))
        self.geometry("900x650")
        self.resizable(True, True)

        # Aplicar tema
        ThemeManager.configure_ctk()
        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Otros desafíos (25 desafíos)
        self.challenges_data = self._load_challenges_data()

        # Valores actuales de los desafíos
        self.challenge_values = {}

        # Referencias a widgets para actualizaciones
        self.widget_refs = {}
        self.challenge_widgets = {}

        # Estado de carga de datos previos
        self.has_previous_data = False

        # Colores para los niveles de importancia (esquema semáforo)
        # Colores para los niveles de importancia - se obtienen dinámicamente

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()
        self._update_texts()

    def _load_challenges_data(self):
        """Carga los datos de desafíos con traducciones"""
        icons = ['🌍','🌡️','💨','🔬','☁️','🌳','🏘️','🏗️','🔧','♻️','📢','🆔','📊','📋','✅','💪','🏥','🏃','🧠','📰','🤝','📜','📐','💰','🦋']
        return [{'code': f'OC{str(i+1).zfill(2)}', 'name': get_text(f'other_challenges.challenges.OC{str(i+1).zfill(2)}'), 'icon': icons[i], 'default_value': 50} for i in range(25)]

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=ThemeManager.COLORS['text_primary']
        )
        title_label.pack(pady=(0, 10))
        self.widget_refs['title'] = title_label

        # Descripción
        desc_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=700
        )
        desc_label.pack(pady=(0, 20))
        self.widget_refs['description'] = desc_label

        # Frame para la tabla con scroll
        table_container = ctk.CTkFrame(main_frame, fg_color=ThemeManager.COLORS['bg_secondary'])
        table_container.pack(fill="both", expand=True, pady=(0, 20))

        # Header de la tabla (fijo)
        self._create_table_header(table_container)

        # Frame scrollable para las filas
        self.scroll_frame = ctk.CTkScrollableFrame(
            table_container,
            fg_color="transparent",
            scrollbar_button_color=ThemeManager.COLORS['accent_primary'],
            scrollbar_button_hover_color=ThemeManager.COLORS['accent_secondary']
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Crear filas de desafíos en el frame scrollable
        self._create_challenge_rows(self.scroll_frame)

        # Cargar evaluación previa DESPUÉS de crear los widgets
        self._load_previous_evaluation()

        # Frame para botones
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        # Botón Cancelar
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="",
            command=self._cancel,
            fg_color=ThemeManager.COLORS['error'],
            hover_color=ThemeManager.COLORS['error_hover'],
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=120
        )
        cancel_btn.pack(side="left", padx=(0, 10))
        self.widget_refs['cancel_btn'] = cancel_btn

        # Botón Guardar
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="",
            command=self._save,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['success_hover'],
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=120
        )
        save_btn.pack(side="right", padx=(10, 0))
        self.widget_refs['save_btn'] = save_btn

    def _create_table_header(self, parent):
        """Crea el header de la tabla (fijo, no se mueve con scroll)"""
        header_frame = ctk.CTkFrame(parent, fg_color=ThemeManager.COLORS['accent_primary'])
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Columna Desafío
        challenge_header = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            width=400
        )
        challenge_header.pack(side="left", padx=15, pady=10)
        self.widget_refs['challenge_header'] = challenge_header

        # Columna Valoración
        value_header = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            width=120
        )
        value_header.pack(side="left", padx=15, pady=10)
        self.widget_refs['value_header'] = value_header

        # Columna Nivel de Importancia
        importance_header = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            width=200
        )
        importance_header.pack(side="left", padx=15, pady=10)
        self.widget_refs['importance_header'] = importance_header

    def _create_challenge_rows(self, parent):
        """Crea las filas de desafíos en el contenedor scrollable"""
        for challenge in self.challenges_data:
            row_widget = OtherChallengeRow(
                parent=parent,
                challenge_code=challenge['code'],
                challenge_name=challenge['name'],
                challenge_icon=challenge['icon'],
                default_value=challenge['default_value'],
                importance_colors=self._get_importance_colors(),
                on_value_change=self._on_challenge_value_change
            )
            row_widget.pack(fill="x", padx=5, pady=1)
            self.challenge_widgets[challenge['code']] = row_widget

    def _on_challenge_value_change(self, challenge_code, value):
        """Maneja el cambio de valor de un desafío"""
        print(f"Valor cambiado: {challenge_code} = {value}")  # Debug
        self.challenge_values[challenge_code] = value

    def _get_importance_level(self, value):
        """Obtiene el nivel de importancia según el valor"""
        if 1 <= value <= 20:
            return get_text("other_challenges.importance_levels.very_low")
        elif 21 <= value <= 40:
            return get_text("other_challenges.importance_levels.low")
        elif 41 <= value <= 60:
            return get_text("other_challenges.importance_levels.medium")
        elif 61 <= value <= 80:
            return get_text("other_challenges.importance_levels.high")
        elif 81 <= value <= 100:
            return get_text("other_challenges.importance_levels.very_high")
        else:
            return get_text("other_challenges.importance_levels.medium")  # Por defecto

    def _get_importance_colors(self):
        """Obtiene el diccionario de colores por etiqueta traducida"""
        return {
            get_text("other_challenges.importance_levels.very_low"): "#4CAF50",
            get_text("other_challenges.importance_levels.low"): "#8BC34A",
            get_text("other_challenges.importance_levels.medium"): "#FFC107",
            get_text("other_challenges.importance_levels.high"): "#FF9800",
            get_text("other_challenges.importance_levels.very_high"): "#F44336"
        }

    def _load_previous_evaluation(self):
        """Carga la evaluación previa desde el CSV (soporta múltiples idiomas en encabezados)"""
        try:
            if not self.project_path:
                return

            # Si project_path es un archivo, obtener el directorio padre
            if os.path.isfile(self.project_path):
                project_dir = os.path.dirname(self.project_path)
            else:
                project_dir = self.project_path

            if not os.path.exists(project_dir):
                return

            # Buscar archivo en todos los idiomas posibles (backward compatibility)
            possible_filenames = [
                "D_O.csv",               # Nombre fijo estándar
                "Otros_Desafios.csv",    # Español
                "Other_Challenges.csv",  # Inglés
                "Outros_Desafios.csv",   # Portugués
                "otros_desafios.csv"     # Legacy
            ]

            csv_file_path = None
            for filename in possible_filenames:
                test_path = os.path.join(project_dir, filename)
                if os.path.exists(test_path):
                    csv_file_path = test_path
                    break

            if not csv_file_path:
                return

            # Cargar datos del CSV
            df = pd.read_csv(csv_file_path, encoding='utf-8-sig')

            print("Cargando evaluación previa de otros desafíos")

            # Los encabezados pueden estar en cualquier idioma, pero sabemos que son 2 columnas
            # en este orden: Codigo_Desafio, Valor_Importancia
            # Normalizar nombres de columnas a un estándar interno
            if len(df.columns) >= 2:
                df.columns = ['Codigo_Desafio', 'Valor_Importancia']

            # Restaurar valores de desafíos
            for _, row in df.iterrows():
                challenge_code = row['Codigo_Desafio']
                value = int(float(row['Valor_Importancia']))
                self.challenge_values[challenge_code] = value
                print(f"Cargando {challenge_code}: {value}")

            # Marcar que se cargó configuración previa
            self.has_previous_data = True

            # Actualizar los widgets ya creados con los valores cargados
            # Usar after para asegurar que los widgets estén completamente renderizados
            self.after(100, self._update_widgets_with_loaded_values)

        except Exception as e:
            print(f"Error cargando evaluación previa: {e}")

    def _update_widgets_with_loaded_values(self):
        """Actualiza los widgets ya creados con los valores cargados del CSV"""
        print("Actualizando widgets de otros desafíos con valores cargados...")
        for challenge_code, challenge_widget in self.challenge_widgets.items():
            if challenge_code in self.challenge_values:
                saved_value = self.challenge_values[challenge_code]
                print(f"Actualizando widget {challenge_code} con valor {saved_value}")

                challenge_widget.value_entry.delete(0, "end")
                challenge_widget.value_entry.insert(0, str(saved_value))
                challenge_widget.current_value = saved_value
                challenge_widget._update_importance_label()

        # Forzar actualización visual
        self.update()

    def _save(self):
        """Guarda las valoraciones en CSV con encabezados traducidos"""
        try:
            # Obtener encabezados traducidos
            header_challenge_code = get_text("other_challenges.csv_headers.challenge_code")
            header_importance_value = get_text("other_challenges.csv_headers.importance_value")

            # Preparar datos para CSV (simplificado: solo código y valor)
            csv_data = []

            for challenge in self.challenges_data:
                challenge_code = challenge['code']
                value = self.challenge_values.get(challenge_code, challenge['default_value'])

                csv_data.append({
                    header_challenge_code: challenge_code,
                    header_importance_value: value
                })

            # Crear DataFrame
            df = pd.DataFrame(csv_data)

            # Guardar automáticamente en la carpeta del proyecto
            if self.project_path:
                # Si project_path es un archivo, obtener el directorio padre
                if os.path.isfile(self.project_path):
                    project_dir = os.path.dirname(self.project_path)
                else:
                    project_dir = self.project_path

                # Asegurar que el directorio existe
                if not os.path.exists(project_dir):
                    os.makedirs(project_dir, exist_ok=True)

                filename = "D_O.csv"  # Nombre fijo
                file_path = os.path.join(project_dir, filename)

                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                messagebox.showinfo(
                    get_text("other_challenges.save_success_title"),
                    get_text("other_challenges.save_success_message")
                )
            else:
                messagebox.showerror(
                    get_text("other_challenges.save_error_title"),
                    get_text("other_challenges.no_project_path")
                )

            # Actualizar estado del workflow en el dashboard
            if self.window_manager:
                self.window_manager.update_workflow_step('other_challenges', True, csv_data)

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                get_text("other_challenges.save_error_title"),
                get_text("other_challenges.save_error_message").format(str(e))
            )

    def _cancel(self):
        """Cancela y cierra la ventana"""
        result = messagebox.askyesno(
            get_text("other_challenges.cancel_title"),
            get_text("other_challenges.cancel_message")
        )
        if result:
            self.destroy()

    def _update_texts(self):
        """Actualiza todos los textos según el idioma actual"""
        self.title(get_text("other_challenges.title"))

        if 'title' in self.widget_refs:
            title_text = get_text("other_challenges.main_title")
            if self.has_previous_data:
                title_text += "\n" + get_text("status.config_loaded")
            self.widget_refs['title'].configure(text=title_text)

        if 'description' in self.widget_refs:
            self.widget_refs['description'].configure(text=get_text("other_challenges.description"))

        if 'challenge_header' in self.widget_refs:
            self.widget_refs['challenge_header'].configure(text=get_text("other_challenges.challenge_header"))

        if 'value_header' in self.widget_refs:
            self.widget_refs['value_header'].configure(text=get_text("other_challenges.value_header"))

        if 'importance_header' in self.widget_refs:
            self.widget_refs['importance_header'].configure(text=get_text("other_challenges.importance_header"))

        if 'save_btn' in self.widget_refs:
            self.widget_refs['save_btn'].configure(text=get_text("other_challenges.save"))

        if 'cancel_btn' in self.widget_refs:
            self.widget_refs['cancel_btn'].configure(text=get_text("other_challenges.cancel"))

        # Recargar challenges_data con traducciones actualizadas
        self.challenges_data = self._load_challenges_data()

        # Destruir y recrear widgets de desafíos
        for widget in self.challenge_widgets.values():
            widget.destroy()
        self.challenge_widgets.clear()

        # Recrear filas de desafíos
        self._create_challenge_rows(self.scroll_frame)


class OtherChallengeRow(ctk.CTkFrame):
    """Widget para mostrar una fila de otro desafío"""

    def __init__(self, parent, challenge_code, challenge_name, challenge_icon,
                 default_value, importance_colors, on_value_change):
        super().__init__(parent, fg_color=ThemeManager.COLORS['bg_card'])

        self.challenge_code = challenge_code
        self.challenge_name = challenge_name
        self.challenge_icon = challenge_icon
        self.default_value = default_value
        self.importance_colors = importance_colors
        self.on_value_change = on_value_change
        self.current_value = default_value

        self._setup_ui()

    def _setup_ui(self):
        """Configura la UI de la fila"""
        # Columna Desafío
        challenge_frame = ctk.CTkFrame(self, fg_color="transparent")
        challenge_frame.pack(side="left", fill="y", padx=15, pady=8)

        challenge_label = ctk.CTkLabel(
            challenge_frame,
            text=f"{self.challenge_icon} {self.challenge_name}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=ThemeManager.COLORS['text_primary'],
            width=400,
            anchor="w",
            wraplength=380
        )
        challenge_label.pack()

        # Columna Valoración (Entry + botones)
        value_frame = ctk.CTkFrame(self, fg_color="transparent")
        value_frame.pack(side="left", fill="y", padx=15, pady=8)

        # Frame para entrada de valor
        entry_frame = ctk.CTkFrame(value_frame, fg_color="transparent")
        entry_frame.pack()

        # Entry para el valor
        self.value_entry = ctk.CTkEntry(
            entry_frame,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=50,
            height=30,
            justify="center",
            corner_radius=4,
            border_width=1,
            border_color=ThemeManager.COLORS['accent_primary']
        )
        self.value_entry.pack(side="left", padx=(0, 3))
        self.value_entry.insert(0, str(self.default_value))
        self.value_entry.bind("<KeyRelease>", self._on_entry_change)
        self.value_entry.bind("<FocusOut>", self._on_entry_change)

        # Botones para incrementar/decrementar
        buttons_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
        buttons_frame.pack(side="left")

        # Botón incrementar
        self.up_button = ctk.CTkButton(
            buttons_frame,
            text="▲",
            command=self._increment,
            width=20,
            height=14,
            font=ctk.CTkFont(size=8),
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        self.up_button.pack(pady=(0, 1))

        # Botón decrementar
        self.down_button = ctk.CTkButton(
            buttons_frame,
            text="▼",
            command=self._decrement,
            width=20,
            height=14,
            font=ctk.CTkFont(size=8),
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        self.down_button.pack()

        # Columna Nivel de Importancia
        importance_frame = ctk.CTkFrame(self, fg_color="transparent")
        importance_frame.pack(side="left", fill="y", padx=15, pady=8)

        self.importance_label = ctk.CTkLabel(
            importance_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=180,
            height=30,
            corner_radius=4
        )
        self.importance_label.pack()

        # Establecer etiqueta inicial
        self._update_importance_label()

    def _on_entry_change(self, event=None):
        """Maneja el cambio del Entry"""
        try:
            value = int(self.value_entry.get())
            if 1 <= value <= 100:
                self.current_value = value
                self._update_importance_label()
                self.on_value_change(self.challenge_code, self.current_value)
            else:
                # Valor fuera del rango, restaurar el anterior
                self.value_entry.delete(0, "end")
                self.value_entry.insert(0, str(self.current_value))
        except ValueError:
            # Si el valor no es válido, restaurar el anterior
            self.value_entry.delete(0, "end")
            self.value_entry.insert(0, str(self.current_value))

    def _increment(self):
        """Incrementa el valor en 1"""
        if self.current_value < 100:
            self.current_value += 1
            self.value_entry.delete(0, "end")
            self.value_entry.insert(0, str(self.current_value))
            self._update_importance_label()
            self.on_value_change(self.challenge_code, self.current_value)

    def _decrement(self):
        """Decrementa el valor en 1"""
        if self.current_value > 1:
            self.current_value -= 1
            self.value_entry.delete(0, "end")
            self.value_entry.insert(0, str(self.current_value))
            self._update_importance_label()
            self.on_value_change(self.challenge_code, self.current_value)

    def _get_importance_level(self, value):
        """Obtiene el nivel de importancia según el valor"""
        if 1 <= value <= 20:
            return get_text("other_challenges.importance_levels.very_low")
        elif 21 <= value <= 40:
            return get_text("other_challenges.importance_levels.low")
        elif 41 <= value <= 60:
            return get_text("other_challenges.importance_levels.medium")
        elif 61 <= value <= 80:
            return get_text("other_challenges.importance_levels.high")
        elif 81 <= value <= 100:
            return get_text("other_challenges.importance_levels.very_high")
        else:
            return get_text("other_challenges.importance_levels.medium")

    def _update_importance_label(self):
        """Actualiza la etiqueta de importancia con color"""
        level = self._get_importance_level(self.current_value)
        color = self.importance_colors[level]

        self.importance_label.configure(
            text=level,
            fg_color=color,
            text_color="white" if self._is_dark_color(color) else "black"
        )

    def _is_dark_color(self, hex_color):
        """Determina si un color es oscuro"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5