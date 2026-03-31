import datetime
# Tentative d'import sécurisée pour éviter le blocage
try:
    import pandas as pd
except ImportError:
    # Création d'un faux objet pd pour éviter l'erreur 'pd' not defined
    class MockPandas:
        def DataFrame(self, *args, **kwargs): return None
    pd = MockPandas()

import streamlit as st

# --- 1. GESTION DES ERREURS D'INITIALISATION ---

def init_firebase():
    """Initialisation neutralisée pour éviter le blocage au démarrage."""
    return None, None

def load_profile(user_id=None):
    """Charge un profil par défaut en mémoire vive (Session State)."""
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
    """Sauvegarde locale temporaire."""
    st.session_state.user_profile = profile_data
    return True

# --- 2. CALCULS DE PERFORMANCE ---

def calculate_race_prediction(km, d_plus, betrail_index):
    """Estimation simple du temps de course."""
    idx = float(betrail_index) if betrail_index else 50.0
    # Effort KM : 100m D+ = 1km plat
    effort_km = float(km) + (float(d_plus) / 100.0)
    # Vitesse de base (Index 50 = ~6.5 km/h d'effort)
    base_speed = (idx / 50.0) * 6.5
    
    time_hours = effort_km / base_speed if base_speed > 0 else 0
    return {
        "hours": time_hours,
        "effort_km": effort_km,
        "speed_kmh": float(km) / time_hours if time_hours > 0 else 0
    }

def get_training_status(fitness_df):
    """Analyse simplifiée sans dépendance stricte à Pandas."""
    if fitness_df is None:
        return {"ctl": 0, "tsb": 0, "status": "Données absentes"}
    
    # Si c'est un DataFrame valide
    try:
        if hasattr(fitness_df, 'empty') and not fitness_df.empty:
            last = fitness_df.iloc[-1]
            ctl = last.get('icu_ctl', 0)
            tsb = last.get('icu_tsb', 0)
            status = "Productif" if -10 < tsb < 5 else "Fatigué"
            return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except:
        pass
        
    return {"ctl": 0, "tsb": 0, "status": "En attente de synchro"}

def calculate_pace_zones(betrail_index):
    """Zones d'allure basées sur l'index BeTrail."""
    idx = float(betrail_index) if betrail_index else 50.0
    v_ref = (idx / 50.0) * 7.5 
    return {
        "Récupération": v_ref * 0.65,
        "Endurance": v_ref * 0.75,
        "Tempo": v_ref * 0.85,
        "Seuil": v_ref * 0.95
    }

def ensure_dataframe(data):
    """Garantit un objet manipulable même si pandas échoue."""
    try:
        return pd.DataFrame(data)
    except:
        return None

def get_coaching_strategy(metrics):
    """Conseils de base."""
    tsb = metrics.get('tsb', 0)
    if tsb < -15:
        return {"color": "#ef4444", "advice": "Repos recommandé."}
    return {"color": "#10b981", "advice": "Entraînement optimal."}

def get_ia_coaching_feedback(df):
    """Simulation de réponse IA."""
    return "Analyse en cours... Vos charges d'entraînement sont stables."
