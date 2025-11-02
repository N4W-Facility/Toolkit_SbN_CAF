import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
import contextily as ctx
import numpy as np
import os
from tkinter import messagebox
from ..core.theme_manager import ThemeManager

try:
    import geopandas as gpd
    from shapely.geometry import Point
    import mercantile
    GEOPANDAS_AVAILABLE = True
    print("Geopandas disponible ✅")
except ImportError:
    GEOPANDAS_AVAILABLE = False
    print("Geopandas NO disponible ❌")

class MatplotlibMapViewer(ctk.CTkFrame):
    
    def __init__(self, parent, hide_colormap_controls=False, reset_callback=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Configuración de controles
        self.hide_colormap_controls = hide_colormap_controls
        self.reset_callback = reset_callback  # Callback personalizado para botón de reset

        self.selected_lat = None
        self.selected_lon = None
        self.coordinate_callback = None
        self.current_marker = None

        # Modos de interacción
        self.point_selection_mode = False
        self.rectangle_draw_mode = False
        self.rectangle_callback = None

        # Variables para dibujo de rectángulo
        self.rect_start_x = None
        self.rect_start_y = None
        self.temp_marker = None  # Punto temporal del primer clic
        self.current_rectangle = None  # Rectángulo actual (solo el último)
        self.drawn_rectangle_coords = None
        self.shapefile_patches = []

        # Configuración del mapa
        self.center_lat = 10  # Centro de América
        self.center_lon = -75
        self.zoom_level = 3
        
        # Variables para interacción fluida
        self.is_panning = False
        self.pan_start_x = None
        self.pan_start_y = None
        self.last_xlim = None
        self.last_ylim = None

        self._basemap_im = None
        self._current_zoom = None
        self._tile_source = None
        self._reload_job = None

        # Control de repintado y labels
        self._basemap_im = None
        self._current_zoom = None
        self._tile_source = None
        self._reload_job = None

        self._last_paint_ms = 0  # throttle de dibujo (ms)
        self._last_coords_ms = 0  # throttle coords (ms)
        self._pan_fast_mode = False  # interp. rápida durante el pan

        self._setup_ui()
        self._create_map()

        # Precarga deshabilitada: con caché persistente en AppData, solo descargamos bajo demanda
        # La precarga desde z=4 era redundante y causaba descargas innecesarias al abrir el visor
        # try:
        #     bbox_latam = (-118.0, -56.0, -34.0, 33.0)
        #     self.precache_tiles(bbox_latam, zmin=4, zmax=12, provider=ctx.providers.OpenStreetMap.Mapnik)
        # except Exception as e:
        #     print(f"Precarga omitida: {e}")

    
    def _setup_ui(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Toolbar superior
        toolbar_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        toolbar_frame.pack(fill="x", pady=(0, 5))
        
        self._create_toolbar(toolbar_frame)
        
        # Frame para el mapa
        self.map_container = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        self.map_container.pack(fill="both", expand=True)
        
        # Crear el visor matplotlib
        self._create_matplotlib_viewer()

    def precache_tiles(self, bbox_wgs84, zmin, zmax, provider=None):
        """
        Precalienta/descarga a caché local las teselas de un BBOX (WGS84) para zmin..zmax.
        Corre en segundo plano, pero TODA actualización de UI se enruta al hilo principal.
        """
        import threading
        import contextily as ctx

        # Helper seguro para UI
        def _ui(update_fn, *args, **kwargs):
            try:
                self.after(0, lambda: update_fn(*args, **kwargs))
            except Exception:
                pass

        # Si aún no existe el label, no intentes usarlo
        def _set_status(msg, color_key="info"):
            if hasattr(self, "status_label"):
                _ui(self.status_label.configure,
                    text=msg, text_color=ThemeManager.COLORS.get(color_key, "#333"))
            else:
                print(msg)

        lon_min, lat_min, lon_max, lat_max = bbox_wgs84
        src = provider if provider is not None else self._get_tile_source()

        def _worker():
            try:
                _set_status("📦 Precargando tiles...", "info")
                for z in range(int(zmin), int(zmax) + 1):
                    # Nota: bbox en WGS84 ⇒ ll=True
                    img, ext = ctx.bounds2img(
                        lon_min, lat_min, lon_max, lat_max,
                        source=src, zoom=z, ll=True, use_cache=True
                    )
                    print(f"Precache z={z}: {img.shape}")
                _set_status(f"✅ Precarga completa z={zmin}..{zmax}", "success")
            except Exception as e:
                print(f"❌ Precarga error: {e}")
                _set_status("❌ Error precargando", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _draw_basemap(self, xlim=None, ylim=None, force=False):
        try:
            # Validar que ax existe y está en estado válido
            if self.ax is None:
                print("❌ _draw_basemap: self.ax is None, skipping")
                return

            # Validar que ax tiene los atributos necesarios (puede no tenerlos justo después de clear())
            if not hasattr(self.ax, 'xaxis') or self.ax.xaxis is None:
                print("❌ _draw_basemap: ax no está completamente inicializado, skipping")
                return

            # Intentar obtener límites con manejo de errores
            try:
                if xlim is None: xlim = self.ax.get_xlim()
                if ylim is None: ylim = self.ax.get_ylim()
            except (AttributeError, TypeError) as e:
                # Axes no está completamente inicializado
                print(f"❌ _draw_basemap: axes no listo (get_xlim/ylim falló), skipping")
                return

            xmin, xmax = xlim;
            ymin, ymax = ylim

            tile_source = self._get_tile_source()

            # Zoom crisp + 'boost' opcional (cap al límite del proveedor)
            # Pasar xlim para evitar get_xlim() en axes que no está listo
            base_zoom = int(self._calculate_safe_zoom_level(xlim=xlim))
            boost = 0  # prueba 1 si quieres aún más detalle
            zoom = base_zoom + boost

            # Evita trabajo inútil
            if (not force and
                    self._basemap_im is not None and
                    zoom == self._current_zoom and
                    tile_source == self._tile_source):
                return

            img, extent = ctx.bounds2img(
                xmin, ymin, xmax, ymax,
                source=tile_source, zoom=zoom,
                ll=False, use_cache=True
            )

            if self._basemap_im is None:
                self._basemap_im = self.ax.imshow(
                    img, extent=extent, zorder=0,
                    interpolation='bilinear' if not self._pan_fast_mode else 'nearest'
                )
            else:
                self._basemap_im.set_data(img)
                self._basemap_im.set_extent(extent)
                # Mantén bilinear fuera del pan (es más bonito)
                if not self._pan_fast_mode:
                    try:
                        self._basemap_im.set_interpolation('bilinear')
                    except:
                        pass

            self._current_zoom = zoom
            self._tile_source = tile_source
            self.canvas.draw_idle()

        except (AttributeError, TypeError) as e:
            # Error típico cuando axes no está completamente inicializado
            if "_process_unit_info" in str(e) or "NoneType" in str(e):
                # Re-lanzar para que _draw_basemap_safe pueda reintentar
                raise
            else:
                print(f"❌ _draw_basemap error: {e}")
                raise
        except Exception as e:
            print(f"❌ _draw_basemap error: {e}")
            try:
                self.ax.set_facecolor('#E8E8E8')
                self.canvas.draw_idle()
            except:
                pass
            raise

    def _create_toolbar(self, parent):
        toolbar_container = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=15, pady=10)
        
        # Título
        title_label = ctk.CTkLabel(
            toolbar_container,
            text="🗺️ Mapa Interactivo",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack(side="left")
        
        # Controles organizados en dos filas
        controls_container = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        controls_container.pack(side="right")
        
        # Fila superior - controles principales
        top_controls = ctk.CTkFrame(controls_container, fg_color="transparent")
        top_controls.pack(side="top", anchor="e", pady=(0, 5))
        
        # Selector de tipo de mapa
        self.map_type_var = ctk.StringVar(value="OpenStreetMap")
        map_type_menu = ctk.CTkOptionMenu(
            top_controls,
            values=["OpenStreetMap", "CartoDB Positron", "CartoDB Voyager", "ESRI World Imagery", "Stamen Terrain"],
            variable=self.map_type_var,
            command=self._change_map_type,
            width=160  # Aumentar ancho para acomodar nombres más largos
        )
        map_type_menu.pack(side="right", padx=8)

        # Botón para resetear vista (comportamiento personalizable)
        # Si hay callback personalizado, se usa ese; sino, vuelve a vista por defecto de Latinoamérica
        reset_view_btn = ctk.CTkButton(
            top_controls,
            text="🌍",
            command=self._handle_reset_view,
            width=30,
            height=32,
            font=ThemeManager.FONTS['body']
        )
        reset_view_btn.pack(side="right", padx=8)

        # Frame para selector de colormap con label (solo si no está oculto)
        if not self.hide_colormap_controls:
            colormap_frame = ctk.CTkFrame(top_controls, fg_color="transparent")
            colormap_frame.pack(side="right", padx=8)

            # Label para el selector
            colormap_label = ctk.CTkLabel(
                colormap_frame,
                text="🎨",
                font=ctk.CTkFont(size=12),
                text_color=ThemeManager.COLORS['text_secondary']
            )
            colormap_label.pack(side="left", padx=(0, 5))

            # Selector de rampa de colores para rasters
            self.colormap_var = ctk.StringVar(value="Viridis")
            colormap_menu = ctk.CTkOptionMenu(
                colormap_frame,
                values=["Viridis", "Verde-Rojo", "Tierra", "Plasma", "Océano"],
                variable=self.colormap_var,
                command=self._change_colormap,
                width=110,
                height=32
            )
            colormap_menu.pack(side="left")
        else:
            # Si está oculto, inicializar la variable con un valor por defecto
            self.colormap_var = ctk.StringVar(value="Viridis")

        # Fila inferior - información
        bottom_controls = ctk.CTkFrame(controls_container, fg_color="transparent")
        bottom_controls.pack(side="top", anchor="e")
        
        # Status del mapa
        self.status_label = ctk.CTkLabel(
            bottom_controls,
            text="🔄 Cargando...",
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['warning']
        )
        self.status_label.pack(side="right", padx=10)
        
        # Información de coordenadas
        self.coords_label = ctk.CTkLabel(
            bottom_controls,
            text="📍 Haga clic en el mapa para seleccionar",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.coords_label.pack(side="right", padx=15)
    
    def _create_matplotlib_viewer(self):
        """Crear visor matplotlib embebido"""
        try:
            # Configurar matplotlib para que se vea bonito
            plt.rcParams.update({
                'font.size': 9,
                'axes.titlesize': 10,
                'axes.labelsize': 9,
                'xtick.labelsize': 8,
                'ytick.labelsize': 8,
                'figure.titlesize': 12,
                'toolbar': 'toolmanager'
            })
            
            # Crear figura con mejor proporción
            # layout='none' deshabilita autolayout para mantener tamaño fijo del axes
            self.fig = Figure(figsize=(20, 8), facecolor='none', dpi=100, layout='none')
            self.ax = self.fig.add_subplot(111)

            # Márgenes fijos (control manual del tamaño del axes)
            # Valores de 0 a 1 (fracción de la figura)
            self.fig.subplots_adjust(left=0.08, right=0.95, bottom=0.08, top=0.95)
            
            # Crear canvas embebido con más espacio
            self.canvas = FigureCanvasTkAgg(self.fig, self.map_container)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
            
            # Conectar eventos para interacción fluida
            self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
            self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
            self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
            self.canvas.mpl_connect('scroll_event', self._on_scroll)
            
            # Hacer que el canvas pueda recibir focus para eventos
            self.canvas.get_tk_widget().focus_set()
            
            self.status_label.configure(text="✅ Visor creado", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self._show_error(f"Error al crear visor: {str(e)}")

    def _create_map(self):
        """Crear mapa inicial con vista por defecto sin bloquear la UI."""
        try:
            self.status_label.configure(text="🌍 ...", text_color=ThemeManager.COLORS['warning'])

            self.ax.clear()

            # Configurar límites iniciales (EPSG:3857)
            west, south, east, north = self._get_bounds_from_center(
                self.center_lat, self.center_lon, self.zoom_level
            )
            self.ax.set_xlim(west, east)
            self.ax.set_ylim(south, north)

            # Apariencia (menos costo de repintado)
            # adjustable='box' fija el tamaño del axes, aspect='equal' mantiene proporciones del mapa
            self.ax.set_aspect('equal', adjustable='box')
            # Evita grid por defecto (caro con imágenes grandes)
            self.ax.grid(False)

            # Configurar formateadores para mostrar coordenadas en lat/lon en lugar de Web Mercator
            self._setup_axes_formatters()

            # Forzar actualización del canvas para que axes se inicialice completamente
            self.canvas.draw_idle()

            # Pintar basemap después de dar tiempo a que axes se inicialice
            # Pasamos los límites explícitamente para evitar get_xlim/ylim en axes recién limpiado
            xlim = (west, east)
            ylim = (south, north)
            self.after(100, lambda: self._draw_basemap_safe(xlim, ylim))

        except Exception as e:
            self._show_error(f"Error al cargar mapa: {str(e)}")

    def _draw_basemap_safe(self, xlim=None, ylim=None, retry_count=0):
        """Wrapper seguro para dibujar basemap con actualización de estado y reintentos"""
        try:
            # Verificar que axes está completamente listo antes de intentar
            if (self.ax is None or
                not hasattr(self.ax, 'xaxis') or
                not hasattr(self.ax, 'yaxis') or
                self.ax.xaxis is None or
                self.ax.yaxis is None or
                not hasattr(self.fig, 'canvas') or
                self.canvas is None):

                if retry_count < 5:  # Aumentar a 5 reintentos
                    # Esperar más y reintentar
                    delay = 150 * (retry_count + 1)  # 150ms, 300ms, 450ms, 600ms, 750ms
                    self.after(delay, lambda: self._draw_basemap_safe(xlim, ylim, retry_count + 1))
                    return
                else:
                    error_msg = "❌ Axes no se inicializó después de varios reintentos"
                    print(error_msg)
                    self.status_label.configure(
                        text="⚠️ Error al cargar mapa",
                        text_color=ThemeManager.COLORS['error']
                    )
                    return

            self._draw_basemap(xlim=xlim, ylim=ylim, force=True)
            self.status_label.configure(text="✅ Mapa cargado", text_color=ThemeManager.COLORS['success'])
        except Exception as e:
            if retry_count < 5:  # Aumentar a 5 reintentos
                # Si falla, reintentar
                delay = 150 * (retry_count + 1)
                self.after(delay, lambda: self._draw_basemap_safe(xlim, ylim, retry_count + 1))
            else:
                error_msg = f"Error en _draw_basemap_safe después de {retry_count} reintentos: {e}"
                print(error_msg)
                self.status_label.configure(
                    text="⚠️ Error al cargar mapa",
                    text_color=ThemeManager.COLORS['error']
                )

    def _create_map_overlay(self):
        """
        Actualiza sólo el basemap sin tocar demás capas.
        Reutiliza el imshow persistente y respeta los límites actuales.
        """
        try:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            self._draw_basemap(xlim, ylim, force=False)
        except Exception as e:
            print(f"❌ Error en overlay: {e}")

    def _get_tile_source(self):
        """Obtener fuente de tiles según selección"""
        map_type = self.map_type_var.get()
        
        sources = {
            "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
            "CartoDB Positron": ctx.providers.CartoDB.Positron,
            "CartoDB Voyager": ctx.providers.CartoDB.Voyager,  # Buena cobertura global
            "ESRI World Imagery": ctx.providers.Esri.WorldImagery,  # Imágenes satelitales
            "Stamen Terrain": ctx.providers.Stamen.Terrain
        }
        
        return sources.get(map_type, ctx.providers.OpenStreetMap.Mapnik)

    def _get_colormap(self):
        """Obtener colormap matplotlib según selección"""
        colormap_name = self.colormap_var.get()

        colormap_mappings = {
            "Viridis": plt.cm.viridis,        # Azul-Verde-Amarillo clásico
            "Verde-Rojo": plt.cm.RdYlGn_r,    # Rojo-Amarillo-Verde (bueno para riesgo)
            "Tierra": plt.cm.terrain,         # Colores naturales tierra
            "Plasma": plt.cm.plasma,          # Púrpura-Rosa-Amarillo
            "Océano": plt.cm.ocean            # Azul-Verde océano
        }

        return colormap_mappings.get(colormap_name, plt.cm.viridis)

    def _change_colormap(self, colormap_name):
        """Cambiar colormap de todos los rasters cargados"""
        try:
            if not hasattr(self, 'raster_layers') or not self.raster_layers:
                # No hay rasters cargados, solo mostrar mensaje
                print(f"🎨 Colormap cambiado a {colormap_name} (se aplicará a futuros rasters)")
                return

            print(f"🎨 Cambiando colormap de {len(self.raster_layers)} rasters a {colormap_name}...")

            # Obtener el colormap correspondiente
            new_cmap = self._get_colormap()
            new_cmap.set_bad(alpha=0)  # Valores no válidos transparentes

            # Aplicar el nuevo colormap a todos los rasters cargados
            for layer_name, raster_plot in self.raster_layers.items():
                raster_plot.set_cmap(new_cmap)

            # Actualizar canvas
            self.canvas.draw()

            print(f"✅ Colormap {colormap_name} aplicado exitosamente a todos los rasters")

        except Exception as e:
            print(f"❌ Error cambiando colormap: {e}")

    def _calculate_safe_zoom_level(self, xlim=None):
        """
        Zoom 'crisp' calculado con base en:
        - Extensión visible (en metros, EPSG:3857)
        - Ancho del widget (píxeles reales)
        - Oversampling (p.ej. 1.6x) para nítido en pantallas HiDPI
        """
        try:
            # 1) Extensión actual (m)
            if xlim is None:
                try:
                    xlim = self.ax.get_xlim()
                except (AttributeError, TypeError):
                    # Axes no está listo
                    return 12  # fallback
            width_m = max(1e-6, xlim[1] - xlim[0])

            # 2) Píxeles reales del canvas (evita 0)
            widget_w = max(1, self.canvas.get_tk_widget().winfo_width())

            # 3) Oversampling para nitidez (ajusta 1.4–2.0 según tu gusto)
            oversample = 1.2
            target_mpp = width_m / (widget_w * oversample)

            # 4) Resolución a nivel z (m/px) para tile 256 px (WebMercator en el ecuador)
            # res(z) = 156543.03392804097 / 2^z
            import math
            raw_zoom = math.log2(156543.03392804097 / target_mpp)
            zoom_level = int(max(0, math.floor(raw_zoom)))  # entero hacia abajo

            # 5) Límite por proveedor (no pidas más de lo que existe)
            # z=4-8 precargado; z>8 se descarga bajo demanda solo para zonas exploradas
            map_type = self.map_type_var.get()
            max_zoom_limits = {
                "OpenStreetMap": 18,
                "CartoDB Positron": 19,
                "CartoDB Voyager": 19,
                "ESRI World Imagery": 20,
                "Stamen Terrain": 17
            }
            max_zoom = max_zoom_limits.get(map_type, 18)
            safe_zoom = min(zoom_level, max_zoom)  # Sin límite artificial; descarga bajo demanda

            # Guarda el nivel para otros usos
            self.zoom_level = safe_zoom
            return safe_zoom

        except Exception as e:
            print(f"Error calculando zoom crisp: {e}")
            return 12  # fallback razonable

    def _get_bounds_from_center(self, lat, lon, zoom):
        """Calcular bounds Web Mercator desde centro y zoom"""
        # Convertir a Web Mercator
        x, y = self._lat_lon_to_web_mercator(lat, lon)
        
        # Calcular extensión basada en zoom
        # zoom más alto = área más pequeña
        extent = 20000000 / (2 ** zoom)  # Aproximación
        
        west = x - extent
        east = x + extent
        south = y - extent
        north = y + extent
        
        return west, south, east, north
    
    def _lat_lon_to_web_mercator(self, lat, lon):
        """Convertir lat/lon a Web Mercator (EPSG:3857)"""
        import math
        
        x = lon * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        
        return x, y
    
    def _web_mercator_to_lat_lon(self, x, y):
        """Convertir Web Mercator a lat/lon"""
        import math

        lon = x * 180 / 20037508.34
        lat = math.atan(math.exp(y * math.pi / 20037508.34)) * 360 / math.pi - 90

        return lat, lon

    def _format_lon(self, x, pos):
        """Formateador para eje X (longitud) - convierte Web Mercator a grados"""
        lon = x * 180 / 20037508.34
        return f"{lon:.2f}°"

    def _format_lat(self, y, pos):
        """Formateador para eje Y (latitud) - convierte Web Mercator a grados"""
        import math
        lat = math.atan(math.exp(y * math.pi / 20037508.34)) * 360 / math.pi - 90
        return f"{lat:.2f}°"

    def _setup_axes_formatters(self):
        """Aplicar formateadores de lat/lon a los ejes (reutilizable)"""
        self.ax.xaxis.set_major_formatter(FuncFormatter(self._format_lon))
        self.ax.yaxis.set_major_formatter(FuncFormatter(self._format_lat))
        self.ax.set_xlabel('Longitud', fontsize=9)
        self.ax.set_ylabel('Latitud', fontsize=9)

    def _on_mouse_press(self, event):
        """Iniciar pan o seleccionar coordenadas"""
        if event.inaxes != self.ax:
            return
        if event.button == 1:
            self.is_panning = True
            self.pan_start_x = event.xdata
            self.pan_start_y = event.ydata
            self.last_xlim = self.ax.get_xlim()
            self.last_ylim = self.ax.get_ylim()

            # Modo rápido: nearest durante el pan (menos CPU)
            if self._basemap_im is not None:
                try:
                    self._basemap_im.set_interpolation('nearest')
                except Exception:
                    pass
            self._pan_fast_mode = True

    def _on_mouse_release(self, event):
        """Finaliza pan/selección y repinta fino (debounced)"""
        if event.inaxes != self.ax:
            self.is_panning = False
            return

        if event.button == 1:
            if self.is_panning:
                # Click corto = selección o dibujo según modo activo
                if (self.pan_start_x is not None and self.pan_start_y is not None and
                        abs(event.xdata - self.pan_start_x) < 50000 and
                        abs(event.ydata - self.pan_start_y) < 50000):

                    # Selección de punto (solo si modo activo)
                    if self.point_selection_mode:
                        self._select_coordinates(event.xdata, event.ydata)

                    # Dibujo de rectángulo (solo si modo activo)
                    elif self.rectangle_draw_mode:
                        self._on_rectangle_click(event.xdata, event.ydata)

                self.is_panning = False

                # Restaurar interpolación bonita
                if self._basemap_im is not None and self._pan_fast_mode:
                    try:
                        self._basemap_im.set_interpolation('bilinear')
                    except Exception:
                        pass
                self._pan_fast_mode = False

                # Tras terminar el pan, dispara recarga (debounced)
                # NO recargar si estamos en modo dibujo de rectángulo (evita movimiento extraño)
                if not self.rectangle_draw_mode:
                    self._schedule_redraw()

    def _on_mouse_move(self, event):
        """Pan suave + throttle; coords con límite de frecuencia"""
        if event.inaxes != self.ax:
            return
        try:
            import time
            x, y = event.xdata, event.ydata
            now_ms = int(time.perf_counter() * 1000)

            # Si estamos paneando, reducir tasa de repintado (~60 FPS = 16 ms)
            if self.is_panning and self.pan_start_x is not None and x is not None and y is not None:
                if (now_ms - self._last_paint_ms) < 33:  # ajusta a 16–33 ms
                    return

                dx = self.pan_start_x - x
                dy = self.pan_start_y - y
                new_xlim = (self.last_xlim[0] + dx, self.last_xlim[1] + dx)
                new_ylim = (self.last_ylim[0] + dy, self.last_ylim[1] + dy)
                self.ax.set_xlim(new_xlim)
                self.ax.set_ylim(new_ylim)

                # No toques labels mientras panes (evita reflow Tk)
                self.canvas.draw_idle()
                self._last_paint_ms = now_ms
                return

            # Si NO estamos paneando: actualiza coords con throttle (cada 80 ms)
            if x is not None and y is not None and (now_ms - self._last_coords_ms) > 80:
                lat, lon = self._web_mercator_to_lat_lon(x, y)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.status_label.configure(
                        text=f"🎯 {lat:.4f}, {lon:.4f}",
                        text_color=ThemeManager.COLORS['text_secondary']
                    )
                self._last_coords_ms = now_ms

        except Exception:
            pass

    def _on_scroll(self, event):
        """Zoom fluido con debounce de recarga de tiles."""
        if event.inaxes != self.ax:
            return
        try:
            # Factor
            zoom_factor = 1.2 if event.step > 0 else 1 / 1.2

            # Límites actuales
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

            # Centro (cursor si existe)
            if event.xdata is not None and event.ydata is not None:
                cx, cy = event.xdata, event.ydata
            else:
                cx = (xlim[0] + xlim[1]) / 2
                cy = (ylim[0] + ylim[1]) / 2

            # Nueva extensión
            width = (xlim[1] - xlim[0]) / zoom_factor
            height = (ylim[1] - ylim[0]) / zoom_factor

            self.ax.set_xlim(cx - width / 2, cx + width / 2)
            self.ax.set_ylim(cy - height / 2, cy + height / 2)

            # Repintado rápido (sin pedir tiles aún)
            self.canvas.draw_idle()

            # Programar recarga de tiles tras pausa breve
            self._schedule_redraw()

        except Exception as e:
            print(f"Error en scroll: {e}")

    def _select_coordinates(self, x, y):
        """Seleccionar coordenadas en el punto dado"""
        try:
            # Convertir a lat/lon
            lat, lon = self._web_mercator_to_lat_lon(x, y)
            
            # Validar coordenadas
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return
            
            # Remover marcador anterior
            if self.current_marker:
                self.current_marker.remove()
            
            # Agregar nuevo marcador
            self.current_marker = self.ax.plot(x, y, 'ro', markersize=10, markeredgecolor='white', markeredgewidth=2, zorder=5)[0]
            
            # Actualizar canvas
            self.canvas.draw_idle()
            
            # Guardar coordenadas y notificar
            self._on_coordinate_selected(lat, lon)
            
        except Exception as e:
            print(f"Error seleccionando coordenadas: {e}")

    def _update_zoom_level(self):
        """
        Mantengo tu utilidad si la usas en otros lados, pero ya no dispara recargas.
        El control de recarga quedó centralizado en _schedule_redraw().
        """
        try:
            xlim = self.ax.get_xlim()
            extent = xlim[1] - xlim[0]
            import math
            new_zoom = int(max(1, min(18, math.log2(40000000 / extent))))
            self.zoom_level = new_zoom
        except:
            pass

    def _reload_tiles_if_needed(self):
        """Recargar tiles si es necesario para mejor calidad"""
        try:
            # Solo recargar si no se está moviendo activamente
            if not self.is_panning:
                self._create_map_overlay()
        except:
            pass
    
    def _on_coordinate_selected(self, lat, lon):
        """Callback cuando se seleccionan coordenadas"""
        self.selected_lat = lat
        self.selected_lon = lon
        
        self.coords_label.configure(
            text=f"📍 Lat: {lat:.6f}, Lon: {lon:.6f}",
            text_color=ThemeManager.COLORS['success']
        )
        
        if self.coordinate_callback:
            self.coordinate_callback(lat, lon)
    
    def _change_map_type(self, map_type):
        """Cambiar tipo de mapa manteniendo la vista actual"""
        self.status_label.configure(text=f"🔄 Cambiando a {map_type}...", text_color=ThemeManager.COLORS['warning'])

        # Guardar los límites actuales de la vista
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()

        # Guardar marcador actual si existe
        current_marker_coords = None
        if self.current_marker:
            current_marker_coords = (self.selected_lat, self.selected_lon)

        print(f"🔄 Cambiando base map a {map_type}, manteniendo vista...")

        # Cambiar el mapa manteniendo la vista
        self.after(100, lambda: self._change_map_preserving_view(current_xlim, current_ylim, current_marker_coords))

    def _change_map_preserving_view(self, xlim, ylim, marker_coords):
        """
        Cambio de proveedor sin resetear vista ni limpiar artistas:
        sólo actualiza el basemap persistente.
        """
        try:
            # Actualizar sólo basemap
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self._draw_basemap(xlim, ylim, force=True)

            # Restaurar marcador si existía
            if marker_coords and marker_coords[0] is not None and marker_coords[1] is not None:
                lat, lon = marker_coords
                x, y = self._lat_lon_to_web_mercator(lat, lon)
                if self.current_marker:
                    self.current_marker.remove()
                self.current_marker = self.ax.plot(
                    x, y, 'ro', markersize=10,
                    markeredgecolor='white', markeredgewidth=2, zorder=5
                )[0]

            self.canvas.draw_idle()

            map_type = self.map_type_var.get()
            self.status_label.configure(
                text=f"✅ Base map cambiado a {map_type}",
                text_color=ThemeManager.COLORS['success']
            )
            print(f"✅ Base map cambiado exitosamente a {map_type}, vista preservada")

        except Exception as e:
            print(f"❌ Error cambiando base map: {e}")
            self.status_label.configure(
                text="❌ Error cambiando mapa",
                text_color=ThemeManager.COLORS['error']
            )

    def _reset_view(self):
        """Resetear vista del mapa - zoom inteligente a rasters o región por defecto"""

        # Limpiar marcador
        if self.current_marker:
            self.current_marker.remove()
            self.current_marker = None

        # Resetear coordenadas
        self.coords_label.configure(
            text="📍 Haga clic en el mapa",
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.selected_lat = None
        self.selected_lon = None

        # Verificar si hay rasters cargados
        if hasattr(self, 'raster_layers') and self.raster_layers:
            # Hay rasters cargados - hacer zoom a todos los rasters
            print("🌍 Reset: Haciendo zoom a rasters cargados")
            self.status_label.configure(
                text="🔍 Zoom a rasters cargados...",
                text_color=ThemeManager.COLORS['info']
            )
            success = self.zoom_to_all_rasters()
            if success:
                self.status_label.configure(
                    text=f"✅ Vista ajustada a {len(self.raster_layers)} rasters",
                    text_color=ThemeManager.COLORS['success']
                )
            else:
                # Si falla el zoom a rasters, usar vista por defecto
                self._reset_to_default_view()
        else:
            # No hay rasters cargados - usar vista por defecto de Latinoamérica
            print("🌍 Reset: No hay rasters, volviendo a vista por defecto")
            self._reset_to_default_view()

    def _handle_reset_view(self):
        """Manejar clic en botón de reset - usa callback personalizado si existe"""
        if self.reset_callback:
            # Usar callback personalizado (ej: zoom a cuenca en ventana de delimitación)
            self.reset_callback()
        else:
            # Comportamiento por defecto: volver a vista de Latinoamérica
            self._reset_to_default_view()

    def _reset_to_default_view(self):
        """Resetear a vista por defecto de Latinoamérica"""
        self.center_lat = 10
        self.center_lon = -75
        self.zoom_level = 3

        self.status_label.configure(
            text="🌍 Restableciendo vista a Latinoamérica...",
            text_color=ThemeManager.COLORS['info']
        )

        # Recrear mapa con vista por defecto
        self._create_map()

    def _manual_coordinates(self):
        """Abrir diálogo para ingresar coordenadas manualmente"""
        from tkinter import simpledialog
        
        try:
            # Diálogo simple para latitud
            lat = simpledialog.askfloat(
                "Coordenadas",
                "Ingrese la latitud (-90 a 90):",
                minvalue=-90,
                maxvalue=90
            )
            
            if lat is None:
                return
            
            # Diálogo simple para longitud  
            lon = simpledialog.askfloat(
                "Coordenadas", 
                "Ingrese la longitud (-180 a 180):",
                minvalue=-180,
                maxvalue=180
            )
            
            if lon is None:
                return
                
            # Establecer coordenadas y centrar mapa
            self._set_coordinates_and_center(lat, lon)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al ingresar coordenadas: {str(e)}")
    
    def _set_coordinates_and_center(self, lat, lon):
        """Establecer coordenadas y centrar mapa en ese punto (sin recrear axes)"""
        try:
            # Actualizar centro
            self.center_lat = lat
            self.center_lon = lon

            # Zoom alejado para dar contexto (nivel país/región)
            # Zoom 5 = ~3 grados de buffer (~300km de lado)
            zoom_level = 5

            # Calcular nuevos límites geográficos
            west, south, east, north = self._get_bounds_from_center(lat, lon, zoom_level)

            # Ajustar vista del axes (SIN clear - solo cambia qué área geográfica se muestra)
            self.ax.set_xlim(west, east)
            self.ax.set_ylim(south, north)

            # Redibujar basemap con los nuevos límites
            xlim = (west, east)
            ylim = (south, north)
            self._draw_basemap(xlim=xlim, ylim=ylim, force=True)

            # Agregar o actualizar marcador
            x, y = self._lat_lon_to_web_mercator(lat, lon)
            if self.current_marker:
                # Actualizar posición del marcador existente
                self.current_marker.set_data([x], [y])
            else:
                # Crear nuevo marcador
                self.current_marker = self.ax.plot(
                    x, y, 'ro',
                    markersize=10,
                    markeredgecolor='white',
                    markeredgewidth=2,
                    zorder=5
                )[0]

            # Redibujar canvas
            self.canvas.draw()

            # Notificar coordenadas
            self._on_coordinate_selected(lat, lon)

        except Exception as e:
            print(f"Error estableciendo coordenadas: {e}")

    def _schedule_redraw(self, delay=400):
        """
        Debounce de repintado: espera 'delay' ms sin nuevos eventos
        antes de pedir/actualizar teselas. Evita bombardeo al proveedor
        y mantiene la UI fluida durante pan/zoom.
        """
        try:
            if self._reload_job is not None:
                self.after_cancel(self._reload_job)
            self._reload_job = self.after(delay, lambda: self._draw_basemap())
        except Exception:
            pass

    def _show_error(self, message):
        """Mostrar mensaje de error"""
        self.status_label.configure(text="❌ Error", text_color=ThemeManager.COLORS['error'])
        print(f"MapViewer Error: {message}")
    
    def set_coordinate_callback(self, callback):
        """Establecer callback para coordenadas"""
        self.coordinate_callback = callback
    
    def get_coordinates(self):
        """Obtener coordenadas seleccionadas"""
        return self.selected_lat, self.selected_lon
    
    def set_coordinates(self, lat, lon):
        """Establecer coordenadas manualmente"""
        self._set_coordinates_and_center(lat, lon)

    def save_map_image(self, filepath):
        """Guardar imagen actual del mapa"""
        try:
            if not hasattr(self, 'fig') or self.fig is None:
                raise Exception("Mapa no inicializado")

            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Guardar con buena calidad y fondo transparente
            self.fig.savefig(
                filepath,
                dpi=150,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
                format='png'
            )
            return True

        except Exception as e:
            print(f"Error al guardar imagen del mapa: {str(e)}")
            return False

    def add_raster_layer(self, raster_path, layer_name, alpha=0.7):
        """Agregar capa raster al mapa"""
        try:
            # Verificar que rasterio esté disponible
            try:
                import rasterio
                from rasterio.plot import show
                from rasterio.warp import calculate_default_transform, reproject, Resampling
                import rasterio.mask
            except ImportError:
                messagebox.showerror("Error", "rasterio no está disponible. Se requiere para cargar archivos .tif")
                return False

            if not os.path.exists(raster_path):
                print(f"Archivo raster no encontrado: {raster_path}")
                return False

            # Leer el raster
            with rasterio.open(raster_path) as src:
                # Leer los datos y la transformación
                raster_data = src.read(1)  # Leer la primera banda
                transform = src.transform
                crs = src.crs

                # Obtener las coordenadas de las esquinas
                bounds = src.bounds

                # Convertir bounds a Web Mercator si es necesario
                if crs.to_string() != 'EPSG:3857':
                    # Transformar coordenadas geográficas a Web Mercator
                    from pyproj import Transformer
                    transformer = Transformer.from_crs(crs, 'EPSG:3857', always_xy=True)
                    left, bottom = transformer.transform(bounds.left, bounds.bottom)
                    right, top = transformer.transform(bounds.right, bounds.top)
                else:
                    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

                # Crear colormaps apropiados para visualización
                import matplotlib.pyplot as plt

                # Usar colormap seleccionado actualmente
                cmap = self._get_colormap()
                cmap.set_bad(alpha=0)  # Valores no válidos transparentes

                # Mostrar el raster en el mapa
                raster_plot = self.ax.imshow(
                    raster_data,
                    extent=[left, right, bottom, top],
                    alpha=alpha,
                    cmap=cmap,
                    interpolation='bilinear',
                    zorder=10  # Asegurar que aparezca sobre el mapa base
                )

                # Guardar referencia para poder removerlo después
                if not hasattr(self, 'raster_layers'):
                    self.raster_layers = {}

                self.raster_layers[layer_name] = raster_plot

                # Actualizar el canvas
                self.canvas.draw()

                print(f"Raster cargado: {layer_name}")
                return True

        except Exception as e:
            print(f"Error cargando raster {layer_name}: {str(e)}")
            messagebox.showerror("Error", f"Error al cargar raster {layer_name}: {str(e)}")
            return False

    def remove_raster_layer(self, layer_name):
        """Remover capa raster del mapa"""
        try:
            if hasattr(self, 'raster_layers') and layer_name in self.raster_layers:
                # Remover el plot del matplotlib
                self.raster_layers[layer_name].remove()
                del self.raster_layers[layer_name]

                # Actualizar el canvas
                self.canvas.draw()

                print(f"Raster removido: {layer_name}")
                return True
            else:
                print(f"Raster no encontrado: {layer_name}")
                return False

        except Exception as e:
            print(f"Error removiendo raster {layer_name}: {str(e)}")
            return False

    def clear_all_rasters(self):
        """Limpiar todas las capas raster"""
        try:
            if hasattr(self, 'raster_layers'):
                for layer_name in list(self.raster_layers.keys()):
                    self.remove_raster_layer(layer_name)

            print("Todos los rasters removidos")
            return True

        except Exception as e:
            print(f"Error limpiando rasters: {str(e)}")
            return False

    def add_vector_layer(self, vector_path, layer_name, color='blue', alpha=0.5, linewidth=2, edgecolor='darkblue'):
        """Agregar capa vectorial (shapefile) al mapa"""
        try:
            print(f"🔍 add_vector_layer iniciado: {vector_path}")

            if not os.path.exists(vector_path):
                print(f"❌ Archivo vectorial no encontrado: {vector_path}")
                return False

            # Leer el shapefile con geopandas
            gdf = gpd.read_file(vector_path)
            print(f"✓ Shapefile leído: {len(gdf)} geometrías, CRS: {gdf.crs}")

            if len(gdf) == 0:
                print("❌ Shapefile vacío")
                return False

            # Reproyectar a Web Mercator si es necesario
            if gdf.crs and gdf.crs.to_string() != 'EPSG:3857':
                print(f"🔄 Reproyectando de {gdf.crs} a EPSG:3857")
                gdf = gdf.to_crs('EPSG:3857')
                print(f"✓ Reproyección completa")

            # Plotear en el mapa - gdf.plot() retorna el axes, no los objetos
            print(f"🎨 Ploteando en el mapa con color={color}, alpha={alpha}, edgecolor={edgecolor}")
            gdf.plot(
                ax=self.ax,
                facecolor=color,
                edgecolor=edgecolor,
                alpha=alpha,
                linewidth=linewidth,
                zorder=15  # Por encima de los rasters
            )

            # Restaurar tamaño fijo del axes (gdf.plot puede modificarlo)
            self.fig.subplots_adjust(left=0.08, right=0.95, bottom=0.08, top=0.95)

            # Restaurar formateadores de lat/lon (gdf.plot puede alterarlos)
            self._setup_axes_formatters()

            # Guardar referencia del GeoDataFrame
            if not hasattr(self, 'vector_layers'):
                self.vector_layers = {}

            self.vector_layers[layer_name] = gdf

            # Actualizar canvas
            print(f"🔄 Actualizando canvas...")
            self.canvas.draw_idle()
            self.canvas.flush_events()

            print(f"✅ Vector cargado exitosamente: {layer_name}")
            return True

        except Exception as e:
            print(f"❌ Error cargando vector {layer_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def zoom_to_vector(self, vector_path, padding_factor=0.1):
        """Hacer zoom a los bounds de un vector"""
        try:
            print(f"🔍 zoom_to_vector iniciado: {vector_path}")

            if not os.path.exists(vector_path):
                print(f"❌ Archivo vectorial no encontrado: {vector_path}")
                return False

            # Leer shapefile
            gdf = gpd.read_file(vector_path)
            print(f"✓ Shapefile leído para zoom: {len(gdf)} geometrías")

            if len(gdf) == 0:
                print("❌ Shapefile vacío")
                return False

            # Reproyectar a Web Mercator si es necesario
            if gdf.crs and gdf.crs.to_string() != 'EPSG:3857':
                print(f"🔄 Reproyectando para zoom...")
                gdf = gdf.to_crs('EPSG:3857')

            # Obtener bounds
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            left, bottom, right, top = bounds
            print(f"📐 Bounds originales: left={left:.2f}, right={right:.2f}, bottom={bottom:.2f}, top={top:.2f}")

            # Calcular padding
            width = right - left
            height = top - bottom
            padding_x = width * padding_factor
            padding_y = height * padding_factor

            # Aplicar padding inicial
            padded_left = left - padding_x
            padded_right = right + padding_x
            padded_bottom = bottom - padding_y
            padded_top = top + padding_y

            # Asegurar área mínima visible para evitar zoom extremadamente cercano
            # Límite reducido para permitir zoom cercano a cuencas específicas
            min_extent = 10000  # metros (10 km mínimo para legibilidad)
            current_width = padded_right - padded_left
            current_height = padded_top - padded_bottom

            # Si el área es muy pequeña, expandir ligeramente para alcanzar el mínimo
            if current_width < min_extent:
                center_x = (padded_left + padded_right) / 2
                padded_left = center_x - min_extent / 2
                padded_right = center_x + min_extent / 2
                print(f"📏 Área muy pequeña en X, expandida a {min_extent/1000:.1f} km")

            if current_height < min_extent:
                center_y = (padded_bottom + padded_top) / 2
                padded_bottom = center_y - min_extent / 2
                padded_top = center_y + min_extent / 2
                print(f"📏 Área muy pequeña en Y, expandida a {min_extent/1000:.1f} km")

            print(f"📐 Bounds finales: left={padded_left:.2f}, right={padded_right:.2f}, bottom={padded_bottom:.2f}, top={padded_top:.2f}")

            # Establecer límites
            self.ax.set_xlim(padded_left, padded_right)
            self.ax.set_ylim(padded_bottom, padded_top)

            # Redibujar basemap con los nuevos límites (igual que en _set_coordinates_and_center)
            xlim = (padded_left, padded_right)
            ylim = (padded_bottom, padded_top)
            print(f"🗺️ Redibujando basemap con nuevos límites...")
            self._draw_basemap(xlim=xlim, ylim=ylim, force=True)

            # Actualizar canvas
            print(f"🔄 Actualizando canvas después del zoom...")
            self.canvas.draw_idle()

            print(f"✅ Zoom aplicado a vector: {os.path.basename(vector_path)}")
            return True

        except Exception as e:
            print(f"❌ Error haciendo zoom al vector: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def zoom_to_raster(self, raster_path, padding_factor=0.1):
        """Hacer zoom automático a los bounds de un raster"""
        try:
            import rasterio

            if not os.path.exists(raster_path):
                print(f"Archivo raster no encontrado: {raster_path}")
                return False

            # Leer los bounds del raster
            with rasterio.open(raster_path) as src:
                bounds = src.bounds
                crs = src.crs

                # Convertir bounds a Web Mercator si es necesario
                if crs.to_string() != 'EPSG:3857':
                    from pyproj import Transformer
                    transformer = Transformer.from_crs(crs, 'EPSG:3857', always_xy=True)
                    left, bottom = transformer.transform(bounds.left, bounds.bottom)
                    right, top = transformer.transform(bounds.right, bounds.top)
                else:
                    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

                # Calcular padding para que el raster no esté pegado a los bordes
                width = right - left
                height = top - bottom
                padding_x = width * padding_factor
                padding_y = height * padding_factor

                # Aplicar padding
                padded_left = left - padding_x
                padded_right = right + padding_x
                padded_bottom = bottom - padding_y
                padded_top = top + padding_y

                # Establecer los límites del mapa
                self.ax.set_xlim(padded_left, padded_right)
                self.ax.set_ylim(padded_bottom, padded_top)

                # Redibujar basemap con los nuevos límites
                xlim = (padded_left, padded_right)
                ylim = (padded_bottom, padded_top)
                self._draw_basemap(xlim=xlim, ylim=ylim, force=True)

                # Actualizar el canvas
                self.canvas.draw()

                print(f"✅ Zoom aplicado a raster: {os.path.basename(raster_path)}")
                return True

        except Exception as e:
            print(f"Error haciendo zoom al raster: {str(e)}")
            return False

    def zoom_to_layer(self, layer_name):
        """Hacer zoom a una capa raster específica que ya está cargada"""
        try:
            if hasattr(self, 'raster_layers') and layer_name in self.raster_layers:
                # Obtener los bounds de la capa cargada
                raster_plot = self.raster_layers[layer_name]
                extent = raster_plot.get_extent()

                # extent es [left, right, bottom, top]
                left, right, bottom, top = extent

                # Calcular padding
                width = right - left
                height = top - bottom
                padding_factor = 0.1
                padding_x = width * padding_factor
                padding_y = height * padding_factor

                # Aplicar padding y zoom
                padded_left = left - padding_x
                padded_right = right + padding_x
                padded_bottom = bottom - padding_y
                padded_top = top + padding_y

                self.ax.set_xlim(padded_left, padded_right)
                self.ax.set_ylim(padded_bottom, padded_top)

                # Redibujar basemap con los nuevos límites
                xlim = (padded_left, padded_right)
                ylim = (padded_bottom, padded_top)
                self._draw_basemap(xlim=xlim, ylim=ylim, force=True)

                # Actualizar el canvas
                self.canvas.draw()

                print(f"✅ Zoom aplicado a capa: {layer_name}")
                return True
            else:
                print(f"Capa no encontrada: {layer_name}")
                return False

        except Exception as e:
            print(f"Error haciendo zoom a la capa {layer_name}: {str(e)}")
            return False

    def zoom_to_all_rasters(self, padding_factor=0.1):
        """Hacer zoom para mostrar todos los rasters cargados"""
        try:
            if not hasattr(self, 'raster_layers') or not self.raster_layers:
                print("No hay rasters cargados para hacer zoom")
                return False

            # Obtener bounds de todos los rasters
            all_extents = []
            for layer_name, raster_plot in self.raster_layers.items():
                extent = raster_plot.get_extent()
                all_extents.append(extent)

            if not all_extents:
                return False

            # Calcular bounds combinados
            # extent es [left, right, bottom, top]
            min_left = min(extent[0] for extent in all_extents)
            max_right = max(extent[1] for extent in all_extents)
            min_bottom = min(extent[2] for extent in all_extents)
            max_top = max(extent[3] for extent in all_extents)

            # Calcular padding
            width = max_right - min_left
            height = max_top - min_bottom
            padding_x = width * padding_factor
            padding_y = height * padding_factor

            # Aplicar padding y zoom
            padded_left = min_left - padding_x
            padded_right = max_right + padding_x
            padded_bottom = min_bottom - padding_y
            padded_top = max_top + padding_y

            self.ax.set_xlim(padded_left, padded_right)
            self.ax.set_ylim(padded_bottom, padded_top)

            # Redibujar basemap con los nuevos límites
            xlim = (padded_left, padded_right)
            ylim = (padded_bottom, padded_top)
            self._draw_basemap(xlim=xlim, ylim=ylim, force=True)

            # Actualizar el canvas
            self.canvas.draw()

            print(f"✅ Zoom aplicado a todos los rasters ({len(self.raster_layers)} capas)")
            return True

        except Exception as e:
            print(f"Error haciendo zoom a todos los rasters: {str(e)}")
            return False

    def enable_point_selection(self):
        """Activa el modo de selección de punto en el mapa"""
        self.point_selection_mode = True
        self.rectangle_draw_mode = False
        print("✅ Modo selección de punto activado")

    def disable_point_selection(self):
        """Desactiva el modo de selección de punto"""
        self.point_selection_mode = False
        print("⭕ Modo selección de punto desactivado")

    def enable_rectangle_draw(self, callback):
        """
        Activa el modo de dibujo de rectángulo

        Args:
            callback: Función a llamar cuando se complete el rectángulo.
                     Recibe dict con 'north', 'south', 'east', 'west'
        """
        self.rectangle_draw_mode = True
        self.point_selection_mode = False
        self.rectangle_callback = callback
        self.rect_start_x = None
        self.rect_start_y = None
        print("✅ Modo dibujo de rectángulo activado - Haga 2 clics para definir el área")

    def disable_rectangle_draw(self):
        """Desactiva el modo de dibujo de rectángulo (pero mantiene el rectángulo dibujado visible)"""
        self.rectangle_draw_mode = False
        self.rectangle_callback = None

        # Limpiar marcador temporal si existe
        if self.temp_marker:
            try:
                self.temp_marker.remove()
            except:
                pass
            self.temp_marker = None

        # NO limpiar current_rectangle - debe permanecer visible hasta que el usuario
        # haga clic nuevamente en el botón "📐 Definir Área SbN"

        self.canvas.draw_idle()

        self.rect_start_x = None
        self.rect_start_y = None
        print("⭕ Modo dibujo de rectángulo desactivado (rectángulo permanece visible)")

    def clear_current_rectangle(self):
        """Limpia el rectángulo actual del mapa (sin desactivar el modo)"""
        # Limpiar marcador temporal si existe
        if self.temp_marker:
            try:
                self.temp_marker.remove()
            except:
                pass
            self.temp_marker = None

        # Limpiar rectángulo actual si existe
        if self.current_rectangle:
            try:
                self.current_rectangle.remove()
            except:
                pass
            self.current_rectangle = None

        self.canvas.draw_idle()
        print("🗑️ Rectángulo anterior limpiado")

    def _on_rectangle_click(self, x, y):
        """Maneja los clics para crear el rectángulo (2 clics necesarios)"""
        try:
            if self.rect_start_x is None:
                # Primer clic - guardar punto inicial y dibujar marcador
                self.rect_start_x = x
                self.rect_start_y = y
                print(f"📍 Esquina 1 seleccionada - Haga clic en la esquina opuesta")

                # Dibujar punto temporal (marcador azul)
                self.temp_marker = self.ax.plot(x, y, 'bs', markersize=8, markeredgecolor='white', markeredgewidth=2, zorder=5)[0]
                self.canvas.draw_idle()

            else:
                # Segundo clic - crear rectángulo inmediatamente
                x1, y1 = self.rect_start_x, self.rect_start_y
                x2, y2 = x, y

                # Calcular bounds
                min_x = min(x1, x2)
                max_x = max(x1, x2)
                min_y = min(y1, y2)
                max_y = max(y1, y2)

                # Convertir a lat/lon
                south, west = self._web_mercator_to_lat_lon(min_x, min_y)
                north, east = self._web_mercator_to_lat_lon(max_x, max_y)

                # Validar coordenadas
                if not (-90 <= south <= 90 and -90 <= north <= 90 and
                        -180 <= west <= 180 and -180 <= east <= 180):
                    messagebox.showerror("Error", "Coordenadas fuera de rango válido")
                    self.rect_start_x = None
                    self.rect_start_y = None
                    # Limpiar marcador temporal
                    if self.temp_marker:
                        try:
                            self.temp_marker.remove()
                        except:
                            pass
                        self.temp_marker = None
                        self.canvas.draw_idle()
                    return

                # Guardar coordenadas
                self.drawn_rectangle_coords = {
                    'north': north,
                    'south': south,
                    'east': east,
                    'west': west
                }

                # Limpiar marcador temporal
                if self.temp_marker:
                    try:
                        self.temp_marker.remove()
                    except:
                        pass
                    self.temp_marker = None

                # Dibujar rectángulo permanente
                from matplotlib.patches import Rectangle
                width = max_x - min_x
                height = max_y - min_y
                self.current_rectangle = Rectangle(
                    (min_x, min_y), width, height,
                    linewidth=2, edgecolor='blue', facecolor='blue',
                    alpha=0.3, zorder=4
                )
                self.ax.add_patch(self.current_rectangle)
                self.canvas.draw_idle()

                print(f"✅ Rectángulo dibujado: N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}")

                # Resetear para permitir nuevo rectángulo
                self.rect_start_x = None
                self.rect_start_y = None

                # Llamar callback (esto guardará el shapefile y desactivará el modo)
                if self.rectangle_callback:
                    self.rectangle_callback(self.drawn_rectangle_coords)

        except Exception as e:
            print(f"Error en clic de rectángulo: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_for_drawn_rectangle(self):
        """
        Verifica si hay un rectángulo dibujado y retorna sus coordenadas

        Returns:
            bool: True si hay rectángulo, False si no
        """
        if self.drawn_rectangle_coords and self.rectangle_callback:
            # Ya fue procesado durante el dibujo, no hacer nada
            return True
        return False

    def add_shapefile_layer(self, shp_path, layer_name="Shapefile", color='blue'):
        """
        Agrega un shapefile al mapa

        Args:
            shp_path: Ruta al archivo .shp
            layer_name: Nombre de la capa
            color: Color del polígono
        """
        try:
            if not GEOPANDAS_AVAILABLE:
                print("⚠️ Geopandas no disponible, no se puede cargar shapefile")
                return

            import geopandas as gpd

            # Leer shapefile
            gdf = gpd.read_file(shp_path)

            # Convertir a Web Mercator si no lo está
            if gdf.crs and gdf.crs != 'EPSG:3857':
                gdf = gdf.to_crs('EPSG:3857')

            # Dibujar geometrías
            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom.geom_type == 'Polygon':
                    x, y = geom.exterior.xy
                    patch = self.ax.fill(x, y, color=color, alpha=0.3, edgecolor=color, linewidth=2, zorder=4)[0]
                    self.shapefile_patches.append(patch)

                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y = poly.exterior.xy
                        patch = self.ax.fill(x, y, color=color, alpha=0.3, edgecolor=color, linewidth=2, zorder=4)[0]
                        self.shapefile_patches.append(patch)

            self.canvas.draw_idle()
            print(f"✅ Shapefile '{layer_name}' agregado al mapa")

        except Exception as e:
            print(f"Error al agregar shapefile: {str(e)}")
            import traceback
            traceback.print_exc()