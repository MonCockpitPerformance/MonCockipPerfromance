import datetime
import streamlit as st
import numpy as np
import requests
import time
import firebase_admin
from firebase_admin import credentials, firestore

# Import standard de pandas
try:
    import pandas as pd
except ImportError:
    pd = None

# --- 1. GESTION DU PROFIL ET INITIALISATION FIREBASE ---

def init_firebase():
    """Initialise la connexion Firestore en utilisant les secrets Streamlit."""
    if not firebase_admin._apps:
        try:
            # On récupère le dictionnaire depuis les secrets
            creds_dict = dict(st.secrets["firebase_service_account"])
            # Correction des sauts de ligne pour la clé privée
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation Firebase : {e}")
            return None, None

    db = firestore.client()
    # On retourne aussi la config firebase (contenant l'API Key) pour cockpit.py
    return db, st.secrets.get("firebase", {})

def load_profile(user_id):
    """Charge le profil utilisateur depuis Firestore ou crée un défaut."""
    if not user_id:
        return {}
        
    db, _ = init_firebase()
    if not db:
        return {}

    try:
        # Chemin strict selon la règle de stockage
        app_id = "cockpit-perf-v2"
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
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
    """Enregistre les modifications du profil dans Firestore."""
    if not user_id:
        return False
        
    db, _ = init_firebase()
    if not db:
        return False

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
    """Récupère les données de fitness depuis Intervals.icu ou génère de la démo."""
    if pd is None:
        return None

    if not icu_id or not icu_api:
        dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(60, -1, -1)]
        data = {
            "date": pd.to_datetime(dates),
            "icu_ctl": np.linspace(30, 55, 61) + np.random.normal(0, 1, 61),
            "icu_atl": np.linspace(35, 70, 61) + np.random.normal(0, 5, 61),
            "icu_tsb": np.random.uniform(-15, 5, 61)
        }
        return pd.DataFrame(data)
    
    # Logique réelle API Intervals.icu peut être ajoutée ici
    return None

def get_betrail_index(username):
    """Simule la récupération de l'index de performance BeTrail."""
    if not username:
        return 50.0
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
    """Calcule le temps estimé sur une course."""
    idx = float(betrail_index) if betrail_index else 50.0
    effort_km = float(km) + (float(d_plus) / 100.0)
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

# --- 4. INTELLIGENCE ARTIFICIELLE (GEMINI) ---

def get_ai_response(user_query, athlete_context, system_prompt=None):
    """
    Envoie une requête à l'API Gemini 2.5 Flash pour obtenir une analyse.
    """
    api_key = "" # Géré par le proxy de l'environnement
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    if system_prompt is None:
        system_prompt = "Tu es un coach expert en Trail Running. Analyse les données de l'athlète et réponds à sa question avec expertise technique (VMA, CTL, TSB)."

    # Construction du prompt final
    full_prompt = f"Contexte athlète : {str(athlete_context)}\n\nQuestion de l'athlète : {user_query}"
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }

    # Exponential Backoff pour la robustesse
    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Erreur de génération.")
            elif response.status_code == 429:
                time.sleep(2**i)
                continue
            else:
                return f"Erreur API ({response.status_code})"
        except Exception as e:
            time.sleep(2**i)
            if i == 4: return f"Erreur de connexion : {str(e)}"
    
    return "L'IA est momentanément indisponible."

# Alias pour compatibilité si nécessaire
def get_ia_coaching_feedback(df):
    """Analyse rapide pour le tableau de bord."""
    if df is None: return "Aucune donnée."
    status = get_training_status(df)
    return f"État actuel : {status['status']}. Votre CTL est de {status['ctl']}."
