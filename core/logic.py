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
    SECRET_KEY = "firebase_service_account"
    if not firebase_admin._apps:
        try:
            if SECRET_KEY not in st.secrets:
                return None, None
            
            fb_conf = st.secrets[SECRET_KEY]
            creds_dict = dict(fb_conf)
            
            # Nettoyage de la clé privée
            raw_key = creds_dict.get("private_key", "").strip()
            if raw_key.startswith('"') and raw_key.endswith('"'):
                raw_key = raw_key[1:-1]
            creds_dict["private_key"] = raw_key.replace("\\n", "\n")
            
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation Firebase : {e}")
            return None, None
    
    try:
        return firestore.client(), "cockpit-perf-v2"
    except:
        return None, None

def load_profile(user_id):
    """Charge le profil utilisateur depuis Firestore."""
    if not user_id:
        return {}
    db, app_id = init_firebase()
    if not db:
        return {}
    try:
        # Respect du chemin de collection strict
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        
        # Valeurs par défaut si le document n'existe pas
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
    db, app_id = init_firebase()
    if not db: return False
    try:
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc_ref.set(profile_data, merge=True)
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde profil : {e}")
        return False

# --- 2. RÉCUPÉRATION DES DONNÉES DE PERFORMANCE ---

def get_athlete_fitness(icu_id, icu_api):
    """Simule ou récupère les données fitness si les IDs sont absents."""
    if pd is None: return None
    # Si pas d'identifiants, on génère des données de simulation pour la démo
    if not icu_id or not icu_api:
        dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(60, -1, -1)]
        data = {
            "date": pd.to_datetime(dates),
            "icu_ctl": np.linspace(30, 55, 61) + np.random.normal(0, 1, 61),
            "icu_atl": np.linspace(35, 70, 61) + np.random.normal(0, 5, 61),
            "icu_tsb": np.random.uniform(-15, 5, 61)
        }
        return pd.DataFrame(data)
    
    # Note: La vraie récupération est gérée dans data.py via get_athlete_fitness
    # Cette fonction ici peut servir de fallback ou de wrapper
    return None

# --- 3. ALGORITHMES DE CALCUL ---

def get_training_status(fitness_df):
    """Analyse l'état de forme actuel basé sur les métriques ICU."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données non disponibles"}
    
    try:
        last_row = fitness_df.iloc[-1]
        ctl = float(last_row.get('icu_ctl', 0))
        tsb = float(last_row.get('icu_tsb', 0))
        
        if tsb < -25: status = "🚨 Risque de Surentraînement"
        elif tsb < -10: status = "🔥 Entraînement Intensif"
        elif tsb < 5: status = "📈 Phase Productive"
        elif tsb < 15: status = "✨ Affûtage / Frais"
        else: status = "💤 Désentraînement"
        
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except:
        return {"ctl": 0, "tsb": 0, "status": "Erreur de calcul"}

def calculate_race_prediction(km, d_plus, betrail_index):
    """Prédit le temps de course basé sur l'indice de performance."""
    idx = float(betrail_index or 50.0)
    effort_km = float(km) + (float(d_plus) / 100.0)
    # Formule simplifiée : un indice 50 correspond à environ 7.5 km-effort/h
    ref_speed = (idx / 50.0) * 7.5
    time_h = effort_km / ref_speed if ref_speed > 0 else 0
    
    return {
        "hours": time_h, 
        "effort_km": round(effort_km, 1), 
        "speed_kmh": round(float(km)/time_h, 2) if time_h > 0 else 0
    }

def calculate_pace_zones(betrail_index):
    """Définit les zones d'entraînement basées sur l'indice Betrail."""
    idx = float(betrail_index or 50.0)
    base_v = (idx / 50.0) * 8.5 # Vitesse de référence en km/h
    return {
        "Récupération": round(base_v * 0.70, 2),
        "Endurance Fondamentale": round(base_v * 0.82, 2),
        "Tempo / Seuil": round(base_v * 0.95, 2),
        "VMA Trail": round(base_v * 1.15, 2)
    }

def get_coaching_strategy(metrics):
    """Définit une stratégie visuelle selon le TSB."""
    tsb = metrics.get('tsb', 0)
    if tsb < -20: return {"color": "#ef4444", "advice": "Priorité absolue au repos et à la récupération."}
    if tsb < 0: return {"color": "#f59e0b", "advice": "Charge de travail importante, maintenez une bonne hygiène."}
    return {"color": "#10b981", "advice": "L'organisme est prêt pour des séances de haute intensité."}

# --- 4. FONCTION IA (GEMINI API) ---

def get_ai_response(user_query, athlete_context, system_prompt=None):
    """Appelle l'API Gemini avec gestion des erreurs et retries."""
    api_key = "" # Fourni par l'environnement au runtime
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    if not system_prompt:
        system_prompt = "Tu es un coach expert en Trail Running. Ton rôle est d'analyser les données de charge (CTL, ATL, TSB) et de donner des conseils précis, motivants et sécuritaires."

    payload = {
        "contents": [{"parts": [{"text": f"Données athlète: {athlete_context}\n\nQuestion de l'athlète: {user_query}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    # Exponential Backoff Strategy
    delays = [1, 2, 4, 8, 16]
    for i, delay in enumerate(delays):
        try:
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                result = res.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 429: # Too Many Requests
                time.sleep(delay)
                continue
            else:
                return f"Désolé, le service de coaching est temporairement indisponible (Code: {res.status_code})."
        except Exception:
            time.sleep(delay)
            if i == len(delays) - 1:
                return "Connexion au coach IA impossible. Vérifiez votre connexion."
    
    return "Le coach IA ne semble pas pouvoir répondre pour le moment."

def get_ia_coaching_feedback(df):
    """Wrapper simplifié pour un feedback rapide."""
    if df is None or (hasattr(df, 'empty') and df.empty): 
        return "Aucune donnée de performance disponible pour analyse."
    st_val = get_training_status(df)
    return f"Analyse actuelle : Votre statut est '{st_val['status']}'. Votre niveau de forme (CTL) est de {st_val['ctl']}."

def get_betrail_index(username):
    """Simule la récupération d'un indice Betrail."""
    return 64.2 if username else 50.0
