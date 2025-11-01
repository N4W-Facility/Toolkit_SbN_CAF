import customtkinter as ctk
import folium
import tempfile
import os
from tkinter import messagebox
from ..core.theme_manager import ThemeManager

try:
    import tkinterweb
    TKINTERWEB_AVAILABLE = True
    print("tkinterweb disponible ✅")
except ImportError:
    TKINTERWEB_AVAILABLE = False
    print("tkinterweb NO disponible ❌")

class TkinterwebMapViewer(ctk.CTkFrame):
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.selected_lat = None
        self.selected_lon = None
        self.coordinate_callback = None
        self.map_html_path = None
        
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
        
        # Crear el visor web embebido
        self._create_web_viewer()
    
    def _create_toolbar(self, parent):
        toolbar_container = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=10, pady=8)
        
        # Título
        title_label = ctk.CTkLabel(
            toolbar_container,
            text="🌍 Mapa Interactivo Embebido",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack(side="left")
        
        # Controles
        controls_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        controls_frame.pack(side="right")
        
        # Información de coordenadas
        self.coords_label = ctk.CTkLabel(
            controls_frame,
            text="📍 Haga clic en el mapa",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.coords_label.pack(side="right", padx=10)
        
        # Botón manual como backup
        manual_btn = ctk.CTkButton(
            controls_frame,
            text="✏️",
            width=40,
            command=self._manual_coordinates,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary']
        )
        manual_btn.pack(side="right", padx=5)
        
        # Botón de reset
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
            text="🔄 Cargando...",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['warning']
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_web_viewer(self):
        """Crear visor web embebido usando tkinterweb"""
        
        if not TKINTERWEB_AVAILABLE:
            self._create_fallback_message()
            return
        
        try:
            # SOLUCIÓN: Usar la ventana raíz como parent
            import tkinter as tk
            
            # Obtener la ventana principal
            root_window = self.winfo_toplevel()
            
            # Crear frame tkinter nativo
            self.tk_container = tk.Frame(root_window)
            
            # Usar place para posicionar dentro del contenedor CustomTkinter
            container_x = self.map_container.winfo_x() + 10
            container_y = self.map_container.winfo_y() + 10
            container_width = self.map_container.winfo_width() - 20
            container_height = self.map_container.winfo_height() - 20
            
            self.tk_container.place(
                x=container_x, 
                y=container_y, 
                width=container_width, 
                height=container_height
            )
            
            # Crear tkinterweb dentro del contenedor
            self.web_frame = tkinterweb.HtmlFrame(
                self.tk_container,
                messages_enabled=False
            )
            self.web_frame.pack(fill="both", expand=True)
            
            # Configurar colores
            self.tk_container.configure(bg="#2B2B2B")
            
            self.status_label.configure(text="✅ Visor embebido", text_color=ThemeManager.COLORS['success'])
            
            # Actualizar posición cuando cambie el tamaño
            self.bind("<Configure>", self._update_container_position)
            
        except Exception as e:
            self._show_error(f"Error al crear visor embebido: {str(e)}")
            self._create_fallback_message()
    
    def _create_fallback_message(self):
        """Mensaje cuando tkinterweb no está disponible"""
        fallback_frame = ctk.CTkFrame(self.map_container, fg_color=ThemeManager.COLORS['bg_secondary'])
        fallback_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        message_label = ctk.CTkLabel(
            fallback_frame,
            text="⚠️ tkinterweb no disponible\n\nPara mapa embebido instale:\npip install tkinterweb",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_secondary']
        )
        message_label.pack(expand=True)
        
        self.status_label.configure(text="❌ Sin tkinterweb", text_color=ThemeManager.COLORS['error'])
    
    def _create_map(self):
        """Crear mapa HTML con Folium"""
        try:
            # Crear mapa centrado en América
            folium_map = folium.Map(
                location=[10, -75],
                zoom_start=4,
                tiles=None
            )
            
            # Capas base
            folium.TileLayer(
                'OpenStreetMap',
                name='Calles',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Topográfico',
                overlay=False,
                control=True
            ).add_to(folium_map)
            
            # Control de capas
            folium.LayerControl().add_to(folium_map)
            
            # JavaScript para comunicación con Python
            click_js = """
            <script>
            var map = window[Object.keys(window).find(key => key.startsWith('map_'))];
            var currentMarker = null;
            
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
                        <strong>Lon:</strong> ${lng.toFixed(6)}
                    </div>
                `).openPopup();
                
                // Guardar coordenadas en el título de la página para comunicación
                try {
                    // Método simple: usar título de documento
                    document.title = `COORDS:${lat.toFixed(6)},${lng.toFixed(6)}:${Date.now()}`;
                    
                    // También guardar en variable global
                    window.selectedCoordinates = {lat: lat, lng: lng, timestamp: Date.now()};
                    
                } catch (e) {
                    console.log('Error guardando coordenadas:', e);
                }
                
                console.log('Coordenadas seleccionadas:', lat, lng);
            });
            
            // Función para resetear vista
            function resetMapView() {
                map.setView([10, -75], 4);
                if (currentMarker) {
                    map.removeLayer(currentMarker);
                    currentMarker = null;
                }
            }
            
            console.log('Mapa interactivo listo');
            </script>
            """
            
            # Agregar JavaScript al mapa
            folium_map.get_root().html.add_child(folium.Element(click_js))
            
            # Guardar mapa en archivo temporal
            self._save_and_load_map(folium_map)
            
        except Exception as e:
            self._show_error(f"Error al crear mapa: {str(e)}")
    
    def _save_and_load_map(self, folium_map):
        """Guardar mapa y cargarlo en tkinterweb"""
        try:
            # Crear archivo temporal
            if self.map_html_path and os.path.exists(self.map_html_path):
                os.remove(self.map_html_path)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            self.map_html_path = temp_file.name
            
            # Guardar mapa
            folium_map.save(self.map_html_path)
            temp_file.close()
            
            # Cargar en tkinterweb
            if hasattr(self, 'web_frame'):
                print(f"Cargando archivo HTML: {self.map_html_path}")
                print(f"Archivo existe: {os.path.exists(self.map_html_path)}")
                
                # Método 1: Cargar archivo HTML
                try:
                    self.web_frame.load_file(self.map_html_path)
                    print("Mapa cargado con load_file()")
                except Exception as e:
                    print(f"Error con load_file: {e}")
                    
                    # Método 2: Cargar HTML directamente
                    try:
                        with open(self.map_html_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        self.web_frame.load_html(html_content)
                        print("Mapa cargado con load_html()")
                    except Exception as e2:
                        print(f"Error con load_html: {e2}")
                        raise e
                
                # Actualizar estado
                self.status_label.configure(text="✅ Mapa cargado", text_color=ThemeManager.COLORS['success'])
                
                # Forzar actualización y reposicionar
                self.web_frame.update()
                self.update()
                self.after(100, self._update_container_position)
                
                # Iniciar monitoreo simple del título
                self.after(5000, self._start_title_monitoring)
                
                # Debug: verificar si se cargó
                self.after(2000, self._debug_web_frame)
            
        except Exception as e:
            self._show_error(f"Error al cargar mapa: {str(e)}")
    
    def _start_title_monitoring(self):
        """Monitorear el título del documento para obtener coordenadas"""
        try:
            if hasattr(self, 'web_frame'):
                # Intentar obtener el título del navegador embebido
                # Esto es un método simple y compatible
                current_title = getattr(self.web_frame, 'title', '') or ''
                
                if current_title.startswith('COORDS:'):
                    # Parsear coordenadas del título
                    coords_part = current_title.replace('COORDS:', '').split(':')[0]
                    if ',' in coords_part:
                        lat_str, lon_str = coords_part.split(',')
                        try:
                            lat = float(lat_str)
                            lon = float(lon_str)
                            
                            # Verificar si son coordenadas nuevas
                            if (self.selected_lat != lat or self.selected_lon != lon):
                                self._on_coordinate_selected(lat, lon)
                        except ValueError:
                            pass
                            
        except Exception as e:
            pass  # Silenciar errores del título
            
        # Continuar monitoreando cada 2 segundos
        self.after(2000, self._start_title_monitoring)
    
    def _debug_web_frame(self):
        """Debug: verificar estado del web frame"""
        try:
            if hasattr(self, 'web_frame'):
                print(f"Web frame visible: {self.web_frame.winfo_viewable()}")
                print(f"Web frame tamaño: {self.web_frame.winfo_width()}x{self.web_frame.winfo_height()}")
                
                # Intentar obtener info del contenido
                try:
                    # Cargar contenido de prueba si el mapa no se ve
                    test_html = """
                    <html>
                    <body style="background-color: lightblue; padding: 20px;">
                        <h1>Test tkinterweb</h1>
                        <p>Si ves esto, tkinterweb funciona correctamente.</p>
                        <p>El problema puede ser con el archivo HTML del mapa.</p>
                    </body>
                    </html>
                    """
                    
                    if self.web_frame.winfo_width() > 1:  # Solo si el frame está visible
                        print("Web frame está visible y tiene tamaño")
                    else:
                        print("Web frame NO está visible o tiene tamaño 0")
                        # Intentar cargar HTML de prueba
                        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                        test_file.write(test_html)
                        test_file.close()
                        self.web_frame.load_file(test_file.name)
                        print(f"Cargando HTML de prueba: {test_file.name}")
                        
                except Exception as e:
                    print(f"Error en debug web frame: {e}")
                    
        except Exception as e:
            print(f"Error general en debug: {e}")
    
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
    
    def _reset_view(self):
        """Resetear vista del mapa"""
        # Resetear coordenadas locales
        self.coords_label.configure(
            text="📍 Haga clic en el mapa",
            text_color=ThemeManager.COLORS['text_secondary']
        )
        self.selected_lat = None
        self.selected_lon = None
        
        # Recargar el mapa para resetear vista
        if hasattr(self, 'web_frame') and self.map_html_path:
            try:
                self.web_frame.load_file(self.map_html_path)
            except Exception as e:
                print(f"Error al resetear vista: {e}")
    
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
        self._on_coordinate_selected(lat, lon)
    
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
                
            # Establecer coordenadas
            self._on_coordinate_selected(lat, lon)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al ingresar coordenadas: {str(e)}")
    
    def _update_container_position(self, event=None):
        """Actualizar posición del contenedor tkinter"""
        try:
            if hasattr(self, 'tk_container') and hasattr(self, 'map_container'):
                # Obtener coordenadas actuales del contenedor
                self.map_container.update_idletasks()
                
                container_x = self.map_container.winfo_rootx() - self.winfo_toplevel().winfo_rootx() + 10
                container_y = self.map_container.winfo_rooty() - self.winfo_toplevel().winfo_rooty() + 10
                container_width = max(self.map_container.winfo_width() - 20, 100)
                container_height = max(self.map_container.winfo_height() - 20, 100)
                
                self.tk_container.place(
                    x=container_x,
                    y=container_y,
                    width=container_width,
                    height=container_height
                )
                
        except Exception as e:
            print(f"Error actualizando posición: {e}")