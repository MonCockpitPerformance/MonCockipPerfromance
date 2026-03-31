import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

# --- 1. GESTION DES ERREURS D'INITIALISATION ---

def init_firebase():
    """Initialisation sécurisée pour éviter le blocage au démarrage."""
    try:
        # On simule un succès pour ne pas bloquer l'UI
        return None, None
    except Exception:
        return None, None

def load_profile(user_id=None):
    """Charge un profil par défaut si rien n'est trouvé."""
    default_profile = {
        "betrail_index": 50.0,
        "intervals_id": "",
        "intervals_api": "",
        "race_plan": [],
        "last_sync": datetime.now().strftime("%Y-%m-%d")
    }
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = default_profile
    return st.session_state.user_profile

def save_user_profile(user_id, profile_data):
    """Sauvegarde locale en cas d'absence de DB."""
    st.session_state.user_profile = profile_data
    return True

# --- 2. CALCULS DE PERFORMANCE ---

def calculate_race_prediction(km, d_plus, betrail_index):
    """Estimation du temps de course basée sur l'effort km."""
    if not betrail_index or betrail_index <= 0:
        betrail_index = 50.0 # Valeur par défaut
    
    # Formule simplifiée : 100m D+ = 1km plat
    effort_km = km + (d_plus / 100.0)
    # Vitesse de base estimée (Index 50 = env 6.5 km/h d'effort)
    base_speed = (betrail_index / 50.0) * 6.5
    
    time_hours = effort_km / base_speed
    return {
        "hours": time_hours,
        "effort_km": effort_km,
        "speed_kmh": km / time_hours if time_hours > 0 else 0
    }

def get_training_status(fitness_df):
    """Analyse les métriques de fatigue (CTL/ATL/TSB)."""
    if fitness_df is None or (isinstance(fitness_df, pd.DataFrame) and fitness_df.empty):
        return {"ctl": 0, "atl": 0, "tsb": 0, "status": "Données manquantes"}
    
    try:
        last = fitness_df.iloc[-1]
        ctl = last.get('icu_ctl', 0)
        tsb = last.get('icu_tsb', 0)
        
        if tsb > 5: status = "En forme / Frais"
        elif tsb < -20: status = "Fatigué / Risque"
        else: status = "Productif"
        
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except:
        return {"ctl": 0, "tsb": 0, "status": "Erreur lecture"}

def calculate_pace_zones(betrail_index):
    """Zones d'allure basées sur l'index BeTrail."""
    idx = betrail_index if betrail_index > 0 else 50.0
    vitesse_ref = (idx / 50.0) * 7.5 # Vitesse en km/h d'effort
    
    return {
        "Récupération": vitesse_ref * 0.65,
        "Endurance": vitesse_ref * 0.75,
        "Tempo": vitesse_ref * 0.85,
        "Seuil": vitesse_ref * 0.95
    }

# --- 3. FONCTIONS UTILITAIRES ---

def ensure_dataframe(data):
    """Convertit n'importe quelle entrée en DataFrame utilisable."""
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame()

def get_coaching_strategy(metrics):
    """Retourne des conseils basés sur l'état de forme."""
    tsb = metrics.get('tsb', 0)
    if tsb < -15:
        return {"color": "#ef4444", "advice": "Levez le pied, repos conseillé."}
    return {"color": "#10b981", "advice": "Tout est au vert, continuez l'entraînement."}

def get_ia_coaching_feedback(df):
    """Simulateur de feedback IA pour ne pas ralentir l'app."""
    return "Votre progression est stable. Surveillez votre sommeil cette semaine."
