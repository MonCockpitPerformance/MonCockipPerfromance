import datetime
import streamlit as st
import numpy as np

# Import standard de pandas
try:
    import pandas as pd
except ImportError:
    # Création d'un objet vide sécurisé si pandas manque (rare sur Streamlit Cloud)
    pd = None

# --- 1. GESTION DU PROFIL ET INITIALISATION ---

def init_firebase():
    """Initialisation des services de données (simulée pour le mode local)."""
    return None, None

def load_profile(user_id=None):
    """
    Charge le profil utilisateur depuis le session_state.
    Initialise des valeurs par défaut si aucune donnée n'existe.
    """
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "betrail_index": 50.0,
            "intervals_id": "",
            "intervals_api": "",
            "race_plan": [],
            "last_sync": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    return st.session_state.user_profile

def save_user_profile(user_id, profile_data):
    """Enregistre les modifications du profil dans la session."""
    st.session_state.user_profile = profile_data
    return True

# --- 2. RÉCUPÉRATION DES DONNÉES DE PERFORMANCE ---

def get_athlete_fitness(icu_id, icu_api):
    """
    Récupère les données de fitness (CTL/ATL/TSB) depuis Intervals.icu.
    Génère des données de démonstration si les identifiants sont absents.
    """
    if pd is None:
        return None

    if not icu_id or not icu_api:
        # Génération de données factices pour éviter le crash de l'interface
        dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(60, -1, -1)]
        data = {
            "date": pd.to_datetime(dates),
            "icu_ctl": np.linspace(30, 55, 61) + np.random.normal(0, 1, 61),
            "icu_atl": np.linspace(35, 70, 61) + np.random.normal(0, 5, 61),
            "icu_tsb": np.random.uniform(-15, 5, 61)
        }
        return pd.DataFrame(data)
    
    # Logique réelle de requête API Intervals.icu à insérer ici
    return None

def get_betrail_index(username):
    """Simule la récupération de l'index de performance BeTrail."""
    if not username:
        return 50.0
    # Simulation d'un index pour un utilisateur actif
    return 64.2

# --- 3. ALGORITHMES DE PRÉDICTION ET ZONES ---

def get_training_status(fitness_df):
    """Analyse les dernières métriques pour définir l'état de forme."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données non disponibles"}
    
    try:
        last_row = fitness_df.iloc[-1]
        ctl = float(last_row.get('icu_ctl', 0))
        tsb = float(last_row.get('icu_tsb', 0))
        
        if tsb < -25: status = "Risque de Fatigue"
        elif tsb < -10: status = "Entraînement Intensif"
        elif tsb < 5: status = "Phase Productive"
        elif tsb < 15: status = "Affûtage / Frais"
        else: status = "Désentraînement"
        
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except Exception:
        return {"ctl": 0, "tsb": 0, "status": "Erreur de lecture"}

def calculate_race_prediction(km, d_plus, betrail_index):
    """
    Calcule le temps estimé sur une course.
    Utilise le concept d'effort-kilomètre (100m D+ = 1km plat).
    """
    idx = float(betrail_index) if betrail_index else 50.0
    # Formule simplifiée : Effort KM = Distance + (D+ / 100)
    effort_km = float(km) + (float(d_plus) / 100.0)
    
    # Vitesse de référence basée sur l'index (Ex: Index 50 ~ 7km/h d'effort)
    ref_speed = (idx / 50.0) * 7.5
    
    time_hours = effort_km / ref_speed if ref_speed > 0 else 0
    
    return {
        "hours": time_hours,
        "effort_km": round(effort_km, 1),
        "speed_kmh": round(float(km) / time_hours, 2) if time_hours > 0 else 0
    }

def calculate_pace_zones(betrail_index):
    """Définit les allures de travail basées sur l'index de performance."""
    idx = float(betrail_index) if betrail_index else 50.0
    # Vitesse de base (Zone Endurance)
    base_v = (idx / 50.0) * 8.5
    
    return {
        "Récupération": round(base_v * 0.70, 2),
        "Endurance Fondamentale": round(base_v * 0.82, 2),
        "Tempo / Seuil": round(base_v * 0.95, 2),
        "VMA Trail": round(base_v * 1.15, 2)
    }

def get_coaching_strategy(metrics):
    """Retourne des conseils visuels selon l'état actuel (TSB)."""
    tsb = metrics.get('tsb', 0)
    if tsb < -20:
        return {"color": "#ef4444", "advice": "Priorité au repos. Sommeil et hydratation requis."}
    elif tsb < 0:
        return {"color": "#f59e0b", "advice": "Charge importante. Continuez mais surveillez les douleurs."}
    else:
        return {"color": "#10b981", "advice": "Prêt pour une séance de qualité ou une compétition."}

def get_ia_coaching_feedback(df):
    """Analyse tendancielle simplifiée simulant une IA."""
    if df is None: return "Connectez vos données pour recevoir une analyse."
    return "Votre charge de travail (CTL) progresse bien. Maintenez cette régularité pour votre prochain objectif."
