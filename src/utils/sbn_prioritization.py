"""
SbN Prioritization Calculation Module

Calculates Nature-based Solutions (SbN) priority scores based on:
- Barriers evaluation (Barriers.csv)
- Water Security challenges (DF_WS.csv)
- Other Challenges (D_O.csv)

Uses weighted matrices from Weight_Matrix.xlsx to compute scores for 21 SbN options.
"""

import pandas as pd
import numpy as np
import os


class SbNPrioritization:
    """Handles SbN prioritization calculations using weighted matrix multiplication"""

    # Path to weight matrix file
    WEIGHT_MATRIX_PATH = os.path.join('src', 'locales', 'Weight_Matrix.xlsx')

    # Template files to copy to new projects
    WEIGHTS_TEMPLATE_PATH = os.path.join('src', 'locales', 'SbN_Weights.csv')
    PRIORITIZATION_TEMPLATE_PATH = os.path.join('src', 'locales', 'SbN_Prioritization.csv')

    @staticmethod
    def calculate_barrier_scores(project_path):
        """
        Calculate SbN scores based on Barriers evaluation.

        Args:
            project_path: Path to project folder

        Returns:
            dict: {sbn_id: score} for all 21 SbN options
        """
        # Read user evaluation
        barriers_file = os.path.join(project_path, 'Barriers.csv')
        if not os.path.exists(barriers_file):
            return {}

        df_barriers = pd.read_csv(barriers_file, encoding='utf-8-sig')

        # Read weight matrix
        weight_matrix_path = SbNPrioritization.WEIGHT_MATRIX_PATH
        df_weights = pd.read_excel(weight_matrix_path, sheet_name='Barreras')

        # Calculate scores
        return SbNPrioritization._calculate_scores(df_barriers, df_weights)

    @staticmethod
    def calculate_water_security_scores(project_path):
        """
        Calculate SbN scores based on Water Security challenges evaluation.

        Args:
            project_path: Path to project folder

        Returns:
            dict: {sbn_id: score} for all 21 SbN options
        """
        # Intentar leer archivo ajustado por costos primero
        ws_file_adjusted = os.path.join(project_path, 'Tmp', 'Weight_Cost_DF_WS.csv')
        ws_file_original = os.path.join(project_path, 'DF_WS.csv')

        if os.path.exists(ws_file_adjusted):
            print("✓ Usando matriz de pesos ajustada por costos")
            ws_file = ws_file_adjusted
        elif os.path.exists(ws_file_original):
            print("⚠️ Usando desafíos de seguridad hídrica originales (sin ajuste de costos)")
            ws_file = ws_file_original
        else:
            return {}

        df_ws = pd.read_csv(ws_file, encoding='utf-8-sig')

        # Si se usa el archivo ajustado, df_ws ya contiene los pesos recategorizados
        # Si se usa el original, necesitamos leer los pesos de Weight_Matrix
        if ws_file == ws_file_adjusted:
            # Los pesos ya están en df_ws, no necesitamos leer Weight_Matrix
            df_weights = df_ws
        else:
            # Leer matriz de pesos original
            weight_matrix_path = SbNPrioritization.WEIGHT_MATRIX_PATH
            df_weights = pd.read_excel(weight_matrix_path, sheet_name='Desafios_Seguridad_Hidrica')

        # Calculate scores
        return SbNPrioritization._calculate_scores(df_ws, df_weights)

    @staticmethod
    def calculate_other_challenges_scores(project_path):
        """
        Calculate SbN scores based on Other Challenges evaluation.

        Args:
            project_path: Path to project folder

        Returns:
            dict: {sbn_id: score} for all 21 SbN options
        """
        # Intentar leer archivo ajustado por costos primero
        oc_file_adjusted = os.path.join(project_path, 'Tmp', 'Weight_Cost_DF_O.csv')
        oc_file_original = os.path.join(project_path, 'D_O.csv')

        if os.path.exists(oc_file_adjusted):
            print("✓ Usando matriz de pesos ajustada por costos")
            oc_file = oc_file_adjusted
        elif os.path.exists(oc_file_original):
            print("⚠️ Usando otros desafíos originales (sin ajuste de costos)")
            oc_file = oc_file_original
        else:
            return {}

        df_oc = pd.read_csv(oc_file, encoding='utf-8-sig')

        # Si se usa el archivo ajustado, df_oc ya contiene los pesos recategorizados
        # Si se usa el original, necesitamos leer los pesos de Weight_Matrix
        if oc_file == oc_file_adjusted:
            # Los pesos ya están en df_oc, no necesitamos leer Weight_Matrix
            df_weights = df_oc
        else:
            # Leer matriz de pesos original
            weight_matrix_path = SbNPrioritization.WEIGHT_MATRIX_PATH
            df_weights = pd.read_excel(weight_matrix_path, sheet_name='Desafios_Otros')

        # Calculate scores
        return SbNPrioritization._calculate_scores(df_oc, df_weights)

    @staticmethod
    def _calculate_scores(df_evaluation, df_weights):
        """
        Core calculation logic using matrix multiplication.

        Process:
        1. Filter by enabled groups: multiply user_value × group_enabled (for barriers)
        2. Transpose values to row vector
        3. Matrix multiply: weights × filtered_values

        Args:
            df_evaluation: DataFrame with user evaluation
                           Barriers: 4 columns (Codigo_Barrera, Valor_Numerico, Codigo_Grupo, Grupo_Habilitado)
                           WS/Other: 2 columns (challenge_code, importance_value)
            df_weights: DataFrame with weight matrix (columns: ID, SbN, [barrier codes...])

        Returns:
            dict: {sbn_id: score} for all 21 SbN options
        """
        try:
            df_eval = df_evaluation.copy()

            # Detect format based on number of columns
            if len(df_eval.columns) == 4:
                # Barriers format: has group_enabled column
                df_eval.columns = ['Codigo_Barrera', 'Valor_Numerico', 'Codigo_Grupo', 'Grupo_Habilitado']

                # Step 1: Element-wise multiplication (user_value × group_enabled)
                # This filters out values from disabled groups
                df_eval['Valor_Filtrado'] = df_eval['Valor_Numerico'] * df_eval['Grupo_Habilitado']

                # Create dict: {barrier_code: filtered_value}
                values_dict = dict(zip(df_eval['Codigo_Barrera'], df_eval['Valor_Filtrado']))

            elif len(df_eval.columns) == 2:
                # Water Security / Other Challenges format: simple code + value
                df_eval.columns = ['Codigo', 'Valor']

                # No filtering needed, use values directly
                values_dict = dict(zip(df_eval['Codigo'], df_eval['Valor']))

            else:
                print(f"Error: Unexpected number of columns: {len(df_eval.columns)}")
                return {}

            # Step 2: Extract weight matrix and barrier codes
            # Weight matrix columns: ID, SbN, [barrier codes...]
            barrier_codes = list(df_weights.columns[2:])  # Skip ID and SbN columns

            # Create value vector aligned with barrier codes in weight matrix
            # If a barrier code is missing, use 0
            value_vector = np.array([values_dict.get(code, 0) for code in barrier_codes])

            # Get weight matrix (rows = SbN, columns = barriers)
            weight_matrix = df_weights[barrier_codes].values

            # Step 3: Matrix multiplication
            # weight_matrix shape: (21, num_barriers)
            # value_vector shape: (num_barriers,)
            # Result: (21,) - one score per SbN
            scores = np.dot(weight_matrix, value_vector)

            # Create result dict: {sbn_id: score}
            result = {}
            for idx, row in df_weights.iterrows():
                sbn_id = row['ID']
                result[sbn_id] = float(scores[idx])

            return result

        except Exception as e:
            print(f"Error calculating SbN scores: {e}")
            return {}

    @staticmethod
    def update_sbn_prioritization(project_path, column_name, scores):
        """
        Update SbN weights and prioritization files with calculated scores.

        Process:
        1. Save raw scores to SbN_Weights.csv
        2. Normalize all columns in SbN_Weights.csv (divide by max)
        3. Save normalized scores to SbN_Prioritization.csv

        Args:
            project_path: Path to project folder
            column_name: Column to update ('Barriers', 'WS', or 'Other')
            scores: dict {sbn_id: raw_score}
        """
        try:
            weights_file = os.path.join(project_path, 'SbN_Weights.csv')
            prioritization_file = os.path.join(project_path, 'SbN_Prioritization.csv')

            # Check if files exist
            if not os.path.exists(weights_file) or not os.path.exists(prioritization_file):
                print(f"Warning: Template files missing. Creating from templates.")
                SbNPrioritization.copy_template_to_project(project_path)

            # Step 1: Update raw scores in SbN_Weights.csv
            df_weights = pd.read_csv(weights_file, encoding='utf-8-sig')

            for sbn_id, score in scores.items():
                mask = df_weights['ID'] == sbn_id
                if mask.any():
                    df_weights.loc[mask, column_name] = score

            df_weights.to_csv(weights_file, index=False, encoding='utf-8-sig')
            print(f"Updated {column_name} raw scores in SbN_Weights.csv")

            # Step 2: Normalize and save to SbN_Prioritization.csv
            SbNPrioritization._normalize_and_save_prioritization(project_path)

        except Exception as e:
            print(f"Error updating SbN prioritization: {e}")

    @staticmethod
    def _normalize_and_save_prioritization(project_path):
        """
        Read SbN_Weights.csv, normalize each column (Barriers, WS, Other),
        and save to SbN_Prioritization.csv

        Args:
            project_path: Path to project folder
        """
        try:
            weights_file = os.path.join(project_path, 'SbN_Weights.csv')
            prioritization_file = os.path.join(project_path, 'SbN_Prioritization.csv')

            # Read raw weights
            df_weights = pd.read_csv(weights_file, encoding='utf-8-sig')

            # Read prioritization (to preserve structure and Prioridad column)
            df_prior = pd.read_csv(prioritization_file, encoding='utf-8-sig')

            # Normalize each column: divide by max value (0-1 range)
            columns_to_normalize = ['Barriers', 'WS', 'Other']

            for col in columns_to_normalize:
                if col in df_weights.columns:
                    max_value = df_weights[col].max()
                    if max_value > 0:
                        # Normalize: divide by max
                        normalized = df_weights[col] / max_value
                        df_prior[col] = normalized
                    else:
                        # If all values are 0, keep them as 0
                        df_prior[col] = 0

            # Calculate final priority: (Barriers + WS + Other) × Idoneidad
            df_prior['Prioridad'] = (df_prior['Barriers'] + df_prior['WS'] + df_prior['Other']) * df_prior['Idoneidad']

            # Save normalized values and priority
            df_prior.to_csv(prioritization_file, index=False, encoding='utf-8-sig')
            print(f"Normalized and saved to SbN_Prioritization.csv with Prioridad calculated")

        except Exception as e:
            print(f"Error normalizing prioritization: {e}")

    @staticmethod
    def copy_template_to_project(project_path):
        """
        Copy SbN_Weights.csv and SbN_Prioritization.csv templates to project folder.

        Args:
            project_path: Path to project folder
        """
        try:
            # Copy SbN_Weights.csv
            weights_template = SbNPrioritization.WEIGHTS_TEMPLATE_PATH
            weights_dest = os.path.join(project_path, 'SbN_Weights.csv')

            if os.path.exists(weights_template):
                df = pd.read_csv(weights_template, encoding='utf-8-sig')
                df.to_csv(weights_dest, index=False, encoding='utf-8-sig')
                print(f"Copied SbN_Weights.csv template to {project_path}")
            else:
                print(f"Warning: Template {weights_template} not found")

            # Copy SbN_Prioritization.csv
            prior_template = SbNPrioritization.PRIORITIZATION_TEMPLATE_PATH
            prior_dest = os.path.join(project_path, 'SbN_Prioritization.csv')

            if os.path.exists(prior_template):
                df = pd.read_csv(prior_template, encoding='utf-8-sig')
                df.to_csv(prior_dest, index=False, encoding='utf-8-sig')
                print(f"Copied SbN_Prioritization.csv template to {project_path}")
            else:
                print(f"Warning: Template {prior_template} not found")

        except Exception as e:
            print(f"Error copying SbN templates: {e}")

    @staticmethod
    def update_barriers(project_path):
        """
        Calculate and update Barriers column in SbN_Prioritization.csv

        Args:
            project_path: Path to project folder
        """
        scores = SbNPrioritization.calculate_barrier_scores(project_path)
        if scores:
            SbNPrioritization.update_sbn_prioritization(project_path, 'Barriers', scores)

    @staticmethod
    def update_water_security(project_path):
        """
        Calculate and update WS column in SbN_Prioritization.csv

        Args:
            project_path: Path to project folder
        """
        scores = SbNPrioritization.calculate_water_security_scores(project_path)
        if scores:
            SbNPrioritization.update_sbn_prioritization(project_path, 'WS', scores)

    @staticmethod
    def update_other_challenges(project_path):
        """
        Calculate and update Other column in SbN_Prioritization.csv

        Args:
            project_path: Path to project folder
        """
        scores = SbNPrioritization.calculate_other_challenges_scores(project_path)
        if scores:
            SbNPrioritization.update_sbn_prioritization(project_path, 'Other', scores)

    @staticmethod
    def get_sbn_priorities_Old(project_path):
        """
        Get final priority for each SbN from SbN_Prioritization.csv.

        The Prioridad column is already calculated as: (Barriers + WS + Other) × Idoneidad

        Returns dict with:
        {
            sbn_id: {
                'priority_value': float,  # Final priority value
                'priority_rank': int,     # Ranking (1 = highest priority)
                'is_enabled': bool        # False if priority = 0
            }
        }

        Args:
            project_path: Path to project folder

        Returns:
            dict: Priority information for each SbN
        """
        try:
            prioritization_file = os.path.join(project_path, 'SbN_Prioritization.csv')

            if not os.path.exists(prioritization_file):
                print(f"Warning: {prioritization_file} not found")
                return {}

            # Read prioritization file
            df = pd.read_csv(prioritization_file, encoding='utf-8-sig')

            # Use the Prioridad column directly (already calculated)
            # Create result dict
            result = {}

            # Filter enabled SbN (priority > 0) and sort by priority
            enabled_df = df[df['Prioridad'] > 0].copy()
            enabled_df = enabled_df.sort_values('Prioridad', ascending=False)

            # Assign ranking
            for rank, (_, row) in enumerate(enabled_df.iterrows(), start=1):
                sbn_id = int(row['ID'])
                result[sbn_id] = {
                    'priority_value': float(row['Prioridad']),
                    'priority_rank': rank,
                    'is_enabled': True
                }

            # Add disabled SbN (priority = 0)
            disabled_df = df[df['Prioridad'] == 0]
            for _, row in disabled_df.iterrows():
                sbn_id = int(row['ID'])
                result[sbn_id] = {
                    'priority_value': 0.0,
                    'priority_rank': None,
                    'is_enabled': False
                }

            return result

        except Exception as e:
            print(f"Error getting SbN priorities: {e}")
            return {}

    def get_sbn_priorities(project_path):
        """
        Igual que antes, pero el dict queda ordenado por priority_rank
        (primero las habilitadas por prioridad, luego las de 0).
        """

        from collections import OrderedDict

        try:
            prioritization_file = os.path.join(project_path, 'SbN_Prioritization.csv')

            if not os.path.exists(prioritization_file):
                print(f"Warning: {prioritization_file} not found")
                return {}

            df = pd.read_csv(prioritization_file, encoding='utf-8-sig')

            result_tmp = {}

            # habilitadas > 0
            enabled_df = df[df['Prioridad'] > 0].copy()
            enabled_df = enabled_df.sort_values('Prioridad', ascending=False)

            for rank, (_, row) in enumerate(enabled_df.iterrows(), start=1):
                sbn_id = int(row['ID'])
                result_tmp[sbn_id] = {
                    'priority_value': float(row['Prioridad']),
                    'priority_rank': rank,
                    'is_enabled': True
                }

            # deshabilitadas = 0
            disabled_df = df[df['Prioridad'] == 0]
            for _, row in disabled_df.iterrows():
                sbn_id = int(row['ID'])
                result_tmp[sbn_id] = {
                    'priority_value': 0.0,
                    'priority_rank': None,
                    'is_enabled': False
                }

            # 👇 ordenar por priority_rank (None al final)
            ordered = OrderedDict(
                sorted(
                    result_tmp.items(),
                    key=lambda x: (x[1]['priority_rank'] is None, x[1]['priority_rank'] or 0)
                )
            )
            return ordered

        except Exception as e:
            print(f"Error getting SbN priorities: {e}")
            return {}