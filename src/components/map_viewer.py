import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import geopandas as gpd
import contextily as ctx
import customtkinter as ctk
from typing import Optional
import numpy as np

class MapViewer(ctk.CTkFrame):
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.watershed_gdf: Optional[gpd.GeoDataFrame] = None
        self.figure = None
        self.canvas = None
        self.ax = None
        
        self._setup_map()
    
    def _setup_map(self):
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.figure.patch.set_facecolor('#FAFAFA')
        self.ax.set_facecolor('#FFFFFF')
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        self._create_toolbar()
    
    def _create_toolbar(self):
        toolbar_frame = ctk.CTkFrame(self)
        toolbar_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        zoom_btn = ctk.CTkButton(
            toolbar_frame,
            text="🔍",
            width=40,
            command=self._zoom_to_watershed
        )
        zoom_btn.pack(side="left", padx=5)
        
        measure_btn = ctk.CTkButton(
            toolbar_frame,
            text="📏",
            width=40,
            command=self._enable_measure
        )
        measure_btn.pack(side="left", padx=5)
        
        center_btn = ctk.CTkButton(
            toolbar_frame,
            text="🎯",
            width=40,
            command=self._center_view
        )
        center_btn.pack(side="left", padx=5)
    
    def load_watershed(self, shapefile_path: str):
        try:
            self.watershed_gdf = gpd.read_file(shapefile_path)
            
            if self.watershed_gdf.crs != 'EPSG:4326':
                self.watershed_gdf = self.watershed_gdf.to_crs('EPSG:4326')
            
            self._plot_watershed()
            
        except Exception as e:
            pass
    
    def _plot_watershed(self):
        if self.watershed_gdf is None:
            return
        
        self.ax.clear()
        
        bounds = self.watershed_gdf.total_bounds
        
        try:
            ctx.add_basemap(
                self.ax,
                crs=self.watershed_gdf.crs,
                source=ctx.providers.CartoDB.Positron,
                bbox=bounds
            )
        except:
            pass
        
        self.watershed_gdf.plot(
            ax=self.ax,
            facecolor='rgba(33, 150, 243, 0.3)',
            edgecolor='#2196F3',
            linewidth=2
        )
        
        self.ax.set_xlim(bounds[0], bounds[2])
        self.ax.set_ylim(bounds[1], bounds[3])
        
        self.ax.set_title('Cuenca Hidrográfica', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        
        self.canvas.draw()
    
    def _zoom_to_watershed(self):
        if self.watershed_gdf is not None:
            bounds = self.watershed_gdf.total_bounds
            self.ax.set_xlim(bounds[0], bounds[2])
            self.ax.set_ylim(bounds[1], bounds[3])
            self.canvas.draw()
    
    def _enable_measure(self):
        pass
    
    def _center_view(self):
        if self.watershed_gdf is not None:
            centroid = self.watershed_gdf.geometry.centroid.iloc[0]
            x, y = centroid.x, centroid.y
            
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            self.ax.set_xlim(x - x_range/2, x + x_range/2)
            self.ax.set_ylim(y - y_range/2, y + y_range/2)
            self.canvas.draw()