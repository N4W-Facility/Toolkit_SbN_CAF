import customtkinter as ctk
import folium
import tempfile
import os
import tkinter as tk
from tkinter import messagebox
import threading
import json
from ..core.theme_manager import ThemeManager

try:
    import webview
    WEBVIEW_AVAILABLE = True
    print("pywebview disponible")
except ImportError:
    WEBVIEW_AVAILABLE = False
    print("pywebview NO disponible")

try:
    from tkinter import Tk
    from tkinter.ttk import Frame
    import tkinter.font as tkFont
    
    # Intentar importar tkinterhtml como fallback
    try:
        from tkinterhtml import HtmlFrame
        HTML_FRAME_AVAILABLE = True
    except ImportError:
        HTML_FRAME_AVAILABLE = False
except ImportError:
    HTML_FRAME_AVAILABLE = False

class EmbeddedMapViewer(ctk.CTkFrame):
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.selected_lat = None
        self.selected_lon = None
        self.map_html_content = None
        self.coordinate_callback = None
        self.webview_window = None
        
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
        
        # Frame para el mapa embebido
        self.map_container = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        self.map_container.pack(fill="both", expand=True)
        
        # Información del estado
        info_frame = ctk.CTkFrame(self.map_container, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.coords_label = ctk.CTkLabel(
            info_frame,
            text="📍 Coordenadas: Haga clic en el mapa para seleccionar",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.coords_label.pack()
        
        # Crear el visor embebido
        self._create_embedded_viewer()
    
    def _create_toolbar(self, parent):
        toolbar_container = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=10, pady=8)
        
        # Título
        title_label = ctk.CTkLabel(
            toolbar_container,
            text="🌍 Mapa Interactivo",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack(side="left")
        
        # Controles
        controls_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        controls_frame.pack(side="right")
        
        # Selector de capa base
        self.layer_var = ctk.StringVar(value="Calles")
        layer_menu = ctk.CTkOptionMenu(
            controls_frame,
            values=["Calles", "Satélite", "Topográfico"],
            variable=self.layer_var,
            command=self._change_base_layer,
            width=120
        )
        layer_menu.pack(side="right", padx=5)
        
        reset_btn = ctk.CTkButton(
            controls_frame,
            text="🌎",
            width=40,
            command=self._reset_view,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        reset_btn.pack(side="right", padx=5)
        
        self.status_label = ctk.CTkLabel(
            controls_frame,
            text="✅ Listo",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['success']
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_embedded_viewer(self):
        """Crear visor embebido según disponibilidad"""
        
        if WEBVIEW_AVAILABLE:
            try:
                self._create_webview_viewer()
            except Exception as e:
                print(f"Webview falló, usando fallback: {e}")
                self._create_fallback_viewer()
        elif HTML_FRAME_AVAILABLE:
            self._create_html_frame_viewer()
        else:
            self._create_fallback_viewer()
    
    def _create_webview_viewer(self):
        """Crear visor usando pywebview embebido"""
        try:
            # Crear archivo temporal primero
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(self.map_html_content)
            temp_file.close()
            
            # Frame contenedor para webview
            webview_frame = ctk.CTkFrame(self.map_container, fg_color="#FFFFFF")
            webview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            # Mostrar mensaje de carga
            loading_label = ctk.CTkLabel(
                webview_frame, 
                text="🌐 Iniciando visor embebido...",
                font=ThemeManager.FONTS['body']
            )
            loading_label.pack(expand=True)
            
            # Crear webview en ventana separada (más estable)
            def create_webview():
                try:
                    self.webview_window = webview.create_window(
                        'Mapa Interactivo',
                        f'file://{temp_file.name}',
                        width=800,
                        height=600,
                        min_size=(400, 300),
                        js_api=MapJSApi(self),
                        resizable=True,
                        on_top=False
                    )
                    
                    webview.start(debug=False)
                    
                except Exception as e:
                    print(f"Webview error: {e}")
                    # Fallback automático
                    self.after(100, self._create_fallback_viewer)
            
            # Iniciar webview en thread separado
            webview_thread = threading.Thread(target=create_webview, daemon=True)
            webview_thread.start()
            
            self.status_label.configure(text="🌐 Webview iniciado", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self._show_error(f"Error al crear webview: {str(e)}")
            self._create_fallback_viewer()
    
    def _create_html_frame_viewer(self):
        """Crear visor usando HtmlFrame"""
        try:
            html_frame = HtmlFrame(self.map_container, horizontal_scrollbar="auto")
            html_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            # Cargar HTML del mapa
            html_frame.set_content(self.map_html_content)
            
            self.status_label.configure(text="✅ HTML Frame", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self._show_error(f"Error HTML Frame: {str(e)}")
            self._create_fallback_viewer()
    
    def _create_fallback_viewer(self):
        """Visor de respaldo con botón para abrir en navegador"""
        fallback_frame = ctk.CTkFrame(self.map_container, fg_color=ThemeManager.COLORS['bg_secondary'])
        fallback_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Contenedor principal
        content_frame = ctk.CTkFrame(fallback_frame, fg_color="transparent")
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Mensaje informativo con diseño mejorado
        info_container = ctk.CTkFrame(content_frame, **ThemeManager.get_frame_style())
        info_container.pack(fill="x", pady=(0, 20))
        
        info_title = ctk.CTkLabel(
            info_container,
            text="🌍 Visor Geográfico Interactivo",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        info_title.pack(pady=(15, 5))
        
        info_text = ctk.CTkLabel(
            info_container,
            text="Para seleccionar coordenadas:\n1. Haga clic en 'Abrir Mapa' para navegar\n2. Clic en el punto deseado en el mapa\n3. Regrese aquí e ingrese las coordenadas",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        info_text.pack(pady=(0, 15))
        
        # Botón para abrir en navegador con mejor diseño
        map_btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        map_btn_frame.pack(pady=10)
        
        open_btn = ctk.CTkButton(
            map_btn_frame,
            text="🗺️ Abrir Mapa Interactivo",
            width=280,
            height=60,
            command=self._open_in_browser,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['heading'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        open_btn.pack()
        
        # Entrada manual de coordenadas con mejor diseño
        manual_container = ctk.CTkFrame(content_frame, **ThemeManager.get_frame_style())
        manual_container.pack(fill="x", pady=(20, 0))
        
        manual_title = ctk.CTkLabel(
            manual_container,
            text="📍 Ingreso Manual de Coordenadas",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        manual_title.pack(pady=(15, 10))
        
        # Campos de entrada organizados
        coords_grid = ctk.CTkFrame(manual_container, fg_color="transparent")
        coords_grid.pack(pady=(0, 15))
        
        # Latitud
        lat_frame = ctk.CTkFrame(coords_grid, fg_color="transparent")
        lat_frame.pack(pady=5)
        
        ctk.CTkLabel(lat_frame, text="Latitud:", width=80).pack(side="left", padx=5)
        self.lat_entry = ctk.CTkEntry(
            lat_frame, 
            width=150, 
            placeholder_text="Ej: 4.6097",
            **ThemeManager.get_entry_style()
        )
        self.lat_entry.pack(side="left", padx=5)
        
        # Longitud
        lon_frame = ctk.CTkFrame(coords_grid, fg_color="transparent")
        lon_frame.pack(pady=5)
        
        ctk.CTkLabel(lon_frame, text="Longitud:", width=80).pack(side="left", padx=5)
        self.lon_entry = ctk.CTkEntry(
            lon_frame, 
            width=150, 
            placeholder_text="Ej: -74.0817",
            **ThemeManager.get_entry_style()
        )
        self.lon_entry.pack(side="left", padx=5)
        
        # Botón de confirmación
        set_btn = ctk.CTkButton(
            manual_container,
            text="✅ Establecer Coordenadas",
            width=200,
            height=40,
            command=self._set_manual_coordinates,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        set_btn.pack(pady=(10, 15))
        
        self.status_label.configure(text="🌐 Navegador externo", text_color=ThemeManager.COLORS['accent_primary'])
    
    def _create_map(self):
        """Crear mapa HTML con Folium"""
        try:
            # Crear mapa centrado en América
            folium_map = folium.Map(
                location=[10, -75],  # Centro de América
                zoom_start=4,
                tiles=None
            )
            
            # Capa de calles (por defecto)
            folium.TileLayer(
                'OpenStreetMap',
                name='Calles',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            # Capa satélite
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            # Capa topográfica
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Topográfico',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            # Control de capas
            folium.LayerControl().add_to(folium_map)
            
            # JavaScript mejorado para capturar clicks
            click_js = """
            <script>
            var map = window[Object.keys(window).find(key => key.startsWith('map_'))];
            var currentMarker = null;
            
            // Función para comunicarse con Python (si está disponible)
            function sendCoordinatesToPython(lat, lng) {
                try {
                    // Intentar comunicación con pywebview
                    if (window.pywebview && window.pywebview.api) {
                        window.pywebview.api.on_coordinate_selected(lat, lng);
                    }
                    // Fallback: localStorage para comunicación
                    localStorage.setItem('selected_lat', lat);
                    localStorage.setItem('selected_lng', lng);
                    localStorage.setItem('coordinates_updated', new Date().getTime());
                } catch (e) {
                    console.log('Python communication not available:', e);
                }
            }
            
            map.on('click', function(e) {
                var lat = e.latlng.lat;
                var lng = e.latlng.lng;
                
                // Remover marcador anterior
                if (currentMarker) {
                    map.removeLayer(currentMarker);
                }
                
                // Agregar nuevo marcador
                currentMarker = L.marker([lat, lng], {
                    icon: L.icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                    })
                }).addTo(map);
                
                // Popup con información
                currentMarker.bindPopup(`
                    <div style="text-align: center;">
                        <b>Punto Seleccionado</b><br>
                        <strong>Lat:</strong> ${lat.toFixed(6)}<br>
                        <strong>Lon:</strong> ${lng.toFixed(6)}<br>
                        <br>
                        <button onclick="copyToClipboard('${lat.toFixed(6)},${lng.toFixed(6)}')" 
                                style="background: #2196F3; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                            Copiar
                        </button>
                    </div>
                `).openPopup();
                
                // Enviar coordenadas a Python
                sendCoordinatesToPython(lat, lng);
                
                console.log('Coordenadas seleccionadas:', lat, lng);
            });
            
            function copyToClipboard(text) {
                navigator.clipboard.writeText(text).then(function() {
                    alert('Coordenadas copiadas: ' + text);
                }).catch(function(err) {
                    console.error('Error al copiar:', err);
                });
            }
            
            // Función para centrar mapa (llamada desde Python)
            function resetMapView() {
                map.setView([10, -75], 4);
            }
            
            console.log('Mapa interactivo listo');
            </script>
            """
            
            # Agregar JavaScript al mapa
            folium_map.get_root().html.add_child(folium.Element(click_js))
            
            # Obtener HTML del mapa
            self.map_html_content = folium_map._repr_html_()
            
            self.status_label.configure(text="✅ Mapa creado", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self._show_error(f"Error al crear mapa: {str(e)}")
    
    def _open_in_browser(self):
        """Abrir mapa en navegador (fallback)"""
        try:
            import webbrowser
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(self.map_html_content)
            temp_file.close()
            
            webbrowser.open(f'file://{temp_file.name}')
            self.status_label.configure(text="🌐 Abierto en navegador", text_color=ThemeManager.COLORS['accent_primary'])
            
        except Exception as e:
            self._show_error(f"Error al abrir navegador: {str(e)}")
    
    def _set_manual_coordinates(self):
        """Establecer coordenadas manualmente"""
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            
            if not (-90 <= lat <= 90):
                raise ValueError("Latitud debe estar entre -90 y 90")
            if not (-180 <= lon <= 180):
                raise ValueError("Longitud debe estar entre -180 y 180")
            
            self._on_coordinate_selected(lat, lon)
            
        except ValueError as e:
            messagebox.showerror("Error", f"Coordenadas inválidas: {str(e)}")
    
    def _change_base_layer(self, layer_name):
        """Cambiar capa base del mapa"""
        # Esta funcionalidad se implementaría con comunicación JS-Python
        self.status_label.configure(text=f"📍 Capa: {layer_name}", text_color=ThemeManager.COLORS['accent_primary'])
    
    def _reset_view(self):
        """Resetear vista del mapa"""
        # Comunicación con JavaScript para resetear vista
        if self.webview_window:
            try:
                self.webview_window.evaluate_js('resetMapView();')
            except:
                pass
        
        self.status_label.configure(text="🌎 Vista reseteada", text_color=ThemeManager.COLORS['success'])
    
    def _on_coordinate_selected(self, lat, lon):
        """Callback cuando se seleccionan coordenadas"""
        self.selected_lat = lat
        self.selected_lon = lon
        
        self.coords_label.configure(
            text=f"📍 Coordenadas: Lat: {lat:.6f}, Lon: {lon:.6f}",
            text_color=ThemeManager.COLORS['success']
        )
        
        if self.coordinate_callback:
            self.coordinate_callback(lat, lon)
        
        self.status_label.configure(text="✅ Coordenadas capturadas", text_color=ThemeManager.COLORS['success'])
    
    def _show_error(self, message):
        """Mostrar mensaje de error"""
        self.status_label.configure(text="❌ Error", text_color=ThemeManager.COLORS['error'])
        print(f"MapViewer Error: {message}")  # Para debugging
    
    def set_coordinate_callback(self, callback):
        """Establecer callback para coordenadas"""
        self.coordinate_callback = callback
    
    def get_coordinates(self):
        """Obtener coordenadas seleccionadas"""
        return self.selected_lat, self.selected_lon

class MapJSApi:
    """API para comunicación JavaScript-Python"""
    
    def __init__(self, map_viewer):
        self.map_viewer = map_viewer
    
    def on_coordinate_selected(self, lat, lon):
        """Llamado desde JavaScript cuando se seleccionan coordenadas"""
        # Ejecutar en el hilo principal de tkinter
        self.map_viewer.after(0, lambda: self.map_viewer._on_coordinate_selected(lat, lon))