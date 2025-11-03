import customtkinter as ctk
from tkinter import messagebox
import os
import pandas as pd
from ..core.theme_manager import ThemeManager
from ..core.language_manager import get_text, subscribe_to_language_changes


class SbnPrioritizationConfigDialog(ctk.CTkToplevel):
    """
    Ventana de configuración de opciones de priorización de SbN.
    Permite al usuario:
    - Seleccionar configuración financiera (inversión, mantenimiento, ambos)
    - Seleccionar qué SbN incluir en el análisis (basado en idoneidad)
    """

    def __init__(self, parent, project_data=None):
        super().__init__(parent)

        self.parent = parent
        self.project_data = project_data
        self.result = None  # Será un dict con la configuración si el usuario confirma

        # Configuración de la ventana
        self.title(get_text("sbn_prioritization.title"))
        self.geometry("700x800")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=ThemeManager.COLORS['bg_primary'])

        # Variables
        self.financial_option_var = ctk.StringVar(value="investment_and_maintenance")
        self.sbn_checkboxes = {}  # {sbn_id: CTkCheckBox}
        self.sbn_availability = {}  # {sbn_id: bool} - True si está disponible

        # Suscribirse a cambios de idioma
        subscribe_to_language_changes(self._update_texts)

        # Cargar disponibilidad de SbN
        self._load_sbn_availability()

        # Crear UI
        self._setup_ui()

        # Sincronizar textos
        self._update_texts()

        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _load_sbn_availability(self):
        """
        Carga la disponibilidad de cada SbN desde SbN_Prioritization.csv
        Si Idoneidad = 1 → disponible
        Si Idoneidad = 0 → no disponible
        """
        try:
            if not self.project_data or 'files' not in self.project_data:
                print("⚠️ No hay project_data disponible")
                # Por defecto, todas disponibles
                for sbn_id in range(1, 22):
                    self.sbn_availability[sbn_id] = True
                return

            project_folder = self.project_data['files'].get('project_folder')
            if not project_folder:
                print("⚠️ No se encontró project_folder")
                # Por defecto, todas disponibles
                for sbn_id in range(1, 22):
                    self.sbn_availability[sbn_id] = True
                return

            csv_path = os.path.join(project_folder, 'SbN_Prioritization.csv')

            if not os.path.exists(csv_path):
                print(f"⚠️ No se encontró {csv_path}")
                # Por defecto, todas disponibles
                for sbn_id in range(1, 22):
                    self.sbn_availability[sbn_id] = True
                return

            # Leer CSV
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # Extraer idoneidad para cada SbN
            for sbn_id in range(1, 22):
                mask = df['ID'] == sbn_id
                if mask.any():
                    idoneidad = df.loc[mask, 'Idoneidad'].values[0]
                    self.sbn_availability[sbn_id] = (idoneidad == 1)
                else:
                    # Si no está en el CSV, asumir disponible
                    self.sbn_availability[sbn_id] = True

            available_count = sum(1 for v in self.sbn_availability.values() if v)
            print(f"✓ Disponibilidad cargada: {available_count}/21 SbN disponibles")

        except Exception as e:
            print(f"⚠️ Error cargando disponibilidad: {e}")
            # Por defecto, todas disponibles
            for sbn_id in range(1, 22):
                self.sbn_availability[sbn_id] = True

    def _setup_ui(self):
        """Crear la interfaz de usuario"""
        # Frame principal con scroll
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text=get_text("sbn_prioritization.title"),
            font=ThemeManager.FONTS['title'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.title_label.pack()

        if self.project_data:
            project_name = self.project_data.get('project_info', {}).get('name', '')
            self.subtitle_label = ctk.CTkLabel(
                header_frame,
                text=f"{get_text('dashboard.name')} {project_name}",
                font=ThemeManager.FONTS['subtitle'],
                text_color=ThemeManager.COLORS['text_secondary']
            )
            self.subtitle_label.pack(pady=(5, 0))

        # ===== SECCIÓN 1: OPCIONES FINANCIERAS =====
        financial_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        financial_frame.pack(fill="x", pady=(0, 15))

        self.financial_title_label = ctk.CTkLabel(
            financial_frame,
            text=get_text("sbn_prioritization.financial_title"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.financial_title_label.pack(pady=(15, 5), padx=15, anchor="w")

        self.financial_desc_label = ctk.CTkLabel(
            financial_frame,
            text=get_text("sbn_prioritization.financial_description"),
            font=ThemeManager.FONTS['caption'],
            text_color=ThemeManager.COLORS['text_secondary'],
            wraplength=600,
            justify="left"
        )
        self.financial_desc_label.pack(pady=(0, 10), padx=15, anchor="w")

        # ComboBox para opciones financieras
        self.financial_combobox = ctk.CTkComboBox(
            financial_frame,
            variable=self.financial_option_var,
            values=[
                get_text("sbn_prioritization.financial_options.investment"),
                get_text("sbn_prioritization.financial_options.maintenance"),
                get_text("sbn_prioritization.financial_options.investment_and_maintenance")
            ],
            width=400,
            font=ThemeManager.FONTS['body'],
            dropdown_font=ThemeManager.FONTS['body'],
            state="readonly"
        )
        self.financial_combobox.pack(pady=(0, 15), padx=15)
        self.financial_combobox.set(get_text("sbn_prioritization.financial_options.investment_and_maintenance"))

        # ===== SECCIÓN 2: SELECCIÓN DE SBN =====
        sbn_frame = ctk.CTkFrame(main_frame, **ThemeManager.get_frame_style())
        sbn_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.sbn_title_label = ctk.CTkLabel(
            sbn_frame,
            text=get_text("sbn_prioritization.sbn_selection_title"),
            font=ThemeManager.FONTS['heading'],
            text_color=ThemeManager.COLORS['accent_primary']
        )
        self.sbn_title_label.pack(pady=(15, 10), padx=15, anchor="w")

        # Botones de seleccionar/deseleccionar
        buttons_frame = ctk.CTkFrame(sbn_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.select_all_btn = ctk.CTkButton(
            buttons_frame,
            text=get_text("sbn_prioritization.select_all"),
            width=150,
            height=30,
            command=self._select_all_sbn,
            fg_color=ThemeManager.COLORS['accent_secondary'],
            hover_color=ThemeManager.COLORS['accent_primary'],
            font=ThemeManager.FONTS['caption']
        )
        self.select_all_btn.pack(side="left", padx=(0, 10))

        self.deselect_all_btn = ctk.CTkButton(
            buttons_frame,
            text=get_text("sbn_prioritization.deselect_all"),
            width=150,
            height=30,
            command=self._deselect_all_sbn,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary'],
            font=ThemeManager.FONTS['caption']
        )
        self.deselect_all_btn.pack(side="left")

        # Frame scrollable para checkboxes
        scrollable_frame = ctk.CTkScrollableFrame(
            sbn_frame,
            height=350,
            fg_color=ThemeManager.COLORS['bg_secondary']
        )
        scrollable_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Crear checkboxes para las 21 SbN
        for sbn_id in range(1, 22):
            sbn_name = get_text(f"sbn_solutions.{sbn_id}")
            is_available = self.sbn_availability.get(sbn_id, True)

            # Texto del checkbox
            checkbox_text = sbn_name
            if not is_available:
                checkbox_text += f" {get_text('sbn_prioritization.not_available')}"

            # Crear checkbox
            checkbox = ctk.CTkCheckBox(
                scrollable_frame,
                text=checkbox_text,
                font=ThemeManager.FONTS['body'],
                text_color=ThemeManager.COLORS['text_primary'] if is_available else ThemeManager.COLORS['text_light'],
                fg_color=ThemeManager.COLORS['accent_primary'],
                hover_color=ThemeManager.COLORS['accent_secondary'],
                state="normal" if is_available else "disabled"
            )

            # Por defecto: seleccionadas si están disponibles
            if is_available:
                checkbox.select()

            checkbox.pack(anchor="w", pady=5, padx=10)
            self.sbn_checkboxes[sbn_id] = checkbox

        # ===== BOTONES DE ACCIÓN =====
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text=get_text("sbn_prioritization.cancel"),
            width=120,
            height=40,
            command=self._on_cancel,
            fg_color=ThemeManager.COLORS['text_light'],
            hover_color=ThemeManager.COLORS['text_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body']
        )
        self.cancel_btn.pack(side="right", padx=(15, 0))

        self.next_btn = ctk.CTkButton(
            button_frame,
            text=get_text("sbn_prioritization.next"),
            width=120,
            height=40,
            command=self._on_next,
            fg_color=ThemeManager.COLORS['success'],
            hover_color=ThemeManager.COLORS['accent_secondary'],
            text_color='#FFFFFF',
            font=ThemeManager.FONTS['body']
        )
        self.next_btn.pack(side="right")

    def _select_all_sbn(self):
        """Seleccionar todas las SbN disponibles"""
        for sbn_id, checkbox in self.sbn_checkboxes.items():
            if self.sbn_availability.get(sbn_id, True):  # Solo las disponibles
                checkbox.select()

    def _deselect_all_sbn(self):
        """Deseleccionar todas las SbN"""
        for checkbox in self.sbn_checkboxes.values():
            checkbox.deselect()

    def _get_selected_sbn_ids(self):
        """Obtener lista de IDs de SbN seleccionadas"""
        selected = []
        for sbn_id, checkbox in self.sbn_checkboxes.items():
            if checkbox.get() == 1:  # Checkbox seleccionado
                selected.append(sbn_id)
        return selected

    def _get_financial_option_key(self):
        """Obtener la key de la opción financiera seleccionada"""
        selected_text = self.financial_option_var.get()

        # Mapear texto a key
        options_map = {
            get_text("sbn_prioritization.financial_options.investment"): "investment",
            get_text("sbn_prioritization.financial_options.maintenance"): "maintenance",
            get_text("sbn_prioritization.financial_options.investment_and_maintenance"): "investment_and_maintenance"
        }

        return options_map.get(selected_text, "investment_and_maintenance")

    def _on_next(self):
        """Validar y guardar configuración"""
        # Validar que al menos una SbN esté seleccionada
        selected_sbn = self._get_selected_sbn_ids()
        if not selected_sbn:
            messagebox.showwarning(
                get_text("messages.warning"),
                get_text("sbn_prioritization.no_selection_error")
            )
            return

        # Construir resultado
        financial_key = self._get_financial_option_key()

        self.result = {
            'financial_option': financial_key,
            'selected_sbn_codes': selected_sbn
        }

        print(f"✓ Configuración guardada: {len(selected_sbn)} SbN, opción: {financial_key}")

        # Cerrar ventana
        self.destroy()

    def _on_cancel(self):
        """Cancelar y cerrar sin guardar"""
        self.result = None
        self.destroy()

    def _update_texts(self):
        """Actualizar textos cuando cambia el idioma"""
        try:
            # Título
            self.title(get_text("sbn_prioritization.title"))

            if hasattr(self, 'title_label'):
                self.title_label.configure(text=get_text("sbn_prioritization.title"))

            if hasattr(self, 'subtitle_label') and self.project_data:
                project_name = self.project_data.get('project_info', {}).get('name', '')
                self.subtitle_label.configure(text=f"{get_text('dashboard.name')} {project_name}")

            # Sección financiera
            if hasattr(self, 'financial_title_label'):
                self.financial_title_label.configure(text=get_text("sbn_prioritization.financial_title"))

            if hasattr(self, 'financial_desc_label'):
                self.financial_desc_label.configure(text=get_text("sbn_prioritization.financial_description"))

            if hasattr(self, 'financial_combobox'):
                current_key = self._get_financial_option_key()
                self.financial_combobox.configure(
                    values=[
                        get_text("sbn_prioritization.financial_options.investment"),
                        get_text("sbn_prioritization.financial_options.maintenance"),
                        get_text("sbn_prioritization.financial_options.investment_and_maintenance")
                    ]
                )
                # Mantener selección actual
                if current_key == "investment":
                    self.financial_combobox.set(get_text("sbn_prioritization.financial_options.investment"))
                elif current_key == "maintenance":
                    self.financial_combobox.set(get_text("sbn_prioritization.financial_options.maintenance"))
                else:
                    self.financial_combobox.set(get_text("sbn_prioritization.financial_options.investment_and_maintenance"))

            # Sección SbN
            if hasattr(self, 'sbn_title_label'):
                self.sbn_title_label.configure(text=get_text("sbn_prioritization.sbn_selection_title"))

            if hasattr(self, 'select_all_btn'):
                self.select_all_btn.configure(text=get_text("sbn_prioritization.select_all"))

            if hasattr(self, 'deselect_all_btn'):
                self.deselect_all_btn.configure(text=get_text("sbn_prioritization.deselect_all"))

            # Checkboxes de SbN
            for sbn_id, checkbox in self.sbn_checkboxes.items():
                sbn_name = get_text(f"sbn_solutions.{sbn_id}")
                is_available = self.sbn_availability.get(sbn_id, True)

                checkbox_text = sbn_name
                if not is_available:
                    checkbox_text += f" {get_text('sbn_prioritization.not_available')}"

                checkbox.configure(text=checkbox_text)

            # Botones
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(text=get_text("sbn_prioritization.cancel"))

            if hasattr(self, 'next_btn'):
                self.next_btn.configure(text=get_text("sbn_prioritization.next"))

        except Exception as e:
            print(f"Error actualizando textos: {e}")
