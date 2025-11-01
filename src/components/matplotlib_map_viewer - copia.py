import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
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
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.selected_lat = None
        self.selected_lon = None
        self.coordinate_callback = None
        self.current_marker = None
        
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
        
        self._setup_ui()
        self._create_map()
    
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

        # Frame para selector de colormap con label
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

        # Botón de reset inteligente
        reset_btn = ctk.CTkButton(
            top_controls,
            text="🎯",  # Ícono más apropiado para "zoom a área de interés"
            width=45,
            height=32,
            command=self._reset_view,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        reset_btn.pack(side="right", padx=5)
        
        # Botón manual como backup
        manual_btn = ctk.CTkButton(
            top_controls,
            text="✏️",
            width=45,
            height=32,
            command=self._manual_coordinates,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        manual_btn.pack(side="right", padx=5)
        
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
            self.fig = Figure(figsize=(12, 9), facecolor='none', dpi=100)
            self.ax = self.fig.add_subplot(111)
            
            # Ajustar márgenes para aprovechar mejor el espacio
            self.fig.tight_layout(pad=1.0)
            
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
        """Crear mapa con OpenStreetMap"""
        try:
            self.status_label.configure(text="🌍 Cargando mapa...", text_color=ThemeManager.COLORS['warning'])
            
            # Limpiar axes
            self.ax.clear()
            
            # Configurar límites iniciales (Web Mercator)
            # Convertir lat/lon a Web Mercator
            west, south, east, north = self._get_bounds_from_center(
                self.center_lat, self.center_lon, self.zoom_level
            )
            
            # Establecer límites
            self.ax.set_xlim(west, east)
            self.ax.set_ylim(south, north)
            
            # Obtener fuente de tiles según selección
            tile_source = self._get_tile_source()
            
            # Agregar mapa base con contextily
            try:
                # Calcular zoom apropiado con límites
                zoom_level = self._calculate_safe_zoom_level()

                ctx.add_basemap(
                    self.ax,
                    crs='EPSG:3857',  # Web Mercator
                    source=tile_source,
                    zoom=zoom_level,  # Usar zoom controlado en lugar de 'auto'
                    alpha=0.8
                )
                print(f"✅ Tiles cargados exitosamente (zoom: {zoom_level})")
            except Exception as e:
                print(f"❌ Error cargando tiles primarios: {e}")

                # Intentar con proveedor de fallback (CartoDB Positron - buena cobertura global)
                try:
                    print("🔄 Intentando con proveedor de fallback...")
                    ctx.add_basemap(
                        self.ax,
                        crs='EPSG:3857',
                        source=ctx.providers.CartoDB.Positron,
                        zoom=min(zoom_level, 18),  # Zoom más conservador
                        alpha=0.8
                    )
                    print("✅ Fallback exitoso con CartoDB Positron")
                except Exception as e2:
                    print(f"❌ Error con fallback: {e2}")
                    # Fallback final: mapa básico sin tiles
                    self.ax.set_facecolor('#E8E8E8')
                    self.ax.text(0.5, 0.5, 'Mapa Base\n(Sin conexión)',
                               transform=self.ax.transAxes, ha='center', va='center',
                               fontsize=12, color='gray')
            
            # Configurar apariencia
            self.ax.set_aspect('equal')
            self.ax.set_xlabel('Longitud', fontsize=9)
            self.ax.set_ylabel('Latitud', fontsize=9)
            self.ax.grid(True, alpha=0.3, linewidth=0.5)
            
            # Ocultar ticks para look más limpio
            self.ax.tick_params(labelsize=8)
            
            # Actualizar canvas
            self.canvas.draw()
            
            self.status_label.configure(text="✅ Mapa cargado", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self._show_error(f"Error al cargar mapa: {str(e)}")
    
    def _create_map_overlay(self):
        """Recargar solo el overlay del mapa sin limpiar todo"""
        try:
            # Obtener límites actuales
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            # Limpiar solo las imágenes de fondo (tiles), preservar rasters SbN y marcadores
            for child in self.ax.get_children()[:]:
                if hasattr(child, 'get_array') and child.get_array() is not None:
                    # Verificar si es un raster de SbN (tienen zorder=10)
                    if hasattr(child, 'zorder') and child.zorder == 10:
                        continue  # No remover rasters SbN
                    # Es un tile del mapa base, remover
                    child.remove()
            
            # Obtener fuente de tiles
            tile_source = self._get_tile_source()
            
            # Agregar nuevo mapa base
            try:
                # Calcular zoom apropiado con límites
                zoom_level = self._calculate_safe_zoom_level()

                ctx.add_basemap(
                    self.ax,
                    crs='EPSG:3857',
                    source=tile_source,
                    zoom=zoom_level,  # Usar zoom controlado
                    alpha=0.8
                )
                print(f"✅ Tiles overlay cargados exitosamente (zoom: {zoom_level})")
            except Exception as e:
                print(f"❌ Error cargando tiles overlay primarios: {e}")

                # Intentar con proveedor de fallback
                try:
                    print("🔄 Intentando overlay con proveedor de fallback...")
                    ctx.add_basemap(
                        self.ax,
                        crs='EPSG:3857',
                        source=ctx.providers.CartoDB.Positron,
                        zoom=min(zoom_level, 18),
                        alpha=0.8
                    )
                    print("✅ Fallback overlay exitoso con CartoDB Positron")
                except Exception as e2:
                    print(f"❌ Error con fallback overlay: {e2}")
                    # No agregar fallback visual aquí ya que no es la carga inicial
            
            # Restaurar límites
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            
            # Actualizar canvas
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Error en overlay: {e}")
    
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

    def _calculate_safe_zoom_level(self):
        """Calcular nivel de zoom seguro para tiles basado en la vista actual"""
        try:
            # Obtener bounds actuales del mapa
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

            # Calcular el ancho y alto en metros (Web Mercator)
            width = xlim[1] - xlim[0]
            height = ylim[1] - ylim[0]

            # Usar la dimensión menor para calcular zoom
            min_dimension = min(width, height)

            # Calcular zoom basado en la escala
            # Zoom 0 = mundo completo (~40M metros)
            # Cada nivel de zoom divide por 2
            if min_dimension <= 0:
                return 10  # Fallback por defecto

            # Fórmula aproximada para calcular zoom
            world_width = 40075016.685  # Circunferencia de la Tierra en metros
            zoom_level = max(0, int(np.log2(world_width / min_dimension)))

            # Aplicar límites seguros para diferentes proveedores
            map_type = self.map_type_var.get()
            max_zoom_limits = {
                "OpenStreetMap": 18,         # OSM límite estándar
                "CartoDB Positron": 19,      # CartoDB buena cobertura
                "CartoDB Voyager": 19,       # CartoDB con mejor detalle
                "ESRI World Imagery": 20,    # ESRI satelital, mejor zoom
                "Stamen Terrain": 17         # Stamen más conservador
            }

            max_zoom = max_zoom_limits.get(map_type, 17)  # 17 por defecto
            safe_zoom = min(zoom_level, max_zoom)

            print(f"🔍 Zoom calculado: {zoom_level} → Limitado a: {safe_zoom} (max: {max_zoom})")
            return safe_zoom

        except Exception as e:
            print(f"Error calculando zoom seguro: {e}")
            return 10  # Fallback conservador

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
    
    def _on_mouse_press(self, event):
        """Manejar press del mouse - iniciar pan o seleccionar coordenadas"""
        if event.inaxes != self.ax:
            return
            
        # Botón izquierdo - iniciar pan o seleccionar
        if event.button == 1:  # Left click
            self.is_panning = True
            self.pan_start_x = event.xdata
            self.pan_start_y = event.ydata
            self.last_xlim = self.ax.get_xlim()
            self.last_ylim = self.ax.get_ylim()
    
    def _on_mouse_release(self, event):
        """Manejar release del mouse - finalizar pan o confirmar selección"""
        if event.inaxes != self.ax:
            self.is_panning = False
            return
            
        if event.button == 1:  # Left click release
            if self.is_panning:
                # Si fue un drag corto, considerarlo como selección de coordenadas
                if (self.pan_start_x is not None and self.pan_start_y is not None and
                    abs(event.xdata - self.pan_start_x) < 50000 and  # Threshold en metros
                    abs(event.ydata - self.pan_start_y) < 50000):
                    
                    self._select_coordinates(event.xdata, event.ydata)
                
                self.is_panning = False
    
    def _on_mouse_move(self, event):
        """Manejar movimiento del mouse - pan o mostrar coordenadas"""
        if event.inaxes != self.ax:
            return
            
        try:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                
                # Si estamos haciendo pan
                if self.is_panning and self.pan_start_x is not None:
                    # Calcular desplazamiento
                    dx = self.pan_start_x - x
                    dy = self.pan_start_y - y
                    
                    # Aplicar desplazamiento
                    new_xlim = (self.last_xlim[0] + dx, self.last_xlim[1] + dx)
                    new_ylim = (self.last_ylim[0] + dy, self.last_ylim[1] + dy)
                    
                    self.ax.set_xlim(new_xlim)
                    self.ax.set_ylim(new_ylim)
                    
                    # Actualizar canvas sin recrear mapa
                    self.canvas.draw_idle()
                
                else:
                    # Mostrar coordenadas actuales
                    lat, lon = self._web_mercator_to_lat_lon(x, y)
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        self.status_label.configure(
                            text=f"🎯 {lat:.4f}, {lon:.4f}",
                            text_color=ThemeManager.COLORS['text_secondary']
                        )
        except:
            pass
    
    def _on_scroll(self, event):
        """Manejar scroll del mouse - zoom fluido"""
        if event.inaxes != self.ax:
            return
            
        try:
            # Factor de zoom
            zoom_factor = 1.2 if event.step > 0 else 1/1.2
            
            # Obtener límites actuales
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            # Obtener punto central para zoom
            if event.xdata is not None and event.ydata is not None:
                # Zoom centrado en cursor
                center_x, center_y = event.xdata, event.ydata
            else:
                # Zoom centrado en vista actual
                center_x = (xlim[0] + xlim[1]) / 2
                center_y = (ylim[0] + ylim[1]) / 2
            
            # Calcular nueva extensión
            width = (xlim[1] - xlim[0]) / zoom_factor
            height = (ylim[1] - ylim[0]) / zoom_factor
            
            # Aplicar nuevos límites
            new_xlim = (center_x - width/2, center_x + width/2)
            new_ylim = (center_y - height/2, center_y + height/2)
            
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
            
            # Actualizar canvas suavemente
            self.canvas.draw_idle()
            
            # Actualizar zoom level para recargar tiles si es necesario
            self._update_zoom_level()
            
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
        """Actualizar zoom level basado en la extensión actual"""
        try:
            xlim = self.ax.get_xlim()
            extent = xlim[1] - xlim[0]  # Extensión en metros
            
            # Calcular zoom level aproximado
            # zoom más alto = extensión más pequeña
            import math
            new_zoom = max(1, min(18, math.log2(40000000 / extent)))
            
            # Si el zoom cambió significativamente, recargar tiles
            if abs(new_zoom - self.zoom_level) > 1:
                self.zoom_level = new_zoom
                self.after(500, self._reload_tiles_if_needed)  # Recargar con delay
                
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
        """Cambiar base map preservando la vista actual"""
        try:
            # Solo necesitamos recrear el overlay del mapa (tiles)
            # sin cambiar los límites o rasters cargados
            self._create_map_overlay()

            # Restaurar los límites exactos de la vista
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)

            # Restaurar marcador si existía
            if marker_coords and marker_coords[0] is not None and marker_coords[1] is not None:
                lat, lon = marker_coords
                self._select_coordinates(*self._lat_lon_to_web_mercator(lat, lon))

            # Actualizar canvas
            self.canvas.draw()

            # Actualizar status
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

    def _reset_to_default_view(self):
        """Resetear a vista por defecto de Latinoamérica"""
        self.center_lat = 10
        self.center_lon = -75
        self.zoom_level = 3

        self.status_label.configure(
            text="🌍 Vista restablecida a Latinoamérica",
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
        """Establecer coordenadas y centrar mapa en ese punto"""
        try:
            # Centrar mapa en las coordenadas
            self.center_lat = lat
            self.center_lon = lon
            self.zoom_level = 8  # Zoom más cercano
            
            # Recrear mapa centrado
            self._create_map()
            
            # Agregar marcador
            x, y = self._lat_lon_to_web_mercator(lat, lon)
            if self.current_marker:
                self.current_marker.remove()
            
            self.current_marker = self.ax.plot(x, y, 'ro', markersize=10, markeredgecolor='white', markeredgewidth=2, zorder=5)[0]
            self.canvas.draw()
            
            # Notificar coordenadas
            self._on_coordinate_selected(lat, lon)
            
        except Exception as e:
            print(f"Error estableciendo coordenadas: {e}")
    
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
                self.ax.set_xlim(left - padding_x, right + padding_x)
                self.ax.set_ylim(bottom - padding_y, top + padding_y)

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
            self.ax.set_xlim(min_left - padding_x, max_right + padding_x)
            self.ax.set_ylim(min_bottom - padding_y, max_top + padding_y)

            # Actualizar el canvas
            self.canvas.draw()

            print(f"✅ Zoom aplicado a todos los rasters ({len(self.raster_layers)} capas)")
            return True

        except Exception as e:
            print(f"Error haciendo zoom a todos los rasters: {str(e)}")
            return False