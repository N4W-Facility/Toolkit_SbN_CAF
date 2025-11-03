import customtkinter as ctk
from tkinter import messagebox
import os
import glob
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, get_current_global_language, set_current_global_language
from ..components.matplotlib_map_viewer import MatplotlibMapViewer
from ..utils.sbn_prioritization import SbNPrioritization

class SbNWindow(ctk.CTkToplevel):

    def __init__(self, parent, project_data=None, project_path=None, window_manager=None, language=None):
        super().__init__(parent)

        self.parent = parent
        self.window_manager = window_manager
        self.project_data = project_data
        self.project_path = project_path

        # Sincronizar idioma antes de crear UI
        if language:
            set_current_global_language(language)

        self.title(get_text("sbn.title"))
        self.geometry("1400x900")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Referencias para el mapa
        self.map_viewer = None
        self.loaded_rasters = {}  # {sbn_id: raster_layer}

        # Lista completa de SbN con iconos apropiados
        all_sbn_list = [
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

        # Filtrar lista según configuración de priorización
        selected_sbn_codes = self._get_selected_sbn_from_config()
        if selected_sbn_codes:
            # Solo mostrar SbN seleccionadas en la configuración
            self.sbn_list = [sbn for sbn in all_sbn_list if sbn['id'] in selected_sbn_codes]
            print(f"✓ Mostrando {len(self.sbn_list)}/{len(all_sbn_list)} SbN según configuración")
        else:
            # Si no hay configuración, mostrar todas (comportamiento por defecto)
            self.sbn_list = all_sbn_list
            print(f"⚠️ No hay configuración de SbN, mostrando todas las 21 SbN")

        # Referencias a widgets para actualización de texto
        self.widget_refs = {}
        self.sbn_checkboxes = {}

        # Cargar prioridades de SbN desde SbN_Prioritization.csv
        self.sbn_priorities = {}
        if self.project_path:
            project_dir = os.path.dirname(self.project_path) if os.path.isfile(self.project_path) else self.project_path
            self.sbn_priorities = SbNPrioritization.get_sbn_priorities(project_dir)

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
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

        if self.project_data:
            project_name = self.project_data.get('project_info', {}).get('name', 'Sin nombre')
            subtitle_label = ctk.CTkLabel(
                header_frame,
                text=get_text("sbn.project_label").format(project_name),
                font=ThemeManager.FONTS['subtitle'],
                text_color=ThemeManager.COLORS['text_secondary']
            )
            subtitle_label.pack(pady=(5, 0))

        # Layout principal: mapa a la izquierda, panel SbN a la derecha
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Panel de SbN (lado derecho) - width fijo
        sbn_panel = ctk.CTkFrame(content_frame, width=450, **ThemeManager.get_frame_style())
        sbn_panel.pack(side="right", fill="y", padx=(15, 0))
        sbn_panel.pack_propagate(False)

        # Visor de mapa (lado izquierdo) - expande
        map_container = ctk.CTkFrame(content_frame, **ThemeManager.get_frame_style())
        map_container.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Crear el visor de mapa
        self._create_map_viewer(map_container)

        # Crear el panel de SbN
        self._create_sbn_panel(sbn_panel)

        # Botones finales
        self._create_buttons(main_frame)

    def _create_map_viewer(self, container):
        """Crear el visor de mapa"""
        try:
            # Título del mapa
            map_title = ctk.CTkLabel(
                container,
                text="",
                font=ThemeManager.FONTS['subtitle'],
                text_color=ThemeManager.COLORS['text_primary']
            )
            map_title.pack(pady=(15, 10))
            self.widget_refs['map_title'] = map_title

            # Crear el visor de mapa
            self.map_viewer = MatplotlibMapViewer(
                container,
                width=800,
                height=600,
                corner_radius=8
            )
            self.map_viewer.pack(fill="both", expand=True, padx=15, pady=(0, 15))

            # Cargar polígono de la cuenca como capa base
            self._load_watershed_boundary()

        except Exception as e:
            print(f"Error creando visor de mapa: {e}")
            error_label = ctk.CTkLabel(
                container,
                text="Error al cargar el mapa",
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['error']
            )
            error_label.pack(fill="both", expand=True)

    def _load_watershed_boundary(self):
        """Cargar el polígono de la cuenca como capa base permanente"""
        try:
            if not self.project_path:
                print("No hay project_path definido")
                return

            # Construir ruta al shapefile
            from pathlib import Path
            if os.path.isfile(self.project_path):
                project_folder = Path(self.project_path).parent
            else:
                project_folder = Path(self.project_path)

            watershed_shp = project_folder / "01-Watershed" / "Watershed.shp"

            if not watershed_shp.exists():
                print(f"Shapefile de cuenca no encontrado: {watershed_shp}")
                return

            # Cargar shapefile con solo borde visible (sin relleno)
            print(f"Cargando polígono de cuenca: {watershed_shp}")
            success = self.map_viewer.add_vector_layer(
                str(watershed_shp),
                layer_name="watershed_boundary",
                color='none',  # Sin relleno
                alpha=1,  # Opacidad completa
                linewidth=3,
                edgecolor='red'  # Color del borde
            )

            if success:
                print("✅ Polígono de cuenca cargado exitosamente")
                # Centrar vista en la cuenca
                self.map_viewer.zoom_to_vector(str(watershed_shp), padding_factor=0.15)
            else:
                print("❌ No se pudo cargar el polígono de cuenca")

        except Exception as e:
            print(f"Error cargando polígono de cuenca: {e}")
            import traceback
            traceback.print_exc()

    def _create_sbn_panel(self, container):
        """Crear el panel lateral con lista de SbN"""
        # Título del panel
        panel_title = ctk.CTkLabel(
            container,
            text="",
            font=ThemeManager.FONTS['subtitle'],
            text_color=ThemeManager.COLORS['text_primary']
        )
        panel_title.pack(pady=(15, 10))
        self.widget_refs['panel_title'] = panel_title

        # Descripción
        desc_label = ctk.CTkLabel(
            container,
            text="",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=400
        )
        desc_label.pack(pady=(0, 15), padx=15)
        self.widget_refs['panel_description'] = desc_label

        # Frame scrollable para la lista de SbN
        scroll_frame = ctk.CTkScrollableFrame(
            container,
            fg_color="transparent",
            scrollbar_button_color=ThemeManager.COLORS['accent_primary'],
            scrollbar_button_hover_color=ThemeManager.COLORS['accent_secondary']
        )
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # self.sbn_priorities es tu OrderedDict
        prio = self.sbn_priorities

        self.sbn_list = sorted(
            self.sbn_list,
            key=lambda item: (
                prio.get(item['id'], {}).get('priority_rank') is None,  # los sin prioridad al final
                prio.get(item['id'], {}).get('priority_rank', 9999)  # y dentro, por rank
            )
        )

        # Crear checkboxes para cada SbN
        for sbn in self.sbn_list:
            self._create_sbn_checkbox(scroll_frame, sbn)

    def _create_sbn_checkbox(self, parent, sbn):
        """Crear checkbox para una SbN específica"""
        sbn_id = sbn['id']

        # Frame para cada SbN
        sbn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sbn_frame.pack(fill="x", pady=2)

        # Construir texto del checkbox con ranking de prioridad si existe
        sbn_name = get_text(f'sbn_solutions.{sbn_id}')
        priority_info = self.sbn_priorities.get(sbn_id, {})

        if priority_info and priority_info.get('is_enabled') and priority_info.get('priority_rank'):
            # SbN habilitada con ranking
            priority_text = get_text('sbn.priority_label').format(priority_info['priority_rank'])
            checkbox_text = f"{sbn_name} {sbn['icon']} {priority_text}"
        else:
            # SbN sin prioridad o deshabilitada
            checkbox_text = f"{sbn_name} {sbn['icon']}"

        # Checkbox
        checkbox = ctk.CTkCheckBox(
            sbn_frame,
            text=checkbox_text,
            command=lambda: self._toggle_sbn_raster(sbn_id),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_primary'],
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            checkmark_color=ThemeManager.COLORS['text_primary']
        )
        checkbox.pack(side="left", padx=5, pady=5)

        # Verificar si la SbN está deshabilitada por prioridad = 0
        if priority_info and not priority_info.get('is_enabled', True):
            checkbox.configure(state="disabled")
            # Agregar indicador de "no apta"
            na_label = ctk.CTkLabel(
                sbn_frame,
                text="⛔",
                font=ThemeManager.FONTS['caption'],
                text_color=ThemeManager.COLORS['error']
            )
            na_label.pack(side="right", padx=5)
        else:
            # Verificar si existe el archivo raster
            raster_path = self._find_sbn_raster(sbn_id)
            if not raster_path:
                checkbox.configure(state="disabled")
                # Agregar indicador de "no disponible"
                na_label = ctk.CTkLabel(
                    sbn_frame,
                    text="❌",
                    font=ThemeManager.FONTS['caption'],
                    text_color=ThemeManager.COLORS['error']
                )
                na_label.pack(side="right", padx=5)

        self.sbn_checkboxes[sbn_id] = checkbox

    def _find_sbn_raster(self, sbn_id):
        """Buscar archivo raster para una SbN específica"""
        if not self.project_path:
            return None

        # Determinar directorio del proyecto
        if os.path.isfile(self.project_path):
            project_dir = os.path.dirname(self.project_path)
        else:
            project_dir = self.project_path

        sbn_dir = os.path.join(project_dir, "03-SbN")

        if not os.path.exists(sbn_dir):
            return None

        # Buscar primero el formato nuevo: SbN_{id}.tif
        new_format = os.path.join(sbn_dir, f"SbN_{sbn_id}.tif")
        if os.path.exists(new_format):
            return new_format

        # Si no existe, buscar formato antiguo: SbN_{id}_*.tif (backward compatibility)
        pattern = os.path.join(sbn_dir, f"SbN_{sbn_id}_*.tif")
        matching_files = glob.glob(pattern)

        if matching_files:
            return matching_files[0]  # Retornar el primer archivo encontrado

        return None

    def _toggle_sbn_raster(self, sbn_id):
        """Mostrar/ocultar raster de SbN en el mapa"""
        checkbox = self.sbn_checkboxes.get(sbn_id)
        if not checkbox or not self.map_viewer:
            return

        if checkbox.get():  # Checkbox activado - mostrar raster
            self._load_sbn_raster(sbn_id)
        else:  # Checkbox desactivado - ocultar raster
            self._unload_sbn_raster(sbn_id)

    def _load_sbn_raster(self, sbn_id):
        """Cargar y mostrar raster de SbN en el mapa"""
        try:
            raster_path = self._find_sbn_raster(sbn_id)
            if not raster_path:
                messagebox.showwarning(
                    get_text("messages.warning"),
                    get_text("sbn.no_raster_found_msg").format(sbn_id)
                )
                return

            print(f"Cargando raster: {raster_path}")

            # Cargar el raster en el visor de mapa
            layer_name = f"SbN_{sbn_id}"
            success = self.map_viewer.add_raster_layer(raster_path, layer_name, alpha=0.6)

            if success:
                self.loaded_rasters[sbn_id] = raster_path
                print(f"✅ Raster SbN {sbn_id} cargado exitosamente")

                # Hacer zoom automático al raster recién cargado
                self.map_viewer.zoom_to_raster(raster_path)
                print(f"🔍 Zoom automático aplicado a SbN {sbn_id}")
            else:
                # Desmarcar el checkbox si falla la carga
                checkbox = self.sbn_checkboxes.get(sbn_id)
                if checkbox:
                    checkbox.deselect()

        except Exception as e:
            print(f"Error cargando raster SbN {sbn_id}: {e}")
            messagebox.showerror(
                get_text("messages.error"),
                get_text("sbn.raster_load_error_msg").format(sbn_id, str(e))
            )
            # Desmarcar el checkbox si hay error
            checkbox = self.sbn_checkboxes.get(sbn_id)
            if checkbox:
                checkbox.deselect()

    def _unload_sbn_raster(self, sbn_id):
        """Quitar raster de SbN del mapa"""
        try:
            if sbn_id in self.loaded_rasters:
                layer_name = f"SbN_{sbn_id}"
                success = self.map_viewer.remove_raster_layer(layer_name)

                if success:
                    del self.loaded_rasters[sbn_id]
                    print(f"✅ Raster SbN {sbn_id} removido del mapa")

        except Exception as e:
            print(f"Error removiendo raster SbN {sbn_id}: {e}")

    def _create_buttons(self, container):
        """Crear botones de la ventana"""
        button_frame = ctk.CTkFrame(container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(15, 0))

        # Botón Cerrar
        close_style = ThemeManager.get_button_style()
        close_style['fg_color'] = ThemeManager.COLORS['text_light']
        close_style['hover_color'] = ThemeManager.COLORS['text_secondary']
        close_button = ctk.CTkButton(
            button_frame,
            text="",
            command=self._on_closing,
            **close_style
        )
        close_button.pack(side="right", padx=(10, 0))
        self.widget_refs['close_button'] = close_button

        # Botón Guardar Selección
        save_button = ctk.CTkButton(
            button_frame,
            text="",
            command=self._save_selection,
            **ThemeManager.get_button_style()
        )
        save_button.pack(side="right")
        self.widget_refs['save_button'] = save_button

        # Botón Zoom a Todas las SbN
        zoom_all_style = ThemeManager.get_button_style()
        zoom_all_style['fg_color'] = ThemeManager.COLORS['success']
        zoom_all_style['hover_color'] = '#2E7D32'  # Verde más oscuro
        zoom_all_button = ctk.CTkButton(
            button_frame,
            text="",
            command=self._zoom_to_all_rasters,
            **zoom_all_style
        )
        zoom_all_button.pack(side="right", padx=(0, 10))
        self.widget_refs['zoom_all_button'] = zoom_all_button

    def _save_selection(self):
        """Guardar selección actual de SbN y actualizar workflow"""
        selected_sbn = [sbn_id for sbn_id, checkbox in self.sbn_checkboxes.items() if checkbox.get()]
        print(f"SbN seleccionadas: {selected_sbn}")

        # Actualizar workflow en el dashboard
        if self.window_manager:
            # Marcar el paso de SbN como completado con datos de selección
            self.window_manager.update_workflow_step('sbn', True, selected_sbn)

        messagebox.showinfo(
            get_text("messages.success"),
            get_text("sbn.selection_saved").format(len(selected_sbn))
        )

        # Cerrar la ventana
        self._on_closing()

    def _zoom_to_all_rasters(self):
        """Hacer zoom para mostrar todas las SbN cargadas con padding extra"""
        if not self.loaded_rasters:
            messagebox.showinfo(
                get_text("messages.info"),
                get_text("sbn.no_sbn_loaded")
            )
            return

        # Usar padding más grande para vista más amplia
        success = self.map_viewer.zoom_to_all_rasters(padding_factor=0.2)  # 20% padding en lugar de 10%
        if success:
            print(f"🔍 Vista amplia aplicada a {len(self.loaded_rasters)} SbN cargadas")
            # Mostrar mensaje de estado en la ventana
            # (No usamos messagebox para no interrumpir el flujo)
        else:
            messagebox.showerror(
                get_text("messages.error"),
                get_text("sbn.zoom_error")
            )

    def _get_selected_sbn_from_config(self):
        """
        Obtener lista de SbN seleccionadas desde la configuración de priorización.
        Retorna lista de IDs de SbN o None si no hay configuración.
        """
        try:
            if not self.project_data:
                return None

            config = self.project_data.get('sbn_analysis', {}).get('prioritization_config', {})
            selected_codes = config.get('selected_sbn_codes', [])

            if selected_codes:
                print(f"✓ Configuración cargada: {len(selected_codes)} SbN seleccionadas")
                return selected_codes
            else:
                return None

        except Exception as e:
            print(f"⚠️ Error leyendo configuración de SbN: {e}")
            return None

    def _update_texts(self):
        """Actualizar todos los textos según el idioma actual"""
        self.title(get_text("sbn.title"))

        if 'title' in self.widget_refs:
            self.widget_refs['title'].configure(text=get_text("sbn.main_title"))

        if 'map_title' in self.widget_refs:
            self.widget_refs['map_title'].configure(text=get_text("sbn.map_title"))

        if 'panel_title' in self.widget_refs:
            self.widget_refs['panel_title'].configure(text=get_text("sbn.panel_title"))

        if 'panel_description' in self.widget_refs:
            self.widget_refs['panel_description'].configure(text=get_text("sbn.panel_description"))

        if 'close_button' in self.widget_refs:
            self.widget_refs['close_button'].configure(text=get_text("sbn.close"))

        if 'save_button' in self.widget_refs:
            self.widget_refs['save_button'].configure(text=get_text("sbn.save_selection"))

        if 'zoom_all_button' in self.widget_refs:
            self.widget_refs['zoom_all_button'].configure(text=get_text("sbn.zoom_all"))

    def _on_closing(self):
        """Manejar cierre de ventana"""
        # Limpiar todos los rasters antes de cerrar
        if self.map_viewer:
            self.map_viewer.clear_all_rasters()
        self.destroy()