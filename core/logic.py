import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

# --- FONCTIONS DE GESTION (Pour éviter les erreurs d'import) ---

def init_firebase():
    """Initialise la connexion Firebase (Simulation pour éviter le crash)."""
    return None, None

def load_profile(user_id=None):
    """Charge le profil utilisateur depuis la session ou défaut."""
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "betrail_index": 50.0,
            "intervals_id": "",
            "intervals_api": "",
            "race_plan": []
        }
    return st.session_state.user_profile

def save_user_profile(user_id, profile_data):
    """Sauvegarde le profil dans la session."""
    st.session_state.user_profile = profile_data
    return True

def get_athlete_fitness(uid, api_key):
    """Simule la récupération des données Fitness si l'API n'est pas prête."""
    return pd.DataFrame()

def ensure_dataframe(df):
    """Sécurité pour transformer n'importe quoi en DataFrame propre."""
    if df is None: return pd.DataFrame()
    return pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df

# --- TES CALCULS DE TRAIL ---

def calculate_race_prediction(km, d_plus, betrail_index):
    """Calcule le temps estimé d'une course (Effort corrigé)."""
    if not betrail_index or betrail_index <= 0:
        return None
    
    effort_km = km + (d_plus / 100.0)
    base_speed_effort = (betrail_index / 50.0) * 6.5
    time_hours = effort_km / base_speed_effort
    
    return {
        "hours": time_hours,
        "effort_km": effort_km,
        "speed_kmh": km / time_hours if time_hours > 0 else 0
    }

def get_training_status(fitness_df):
    """Analyse l'état de forme (CTL/ATL/TSB)."""
    df = ensure_dataframe(fitness_df)
    if df.empty or 'icu_ctl' not in df.columns:
        return None
    
    last_row = df.iloc[-1]
    ctl, atl, tsb = last_row.get('icu_ctl', 0), last_row.get('icu_atl', 0), last_row.get('icu_tsb', 0)
    
    if tsb > 5: status = "Frais (Optimisation)"
    elif tsb < -20: status = "Surentraînement"
    elif tsb < -10: status = "Productif"
    else: status = "Neutre"
    
    return {"ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(tsb, 1), "status": status}

def calculate_pace_zones(betrail_index):
    """Génère les zones d'allure théoriques."""
    vbe = (betrail_index / 50.0) * 7.0 
    return {
        "Z1 (Récupération)": vbe * 0.60,
        "Z2 (Endurance)": vbe * 0.75,
        "Z3 (Tempo)": vbe * 0.85,
        "Z4 (Seuil)": vbe * 0.95,
        "Z5 (VMA)": vbe * 1.10
    }

def get_coaching_strategy(metrics):
    """Définit la couleur et le conseil selon le TSB."""
    tsb = metrics.get('tsb', 0)
    if tsb < -20: return {"status": "Fatigue", "advice": "Repos requis.", "color": "#ef4444"}
    return {"status": "OK", "advice": "Continuez.", "color": "#10b981"}

def get_ia_coaching_feedback(df):
    """Analyse IA simplifiée."""
    return "Analyse IA : Votre volume est stable, restez régulier."

def parse_betrail_paste(text):
    """Extrait sommairement les données BeTrail collées."""
    return []
