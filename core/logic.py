import datetime
import streamlit as st
import numpy as np
import requests
import time
import firebase_admin
from firebase_admin import credentials, firestore

# Import standard de pandas avec gestion d'erreur
try:
    import pandas as pd
except ImportError:
    pd = None

# --- 1. GESTION DU PROFIL ET INITIALISATION FIREBASE ---

def init_firebase():
    """Initialise la connexion Firestore en utilisant les secrets Streamlit."""
    if not firebase_admin._apps:
        try:
            creds_dict = dict(st.secrets["firebase_service_account"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation Firebase : {e}")
            return None, None
    db = firestore.client()
    return db, st.secrets.get("firebase", {})

def load_profile(user_id):
    """Charge le profil utilisateur depuis Firestore."""
    if not user_id:
        return {}
    db, _ = init_firebase()
    if not db:
        return {}
    try:
        app_id = "cockpit-perf-v2"
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {
            "betrail_index": 50.0,
            "intervals_id": "",
            "intervals_api": "",
            "race_plan": [],
            "last_sync": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    except Exception as e:
        st.error(f"Erreur chargement profil : {e}")
        return {}

def save_user_profile(user_id, profile_data):
    """Enregistre les modifications du profil."""
    if not user_id: return False
    db, _ = init_firebase()
    if not db: return False
    try:
        app_id = "cockpit-perf-v2"
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc_ref.set(profile_data, merge=True)
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde profil : {e}")
        return False

# --- 2. RÉCUPÉRATION DES DONNÉES DE PERFORMANCE ---

def get_athlete_fitness(icu_id, icu_api):
    """Simule ou récupère les données fitness."""
    if pd is None: return None
    if not icu_id or not icu_api:
        dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(60, -1, -1)]
        data = {
            "date": pd.to_datetime(dates),
            "icu_ctl": np.linspace(30, 55, 61) + np.random.normal(0, 1, 61),
            "icu_atl": np.linspace(35, 70, 61) + np.random.normal(0, 5, 61),
            "icu_tsb": np.random.uniform(-15, 5, 61)
        }
        return pd.DataFrame(data)
    return None

# --- 3. ALGORITHMES DE CALCUL ---

def get_training_status(fitness_df):
    """Analyse l'état de forme actuel."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données non disponibles"}
    last_row = fitness_df.iloc[-1]
    ctl, tsb = float(last_row.get('icu_ctl', 0)), float(last_row.get('icu_tsb', 0))
    if tsb < -25: status = "Risque de Fatigue"
    elif tsb < -10: status = "Entraînement Intensif"
    elif tsb < 5: status = "Phase Productive"
    elif tsb < 15: status = "Affûtage / Frais"
    else: status = "Désentraînement"
    return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}

def calculate_race_prediction(km, d_plus, betrail_index):
    idx = float(betrail_index or 50.0)
    effort_km = float(km) + (float(d_plus) / 100.0)
    ref_speed = (idx / 50.0) * 7.5
    time_h = effort_km / ref_speed if ref_speed > 0 else 0
    return {"hours": time_h, "effort_km": round(effort_km, 1), "speed_kmh": round(float(km)/time_h, 2) if time_h > 0 else 0}

def calculate_pace_zones(betrail_index):
    idx = float(betrail_index or 50.0)
    base_v = (idx / 50.0) * 8.5
    return {
        "Récupération": round(base_v * 0.70, 2),
        "Endurance Fondamentale": round(base_v * 0.82, 2),
        "Tempo / Seuil": round(base_v * 0.95, 2),
        "VMA Trail": round(base_v * 1.15, 2)
    }

def get_coaching_strategy(metrics):
    tsb = metrics.get('tsb', 0)
    if tsb < -20: return {"color": "#ef4444", "advice": "Priorité au repos."}
    if tsb < 0: return {"color": "#f59e0b", "advice": "Charge importante."}
    return {"color": "#10b981", "advice": "Prêt pour l'intensité."}

# --- 4. FONCTION IA (CRITIQUE POUR L'IMPORT) ---

def get_ai_response(user_query, athlete_context, system_prompt=None):
    """
    Fonction appelée par cockpit.py pour l'analyse IA.
    """
    api_key = "" # Fourni par l'environnement
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    if not system_prompt:
        system_prompt = "Tu es un coach expert en Trail Running. Analyse les données (CTL, TSB) et conseille l'athlète."

    payload = {
        "contents": [{"parts": [{"text": f"Context: {athlete_context}\nQuery: {user_query}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    # Tentatives avec exponential backoff
    for i in range(5):
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 429:
                time.sleep(2**i)
                continue
            break
        except:
            time.sleep(2**i)
    return "L'IA ne répond pas pour le moment."

# Alias pour compatibilité descendante
def get_ia_coaching_feedback(df):
    if df is None: return "Pas de données."
    st_val = get_training_status(df)
    return f"Statut: {st_val['status']} (CTL: {st_val['ctl']})"

def get_betrail_index(username):
    return 64.2 if username else 50.0
