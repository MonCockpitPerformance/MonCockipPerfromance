import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

# Import sécurisé de ensure_dataframe
try:
    from core.data import ensure_dataframe
except ImportError:
    def ensure_dataframe(df):
        return pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df

def init_firebase():
    """Initialise la connexion à Firebase (Placeholder pour l'import)."""
    return True

def load_profile(user_id=None):
    """
    Charge le profil utilisateur. 
    Ajouté pour corriger l'erreur : cannot import name 'load_profile'
    """
    # Si vous n'utilisez pas encore de base de données, on retourne des valeurs par défaut
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "betrail_index": 45.0,
            "name": "Athlète",
            "weight": 70.0
        }
    return st.session_state.user_profile

def save_profile(profile_data):
    """Sauvegarde le profil utilisateur."""
    st.session_state.user_profile = profile_data
    return True

def calculate_race_prediction(km, d_plus, betrail_index):
    """
    Calcule le temps estimé d'une course.
    Formule basée sur l'effort corrigé (km + d+/100) et l'indice de performance.
    """
    if not betrail_index or betrail_index <= 0:
        return None
    
    # Effort corrigé (méthode classique trail : 1km = 100m D+)
    effort_km = km + (d_plus / 100.0)
    
    # L'indice BeTrail reflète la vitesse sur un effort corrigé.
    # Un indice de 50 correspond environ à 6.5 km effort / h
    base_speed_effort = (betrail_index / 50.0) * 6.5
    
    time_hours = effort_km / base_speed_effort
    
    return {
        "hours": time_hours,
        "effort_km": effort_km,
        "speed_kmh": km / time_hours if time_hours > 0 else 0
    }

def get_training_status(fitness_df):
    """Analyse le dernier état de forme (CTL/ATL/TSB)."""
    df = ensure_dataframe(fitness_df)
    if df.empty or 'icu_ctl' not in df.columns:
        return None
    
    last_row = df.iloc[-1]
    ctl = last_row.get('icu_ctl', 0)
    atl = last_row.get('icu_atl', 0)
    tsb = last_row.get('icu_tsb', 0)
    
    if tsb > 5: status = "Frais (Optimisation)"
    elif tsb < -20: status = "Surentraînement (Risque)"
    elif tsb < -10: status = "Productif"
    else: status = "Neutre"
    
    return {
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "tsb": round(tsb, 1),
        "status": status
    }

def estimate_finish_time_from_gpx(gpx_df, betrail_index):
    """Utilise les données GPX pour une estimation fine."""
    df = ensure_dataframe(gpx_df)
    if df.empty or 'distance' not in df.columns or 'elevation' not in df.columns:
        return None
    
    total_km = df['distance'].max()
    df['ele_diff'] = df['elevation'].diff().fillna(0)
    total_d_plus = df[df['ele_diff'] > 0]['ele_diff'].sum()
    
    prediction = calculate_race_prediction(total_km, total_d_plus, betrail_index)
    
    if prediction:
        prediction['total_km'] = total_km
        prediction['total_d_plus'] = total_d_plus
        
    return prediction

def calculate_pace_zones(betrail_index):
    """Génère des zones d'allure théoriques."""
    vbe = (betrail_index / 50.0) * 7.0 
    
    zones = {
        "Z1 (Récupération)": vbe * 0.60,
        "Z2 (Endurance)": vbe * 0.75,
        "Z3 (Tempo)": vbe * 0.85,
        "Z4 (Seuil)": vbe * 0.95,
        "Z5 (VMA)": vbe * 1.10
    }
    return zones
