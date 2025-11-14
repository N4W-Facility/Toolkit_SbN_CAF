import customtkinter as ctk
from tkinter import messagebox, simpledialog
import os
import geopandas as gpd
from pathlib import Path
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes, get_current_global_language, set_current_global_language
from ..core.database_manager import DatabaseManager
from ..components.matplotlib_map_viewer import MatplotlibMapViewer
from .database_processing_dialog import DatabaseProcessingDialog
from ..core import ProcessingPackage as PackCAF
from ..core import DelimitacionCuenca as PackCAF_DC
from ..core.normalize_raster_sbn import normalize_raster


class WatershedDelimitationFolium(ctk.CTkToplevel):
    
    def __init__(self, parent, project_data=None, language=None, watershed_shapefile=None, current_project_path=None):
        super().__init__(parent)

        self.parent = parent
        self.project_data = project_data
        self.watershed_shapefile = watershed_shapefile
        self.current_project_path = current_project_path

        # Sincronizar idioma antes de crear UI
        if language:
            set_current_global_language(language)

        self.title(get_text("watershed.title"))
        self.geometry("1200x800")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        self.result = None
        self.lat = None
        self.lon = None
        self.current_watershed = None
        self.databases_processed = False
        self.drawing_sbn_mode = False  # Estado del modo de dibujo de área SbN
        self.point_selection_mode = False  # Estado del modo de selección de punto

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        # Sincronizar con el idioma actual al abrir
        self._update_texts()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Cargar shapefile existente si se proporcionó (después de que el widget esté renderizado)
        if self.watershed_shapefile and os.path.exists(self.watershed_shapefile):
            self.after(500, self._load_existing_watershed)
        # Si no hay shapefile pero sí coordenadas guardadas, cargarlas
        elif self.project_data:
            coordinates = self.project_data.get('watershed_data', {}).get('coordinates', {})
            saved_lat = coordinates.get('latitude')
            saved_lon = coordinates.get('longitude')

            if saved_lat is not None and saved_lon is not None:
                self.after(500, lambda: self._load_saved_coordinates(saved_lat, saved_lon))
    
    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text=get_text("watershed.main_title"),
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.title_label.pack()

        if self.project_data:
            project_name = self.project_data.get('project_info', {}).get('name', get_text("messages.not_available"))
            self.subtitle_label = ctk.CTkLabel(
                header_frame,
                text=f"{get_text('watershed.project_label')} {project_name}",
                font=ThemeManager.FONTS['subtitle'],
                text_color=ThemeManager.COLORS['text_secondary']
            )
            self.subtitle_label.pack(pady=(5, 0))
        
        # Layout principal: mapa a la izquierda, panel a la derecha
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Panel de información (lado derecho) - más ancho
        info_panel = ctk.CTkFrame(content_frame, width=400, **ThemeManager.get_frame_style())
        info_panel.pack(side="right", fill="y", padx=(15, 0))
        info_panel.pack_propagate(False)
        
        # Visor de mapa (lado izquierdo) - ahora tendrá más espacio
        map_container = ctk.CTkFrame(content_frame, **ThemeManager.get_frame_style())
        map_container.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Ocultar controles de colormap en ventana de cuenca (no se usan rasters aquí)
        # Pasar callback para botón de reset: en vez de volver a Latinoamérica, centra en la cuenca
        self.map_viewer = MatplotlibMapViewer(
            map_container,
            hide_colormap_controls=True,
            reset_callback=self._zoom_to_watershed,
            fg_color="transparent"
        )
        self.map_viewer.pack(fill="both", expand=True, padx=8, pady=8)
        self.map_viewer.set_coordinate_callback(self._on_coordinates_selected)
        
        self._create_info_panel(info_panel)
        
        # Footer con botones
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        self._create_buttons(button_frame)
    
    def _create_info_panel(self, parent):
        # Título del panel
        self.panel_title = ctk.CTkLabel(
            parent,
            text=get_text("watershed.info_title"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.panel_title.pack(pady=(20, 15))

        # Coordenadas seleccionadas
        coords_frame = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        coords_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.coords_title = ctk.CTkLabel(
            coords_frame,
            text=get_text("watershed.coordinates_title"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.coords_title.pack(pady=(15, 5))

        self.coords_display = ctk.CTkLabel(
            coords_frame,
            text=get_text("watershed.coordinates_none"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=300
        )
        self.coords_display.pack(padx=15, pady=(0, 15))

        # Opción manual para ingresar coordenadas
        self.manual_btn = ctk.CTkButton(
            coords_frame,
            text=get_text("watershed.manual_input"),
            width=200,
            command=self._manual_coordinates,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.manual_btn.pack(pady=(0, 15))

        # Resultado de macrocuenca
        result_frame = ctk.CTkFrame(parent, **ThemeManager.get_frame_style())
        result_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.result_title = ctk.CTkLabel(
            result_frame,
            text=get_text("watershed.watershed_title"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.result_title.pack(pady=(15, 5))

        self.watershed_display = ctk.CTkLabel(
            result_frame,
            text=get_text("watershed.watershed_pending"),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=300
        )
        self.watershed_display.pack(padx=15, pady=(0, 15))

        # Estado del proceso
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(fill="x", padx=15, pady=(15, 0))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text=get_text("watershed.waiting_coordinates"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_light'],
            wraplength=300
        )
        self.status_label.pack()

        # Botón seleccionar punto en mapa - ubicado debajo del estado
        self.select_point_btn = ctk.CTkButton(
            status_frame,
            text=get_text("watershed.select_point_map"),
            width=200,
            height=40,
            command=self._toggle_point_selection_mode,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="normal"
        )
        self.select_point_btn.pack(pady=(10, 0))

        # Botón delimitar cuenca - ubicado justo debajo del botón de selección
        self.delimit_btn = ctk.CTkButton(
            status_frame,
            text=get_text("watershed.delimit_button"),
            width=200,
            height=40,
            command=self._delimit_watershed,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="disabled"
        )
        self.delimit_btn.pack(pady=(10, 0))

        # Botón para definir área SbN - ubicado debajo del botón delimitar
        self.define_sbn_btn = ctk.CTkButton(
            status_frame,
            text=get_text("watershed.define_sbn_area"),
            width=200,
            height=40,
            command=self._toggle_sbn_drawing_mode,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="disabled"  # Inicialmente deshabilitado hasta que exista cuenca
        )
        self.define_sbn_btn.pack(pady=(10, 0))

        # Botón guardar y cerrar - ÚLTIMO botón
        self.save_and_close_btn = ctk.CTkButton(
            status_frame,
            text=get_text("watershed.save_and_close"),
            width=200,
            height=40,
            command=self._save_and_close,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="disabled"
        )
        self.save_and_close_btn.pack(pady=(10, 0))
    
    def _create_buttons(self, parent):
        # Botón cancelar
        self.cancel_btn = ctk.CTkButton(
            parent,
            text=get_text("watershed.cancel"),
            width=120,
            height=40,
            command=self._cancel,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.cancel_btn.pack(side="right", padx=(15, 0))

        # Botón guardar
        self.save_btn = ctk.CTkButton(
            parent,
            text=get_text("watershed.save_project"),
            width=160,
            height=40,
            command=self._save_project,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius'],
            state="disabled"
        )
        self.save_btn.pack(side="right", padx=(10, 0))
        
    
    def _on_coordinates_selected(self, lat, lon):
        """Callback cuando se seleccionan coordenadas en el mapa"""
        self.lat = lat
        self.lon = lon

        self.coords_display.configure(
            text=f"Lat: {lat:.6f}\nLon: {lon:.6f}",
            text_color=ThemeManager.COLORS['text_primary']
        )

        self.status_label.configure(
            text=get_text("watershed.coordinates_selected"),
            text_color=ThemeManager.COLORS['success']
        )

        # Habilitar botón de delimitación
        self.delimit_btn.configure(state="normal")

        # Reset estado de guardado
        self.current_watershed = None
        self.save_btn.configure(state="disabled")
        self.watershed_display.configure(
            text=get_text("watershed.watershed_click"),
            text_color=ThemeManager.COLORS['text_secondary']
        )
    
    def _manual_coordinates(self):
        """Permitir ingreso manual de coordenadas"""
        dialog = CoordinateInputDialog(self)
        self.wait_window(dialog)
        
        if hasattr(dialog, 'result') and dialog.result:
            lat, lon = dialog.result
            self.map_viewer.set_coordinates(lat, lon)
            self._on_coordinates_selected(lat, lon)
    
    def _delimit_watershed(self):
        if self.lat is None or self.lon is None:
            messagebox.showwarning(
                get_text("messages.warning"),
                get_text("messages.must_delimit_first")
            )
            return

        # Validar que existen los datos necesarios
        if not self.project_data or 'files' not in self.project_data:
            messagebox.showerror(
                get_text("messages.error"),
                "No se encontró información del proyecto"
            )
            return

        # IMPORTANTE: Resetear workflow cuando se delimita nueva cuenca
        # Esto previene usar datos antiguos si el usuario no guarda
        if hasattr(self.parent, 'reset_workflow_on_new_delineation'):
            self.parent.reset_workflow_on_new_delineation()
            print("🔄 Workflow reseteado - esperando nueva delimitación")

        # Obtener database_folder desde DatabaseManager (BD global)
        from ..core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        database_folder = db_manager.get_database_path()

        project_folder = self.project_data['files'].get('project_folder')

        if not database_folder or not project_folder:
            messagebox.showerror(
                get_text("messages.error"),
                "Falta configurar la carpeta de base de datos o del proyecto"
            )
            return

        # Abrir ventana de progreso
        progress_dialog = ProgressDialog(self)

        # Ejecutar delimitación después de que se renderice la ventana
        self.after(100, lambda: self._run_delineation(progress_dialog, database_folder, project_folder))

    def _run_delineation(self, progress_dialog, database_folder, project_folder):
        """Ejecutar el proceso de delimitación con ventana de progreso"""
        try:
            self.status_label.configure(
                text=get_text("watershed.delimit_process"),
                text_color=ThemeManager.COLORS['warning']
            )
            self.update()

            # Importar ProcessingPackage
            from pathlib import Path
            import sys

            # Step 1 - Crear carpetas de trabajo
            print("Step 1: Creando carpetas de trabajo...")
            PackCAF.CreateFolders(project_folder)

            # Step 2 - Identificar Macro-Cuenca
            print("Step 2: Identificando macro-cuenca...")
            PathRegion  = os.path.join(database_folder, "Basin", "LATAM.shp")
            PathRegion2 = os.path.join(database_folder, "Basin", "LATAM_1_SPLIT.shp")
            PathRegion3 = os.path.join(database_folder, "Basin", "LATAM_16_25_SPLIT.shp")

            if not os.path.exists(PathRegion):
                raise FileNotFoundError(f"No se encontró el archivo de regiones: {PathRegion}")

            NameRegion = PackCAF.C00_EncontrarMacrocuenca(self.lat, self.lon, PathRegion)

            if NameRegion == 'LATAM_1':
                NameRegion = PackCAF.C00_EncontrarMacrocuenca(self.lat, self.lon, PathRegion2)

            if NameRegion == 'LATAM_16' or NameRegion == 'LATAM_25':
                NameRegion = PackCAF.C00_EncontrarMacrocuenca(self.lat, self.lon, PathRegion3)
            print(f"Macro-cuenca identificada: {NameRegion}")

            # Step 3 - Delimitación de la cuenca
            print("Step 3: Delimitando cuenca...")
            Path_FlowDir    = os.path.join(database_folder, "FlowDir", f"FlowDir_{NameRegion}.tif")
            Path_FlowAccum  = os.path.join(database_folder, "FlowAccum", f"FlowAccum_{NameRegion}.tif")

            if not os.path.exists(Path_FlowDir):
                raise FileNotFoundError(f"No se encontró el archivo FlowDir: {Path_FlowDir}")

            threshold = 1
            resultado = PackCAF.C01_BasinDelineation(
                PathOut=project_folder,
                Path_FlowDir=Path_FlowDir,
                Path_FlowAccum=Path_FlowAccum,
                lat=self.lat,
                lon=self.lon,
                threshold=threshold
            )

            # Actualizar current_watershed con resultado
            self.current_watershed = {
                'name': NameRegion,
                'lat': self.lat,
                'lon': self.lon,
                'coordinates': [self.lon, self.lat]
            }

            # Actualizar UI
            self.watershed_display.configure(
                text=f"{NameRegion}\n\n{get_text('watershed.delimit_success')}",
                text_color=ThemeManager.COLORS['success']
            )

            self.status_label.configure(
                text=get_text("watershed.delimit_success"),
                text_color=ThemeManager.COLORS['success']
            )

            # Habilitar botones de guardado
            self.save_btn.configure(state="normal")
            self.save_and_close_btn.configure(state="normal")

            # Habilitar botón de definir área SbN (ya que la cuenca fue delimitada exitosamente)
            if hasattr(self, 'define_sbn_btn'):
                self.define_sbn_btn.configure(state="normal")

            # Agregar datos al proyecto
            if self.project_data:
                # Asegurar que watershed_data existe con estructura completa
                if 'watershed_data' not in self.project_data:
                    self.project_data['watershed_data'] = {}

                # Guardar coordenadas
                self.project_data['watershed_data']['coordinates'] = {
                    'latitude': self.lat,
                    'longitude': self.lon
                }

                # Información del punto de interés
                self.project_data['watershed_data']['point_of_interest'] = {
                    'lat': self.lat,
                    'lon': self.lon,
                    'macrocuenca': NameRegion
                }

                # Datos morfométricos (se llenarán posteriormente)
                self.project_data['watershed_data']['morphometry'] = {
                    'area': None,
                    'perimeter': None,
                    'min_elevation': None,
                    'max_elevation': None,
                    'avg_slope': None
                }

                # Datos climáticos
                self.project_data['watershed_data']['climate'] = {
                    'precipitation': None,
                    'temperature': None
                }

                # Datos hidrológicos
                self.project_data['watershed_data']['hydrology'] = {
                    'avg_flow': None,
                    'flood_risk': "",
                    'water_stress': ""
                }

                # Datos de nutrientes
                self.project_data['watershed_data']['nutrients'] = {
                    'sediments': None,
                    'phosphorus': None,
                    'nitrogen': None
                }

                # Asegurar que sbn_analysis existe
                if 'sbn_analysis' not in self.project_data:
                    self.project_data['sbn_analysis'] = {
                        'selected_solutions': [],
                        'scenarios': [],
                        'results': {}
                    }

            # Cargar y mostrar shapefile generado en el mapa
            from pathlib import Path
            watershed_shp_path = Path(project_folder) / "01-Watershed" / "Watershed.shp"
            if watershed_shp_path.exists():
                print("Cargando shapefile generado en el mapa...")

                # Actualizar referencia al shapefile para que el botón de zoom funcione
                self.watershed_shapefile = str(watershed_shp_path)

                self.map_viewer.add_vector_layer(
                    str(watershed_shp_path),
                    layer_name="watershed",
                    color='lightblue',
                    alpha=0.5,
                    linewidth=2
                )
                # Centrar y hacer zoom específico a la cuenca con margen mínimo
                self.map_viewer.zoom_to_vector(str(watershed_shp_path), padding_factor=0.05)

            # Cerrar ventana de progreso antes del mensaje de éxito
            try:
                if progress_dialog and progress_dialog.winfo_exists():
                    progress_dialog.destroy()
            except:
                pass

            messagebox.showinfo(
                get_text("messages.success"),
                f"{get_text('messages.delimitation_success')}\n{NameRegion}"
            )

        except Exception as e:
            # Cerrar ventana de progreso
            try:
                if progress_dialog and progress_dialog.winfo_exists():
                    progress_dialog.destroy()
            except:
                pass

            import traceback
            traceback.print_exc()

            self.status_label.configure(
                text=get_text("watershed.delimit_error"),
                text_color=ThemeManager.COLORS['error']
            )
            messagebox.showerror(
                get_text("messages.error"),
                f"{get_text('messages.delimitation_error')} {str(e)}"
            )
    
    def _save_project(self):
        if self.current_watershed is None:
            messagebox.showwarning(
                get_text("messages.warning"),
                get_text("messages.must_save_watershed")
            )
            return

        try:
            # Capturar imagen del mapa si existe el proyecto
            if self.project_data and 'files' in self.project_data and 'project_folder' in self.project_data['files']:
                project_folder = self.project_data['files']['project_folder']
                image_filename = "watershed_map.png"
                image_path = os.path.join(project_folder, image_filename)

                # Intentar guardar la imagen del mapa
                if self.map_viewer.save_map_image(image_path):
                    # Agregar ruta de imagen a los datos del proyecto
                    if 'watershed_data' not in self.project_data:
                        self.project_data['watershed_data'] = {}

                    self.project_data['watershed_data']['map_image'] = image_filename
                    print(f"Imagen del mapa guardada: {image_path}")
                else:
                    print("No se pudo guardar la imagen del mapa")

            self.result = self.project_data
            self._on_closing()

        except Exception as e:
            print(f"Error al guardar imagen: {str(e)}")
            # Continuar guardando el proyecto aunque falle la imagen
            self.result = self.project_data
            self._on_closing()
    
    def _cancel(self):
        self._on_closing()

    def _save_and_close(self):
        """Guardar imagen del visor y cerrar ventana"""
        try:
            # Validar que existe proyecto
            if not self.project_data or 'files' not in self.project_data:
                messagebox.showerror(
                    get_text("messages.error"),
                    "No se encontró información del proyecto"
                )
                return

            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                messagebox.showerror(
                    get_text("messages.error"),
                    "No se encontró la carpeta del proyecto"
                )
                return

            # Construir ruta para guardar imagen
            from pathlib import Path
            watershed_folder = Path(project_folder) / "01-Watershed"
            image_path = watershed_folder / "Watershed.jpg"

            # Guardar imagen del mapa
            if self.map_viewer.save_map_image(str(image_path)):
                print(f"Imagen guardada: {image_path}")

                # Procesar bases de datos si no se ha hecho
                if not self.databases_processed:
                    self._process_database_rasters()
                    self.databases_processed = True

                # Guardar proyecto en JSON (después de procesar y calcular estadísticas)
                if self.current_project_path:
                    from ..utils.project_manager import ProjectManager
                    project_json_path = os.path.join(self.current_project_path, 'project.json')
                    success = ProjectManager.save_project(self.project_data, project_json_path)
                    if success:
                        print(f"Proyecto guardado en: {project_json_path}")
                    else:
                        print(f"Error al guardar proyecto en: {project_json_path}")

                # Guardar datos del proyecto
                self.result = self.project_data

                # Cerrar ventana
                self._on_closing()
            else:
                messagebox.showerror(
                    get_text("messages.error"),
                    "No se pudo guardar la imagen del mapa"
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                get_text("messages.error"),
                f"Error al guardar: {str(e)}"
            )

    def _toggle_point_selection_mode(self):
        """Activar/desactivar el modo de selección de punto en el mapa"""
        if not self.point_selection_mode:
            # Activar modo de selección de punto
            self.point_selection_mode = True
            self.select_point_btn.configure(
                text=get_text("watershed.confirm_point"),
                fg_color=ThemeManager.COLORS['success']
            )

            # Deshabilitar botón de SbN mientras punto está activo
            if hasattr(self, 'define_sbn_btn'):
                self.define_sbn_btn.configure(state="disabled")

            # Borrar marcador anterior si existe
            if hasattr(self, 'map_viewer') and self.map_viewer.current_marker:
                try:
                    self.map_viewer.current_marker.remove()
                    self.map_viewer.current_marker = None
                    self.map_viewer.canvas.draw_idle()
                except:
                    pass

            # Habilitar selección de punto en el mapa
            if hasattr(self, 'map_viewer'):
                self.map_viewer.enable_point_selection()

        else:
            # Desactivar modo de selección de punto
            self.point_selection_mode = False
            self.select_point_btn.configure(
                text=get_text("watershed.select_point_map"),
                fg_color=ThemeManager.COLORS['accent_primary']
            )

            # Rehabilitar botón de SbN
            if hasattr(self, 'define_sbn_btn'):
                self.define_sbn_btn.configure(state="normal")

            # Desactivar selección en el mapa
            if hasattr(self, 'map_viewer'):
                self.map_viewer.disable_point_selection()

    def _toggle_sbn_drawing_mode(self):
        """Activar modo de dibujo de área SbN - solo se usa para activar, no para confirmar"""
        if not self.drawing_sbn_mode:
            # Activar modo de dibujo
            self.drawing_sbn_mode = True
            self.define_sbn_btn.configure(
                text=get_text("watershed.confirm_sbn_area"),
                fg_color=ThemeManager.COLORS['success']
            )

            # Deshabilitar botón de selección de punto mientras SbN está activo
            if hasattr(self, 'select_point_btn'):
                self.select_point_btn.configure(state="disabled")

            # Limpiar rectángulo anterior del mapa
            if hasattr(self, 'map_viewer'):
                self.map_viewer.clear_current_rectangle()

            # Habilitar dibujo de rectángulo en el mapa
            if hasattr(self, 'map_viewer'):
                self.map_viewer.enable_rectangle_draw(callback=self._on_rectangle_drawn)

    def _on_rectangle_drawn(self, coordinates):
        """
        Callback cuando el usuario dibuja el rectángulo (segundo clic).
        coordinates: dict con keys 'north', 'south', 'east', 'west' en WGS84
        """
        # Guardar shapefile
        self._save_sbn_window(coordinates)

        # Desactivar modo de dibujo automáticamente
        self.drawing_sbn_mode = False
        self.define_sbn_btn.configure(
            text=get_text("watershed.define_sbn_area"),
            fg_color=ThemeManager.COLORS['accent_primary']
        )

        # Rehabilitar botón de selección de punto
        if hasattr(self, 'select_point_btn'):
            self.select_point_btn.configure(state="normal")

        # Desactivar dibujo en el mapa
        if hasattr(self, 'map_viewer'):
            self.map_viewer.disable_rectangle_draw()

    def _save_sbn_window(self, coordinates):
        """
        Guarda el rectángulo como polígono shapefile en 03-SbN/Window_SbN.shp
        coordinates: dict con keys 'north', 'south', 'east', 'west' en WGS84
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Polygon

            # Validar que existe carpeta del proyecto
            if not self.project_data or 'files' not in self.project_data:
                messagebox.showerror(
                    get_text("messages.error"),
                    "No se encontró información del proyecto"
                )
                return

            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                messagebox.showerror(
                    get_text("messages.error"),
                    "No se encontró la carpeta del proyecto"
                )
                return

            # Crear carpeta 03-SbN si no existe
            sbn_folder = os.path.join(project_folder, "03-SbN")
            os.makedirs(sbn_folder, exist_ok=True)

            # Extraer coordenadas
            north = coordinates['north']
            south = coordinates['south']
            east = coordinates['east']
            west = coordinates['west']

            # Crear polígono rectangular en orden correcto (antihorario)
            polygon = Polygon([
                (west, south),  # Esquina inferior izquierda
                (east, south),  # Esquina inferior derecha
                (east, north),  # Esquina superior derecha
                (west, north),  # Esquina superior izquierda
                (west, south)   # Cerrar polígono
            ])

            # Crear GeoDataFrame con CRS WGS84
            gdf = gpd.GeoDataFrame(
                {'geometry': [polygon],
                 'name': ['Window_SbN'],
                 'description': ['Area delimitada para SbN']},
                crs='EPSG:4326'  # WGS84
            )

            # Guardar shapefile (sobreescribe si existe)
            shp_path = os.path.join(sbn_folder, "Window_SbN.shp")
            gdf.to_file(shp_path)

            print(f"✅ Área SbN guardada en: {shp_path}")

            # Mostrar mensaje de éxito
            messagebox.showinfo(
                get_text("messages.success"),
                get_text("watershed.area_saved")
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                get_text("messages.error"),
                get_text("watershed.area_save_error").format(str(e))
            )

    def _process_database_rasters(self):
        """
        Procesa todos los rasters de la base de datos recortándolos al área de la cuenca.
        Muestra ventana de progreso modal durante el procesamiento.
        """

        try:
            # Obtener rutas necesarias
            db_manager = DatabaseManager()
            db_path = db_manager.get_database_path()

            if not db_path or not os.path.exists(db_path):
                messagebox.showerror(
                    get_text("database_processing.error_title"),
                    get_text("database_processing.error_message").format("No se encontró la ruta de la base de datos")
                )
                return

            project_folder = Path(self.project_data['files'].get('project_folder'))
            watershed_folder = project_folder / "01-Watershed"

            # Rutas de archivos
            path_basin  = str(watershed_folder / "Watershed.shp")
            path_nbs    = str(project_folder / "03-SbN" /  "Window_SbN.shp")
            path_ref    = str(project_folder / "02-Rasters" / "DEM.tif")

            # Verificar que existe el shapefile de la cuenca
            if not os.path.exists(path_basin):
                messagebox.showerror(
                    get_text("database_processing.error_title"),
                    get_text("database_processing.error_message").format("No se encontró el archivo de cuenca delimitada")
                )
                return

            # Diccionario de rasters de referencia
            NameRaster = {
                'DEM': [None, project_folder / "02-Rasters", "DEM", os.path.join(db_path, "DEM"), path_basin],
                'Network': [None, project_folder / "02-Rasters", "Network", os.path.join(db_path, "Network"), path_basin],
                'P': [path_ref, project_folder / "02-Rasters","P", os.path.join(db_path, "P"), path_basin],
                'T': [path_ref, project_folder / "02-Rasters", "T", os.path.join(db_path, "T"), path_basin],
                'Slope': [None, project_folder / "02-Rasters", "Slope", os.path.join(db_path, "Slope"), path_basin],
                'ETP': [path_ref, project_folder / "02-Rasters","ETP", os.path.join(db_path, "ETP"), path_basin],
                'AWY': [path_ref, project_folder / "02-Rasters","AWY", os.path.join(db_path, "AWY"), path_basin],
                'SDR': [path_ref, project_folder / "02-Rasters" ,"SDR", os.path.join(db_path, "SDR"), path_basin],
                'NDR_N': [path_ref, project_folder / "02-Rasters", "NDR_N", os.path.join(db_path, "NDR_N"), path_basin],
                'NDR_P': [path_ref, project_folder / "02-Rasters" , "NDR_P", os.path.join(db_path, "NDR_P"), path_basin],
                'SbN_01': [None, project_folder / "03-SbN","SbN_1", os.path.join(db_path, "SbN_01"), path_nbs],
                'SbN_02': [None, project_folder / "03-SbN","SbN_2", os.path.join(db_path, "SbN_02"), path_nbs],
                'SbN_03': [None, project_folder / "03-SbN","SbN_3", os.path.join(db_path, "SbN_03"), path_nbs],
                'SbN_04': [None, project_folder / "03-SbN","SbN_4", os.path.join(db_path, "SbN_04"), path_nbs],
                'SbN_05': [None, project_folder / "03-SbN","SbN_5", os.path.join(db_path, "SbN_05"), path_nbs],
                'SbN_06': [None, project_folder / "03-SbN","SbN_6", os.path.join(db_path, "SbN_06"), path_nbs],
                'SbN_07': [None, project_folder / "03-SbN","SbN_7", os.path.join(db_path, "SbN_07"), path_nbs],
                'SbN_08': [None, project_folder / "03-SbN","SbN_8", os.path.join(db_path, "SbN_08"), path_nbs],
                'SbN_09': [None, project_folder / "03-SbN","SbN_9", os.path.join(db_path, "SbN_09"), path_nbs],
                'SbN_10': [None, project_folder / "03-SbN","SbN_10", os.path.join(db_path, "SbN_10"), path_nbs],
                'SbN_11': [None, project_folder / "03-SbN","SbN_11", os.path.join(db_path, "SbN_11"), path_nbs],
                'SbN_12': [None, project_folder / "03-SbN","SbN_12", os.path.join(db_path, "SbN_12"), path_nbs],
                'SbN_13': [None, project_folder / "03-SbN","SbN_13", os.path.join(db_path, "SbN_13"), path_nbs],
                'SbN_14': [None, project_folder / "03-SbN","SbN_14", os.path.join(db_path, "SbN_14"), path_nbs],
                'SbN_15': [None, project_folder / "03-SbN","SbN_15", os.path.join(db_path, "SbN_15"), path_nbs],
                'SbN_16': [None, project_folder / "03-SbN","SbN_16", os.path.join(db_path, "SbN_16"), path_nbs],
                'SbN_17': [None, project_folder / "03-SbN","SbN_17", os.path.join(db_path, "SbN_17"), path_nbs],
                'SbN_18': [None, project_folder / "03-SbN","SbN_18", os.path.join(db_path, "SbN_18"), path_nbs],
                'SbN_19': [None, project_folder / "03-SbN","SbN_19", os.path.join(db_path, "SbN_19"), path_nbs],
                'SbN_20': [None, project_folder / "03-SbN","SbN_20", os.path.join(db_path, "SbN_20"), path_nbs],
                'SbN_21': [None, project_folder / "03-SbN","SbN_21", os.path.join(db_path, "SbN_21"), path_nbs],
            }

            # Crear ventana de progreso
            total_rasters = len(NameRaster)
            progress_dialog = DatabaseProcessingDialog(self, total_rasters)

            # Diccionario para almacenar idoneidad de cada SbN {sbn_id: 0 o 1}
            sbn_suitability = {}

            # Procesar cada raster
            processed_count = 0
            for index, (raster_name, ref_path) in enumerate(NameRaster.items()):
                # Actualizar ventana de progreso
                progress_dialog.update_progress(raster_name, index)

                try:
                    # Ruta del raster en la base de datos
                    raster_db_path = NameRaster[raster_name][3]

                    # Ruta de salida
                    output_path = str(NameRaster[raster_name][1] / f"{NameRaster[raster_name][2]}.tif")

                    # Procesar raster usando ProcessingPackage
                    resultado = PackCAF.C02_Crear_Mosaico(
                        ruta_rasters=raster_db_path,
                        archivo_poligono=NameRaster[raster_name][4],
                        crs_salida='EPSG:4326',
                        archivo_salida=output_path,
                        raster_referencia=NameRaster[raster_name][0],
                    )

                    # Normalizar SOLO los rasters de SbN (SbN_01 a SbN_21)
                    if raster_name.startswith('SbN_'):
                        try:
                            # Normalizar y obtener información
                            result      = normalize_raster(output_path)
                            max_value   = result.get('max_value', 0.0)
                            has_data    = result.get('has_data', False)

                            # Extraer ID de SbN (SbN_01 → 1, SbN_21 → 21)
                            sbn_id = int(raster_name.split('_')[1])

                            # Determinar idoneidad: 1 si tiene datos, 0 si no
                            sbn_suitability[sbn_id] = 1 if has_data else 0

                            print(f"✓ Raster {raster_name} normalizado (max: {max_value:.2f}, idoneidad: {sbn_suitability[sbn_id]})")
                        except Exception as norm_error:
                            print(f"⚠ Error normalizando {raster_name}: {str(norm_error)}")
                            # Si falla, asumir idoneidad = 0
                            sbn_id = int(raster_name.split('_')[1])
                            sbn_suitability[sbn_id] = 0

                    processed_count += 1

                except Exception as e:
                    print(f"Error procesando {raster_name}: {str(e)}")
                    # Continuar con el siguiente raster
                    continue

            # Finalizar procesamiento
            progress_dialog.finish_processing()
            progress_dialog.destroy()

            # Actualizar columna Idoneidad en SbN_Prioritization.csv
            if sbn_suitability:
                self._update_sbn_suitability(project_folder, sbn_suitability)

            # Calcular estadísticas de la cuenca
            self._calculate_watershed_statistics()

            # Calcular valores por defecto de seguridad hídrica
            self._calculate_default_water_security_values()

            # Calcular valores por defecto de otros desafíos
            self._calculate_default_other_challenges_values()

            # Traer ventana al frente antes de mostrar mensaje
            self.lift()
            self.focus_force()

            # Mostrar mensaje de éxito
            messagebox.showinfo(
                get_text("database_processing.completed_title"),
                get_text("database_processing.completed_message").format(processed_count)
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Cerrar diálogo de progreso si está abierto
            if 'progress_dialog' in locals():
                progress_dialog.finish_processing()
                progress_dialog.destroy()

            messagebox.showerror(
                get_text("database_processing.error_title"),
                get_text("database_processing.error_message").format(str(e))
            )

    def _calculate_watershed_statistics(self):
        """
        Calcula las estadísticas de la cuenca usando los rasters procesados.
        Actualiza self.project_data con los valores calculados.
        """

        try:
            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                print("No se encontró project_folder para calcular estadísticas")
                return

            # Rutas principales
            path_basin = os.path.join(project_folder, "01-Watershed", "Watershed.shp")

            # Verificar que existe el shapefile
            if not os.path.exists(path_basin):
                print(f"No se encontró el shapefile de cuenca: {path_basin}")
                return

            # Calcular área y perímetro
            print("Calculando área y perímetro...")
            area, perimetro = PackCAF.cuenca_area_perimetro(path_basin)

            # Inicializar estructura de datos si no existe
            if 'watershed_data' not in self.project_data:
                self.project_data['watershed_data'] = {}
            if 'morphometry' not in self.project_data['watershed_data']:
                self.project_data['watershed_data']['morphometry'] = {}
            if 'climate' not in self.project_data['watershed_data']:
                self.project_data['watershed_data']['climate'] = {}
            if 'hydrology' not in self.project_data['watershed_data']:
                self.project_data['watershed_data']['hydrology'] = {}
            if 'nutrients' not in self.project_data['watershed_data']:
                self.project_data['watershed_data']['nutrients'] = {}

            # Guardar área y perímetro
            self.project_data['watershed_data']['morphometry']['area'] = round(area, 2)
            self.project_data['watershed_data']['morphometry']['perimeter'] = round(perimetro, 2)

            # Elevación mínima (m.s.n.m)
            print("Calculando elevación mínima...")
            path_raster = os.path.join(project_folder, "02-Rasters", "DEM.tif")
            if os.path.exists(path_raster):
                elev_min = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='min')[0]
                self.project_data['watershed_data']['morphometry']['min_elevation'] = round(elev_min, 2)
            else:
                print(f"No se encontró: {path_raster}")

            # Elevación máxima (m.s.n.m)
            print("Calculando elevación máxima...")
            path_raster = os.path.join(project_folder, "02-Rasters", "DEM.tif")
            if os.path.exists(path_raster):
                elev_max = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='max')[0]
                self.project_data['watershed_data']['morphometry']['max_elevation'] = round(elev_max, 2)
            else:
                print(f"No se encontró: {path_raster}")

            # Pendiente promedio (%)
            print("Calculando pendiente promedio...")
            path_raster = os.path.join(project_folder, "02-Rasters", "Slope.tif")
            if os.path.exists(path_raster):
                value_slope = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='mean')[0]
                self.project_data['watershed_data']['morphometry']['avg_slope'] = round(value_slope, 2)/100
            else:
                print(f"No se encontró: {path_raster}")

            # Precipitación (mm)
            print("Calculando precipitación...")
            path_raster = os.path.join(project_folder, "02-Rasters", "P.tif")
            if os.path.exists(path_raster):
                value_p = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='mean')[0]
                self.project_data['watershed_data']['climate']['precipitation'] = round(value_p, 2)
            else:
                print(f"No se encontró: {path_raster}")

            # Temperatura (Celsius)
            print("Calculando temperatura...")
            path_raster = os.path.join(project_folder, "02-Rasters", "T.tif")
            if os.path.exists(path_raster):
                value_t = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='mean')[0]
                self.project_data['watershed_data']['climate']['temperature'] = round(value_t, 2)
            else:
                print(f"No se encontró: {path_raster}")

            # Evapotranspiración (mm)
            print("Calculando evapotranspiración...")
            path_raster = os.path.join(project_folder, "02-Rasters", "ETP.tif")
            if os.path.exists(path_raster):
                value_etp = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='mean')[0]
                self.project_data['watershed_data']['climate']['evapotranspiration'] = round(value_etp, 2)
            else:
                print(f"No se encontró: {path_raster}")

            # Flujo promedio (m3/seg)
            print("Calculando flujo promedio...")
            path_raster = os.path.join(project_folder, "02-Rasters", "AWY.tif")
            if os.path.exists(path_raster):
                value_awy = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='mean')[0]
                v = (value_awy / 1000.0) * (area * 1.0E6)
                q = v / (3600.0 * 24.0 * 365.0)
                self.project_data['watershed_data']['hydrology']['avg_flow'] = round(q, 4)
            else:
                print(f"No se encontró: {path_raster}")
                v = None

            # Sedimentos (ton) -> (mg/l)
            print("Calculando sedimentos...")
            path_raster = os.path.join(project_folder, "02-Rasters", "SDR.tif")
            if os.path.exists(path_raster) and v is not None:
                value_s_sum = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='sum')[0]
                value_s = (value_s_sum*1000000) / v
                self.project_data['watershed_data']['nutrients']['sediments'] = round(value_s, 4)
            else:
                print(f"No se encontró: {path_raster} o falta valor de v")

            # Nitrógeno (kg) -> (mg/l)
            print("Calculando nitrógeno...")
            path_raster = os.path.join(project_folder, "02-Rasters", "NDR_N.tif")
            if os.path.exists(path_raster) and v is not None:
                value_n_sum = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='sum')[0]
                value_n = (value_n_sum*1000) / v
                self.project_data['watershed_data']['nutrients']['nitrogen'] = round(value_n, 4)
            else:
                print(f"No se encontró: {path_raster} o falta valor de v")

            # Fósforo (kg) -> (mg/l)
            print("Calculando fósforo...")
            path_raster = os.path.join(project_folder, "02-Rasters", "NDR_P.tif")
            if os.path.exists(path_raster) and v is not None:
                value_p_sum = PackCAF.polygon_pixel_stats(path_raster, path_basin, stat='sum')[0]
                value_p_nutrient = (value_p_sum*1000) / v
                self.project_data['watershed_data']['nutrients']['phosphorus'] = round(value_p_nutrient, 4)
            else:
                print(f"No se encontró: {path_raster} o falta valor de v")

            print("✅ Estadísticas de cuenca calculadas exitosamente")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error calculando estadísticas de cuenca: {str(e)}")
            # No mostrar error al usuario, solo log

    def _convert_value_to_category(self, value):
        """
        Convierte un valor numérico (0-100) a una categoría textual.
        Retorna la key para traducción multiidioma.

        Rangos:
        - 0-20: "very_low"
        - 20-40: "low"
        - 40-60: "medium"
        - 60-80: "high"
        - 80-100: "very_high"
        """
        if value < 20:
            return "very_low"
        elif value < 40:
            return "low"
        elif value < 60:
            return "medium"
        elif value < 80:
            return "high"
        else:
            return "very_high"

    def _calculate_default_water_security_values(self):
        """
        Calcula los valores por defecto de los desafíos de seguridad hídrica.
        Guarda resultados en DF_WS.csv en la carpeta del proyecto.
        """
        import pandas as pd
        import numpy as np

        try:
            # Obtener rutas necesarias
            from ..core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            db_path = db_manager.get_database_path()

            if not db_path or not os.path.exists(db_path):
                print("No se encontró la ruta de la base de datos")
                return

            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                print("No se encontró project_folder")
                return

            # Obtener nombre de región y área
            name_region = self.project_data.get('watershed_data', {}).get('point_of_interest', {}).get('macrocuenca')
            area = self.project_data.get('watershed_data', {}).get('morphometry', {}).get('area')

            if not name_region or not area:
                print(f"Faltan datos: NameRegion={name_region}, Area={area}")
                return

            # Rutas principales
            path_basin = os.path.join(project_folder, "01-Watershed", "Watershed.shp")
            cha_path = os.path.join(db_path, "Desafios")

            # Verificar que existe el shapefile
            if not os.path.exists(path_basin):
                print(f"No se encontró el shapefile de cuenca: {path_basin}")
                return

            # Inicializar DataFrames
            dff = pd.DataFrame(index=[0, 1, 2, 3, 4, 5])
            values_cat = pd.DataFrame(columns=['categoria', 'Value'],
                                     data=[[0, 60], [1, 10], [2, 30], [3, 50], [4, 70], [5, 90]])
            values_cat = values_cat.set_index("categoria")

            # Definir bins y labels
            bins_s = [0, 0.05, 0.2, 0.5, 2.0, float('inf')]
            bins_tn = [0, 0.5, 1.0, 3.0, 5.0, float('inf')]
            bins_tp = [0, 0.01, 0.02, 0.05, 0.1, float('inf')]
            labels = [10, 30, 50, 70, 90]

            # Variables para almacenar resultados
            df_s_value = None
            df_4_value = None

            # Procesar cada desafío (i = 1 a 4)
            for i in range(1, 5):
                if i == 3:
                    # WS03 - Sedimentos
                    print(f"Calculando WS0{i} (Sedimentos)...")
                    path_raster = os.path.join(db_path, "Desafios", f"DF{i}", f"DF{i}_{name_region}.tif")

                    if os.path.exists(path_raster):
                        value = PackCAF.polygon_pixel_stats(path_raster, path_basin)[0] / (area * 100)

                        # Clasificar con bins de sedimentos
                        df_temp = pd.DataFrame({"Value": [value]})
                        df_s = pd.cut(df_temp["Value"], bins=bins_s, labels=labels, right=True)
                        df_s_value = int(df_s[0])

                        # Clasificar raster continuo
                        df = PackCAF.classify_continuous_raster(
                            path_basin,
                            path_raster,
                            method='custom',
                            custom_breaks=[0, 0.9, 4.5, 18, 45, 1E10],
                            NameCol=f"DF{i}"
                        )
                        dff = pd.concat([dff, df], axis=1)
                    else:
                        print(f"No se encontró: {path_raster}")

                elif i == 4:
                    # WS04 - Calidad del agua (Nitrógeno y Fósforo)
                    print(f"Calculando WS0{i} (Calidad del agua)...")

                    # Nitrógeno
                    path_raster_n = os.path.join(db_path, "Desafios", f"DF{i}", f"DF{i}_N_{name_region}.tif")
                    if os.path.exists(path_raster_n):
                        value_n = PackCAF.polygon_pixel_stats(path_raster_n, path_basin)[0] / (area * 100)

                        df_temp = pd.DataFrame({"Value": [value_n]})
                        df_n = pd.cut(df_temp["Value"], bins=bins_tn, labels=labels, right=True)

                        dfn = PackCAF.classify_continuous_raster(
                            path_basin,
                            path_raster_n,
                            method='jenks',
                            NameCol=f"DF{i}"
                        )
                    else:
                        print(f"No se encontró: {path_raster_n}")
                        df_n = pd.Series([50])
                        dfn = pd.DataFrame()

                    # Fósforo
                    path_raster_p = os.path.join(db_path, "Desafios", f"DF{i}", f"DF{i}_P_{name_region}.tif")
                    if os.path.exists(path_raster_p):
                        value_p = PackCAF.polygon_pixel_stats(path_raster_p, path_basin)[0] / (area * 100)

                        df_temp = pd.DataFrame({"Value": [value_p]})
                        df_p = pd.cut(df_temp["Value"], bins=bins_tp, labels=labels, right=True)

                        dfp = PackCAF.classify_continuous_raster(
                            path_basin,
                            path_raster_p,
                            method='jenks',
                            NameCol=f"DF{i}"
                        )
                    else:
                        print(f"No se encontró: {path_raster_p}")
                        df_p = pd.Series([50])
                        dfp = pd.DataFrame()

                    # Promedio y máximo
                    if not dfn.empty and not dfp.empty:
                        df = (dfn + dfp) / 2
                        dff = pd.concat([dff, df], axis=1)

                    df_4_value = int(np.max([df_n[0], df_p[0]]))

                else:
                    # WS01 y WS02
                    print(f"Calculando WS0{i}...")
                    path_raster = os.path.join(db_path, "Desafios", f"DF{i}.tif")
                    if os.path.exists(path_raster):
                        df = PackCAF.extract_pixel_counts(path_basin, path_raster, NameCol=f"DF{i}")
                        dff = pd.concat([dff, df], axis=1)
                    else:
                        print(f"No se encontró: {path_raster}")

            # Calcular ValueDF
            value_df = dff.mul(values_cat["Value"], axis=0).sum().div(dff.sum())

            # Asignar valores específicos de WS03 y WS04
            if df_s_value is not None:
                value_df.loc['DF3'] = df_s_value
            if df_4_value is not None:
                value_df.loc['DF4'] = df_4_value

            # Crear CSV con mapeo DF -> WS
            csv_data = []
            for i in range(1, 5):
                df_key = f'DF{i}'
                ws_code = f'WS0{i}'

                if df_key in value_df.index:
                    value = int(round(value_df.loc[df_key]))
                else:
                    value = 50  # Valor por defecto

                csv_data.append({
                    'Codigo_Desafio': ws_code,
                    'Valor_Importancia': value
                })

            # Guardar CSV
            df_csv = pd.DataFrame(csv_data)
            csv_path = os.path.join(project_folder, "DF_WS.csv")
            df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')

            print(f"✅ Valores de seguridad hídrica calculados y guardados en: {csv_path}")
            print(f"Valores: WS01={csv_data[0]['Valor_Importancia']}, WS02={csv_data[1]['Valor_Importancia']}, "
                  f"WS03={csv_data[2]['Valor_Importancia']}, WS04={csv_data[3]['Valor_Importancia']}")

            # Convertir WS01 y WS02 a categorías y guardar en hydrology
            ws01_value = csv_data[0]['Valor_Importancia']  # Flood risk
            ws02_value = csv_data[1]['Valor_Importancia']  # Water stress

            flood_risk_category = self._convert_value_to_category(ws01_value)
            water_stress_category = self._convert_value_to_category(ws02_value)

            # Guardar en project_data
            self.project_data['watershed_data']['hydrology']['flood_risk'] = flood_risk_category
            self.project_data['watershed_data']['hydrology']['water_stress'] = water_stress_category

            print(f"Riesgo de inundación: {ws01_value} → {flood_risk_category}")
            print(f"Estrés hídrico: {ws02_value} → {water_stress_category}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error calculando valores de seguridad hídrica: {str(e)}")
            # No mostrar error al usuario, solo log

    def _calculate_default_other_challenges_values(self):
        """
        Calcula los valores por defecto de otros desafíos.
        Guarda resultados en D_O.csv en la carpeta del proyecto.
        """
        import pandas as pd

        try:
            # Obtener rutas necesarias
            from ..core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            db_path = db_manager.get_database_path()

            if not db_path or not os.path.exists(db_path):
                print("No se encontró la ruta de la base de datos")
                return

            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                print("No se encontró project_folder")
                return

            # Ruta del shapefile de cuenca
            path_basin = os.path.join(project_folder, "01-Watershed", "Watershed.shp")

            if not os.path.exists(path_basin):
                print(f"No se encontró el shapefile de cuenca: {path_basin}")
                return

            # Inicializar DataFrames
            dff = pd.DataFrame(index=[0, 1, 2, 3, 4, 5])
            values_cat = pd.DataFrame(columns=['categoria', 'Value'],
                                     data=[[0, 60], [1, 10], [2, 30], [3, 50], [4, 70], [5, 90]])
            values_cat = values_cat.set_index("categoria")

            # Procesar desafíos DF5 a DF13
            for i in range(5, 14):
                print(f"Calculando DF{i}...")
                path_raster = os.path.join(db_path, "Desafios", f"DF{i}.tif")
                if os.path.exists(path_raster):
                    df = PackCAF.extract_pixel_counts(path_basin, path_raster, NameCol=f"DF{i}")
                    dff = pd.concat([dff, df], axis=1)
                else:
                    print(f"No se encontró: {path_raster}")

            # Calcular ValueDF
            value_df = dff.mul(values_cat["Value"], axis=0).sum().div(dff.sum())

            # Mapeo de DF a OC
            df_to_oc_mapping = {
                'DF5': ['OC01', 'OC02'],
                'DF6': ['OC03', 'OC04', 'OC05'],
                'DF7': ['OC06'],
                'DF8': ['OC07', 'OC08', 'OC09'],
                'DF9': ['OC10', 'OC11', 'OC12'],
                'DF10': ['OC13', 'OC14', 'OC15', 'OC16'],
                'DF11': ['OC17', 'OC18', 'OC19'],
                'DF12': ['OC20', 'OC21', 'OC22', 'OC23', 'OC24'],
                'DF13': ['OC25']
            }

            # Crear CSV con todos los OC
            csv_data = []
            for df_key, oc_codes in df_to_oc_mapping.items():
                # Obtener valor del DF (o valor por defecto si no existe)
                if df_key in value_df.index:
                    value = int(round(value_df.loc[df_key]))
                else:
                    value = 50  # Valor por defecto

                # Asignar el mismo valor a todos los OC asociados a este DF
                for oc_code in oc_codes:
                    csv_data.append({
                        'Codigo_Desafio': oc_code,
                        'Valor_Importancia': value
                    })

            # Guardar CSV
            df_csv = pd.DataFrame(csv_data)
            csv_path = os.path.join(project_folder, "D_O.csv")
            df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')

            print(f"✅ Valores de otros desafíos calculados y guardados en: {csv_path}")
            print(f"Total de desafíos: {len(csv_data)} (OC01 a OC25)")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error calculando valores de otros desafíos: {str(e)}")
            # No mostrar error al usuario, solo log

    def _update_sbn_suitability(self, project_folder, sbn_suitability):
        """
        Actualiza la columna Idoneidad en SbN_Prioritization.csv basado en la
        disponibilidad de datos en los rasters SbN.

        Args:
            project_folder: Ruta de la carpeta del proyecto
            sbn_suitability: dict {sbn_id: 0 o 1}
                             1 = tiene datos válidos (idóneo)
                             0 = sin datos o solo nodata (no idóneo)
        """
        import pandas as pd

        try:
            prioritization_file = os.path.join(project_folder, 'SbN_Prioritization.csv')

            if not os.path.exists(prioritization_file):
                print(f"⚠ No se encontró {prioritization_file}")
                return

            # Leer archivo de priorización
            df = pd.read_csv(prioritization_file, encoding='utf-8-sig')

            # Actualizar columna Idoneidad
            for sbn_id, suitability in sbn_suitability.items():
                mask = df['ID'] == sbn_id
                if mask.any():
                    df.loc[mask, 'Idoneidad'] = suitability

            # Guardar archivo actualizado (NO recalculamos Prioridad aquí)
            df.to_csv(prioritization_file, index=False, encoding='utf-8-sig')

            # Contar SbN idóneas y no idóneas
            suitable_count = sum(1 for v in sbn_suitability.values() if v == 1)
            unsuitable_count = sum(1 for v in sbn_suitability.values() if v == 0)

            print(f"✅ Idoneidad actualizada en SbN_Prioritization.csv")
            print(f"   SbN idóneas (con datos): {suitable_count}")
            print(f"   SbN no idóneas (sin datos): {unsuitable_count}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠ Error actualizando idoneidad SbN: {str(e)}")

    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        try:
            # Actualizar título de la ventana
            self.title(get_text("watershed.title"))

            # Actualizar header
            if hasattr(self, 'title_label'):
                self.title_label.configure(text=get_text("watershed.main_title"))

            if hasattr(self, 'subtitle_label') and self.project_data:
                project_name = self.project_data.get('project_info', {}).get('name', get_text("messages.not_available"))
                self.subtitle_label.configure(text=f"{get_text('watershed.project_label')} {project_name}")

            # Actualizar panel de información
            if hasattr(self, 'panel_title'):
                self.panel_title.configure(text=get_text("watershed.info_title"))

            # Actualizar coordenadas
            if hasattr(self, 'coords_title'):
                self.coords_title.configure(text=get_text("watershed.coordinates_title"))

            # Actualizar display de coordenadas solo si no hay coordenadas seleccionadas
            if hasattr(self, 'coords_display') and self.lat is None:
                self.coords_display.configure(text=get_text("watershed.coordinates_none"))

            # Actualizar botón manual
            if hasattr(self, 'manual_btn'):
                self.manual_btn.configure(text=get_text("watershed.manual_input"))

            # Actualizar título de macrocuenca
            if hasattr(self, 'result_title'):
                self.result_title.configure(text=get_text("watershed.watershed_title"))

            # Actualizar display de cuenca solo si no hay cuenca delimitada
            if hasattr(self, 'watershed_display') and self.current_watershed is None:
                self.watershed_display.configure(text=get_text("watershed.watershed_pending"))

            # Actualizar estado solo si está en estado inicial
            if hasattr(self, 'status_label') and self.lat is None:
                self.status_label.configure(text=get_text("watershed.waiting_coordinates"))

            # Actualizar botón seleccionar punto según el estado
            if hasattr(self, 'select_point_btn'):
                if self.point_selection_mode:
                    self.select_point_btn.configure(text=get_text("watershed.confirm_point"))
                else:
                    self.select_point_btn.configure(text=get_text("watershed.select_point_map"))

            # Actualizar botón delimitar
            if hasattr(self, 'delimit_btn'):
                self.delimit_btn.configure(text=get_text("watershed.delimit_button"))

            # Actualizar botón guardar y cerrar
            if hasattr(self, 'save_and_close_btn'):
                self.save_and_close_btn.configure(text=get_text("watershed.save_and_close"))

            # Actualizar botón definir área SbN según el estado
            if hasattr(self, 'define_sbn_btn'):
                if self.drawing_sbn_mode:
                    self.define_sbn_btn.configure(text=get_text("watershed.confirm_sbn_area"))
                else:
                    self.define_sbn_btn.configure(text=get_text("watershed.define_sbn_area"))

            # Actualizar botones
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(text=get_text("watershed.cancel"))

            if hasattr(self, 'save_btn'):
                self.save_btn.configure(text=get_text("watershed.save_project"))

        except Exception as e:
            # Fail silently si no se pueden actualizar los textos
            print(f"Error updating texts: {e}")

    def _load_existing_watershed(self):
        """Cargar shapefile de cuenca existente"""
        try:
            print(f"🔍 Intentando cargar shapefile: {self.watershed_shapefile}")

            # Verificar que el archivo existe
            if not os.path.exists(self.watershed_shapefile):
                print(f"❌ Archivo no encontrado: {self.watershed_shapefile}")
                return

            # Leer shapefile
            gdf = gpd.read_file(self.watershed_shapefile)
            print(f"✓ Shapefile leído: {len(gdf)} geometrías")

            if len(gdf) == 0:
                print("❌ Shapefile vacío")
                return

            # Obtener coordenadas del punto de cierre desde project_data
            outlet_lat = None
            outlet_lon = None

            if self.project_data:
                # Intentar obtener desde point_of_interest (prioridad 1)
                point_of_interest = self.project_data.get('watershed_data', {}).get('point_of_interest', {})
                outlet_lat = point_of_interest.get('lat')
                outlet_lon = point_of_interest.get('lon')

                # Fallback: usar coordinates si point_of_interest no existe (prioridad 2)
                if outlet_lat is None or outlet_lon is None:
                    coordinates = self.project_data.get('watershed_data', {}).get('coordinates', {})
                    outlet_lat = coordinates.get('latitude')
                    outlet_lon = coordinates.get('longitude')

            # Si encontramos coordenadas guardadas, usarlas
            if outlet_lat is not None and outlet_lon is not None:
                self.lat = outlet_lat
                self.lon = outlet_lon
                print(f"✓ Coordenadas del punto de cierre: lat={self.lat}, lon={self.lon}")
            else:
                # Fallback: calcular centroide si no hay coordenadas guardadas
                if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
                    gdf_latlon = gdf.to_crs('EPSG:4326')
                    centroid = gdf_latlon.geometry.iloc[0].centroid
                else:
                    centroid = gdf.geometry.iloc[0].centroid

                self.lat = centroid.y
                self.lon = centroid.x
                print(f"✓ Coordenadas del centroide (fallback): lat={self.lat}, lon={self.lon}")

            # Extraer nombre de la cuenca si existe en los atributos
            watershed_name = "Cuenca_Existente"
            if 'Name' in gdf.columns:
                watershed_name = gdf['Name'].iloc[0]
            elif 'name' in gdf.columns:
                watershed_name = gdf['name'].iloc[0]
            print(f"✓ Nombre de cuenca: {watershed_name}")

            # Establecer current_watershed
            self.current_watershed = {
                'name': watershed_name,
                'lat': self.lat,
                'lon': self.lon,
                'coordinates': [self.lon, self.lat],
                'shapefile': self.watershed_shapefile
            }

            # Guardar coordenadas en project_data
            if self.project_data:
                if 'watershed_data' not in self.project_data:
                    self.project_data['watershed_data'] = {}

                self.project_data['watershed_data']['coordinates'] = {
                    'latitude': self.lat,
                    'longitude': self.lon
                }

            # Actualizar UI
            if hasattr(self, 'lat_entry') and self.lat_entry:
                self.lat_entry.delete(0, 'end')
                self.lat_entry.insert(0, str(round(self.lat, 6)))

            if hasattr(self, 'lon_entry') and self.lon_entry:
                self.lon_entry.delete(0, 'end')
                self.lon_entry.insert(0, str(round(self.lon, 6)))

            if hasattr(self, 'watershed_display'):
                self.watershed_display.configure(
                    text=f"{watershed_name}\n\n{get_text('watershed.existing_loaded')}",
                    text_color=ThemeManager.COLORS['success']
                )

            if hasattr(self, 'status_label'):
                self.status_label.configure(
                    text=get_text('watershed.existing_loaded'),
                    text_color=ThemeManager.COLORS['success']
                )

            # Habilitar botones de guardado
            if hasattr(self, 'save_btn'):
                self.save_btn.configure(state="normal")
            if hasattr(self, 'save_and_close_btn'):
                self.save_and_close_btn.configure(state="normal")

            # Habilitar botón de definir área SbN (ya que la cuenca existe)
            if hasattr(self, 'define_sbn_btn'):
                self.define_sbn_btn.configure(state="normal")

            # Actualizar display de coordenadas y habilitar delimitación
            if hasattr(self, 'coords_display'):
                self.coords_display.configure(
                    text=f"Lat: {self.lat:.6f}\nLon: {self.lon:.6f}",
                    text_color=ThemeManager.COLORS['text_primary']
                )

            if hasattr(self, 'delimit_btn'):
                self.delimit_btn.configure(state="normal")

            # Graficar shapefile en el mapa y hacer zoom
            print(f"🗺️  Graficando shapefile en el mapa...")
            if hasattr(self, 'map_viewer') and self.map_viewer:
                print(f"✓ map_viewer disponible")

                # Agregar capa vectorial al mapa
                success_vector = self.map_viewer.add_vector_layer(
                    self.watershed_shapefile,
                    layer_name="watershed",
                    color='lightblue',
                    alpha=0.5,
                    linewidth=2
                )
                print(f"{'✓' if success_vector else '❌'} add_vector_layer: {success_vector}")

                # Marcar punto de cierre en el mapa
                if self.lat is not None and self.lon is not None:
                    self.map_viewer.set_coordinates(self.lat, self.lon)
                    print(f"✓ Punto de cierre marcado en el mapa")

                # Centrar y hacer zoom específico a la cuenca con margen mínimo
                # if success_vector:
                    self.map_viewer.zoom_to_vector(self.watershed_shapefile, padding_factor=0.05)
            else:
                print("❌ map_viewer NO disponible")

            print(f"✅ Cuenca existente cargada y graficada: {watershed_name}")

        except Exception as e:
            print(f"❌ Error cargando shapefile existente: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showwarning(
                get_text("messages.warning"),
                f"No se pudo cargar la cuenca existente: {str(e)}"
            )

    def _zoom_to_watershed(self):
        """Hacer zoom a la cuenca cargada (callback para botón de reset del mapa)"""
        if self.watershed_shapefile and os.path.exists(self.watershed_shapefile):
            try:
                self.map_viewer.zoom_to_vector(self.watershed_shapefile, padding_factor=0.05)
                print("🌍 Vista centrada en la cuenca")
            except Exception as e:
                print(f"⚠️ Error al hacer zoom a cuenca: {e}")
        else:
            print("⚠️ No hay cuenca cargada para centrar")

    def _load_saved_coordinates(self, lat, lon):
        """Cargar coordenadas guardadas previamente"""
        try:
            print(f"🔍 Cargando coordenadas guardadas: lat={lat}, lon={lon}")

            # Establecer coordenadas
            self.lat = lat
            self.lon = lon

            # Actualizar display de coordenadas
            if hasattr(self, 'coords_display'):
                self.coords_display.configure(
                    text=f"Lat: {lat:.6f}\nLon: {lon:.6f}",
                    text_color=ThemeManager.COLORS['text_primary']
                )

            # Centrar mapa y marcar punto
            if hasattr(self, 'map_viewer') and self.map_viewer:
                self.map_viewer._set_coordinates_and_center(lat, lon)

            # Habilitar botón de delimitación
            if hasattr(self, 'delimit_btn'):
                self.delimit_btn.configure(state="normal")

            # Actualizar status
            if hasattr(self, 'status_label'):
                self.status_label.configure(
                    text=get_text("watershed.coordinates_selected"),
                    text_color=ThemeManager.COLORS['success']
                )

            print(f"✅ Coordenadas guardadas cargadas exitosamente")

        except Exception as e:
            print(f"❌ Error cargando coordenadas guardadas: {e}")
            import traceback
            traceback.print_exc()

    def _on_closing(self):
        """Cerrar ventana de forma segura"""
        self.destroy()

class CoordinateInputDialog(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)

        self.title(get_text("coordinate_dialog.title"))
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])
        self.result = None

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        self._setup_ui()

        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        self.title_label = ctk.CTkLabel(
            main_frame,
            text=get_text("coordinate_dialog.title"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.title_label.pack(pady=(0, 20))

        # Campos de entrada
        form_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        form_frame.pack(fill="x", pady=(0, 20))

        self.lat_label = ctk.CTkLabel(form_frame, text=get_text("coordinate_dialog.latitude"), **ThemeManager.get_label_style())
        self.lat_label.pack(anchor="w", padx=20, pady=(20, 5))
        self.lat_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text=get_text("coordinate_dialog.latitude_placeholder"),
            **ThemeManager.get_entry_style()
        )
        self.lat_entry.pack(fill="x", padx=20, pady=(0, 15))

        self.lon_label = ctk.CTkLabel(form_frame, text=get_text("coordinate_dialog.longitude"), **ThemeManager.get_label_style())
        self.lon_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.lon_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text=get_text("coordinate_dialog.longitude_placeholder"),
            **ThemeManager.get_entry_style()
        )
        self.lon_entry.pack(fill="x", padx=20, pady=(0, 20))

        # Botones
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text=get_text("coordinate_dialog.cancel"),
            width=120,
            command=self._cancel,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary']
        )
        self.cancel_btn.pack(side="right", padx=(15, 0))

        self.ok_btn = ctk.CTkButton(
            button_frame,
            text=get_text("coordinate_dialog.accept"),
            width=120,
            command=self._accept,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.ok_btn.pack(side="right")
    
    def _accept(self):
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())

            # Validar rangos básicos
            if not (-90 <= lat <= 90):
                raise ValueError(get_text("coordinate_dialog.latitude_range"))
            if not (-180 <= lon <= 180):
                raise ValueError(get_text("coordinate_dialog.longitude_range"))

            self.result = (lat, lon)
            self.destroy()

        except ValueError as e:
            messagebox.showerror(
                get_text("messages.error"),
                f"{get_text('coordinate_dialog.invalid_coordinates')}: {str(e)}"
            )

    def _cancel(self):
        self.destroy()

    def _update_texts(self):
        """Actualizar todos los textos cuando cambia el idioma"""
        try:
            # Actualizar título de la ventana
            self.title(get_text("coordinate_dialog.title"))

            # Actualizar widgets
            if hasattr(self, 'title_label'):
                self.title_label.configure(text=get_text("coordinate_dialog.title"))

            if hasattr(self, 'lat_label'):
                self.lat_label.configure(text=get_text("coordinate_dialog.latitude"))

            if hasattr(self, 'lat_entry'):
                self.lat_entry.configure(placeholder_text=get_text("coordinate_dialog.latitude_placeholder"))

            if hasattr(self, 'lon_label'):
                self.lon_label.configure(text=get_text("coordinate_dialog.longitude"))

            if hasattr(self, 'lon_entry'):
                self.lon_entry.configure(placeholder_text=get_text("coordinate_dialog.longitude_placeholder"))

            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(text=get_text("coordinate_dialog.cancel"))

            if hasattr(self, 'ok_btn'):
                self.ok_btn.configure(text=get_text("coordinate_dialog.accept"))

        except Exception as e:
            # Fail silently si no se pueden actualizar los textos
            print(f"Error updating coordinate dialog texts: {e}")

class ProgressDialog(ctk.CTkToplevel):
    """Ventana de progreso simple con barra indeterminada"""

    def __init__(self, parent, title_key="watershed.processing_title", message_key="watershed.delimit_process"):
        super().__init__(parent)

        self.title(get_text(title_key))
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # No permitir cerrar la ventana
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self._setup_ui(message_key)

        # Renderizar ventana antes de continuar
        self.update()
        self.grab_set()

    def _setup_ui(self, message_key):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # Mensaje
        message_label = ctk.CTkLabel(
            main_frame,
            text=get_text(message_key),
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_primary']
        )
        message_label.pack(pady=(10, 20))

        # Barra de progreso indeterminada
        progress_bar = ctk.CTkProgressBar(
            main_frame,
            mode="indeterminate",
            width=300
        )
        progress_bar.pack(pady=10)
        progress_bar.start()  # Iniciar animación