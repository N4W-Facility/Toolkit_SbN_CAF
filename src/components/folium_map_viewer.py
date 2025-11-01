import customtkinter as ctk
import folium
import tempfile
import os
import webbrowser
from tkinter import messagebox
import threading
import time
from ..core.theme_manager import ThemeManager

class FoliumMapViewer(ctk.CTkFrame):
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.selected_lat = None
        self.selected_lon = None
        self.map_html_path = None
        self.coordinate_callback = None
        self.rectangle_draw_callback = None
        self.drawing_enabled = False
        self.shapefile_layers = []  # Store added shapefile layers

        self._setup_ui()
        self._create_map()
    
    def _setup_ui(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar superior
        toolbar_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        self._create_toolbar(toolbar_frame)
        
        # Frame para el mapa
        map_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        map_frame.pack(fill="both", expand=True)
        
        # Instrucciones y información
        info_frame = ctk.CTkFrame(map_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=15)
        
        instruction_label = ctk.CTkLabel(
            info_frame,
            text="🌎 Mapa Interactivo - Haga clic en 'Abrir Mapa' para navegar y seleccionar coordenadas",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        instruction_label.pack()
        
        # Panel de coordenadas
        coords_frame = ctk.CTkFrame(map_frame, **ThemeManager.get_frame_style())
        coords_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.coords_label = ctk.CTkLabel(
            coords_frame,
            text="📍 Coordenadas: Ninguna seleccionada",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['text_primary']
        )
        self.coords_label.pack(pady=15)
        
        # Botón para abrir mapa
        self.open_map_btn = ctk.CTkButton(
            map_frame,
            text="🗺️ Abrir Mapa Interactivo",
            width=250,
            height=50,
            command=self._open_interactive_map,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['heading'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        self.open_map_btn.pack(pady=20)
    
    def _create_toolbar(self, parent):
        toolbar_container = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=15, pady=10)
        
        # Título
        title_label = ctk.CTkLabel(
            toolbar_container,
            text="🌎 Visor Geográfico Interactivo",
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        title_label.pack(side="left")
        
        # Botones de acción
        button_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        button_frame.pack(side="right")
        
        refresh_btn = ctk.CTkButton(
            button_frame,
            text="🔄",
            width=40,
            command=self._refresh_map,
            fg_color=ThemeManager.COLORS['accent_primary'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body'],
            corner_radius=ThemeManager.DIMENSIONS['corner_radius']
        )
        refresh_btn.pack(side="right", padx=5)
        
        self.status_label = ctk.CTkLabel(
            button_frame,
            text="✅ Listo",
            font=ThemeManager.FONTS['body'],
            text_color=ThemeManager.COLORS['success']
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_map(self):
        """Crear mapa HTML con Folium"""
        try:
            # Crear mapa centrado en América
            self.folium_map = folium.Map(
                location=[10, -75],  # Centro de América
                zoom_start=3,
                tiles=None
            )
            
            # Agregar múltiples capas de mapa
            folium.TileLayer(
                'OpenStreetMap',
                name='Calles',
                overlay=False,
                control=True
            ).add_to(self.folium_map)
            
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite',
                overlay=False,
                control=True
            ).add_to(self.folium_map)
            
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Topográfico',
                overlay=False,
                control=True
            ).add_to(self.folium_map)
            
            # Agregar control de capas
            folium.LayerControl().add_to(self.folium_map)
            
            # JavaScript para capturar clicks y dibujar rectángulos
            click_js = """
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"/>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>

            <script>
            var map = window[Object.keys(window).find(key => key.startsWith('map_'))];
            var marker = null;
            var drawnItems = new L.FeatureGroup();
            map.addLayer(drawnItems);

            var drawControl = null;

            // Función para habilitar el dibujo de rectángulos
            window.enableRectangleDraw = function() {
                if (drawControl) {
                    map.removeControl(drawControl);
                }

                drawControl = new L.Control.Draw({
                    draw: {
                        rectangle: {
                            shapeOptions: {
                                color: '#FF0000',
                                weight: 2,
                                fillOpacity: 0.2
                            }
                        },
                        polyline: false,
                        polygon: false,
                        circle: false,
                        marker: false,
                        circlemarker: false
                    },
                    edit: {
                        featureGroup: drawnItems
                    }
                });

                map.addControl(drawControl);
                localStorage.setItem('rectangle_draw_enabled', 'true');
            };

            // Función para deshabilitar el dibujo de rectángulos
            window.disableRectangleDraw = function() {
                if (drawControl) {
                    map.removeControl(drawControl);
                    drawControl = null;
                }
                localStorage.setItem('rectangle_draw_enabled', 'false');
            };

            // Crear div oculto para almacenar coordenadas
            var coordsDiv = document.createElement('div');
            coordsDiv.id = 'drawn_rectangle_coords';
            coordsDiv.style.display = 'none';
            document.body.appendChild(coordsDiv);

            // Evento cuando se dibuja un rectángulo
            map.on(L.Draw.Event.CREATED, function(e) {
                var layer = e.layer;

                // Obtener coordenadas del rectángulo
                var bounds = layer.getBounds();
                var north = bounds.getNorth();
                var south = bounds.getSouth();
                var east = bounds.getEast();
                var west = bounds.getWest();

                // Preguntar al usuario si desea guardar
                var saveConfirm = confirm('¿Desea guardar el área delimitada?');

                if (saveConfirm) {
                    // Limpiar rectángulos anteriores
                    drawnItems.clearLayers();

                    // Agregar nuevo rectángulo
                    drawnItems.addLayer(layer);

                    // Guardar coordenadas en el div oculto
                    var coords = {
                        north: north,
                        south: south,
                        east: east,
                        west: west,
                        saved: true
                    };

                    coordsDiv.textContent = JSON.stringify(coords);

                    // También guardar en localStorage como respaldo
                    localStorage.setItem('rectangle_coords', JSON.stringify(coords));

                    console.log('Rectángulo guardado:', coords);

                    // Mostrar mensaje de confirmación
                    alert('Área guardada. Puede cerrar esta pestaña y regresar a la aplicación para confirmar.');
                } else {
                    // Usuario canceló, no agregar el rectángulo al mapa
                    console.log('Usuario canceló el guardado del rectángulo');
                }
            });

            // Evento de click para seleccionar coordenadas (cuando no está en modo dibujo)
            map.on('click', function(e) {
                // Solo capturar clicks si no está habilitado el modo dibujo
                var drawEnabled = localStorage.getItem('rectangle_draw_enabled');
                if (drawEnabled === 'true') {
                    return;
                }

                var lat = e.latlng.lat;
                var lng = e.latlng.lng;

                // Remover marcador anterior
                if (marker) {
                    map.removeLayer(marker);
                }

                // Agregar nuevo marcador
                marker = L.marker([lat, lng], {
                    icon: L.icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                    })
                }).addTo(map);

                // Mostrar popup con coordenadas
                marker.bindPopup(`
                    <b>📍 Coordenadas Seleccionadas</b><br>
                    Latitud: ${lat.toFixed(6)}<br>
                    Longitud: ${lng.toFixed(6)}<br>
                    <br>
                    <button onclick="copyCoords('${lat.toFixed(6)},${lng.toFixed(6)}')">
                        📋 Copiar Coordenadas
                    </button>
                `).openPopup();

                // Guardar coordenadas en localStorage
                localStorage.setItem('selected_lat', lat);
                localStorage.setItem('selected_lng', lng);

                console.log('Coordenadas seleccionadas:', lat, lng);
            });

            function copyCoords(coords) {
                navigator.clipboard.writeText(coords).then(function() {
                    alert('Coordenadas copiadas al portapapeles: ' + coords);
                });
            }
            </script>
            """
            
            # Agregar JavaScript al mapa
            self.folium_map.get_root().html.add_child(folium.Element(click_js))
            
            self.status_label.configure(text="✅ Mapa creado", text_color=ThemeManager.COLORS['success'])
            
        except Exception as e:
            self.status_label.configure(text="❌ Error", text_color=ThemeManager.COLORS['error'])
            messagebox.showerror("Error", f"Error al crear mapa: {str(e)}")
    
    def _open_interactive_map(self):
        """Abrir mapa en navegador web"""
        try:
            # Crear archivo temporal
            if self.map_html_path:
                try:
                    os.remove(self.map_html_path)
                except:
                    pass
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False)
            self.map_html_path = temp_file.name
            
            # Guardar mapa como HTML
            self.folium_map.save(self.map_html_path)
            temp_file.close()
            
            # Abrir en navegador
            webbrowser.open(f'file://{self.map_html_path}')
            
            self.status_label.configure(text="🌐 Mapa abierto", text_color=ThemeManager.COLORS['accent_primary'])
            
            # Cambiar texto del botón
            self.open_map_btn.configure(text="🔄 Actualizar Coordenadas")
            
            # Iniciar monitoreo de coordenadas
            self._start_coordinate_monitoring()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir mapa: {str(e)}")
    
    def _start_coordinate_monitoring(self):
        """Monitorear si se han seleccionado coordenadas en el navegador"""
        def monitor():
            try:
                # Leer archivo HTML generado para extraer coordenadas
                # (implementación simplificada)
                time.sleep(2)  # Dar tiempo para que se abra el navegador
                
                # Aquí podrías implementar un server local para recibir coordenadas
                # Por ahora, mostrar instrucciones al usuario
                self.after(2000, self._show_coordinate_instructions)
                
            except Exception as e:
                pass
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _show_coordinate_instructions(self):
        """Mostrar instrucciones para obtener coordenadas"""
        self.coords_label.configure(
            text="🌐 Mapa abierto en navegador. Haga clic en el mapa para seleccionar coordenadas.\nLuego presione 'Actualizar Coordenadas' para continuar."
        )
    
    def _refresh_map(self):
        """Refrescar y recrear mapa"""
        self._create_map()
        self.coords_label.configure(text="📍 Coordenadas: Ninguna seleccionada")
        self.open_map_btn.configure(text="🗺️ Abrir Mapa Interactivo")
    
    def set_coordinate_callback(self, callback):
        """Establecer callback para cuando se seleccionen coordenadas"""
        self.coordinate_callback = callback
    
    def get_coordinates(self):
        """Obtener coordenadas seleccionadas"""
        return self.selected_lat, self.selected_lon
    
    def set_coordinates(self, lat, lon):
        """Establecer coordenadas manualmente"""
        self.selected_lat = lat
        self.selected_lon = lon
        self.coords_label.configure(
            text=f"📍 Coordenadas: Lat: {lat:.6f}, Lon: {lon:.6f}"
        )

        if self.coordinate_callback:
            self.coordinate_callback(lat, lon)

    def enable_rectangle_draw(self, callback):
        """
        Habilita el modo de dibujo de rectángulos en el mapa

        Args:
            callback: Función a llamar cuando se dibuje un rectángulo.
                     Recibe un dict con las claves: 'north', 'south', 'east', 'west'
        """
        self.rectangle_draw_callback = callback
        self.drawing_enabled = True

        # Abrir el mapa si no está abierto
        if not self.map_html_path:
            self._open_interactive_map()

        # Ejecutar JavaScript para habilitar el dibujo
        # Necesitamos recargar el mapa con el modo de dibujo habilitado
        self._recreate_map_with_drawing()

        # Iniciar monitoreo de rectángulos dibujados
        self._start_rectangle_monitoring()

    def disable_rectangle_draw(self):
        """Deshabilita el modo de dibujo de rectángulos"""
        self.drawing_enabled = False
        self.rectangle_draw_callback = None

        # Si el mapa está abierto, deshabilitar el control de dibujo
        if self.map_html_path:
            self._recreate_map_without_drawing()

    def add_shapefile_layer(self, shp_path, layer_name="Shapefile", color='blue'):
        """
        Agrega una capa de shapefile al mapa

        Args:
            shp_path: Ruta al archivo shapefile (.shp)
            layer_name: Nombre de la capa (default: 'Shapefile')
            color: Color del polígono (default: 'blue')
        """
        try:
            import geopandas as gpd

            # Leer shapefile
            gdf = gpd.read_file(shp_path)

            # Asegurarse de que está en WGS84
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            # Convertir a GeoJSON y agregar al mapa
            style_function = lambda x: {
                'fillColor': color,
                'color': color,
                'weight': 2,
                'fillOpacity': 0.3
            }

            folium.GeoJson(
                gdf,
                name=layer_name,
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(fields=['name'] if 'name' in gdf.columns else [])
            ).add_to(self.folium_map)

            # Guardar referencia
            self.shapefile_layers.append({
                'path': shp_path,
                'name': layer_name,
                'color': color
            })

            # Si el mapa está abierto, recargarlo para mostrar la nueva capa
            if self.map_html_path:
                self._refresh_opened_map()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar shapefile: {str(e)}")

    def _recreate_map_with_drawing(self):
        """Recrea el mapa y abre en navegador con el modo de dibujo habilitado"""
        try:
            # Guardar el mapa actualizado
            if self.map_html_path:
                self.folium_map.save(self.map_html_path)

                # Leer el contenido HTML
                with open(self.map_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Agregar script para habilitar el dibujo automáticamente
                enable_script = """
                <script>
                window.addEventListener('load', function() {
                    setTimeout(function() {
                        if (typeof window.enableRectangleDraw === 'function') {
                            window.enableRectangleDraw();
                        }
                    }, 500);
                });
                </script>
                """

                # Insertar antes del cierre de body
                html_content = html_content.replace('</body>', enable_script + '</body>')

                # Guardar el HTML modificado
                with open(self.map_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # Recargar la página en el navegador
                webbrowser.open(f'file://{self.map_html_path}')

        except Exception as e:
            messagebox.showerror("Error", f"Error al activar modo de dibujo: {str(e)}")

    def _recreate_map_without_drawing(self):
        """Recrea el mapa sin el modo de dibujo"""
        try:
            if self.map_html_path:
                self.folium_map.save(self.map_html_path)

                # Leer el contenido HTML
                with open(self.map_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Agregar script para deshabilitar el dibujo
                disable_script = """
                <script>
                window.addEventListener('load', function() {
                    setTimeout(function() {
                        if (typeof window.disableRectangleDraw === 'function') {
                            window.disableRectangleDraw();
                        }
                    }, 500);
                });
                </script>
                """

                # Insertar antes del cierre de body
                html_content = html_content.replace('</body>', disable_script + '</body>')

                # Guardar el HTML modificado
                with open(self.map_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # Recargar la página
                webbrowser.open(f'file://{self.map_html_path}')

        except Exception as e:
            pass

    def _start_rectangle_monitoring(self):
        """Monitorea si se ha dibujado un rectángulo en el navegador"""
        def monitor():
            import json

            while self.drawing_enabled:
                try:
                    time.sleep(1)  # Verificar cada segundo

                    # En un entorno real, necesitaríamos un servidor local para comunicarnos
                    # con el navegador. Por ahora, vamos a simular verificando localStorage
                    # mediante un archivo temporal compartido

                    # Crear un archivo temporal para comunicación
                    temp_coords_file = os.path.join(tempfile.gettempdir(), 'folium_rectangle_coords.json')

                    # Modificar el HTML para que escriba en este archivo
                    # (esto es una simplificación, en producción usarías un servidor local)

                    # Por ahora, vamos a usar un enfoque diferente:
                    # El usuario debe cerrar el navegador o hacer clic en un botón cuando termine

                except Exception as e:
                    pass

            # Cuando se termine el monitoreo, verificar si hay coordenadas guardadas
            # y llamar al callback si están disponibles

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def _refresh_opened_map(self):
        """Refresca el mapa abierto en el navegador"""
        if self.map_html_path:
            try:
                self.folium_map.save(self.map_html_path)
                webbrowser.open(f'file://{self.map_html_path}')
            except Exception as e:
                pass

    def check_for_drawn_rectangle(self):
        """
        Verifica si se ha dibujado un rectángulo en el mapa HTML y llama al callback

        Retorna:
            bool: True si se encontró y procesó un rectángulo, False en caso contrario
        """
        try:
            if not self.map_html_path or not os.path.exists(self.map_html_path):
                return False

            import json
            import re

            # Leer el archivo HTML
            with open(self.map_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Buscar el div con id 'drawn_rectangle_coords'
            pattern = r'<div[^>]*id=["\']drawn_rectangle_coords["\'][^>]*>([^<]*)</div>'
            match = re.search(pattern, html_content)

            if match and match.group(1).strip():
                coords_json = match.group(1).strip()

                # Parsear JSON
                coords = json.loads(coords_json)

                # Verificar que tiene la estructura correcta
                if ('north' in coords and 'south' in coords and
                    'east' in coords and 'west' in coords and
                    coords.get('saved', False)):

                    # Llamar al callback con las coordenadas
                    if self.rectangle_draw_callback:
                        self.rectangle_draw_callback(coords)

                    # Limpiar las coordenadas del HTML para evitar procesamiento duplicado
                    html_content = re.sub(
                        r'(<div[^>]*id=["\']drawn_rectangle_coords["\'][^>]*>)[^<]*(</div>)',
                        r'\1\2',
                        html_content
                    )

                    with open(self.map_html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)

                    return True

        except Exception as e:
            print(f"Error al verificar rectángulo dibujado: {str(e)}")

        return False