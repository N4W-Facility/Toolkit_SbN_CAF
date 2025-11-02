import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
import os
from datetime import datetime
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes
from ..utils.resource_path import get_resource_path
from ..utils.sbn_prioritization import SbNPrioritization


class BarriersWindow(ctk.CTkToplevel):

    def __init__(self, window_manager=None, project_path=None):
        super().__init__()

        self.window_manager = window_manager
        self.project_path = project_path

        # Configuración de la ventana
        self.title(get_text("barriers.title"))
        self.geometry("1000x700")
        self.resizable(True, True)

        # Configurar ventana modal al frente
        if window_manager:
            self.transient(window_manager)  # Vincular al dashboard
            self.grab_set()  # Hacer modal
        self.lift()  # Traer al frente
        self.focus_force()  # Forzar foco
        self.attributes('-topmost', True)  # Temporal
        self.after(100, lambda: self.attributes('-topmost', False))  # Quitar topmost después

        # Aplicar tema
        ThemeManager.configure_ctk()
        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Datos de barreras - cargados desde Excel
        self.barriers_data = self._load_barriers_data()

        # Estado de los grupos (habilitado/deshabilitado)
        self.group_states = {
            'GB01': True,  # Políticas
            'GB02': True,  # Técnicas
            'GB03': True,  # Legales
            'GB04': True,  # Socio-culturales
            'GB05': True   # Financieras
        }

        # Valores actuales de las barreras
        self.barrier_values = {}

        # Referencias a widgets para actualizaciones
        self.widget_refs = {}
        self.group_widgets = {}

        # Estado de carga de datos previos
        self.has_previous_data = False

        # Colores para las etiquetas de valoración - se obtienen dinámicamente
        # Ver método _get_value_colors() para obtener versión traducida

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

    def _load_barriers_data(self):
        """Carga los datos de barreras desde el archivo CSV según el idioma actual"""
        try:
            # Obtener idioma actual
            from ..core.language_manager import get_current_language
            current_lang = get_current_language()

            # Determinar archivo CSV según idioma
            csv_filename = f"Barries_{current_lang}.csv"
            csv_path = get_resource_path(os.path.join('locales', csv_filename))

            if not os.path.exists(csv_path):
                print(f"Archivo de barreras no encontrado: {csv_path}")
                return self._get_default_barriers_data()

            # Leer CSV
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # Normalizar nombres de columnas (los headers varían por idioma)
            # Formato nuevo con 5 columnas: Codigo_Barrera, Descripcion, Subcategoria, Grupo, Codigo_Grupo
            df.columns = ['Codigo_Barrera', 'Descripcion', 'Subcategoria', 'Grupo', 'Codigo_Grupo']

            barriers_data = {
                'GB01': {'name': get_text('barriers.groups.GB01'), 'barriers': []},
                'GB02': {'name': get_text('barriers.groups.GB02'), 'barriers': []},
                'GB03': {'name': get_text('barriers.groups.GB03'), 'barriers': []},
                'GB04': {'name': get_text('barriers.groups.GB04'), 'barriers': []},
                'GB05': {'name': get_text('barriers.groups.GB05'), 'barriers': []}
            }

            # Procesar cada fila del CSV
            for _, row in df.iterrows():
                codigo_barrera = str(row['Codigo_Barrera']) if pd.notna(row['Codigo_Barrera']) else None
                descripcion = str(row['Descripcion']) if pd.notna(row['Descripcion']) else None
                subcategoria = str(row['Subcategoria']) if pd.notna(row['Subcategoria']) else ''
                codigo_grupo = str(row['Codigo_Grupo']) if pd.notna(row['Codigo_Grupo']) else None

                if codigo_barrera and descripcion and codigo_grupo in barriers_data:
                    barrier_item = {
                        'code': codigo_barrera,
                        'description': descripcion,
                        'subcategory': subcategoria,
                        'default_value': 1  # "No hay barreras" por defecto
                    }
                    barriers_data[codigo_grupo]['barriers'].append(barrier_item)

            return barriers_data

        except Exception as e:
            print(f"Error cargando datos de barreras: {e}")
            return self._get_default_barriers_data()

    def _create_default_barriers_file(self):
        """Crea el archivo CSV de barreras con configuración por defecto"""
        try:
            if not self.project_path:
                return

            # Si project_path es un archivo, obtener el directorio padre
            if os.path.isfile(self.project_path):
                project_dir = os.path.dirname(self.project_path)
            else:
                project_dir = self.project_path

            if not os.path.exists(project_dir):
                os.makedirs(project_dir, exist_ok=True)

            # Obtener encabezados traducidos
            header_barrier_code = get_text("barriers.csv_headers.barrier_code")
            header_numeric_value = get_text("barriers.csv_headers.numeric_value")
            header_group_code = get_text("barriers.csv_headers.group_code")
            header_group_enabled = get_text("barriers.csv_headers.group_enabled")

            # Preparar datos por defecto
            csv_data = []
            for group_code, group_data in self.barriers_data.items():
                for barrier in group_data['barriers']:
                    csv_data.append({
                        header_barrier_code: barrier['code'],
                        header_numeric_value: 1,  # Valor por defecto: "No hay barreras"
                        header_group_code: group_code,
                        header_group_enabled: 1  # Todos los grupos habilitados por defecto
                    })

            # Crear DataFrame y guardar
            df = pd.DataFrame(csv_data)
            filename = "Barriers.csv"  # Nombre fijo sin traducir
            file_path = os.path.join(project_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')

            print(f"Archivo de barreras por defecto creado en: {file_path}")

        except Exception as e:
            print(f"Error creando archivo de barreras por defecto: {e}")

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

            # Buscar archivo con nombre estándar
            csv_file_path = os.path.join(project_dir, "Barriers.csv")

            if not os.path.exists(csv_file_path):
                # Si no existe, crear uno por defecto
                print("No se encontró archivo de barreras. Creando configuración por defecto...")
                self._create_default_barriers_file()

                # Verificar que se creó correctamente
                if not os.path.exists(csv_file_path):
                    print("No se pudo crear el archivo de barreras")
                    return

            # Cargar datos del CSV
            df = pd.read_csv(csv_file_path, encoding='utf-8-sig')

            print("Cargando evaluación previa desde archivo guardado")

            # Los encabezados pueden estar en cualquier idioma, pero sabemos que son 4 columnas
            # en este orden: Codigo_Barrera, Valor_Numerico, Codigo_Grupo, Grupo_Habilitado
            # Normalizar nombres de columnas a un estándar interno
            if len(df.columns) >= 4:
                df.columns = ['Codigo_Barrera', 'Valor_Numerico', 'Codigo_Grupo', 'Grupo_Habilitado']

            # Restaurar valores de barreras
            for _, row in df.iterrows():
                barrier_code = row['Codigo_Barrera']
                value = int(float(row['Valor_Numerico']))  # Convertir a entero
                self.barrier_values[barrier_code] = value
                print(f"Cargando {barrier_code}: {value}")  # Debug

            # Restaurar estados de grupos
            group_states_from_csv = {}
            for _, row in df.iterrows():
                group_code = row['Codigo_Grupo']
                group_enabled = bool(row['Grupo_Habilitado'])
                group_states_from_csv[group_code] = group_enabled

            # Actualizar estados de grupos
            for group_code, enabled in group_states_from_csv.items():
                if group_code in self.group_states:
                    self.group_states[group_code] = enabled

            # Marcar que se cargó configuración previa
            self.has_previous_data = True

            # Actualizar los widgets SOLO si ya fueron creados (cuando se llama desde _update_texts)
            if self.group_widgets:
                self._update_widgets_with_loaded_values()

        except Exception as e:
            print(f"Error cargando evaluación previa: {e}")

    def _update_widgets_with_loaded_values(self):
        """Actualiza los widgets ya creados con los valores cargados del CSV"""
        print("Actualizando widgets con valores cargados...")
        for group_code, group_widget in self.group_widgets.items():
            # Actualizar estado del switch del grupo
            group_widget.enable_switch.select() if self.group_states[group_code] else group_widget.enable_switch.deselect()
            group_widget._update_enabled_state()

            # Actualizar cada barrera del grupo
            for barrier_code, barrier_widget in group_widget.barrier_widgets.items():
                if barrier_code in self.barrier_values:
                    saved_value = self.barrier_values[barrier_code]
                    print(f"Actualizando widget {barrier_code} con valor {saved_value}")

                    # Encontrar la etiqueta correspondiente al valor
                    for label, value, color in barrier_widget.options_data:
                        if value == saved_value:
                            barrier_widget.combobox.set(label)
                            barrier_widget.current_value = saved_value
                            barrier_widget._update_combobox_color()
                            print(f"Widget {barrier_code} actualizado a '{label}'")
                            break

    def _get_default_barriers_data(self):
        """Datos por defecto si no se puede cargar el Excel"""
        return {
            'GB01': {
                'name': get_text('barriers.groups.GB01'),
                'barriers': [
                    {'code': 'GB0101', 'description': 'Desconexión entre acciones a corto y largo plazo', 'default_value': 1},
                    {'code': 'GB0102', 'description': 'Discontinuidad entre planes estratégicos', 'default_value': 1}
                ]
            },
            'GB02': {
                'name': get_text('barriers.groups.GB02'),
                'barriers': [
                    {'code': 'GB0201', 'description': 'Barreras infraestructurales', 'default_value': 1},
                    {'code': 'GB0202', 'description': 'Localización de intervenciones', 'default_value': 1}
                ]
            },
            'GB03': {
                'name': get_text('barriers.groups.GB03'),
                'barriers': [
                    {'code': 'GB0301', 'description': 'Barreras legales generales', 'default_value': 1},
                    {'code': 'GB0302', 'description': 'Barreras organizativas', 'default_value': 1}
                ]
            },
            'GB04': {
                'name': get_text('barriers.groups.GB04'),
                'barriers': [
                    {'code': 'GB0401', 'description': 'Lagunas de conocimiento', 'default_value': 1},
                    {'code': 'GB0402', 'description': 'Falta de concienciación', 'default_value': 1}
                ]
            },
            'GB05': {
                'name': get_text('barriers.groups.GB05'),
                'barriers': [
                    {'code': 'GB0501', 'description': 'Limitaciones presupuestarias', 'default_value': 1},
                    {'code': 'GB0502', 'description': 'Falta de financiación', 'default_value': 1}
                ]
            }
        }

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
        title_label.pack(pady=(0, 20))
        self.widget_refs['title'] = title_label

        # Frame con scroll para el contenido
        self.scroll_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color=ThemeManager.COLORS['bg_secondary'],
            scrollbar_button_color=ThemeManager.COLORS['accent_primary'],
            scrollbar_button_hover_color=ThemeManager.COLORS['accent_secondary']
        )
        self.scroll_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Cargar evaluación previa (o crear archivo por defecto si no existe)
        self._load_previous_evaluation()

        # Crear grupos de barreras con los valores ya cargados
        self._create_barrier_groups()

        # Frame para botones
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        # Botón Cancelar
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text=get_text("barriers.cancel"),
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
            text=get_text("barriers.save"),
            command=self._save,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['success_hover'],
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=120
        )
        save_btn.pack(side="right", padx=(10, 0))
        self.widget_refs['save_btn'] = save_btn

    def _create_barrier_groups(self):
        """Crea los grupos expandibles de barreras"""
        for group_code, group_data in self.barriers_data.items():
            group_widget = BarrierGroup(
                parent=self.scroll_frame,
                group_code=group_code,
                group_name=group_data['name'],
                barriers=group_data['barriers'],
                is_enabled=self.group_states[group_code],
                value_colors=self._get_value_colors(),
                on_group_toggle=self._on_group_toggle,
                on_value_change=self._on_barrier_value_change,
                barrier_values=self.barrier_values  # Pasar valores ya cargados
            )
            group_widget.pack(fill="x", padx=10, pady=5)
            self.group_widgets[group_code] = group_widget

    def _on_group_toggle(self, group_code, is_enabled):
        """Maneja el cambio de estado de un grupo"""
        self.group_states[group_code] = is_enabled

        # Si se deshabilita el grupo, poner todas las barreras en valor neutro
        if not is_enabled:
            for barrier in self.barriers_data[group_code]['barriers']:
                self.barrier_values[barrier['code']] = 1  # "No hay barreras"

    def _on_barrier_value_change(self, barrier_code, value):
        """Maneja el cambio de valor de una barrera"""
        print(f"Valor cambiado: {barrier_code} = {value}")  # Debug
        self.barrier_values[barrier_code] = value

    def _get_value_label(self, value):
        """Obtiene la etiqueta según el valor discreto, traducida"""
        value_labels = {
            -1: get_text("barriers.value_labels.gran_facilitador"),
            0: get_text("barriers.value_labels.facilitador"),
            1: get_text("barriers.value_labels.no_hay_barreras"),
            2: get_text("barriers.value_labels.barrera"),
            3: get_text("barriers.value_labels.barrera_importante")
        }
        return value_labels.get(value, get_text("barriers.value_labels.no_hay_barreras"))

    def _get_value_colors(self):
        """Obtiene el diccionario de colores por etiqueta traducida"""
        return {
            get_text("barriers.value_labels.gran_facilitador"): "#2196F3",
            get_text("barriers.value_labels.facilitador"): "#4CAF50",
            get_text("barriers.value_labels.no_hay_barreras"): "#9E9E9E",
            get_text("barriers.value_labels.barrera"): "#FF9800",
            get_text("barriers.value_labels.barrera_importante"): "#F44336"
        }

    def _save(self):
        """Guarda las valoraciones en CSV con encabezados traducidos"""
        try:
            # Obtener encabezados traducidos
            header_barrier_code = get_text("barriers.csv_headers.barrier_code")
            header_numeric_value = get_text("barriers.csv_headers.numeric_value")
            header_group_code = get_text("barriers.csv_headers.group_code")
            header_group_enabled = get_text("barriers.csv_headers.group_enabled")

            # Preparar datos para CSV
            csv_data = []

            for group_code, group_data in self.barriers_data.items():
                group_enabled = self.group_states[group_code]

                for barrier in group_data['barriers']:
                    barrier_code = barrier['code']
                    value = self.barrier_values.get(barrier_code, 1)  # Por defecto "No hay barreras"

                    # Si el grupo está deshabilitado, forzar valor neutro
                    if not group_enabled:
                        value = 1  # "No hay barreras"

                    csv_data.append({
                        header_barrier_code: barrier_code,
                        header_numeric_value: value,
                        header_group_code: group_code,
                        header_group_enabled: 1 if group_enabled else 0
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

                filename = "Barriers.csv"  # Nombre fijo sin traducir
                file_path = os.path.join(project_dir, filename)

                df.to_csv(file_path, index=False, encoding='utf-8-sig')

                # Actualizar priorización de SbN
                try:
                    SbNPrioritization.update_barriers(project_dir)
                except Exception as e:
                    print(f"Error actualizando priorización SbN: {e}")

                messagebox.showinfo(
                    get_text("barriers.save_success_title"),
                    get_text("barriers.save_success_message")
                )
            else:
                messagebox.showerror(
                    get_text("barriers.save_error_title"),
                    get_text("messages.no_project_path")
                )

            # Actualizar estado del workflow en el dashboard
            if self.window_manager:
                self.window_manager.update_workflow_step('barreras', True, csv_data)

                self.destroy()

        except Exception as e:
            messagebox.showerror(
                get_text("barriers.save_error_title"),
                get_text("barriers.save_error_message").format(str(e))
            )

    def _cancel(self):
        """Cancela y cierra la ventana"""
        result = messagebox.askyesno(
            get_text("barriers.cancel_title"),
            get_text("barriers.cancel_message")
        )
        if result:
            self.destroy()

    def _update_texts(self):
        """Actualiza todos los textos según el idioma actual"""
        self.title(get_text("barriers.title"))

        if 'title' in self.widget_refs:
            title_text = get_text("barriers.main_title")
            # if self.has_previous_data:
            #     title_text += "\n" + get_text("status.config_loaded")
            self.widget_refs['title'].configure(text=title_text)
        if 'save_btn' in self.widget_refs:
            self.widget_refs['save_btn'].configure(text=get_text("barriers.save"))
        if 'cancel_btn' in self.widget_refs:
            self.widget_refs['cancel_btn'].configure(text=get_text("barriers.cancel"))

        # Recargar barriers_data con traducciones del nuevo idioma
        self.barriers_data = self._load_barriers_data()

        # Destruir widgets actuales
        for group_widget in self.group_widgets.values():
            group_widget.destroy()
        self.group_widgets.clear()

        # Recrear widgets con nuevos datos traducidos
        self._create_barrier_groups()

        # Recargar datos guardados después de recrear widgets
        self._load_previous_evaluation()


class BarrierGroup(ctk.CTkFrame):
    """Widget para mostrar un grupo de barreras"""

    def __init__(self, parent, group_code, group_name, barriers, is_enabled,
                 value_colors, on_group_toggle, on_value_change, barrier_values=None):
        super().__init__(parent, fg_color=ThemeManager.COLORS['bg_tertiary'])

        self.group_code = group_code
        self.group_name = group_name
        self.barriers = barriers
        self.is_enabled = is_enabled
        self.value_colors = value_colors
        self.on_group_toggle = on_group_toggle
        self.on_value_change = on_value_change
        self.barrier_values = barrier_values if barrier_values is not None else {}

        self.is_expanded = False
        self.barrier_widgets = {}

        self._setup_ui()

    def _setup_ui(self):
        """Configura la UI del grupo"""
        # Header del grupo
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)

        # Switch para habilitar/deshabilitar
        self.enable_switch = ctk.CTkSwitch(
            header_frame,
            text="",
            command=self._toggle_group,
            progress_color=ThemeManager.COLORS['success']
        )
        self.enable_switch.pack(side="left", padx=(0, 10))
        if self.is_enabled:
            self.enable_switch.select()

        # Título del grupo
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=self.group_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ThemeManager.COLORS['text_primary']
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        # Botón expandir/contraer
        self.expand_btn = ctk.CTkButton(
            header_frame,
            text="▼",
            command=self._toggle_expand,
            width=30,
            height=30,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        self.expand_btn.pack(side="right")

        # Frame para las barreras (inicialmente oculto)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._create_barriers()
        self._update_enabled_state()

    def _create_barriers(self):
        """Crea los widgets de las barreras agrupadas por subcategoría"""
        from collections import OrderedDict

        # Agrupar barreras por subcategoría
        subcategories = OrderedDict()
        for barrier in self.barriers:
            subcat = barrier.get('subcategory', '')
            if subcat not in subcategories:
                subcategories[subcat] = []
            subcategories[subcat].append(barrier)

        # Crear widgets por subcategoría
        for subcategory, barriers_in_subcat in subcategories.items():
            # Si hay subcategoría, mostrar header
            if subcategory:
                subcat_label = ctk.CTkLabel(
                    self.content_frame,
                    text=subcategory,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=ThemeManager.COLORS['accent_primary'],
                    anchor="w"
                )
                subcat_label.pack(fill="x", padx=10, pady=(10, 5))

            # Crear widgets de barreras
            for barrier in barriers_in_subcat:
                # Usar valor cargado si existe, sino usar valor por defecto
                barrier_code = barrier['code']
                initial_value = self.barrier_values.get(barrier_code, barrier['default_value'])

                barrier_widget = BarrierItem(
                    parent=self.content_frame,
                    barrier_code=barrier_code,
                    description=barrier['description'],
                    default_value=initial_value,  # Usar valor cargado o por defecto
                    value_colors=self.value_colors,
                    on_value_change=self.on_value_change,
                    is_enabled=self.is_enabled
                )
                barrier_widget.pack(fill="x", padx=5, pady=2)
                self.barrier_widgets[barrier_code] = barrier_widget

    def _toggle_group(self):
        """Alterna el estado habilitado/deshabilitado del grupo"""
        self.is_enabled = self.enable_switch.get()
        self.on_group_toggle(self.group_code, self.is_enabled)
        self._update_enabled_state()

    def _update_enabled_state(self):
        """Actualiza el estado visual según esté habilitado o no"""
        alpha = 1.0 if self.is_enabled else 0.5

        # Actualizar opacidad del título
        color = ThemeManager.COLORS['text_primary'] if self.is_enabled else ThemeManager.COLORS['text_secondary']
        self.title_label.configure(text_color=color)

        # Actualizar estado de las barreras
        for barrier_widget in self.barrier_widgets.values():
            barrier_widget.set_enabled(self.is_enabled)

    def _toggle_expand(self):
        """Alterna la expansión del grupo"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.content_frame.pack(fill="x", padx=10, pady=(0, 10))
            self.expand_btn.configure(text="▲")
        else:
            self.content_frame.pack_forget()
            self.expand_btn.configure(text="▼")

    def update_texts(self):
        """Actualiza textos según idioma"""
        # Actualizar nombre del grupo
        group_translations = {
            'GB01': get_text('barriers.groups.GB01'),
            'GB02': get_text('barriers.groups.GB02'),
            'GB03': get_text('barriers.groups.GB03'),
            'GB04': get_text('barriers.groups.GB04'),
            'GB05': get_text('barriers.groups.GB05')
        }
        if self.group_code in group_translations:
            self.group_name = group_translations[self.group_code]
            if hasattr(self, 'title_label'):
                self.title_label.configure(text=self.group_name)

        # Actualizar BarrierItems
        for barrier_widget in self.barrier_widgets.values():
            if hasattr(barrier_widget, 'update_texts'):
                barrier_widget.update_texts()


class BarrierItem(ctk.CTkFrame):
    """Widget para una barrera individual"""

    def __init__(self, parent, barrier_code, description, default_value,
                 value_colors, on_value_change, is_enabled=True):
        super().__init__(parent, fg_color=ThemeManager.COLORS['bg_primary'])

        self.barrier_code = barrier_code
        self.description = description
        self.default_value = default_value
        self.value_colors = value_colors
        self.on_value_change = on_value_change
        self.is_enabled = is_enabled
        self.current_value = default_value

        self._setup_ui()

    def _setup_ui(self):
        """Configura la UI de la barrera"""
        # Descripción
        self.description_label = ctk.CTkLabel(
            self,
            text=self.description,
            font=ctk.CTkFont(size=12),
            text_color=ThemeManager.COLORS['text_primary'],
            wraplength=400,
            justify="left",
            anchor="w"
        )
        self.description_label.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=8)

        # Frame para el dropdown
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(side="right", padx=(0, 10), pady=5)

        # Opciones de evaluación (texto, valor, color)
        self.options_data = self._get_options_data()

        # Crear lista de opciones para el ComboBox
        self.option_labels = [option[0] for option in self.options_data]

        # Encontrar la opción por defecto
        default_label = self._get_default_label()

        # Crear ComboBox con estilo moderno
        self.combobox = ctk.CTkComboBox(
            controls_frame,
            values=self.option_labels,
            command=self._on_combobox_change,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=180,
            height=35,
            state="readonly",
            corner_radius=8,
            border_width=2,
            dropdown_font=ctk.CTkFont(size=11)
        )
        self.combobox.pack(pady=5)
        self.combobox.set(default_label)

        print(f"Configurando ComboBox para {self.barrier_code} con valor {self.default_value} -> {default_label}")  # Debug

        # Establecer color inicial
        self._update_combobox_color()

        self.set_enabled(self.is_enabled)

    def _get_options_data(self):
        """Obtiene las opciones traducidas"""
        return [
            (get_text("barriers.value_labels.gran_facilitador"), -1, self.value_colors[get_text("barriers.value_labels.gran_facilitador")]),
            (get_text("barriers.value_labels.facilitador"), 0, self.value_colors[get_text("barriers.value_labels.facilitador")]),
            (get_text("barriers.value_labels.no_hay_barreras"), 1, self.value_colors[get_text("barriers.value_labels.no_hay_barreras")]),
            (get_text("barriers.value_labels.barrera"), 2, self.value_colors[get_text("barriers.value_labels.barrera")]),
            (get_text("barriers.value_labels.barrera_importante"), 3, self.value_colors[get_text("barriers.value_labels.barrera_importante")])
        ]

    def _get_default_label(self):
        """Encuentra la etiqueta por defecto"""
        default_label = get_text("barriers.value_labels.no_hay_barreras")
        for label, value, color in self.options_data:
            if value == self.default_value:
                default_label = label
                break
        return default_label

    def _on_combobox_change(self, choice):
        """Maneja el cambio del ComboBox"""
        # Encontrar el valor correspondiente al texto seleccionado
        for label, value, color in self.options_data:
            if label == choice:
                self.current_value = value
                self._update_combobox_color()
                self.on_value_change(self.barrier_code, value)
                break

    def _update_combobox_color(self):
        """Actualiza el color del ComboBox según la selección actual"""
        current_label = self.combobox.get()

        # Encontrar el color correspondiente
        for label, value, color in self.options_data:
            if label == current_label:
                if self.is_enabled:
                    # Colores más suaves y modernos
                    lighter_color = self._lighten_color(color, 0.9)
                    self.combobox.configure(
                        fg_color=lighter_color,
                        border_color=color,
                        button_color=color,
                        button_hover_color=self._darken_color(color, 0.8),
                        text_color="white" if self._is_dark_color(color) else "black",
                        dropdown_fg_color=ThemeManager.COLORS['bg_card'],
                        dropdown_hover_color=lighter_color
                    )
                else:
                    # Color gris cuando está deshabilitado
                    gray_color = ThemeManager.COLORS['text_secondary']
                    self.combobox.configure(
                        fg_color=ThemeManager.COLORS['bg_secondary'],
                        border_color=gray_color,
                        button_color=gray_color,
                        button_hover_color=gray_color,
                        text_color=gray_color
                    )
                break

    def _lighten_color(self, hex_color, factor):
        """Aclara un color hexadecimal"""
        # Remover el #
        hex_color = hex_color.lstrip('#')
        # Convertir a RGB
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Aclarar
        r = int(r + (255 - r) * (1 - factor))
        g = int(g + (255 - g) * (1 - factor))
        b = int(b + (255 - b) * (1 - factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _darken_color(self, hex_color, factor):
        """Oscurece un color hexadecimal"""
        # Remover el #
        hex_color = hex_color.lstrip('#')
        # Convertir a RGB
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Oscurecer
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _is_dark_color(self, hex_color):
        """Determina si un color es oscuro"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Fórmula de luminancia
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5

    def set_enabled(self, enabled):
        """Establece el estado habilitado/deshabilitado"""
        self.is_enabled = enabled

        if enabled:
            # Habilitar ComboBox
            self.combobox.configure(state="readonly")
            self.description_label.configure(text_color=ThemeManager.COLORS['text_primary'])
        else:
            # Deshabilitar ComboBox y establecer valor neutro
            self.combobox.configure(state="disabled")
            self.combobox.set(get_text("barriers.value_labels.no_hay_barreras"))
            self.current_value = 1
            self.description_label.configure(text_color=ThemeManager.COLORS['text_secondary'])
            self.on_value_change(self.barrier_code, 1)

        # Actualizar colores
        self._update_combobox_color()

    def update_texts(self):
        """Actualiza las opciones del combobox cuando cambia el idioma"""
        # Guardar el valor actual
        current_value = self.current_value

        # Recrear options_data con traducciones actuales
        self.options_data = self._get_options_data()
        self.option_labels = [option[0] for option in self.options_data]

        # Actualizar valores del combobox
        self.combobox.configure(values=self.option_labels)

        # Establecer el texto traducido correspondiente al valor actual
        for label, value, color in self.options_data:
            if value == current_value:
                self.combobox.set(label)
                break

        # Actualizar color
        self._update_combobox_color()