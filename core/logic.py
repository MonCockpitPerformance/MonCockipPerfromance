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
            
            # Nettoyage et formatage de la clé privée
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
        # L'ID de l'application pour le chemin Firestore
        app_id = "cockpit-perf-v2"
        return firestore.client(), app_id
    except:
        return None, None

def load_profile(user_id):
    """Charge le profil utilisateur depuis Firestore avec le chemin strict requis."""
    if not user_id:
        return {}
    db, app_id = init_firebase()
    if not db:
        return {}
    try:
        # RÈGLE : /artifacts/{appId}/users/{userId}/{collectionName}
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
        return {"error": str(e)}

def save_user_profile(user_id, profile_data):
    """Enregistre les modifications du profil."""
    if not user_id: return False
    db, app_id = init_firebase()
    if not db: return False
    try:
        doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("profile").document("settings")
        doc_ref.set(profile_data, merge=True)
        return True
    except Exception:
        return False

# --- 2. ALGORITHMES DE CALCUL ---

def get_training_status(fitness_df):
    """Analyse l'état de forme actuel."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données non disponibles"}
    
    try:
        last_row = fitness_df.iloc[-1]
        ctl = float(last_row.get('icu_ctl', 0))
        tsb = float(last_row.get('icu_tsb', 0))
        
        if tsb < -25: status = "🚨 Risque de Fatigue"
        elif tsb < -10: status = "🔥 Entraînement Intensif"
        elif tsb < 5: status = "📈 Phase Productive"
        elif tsb < 15: status = "✨ Affûtage / Frais"
        else: status = "💤 Désentraînement"
        
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except:
        return {"ctl": 0, "tsb": 0, "status": "Erreur de calcul"}

def calculate_race_prediction(km, d_plus, betrail_index):
    """Prédit le temps de course."""
    idx = float(betrail_index or 50.0)
    effort_km = float(km) + (float(d_plus) / 100.0)
    ref_speed = (idx / 50.0) * 7.5
    time_h = effort_km / ref_speed if ref_speed > 0 else 0
    return {
        "hours": time_h, 
        "effort_km": round(effort_km, 1), 
        "speed_kmh": round(float(km)/time_h, 2) if time_h > 0 else 0
    }

# --- 3. FONCTION IA (GEMINI API) ---

def get_ai_response(user_query, athlete_context, system_prompt=None):
    """
    Appelle l'API Gemini. 
    IMPORTANT: La clé API doit rester vide (""), l'environnement l'injecte.
    """
    api_key = "" 
    model_name = "gemini-2.5-flash-preview-09-2025"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    if not system_prompt:
        system_prompt = "Tu es un coach expert en Trail Running. Analyse les données de l'athlète et réponds à ses questions avec précision et empathie."

    payload = {
        "contents": [{"parts": [{"text": f"Contexte de l'athlète: {athlete_context}\nQuestion: {user_query}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    # Stratégie de retry (Exponential Backoff) : 1s, 2s, 4s, 8s, 16s
    delays = [1, 2, 4, 8, 16]
    for delay in delays:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429: # Rate limit
                time.sleep(delay)
                continue
            else:
                return f"Le coach n'est pas disponible (Erreur {response.status_code})."
        except Exception:
            time.sleep(delay)
            
    return "L'IA de coaching ne répond pas. Vérifiez votre connexion."

def get_ia_coaching_feedback(df):
    """Feedback rapide pour l'affichage."""
    if df is None: return "En attente de données..."
    status = get_training_status(df)
    return f"{status['status']} (Charge actuelle: {status['ctl']})"
