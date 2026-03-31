import datetime
import streamlit as st

# Tentative d'import sécurisée de pandas
try:
    import pandas as pd
except ImportError:
    # Fallback pour éviter l'erreur 'pd' not defined
    class MockPandas:
        def DataFrame(self, data=None, *args, **kwargs): 
            return None
    pd = MockPandas()

# --- 1. INITIALISATION ET PROFIL ---

def init_firebase():
    """Initialisation neutralisée pour le mode local/session."""
    return None, None

def load_profile(user_id=None):
    """Charge un profil par défaut dans le st.session_state."""
    default_profile = {
        "betrail_index": 50.0,
        "intervals_id": "",
        "intervals_api": "",
        "race_plan": [],
        "last_sync": datetime.datetime.now().strftime("%Y-%m-%d")
    }
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = default_profile
    return st.session_state.user_profile

def save_user_profile(user_id, profile_data):
    """Sauvegarde les données dans la session en cours."""
    st.session_state.user_profile = profile_data
    return True

# --- 2. RÉCUPÉRATION DES DONNÉES (FITNESS & BETRAIL) ---

def get_athlete_fitness(icu_id, icu_api):
    """
    Simule ou récupère les données de fitness depuis Intervals.icu.
    Si les IDs sont vides, retourne un DataFrame de démonstration.
    """
    if not icu_id or not icu_api:
        # Données fictives pour que l'app s'affiche même sans API
        data = {
            "date": pd.to_datetime([datetime.date.today() - datetime.timedelta(days=i) for i in range(30, -1, -1)]),
            "icu_ctl": [40 + i*0.5 for i in range(31)],
            "icu_atl": [50 + i*0.3 for i in range(31)],
            "icu_tsb": [-10 + (i%5) for i in range(31)]
        }
        return pd.DataFrame(data) if not isinstance(pd, MockPandas) else None
    
    # Logique réelle de fetch (simplifiée pour l'exemple)
    return None

def get_betrail_index(username):
    """Simule la récupération de l'index BeTrail."""
    if not username:
        return 50.0
    # Logique de scraping ou API à implémenter ici
    return 62.5 

# --- 3. ANALYSE ET CALCULS ---

def get_training_status(fitness_df):
    """Analyse l'état de forme actuel via le CTL/TSB."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données absentes"}
    
    try:
        last = fitness_df.iloc[-1]
        ctl = last.get('icu_ctl', 0)
        tsb = last.get('icu_tsb', 0)
        
        if tsb < -20: status = "Surentraînement"
        elif tsb < -10: status = "Intensif"
        elif tsb < 5: status = "Productif"
        else: status = "Repos / Frais"
        
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except Exception:
        return {"ctl": 0, "tsb": 0, "status": "Erreur analyse"}

def calculate_race_prediction(km, d_plus, betrail_index):
    """Estime le temps de course basé sur l'effort-kilomètre."""
    idx = float(betrail_index) if betrail_index else 50.0
    effort_km = float(km) + (float(d_plus) / 100.0)
    base_speed = (idx / 50.0) * 6.5 # Vitesse de base arbitraire
    
    time_hours = effort_km / base_speed if base_speed > 0 else 0
    return {
        "hours": time_hours,
        "effort_km": effort_km,
        "speed_kmh": float(km) / time_hours if time_hours > 0 else 0
    }

def calculate_pace_zones(betrail_index):
    """Détermine les zones d'allure d'entraînement."""
    idx = float(betrail_index) if betrail_index else 50.0
    v_ref = (idx / 50.0) * 8.0 
    return {
        "Récupération": v_ref * 0.65,
        "Endurance": v_ref * 0.75,
        "Tempo": v_ref * 0.85,
        "Seuil": v_ref * 0.95
    }

def get_coaching_strategy(metrics):
    """Génère une recommandation de couleur et de conseil."""
    tsb = metrics.get('tsb', 0)
    if tsb < -15:
        return {"color": "#ef4444", "advice": "Le risque de blessure est élevé. Levez le pied."}
    elif tsb < 5:
        return {"color": "#10b981", "advice": "Charge de travail idéale pour progresser."}
    else:
        return {"color": "#3b82f6", "advice": "Vous êtes frais. C'est le moment d'une séance intense."}

def get_ia_coaching_feedback(df):
    """Simule un retour d'IA sur l'historique d'entraînement."""
    return "Votre progression CTL est constante. Attention à ne pas dépasser un pic de fatigue (TSB) trop brutal avant votre objectif."
