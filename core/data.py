import streamlit as st
import pandas as pd
import requests
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime

# Identifiant pour le chemin Firestore
APP_ID = "cockpit-perf-v2"

def init_firebase():
    """Initialise Firebase avec les secrets Streamlit."""
    if not firebase_admin._apps:
        try:
            fb_conf = st.secrets["firebase_service_account"]
            creds_dict = dict(fb_conf)
            # Nettoyage de la clé privée pour éviter les erreurs de format
            raw_key = creds_dict.get("private_key", "").strip()
            if raw_key.startswith('"') and raw_key.endswith('"'):
                raw_key = raw_key[1:-1]
            creds_dict["private_key"] = raw_key.replace("\\n", "\n")
            
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation Firebase : {e}")
    return firestore.client()

def load_profile(user_id):
    """Charge le profil utilisateur depuis Firestore."""
    db = init_firebase()
    default_profile = {
        "intervals_id": "",
        "intervals_api": "",
        "betrail_index": 50.0,
        "race_plan": []
    }
    if not user_id:
        return default_profile
    try:
        doc_ref = db.collection("artifacts").document(APP_ID).collection("users").document(user_id).collection("profile").document("settings")
        doc = doc_ref.get()
        if doc.exists:
            return {**default_profile, **doc.to_dict()}
    except Exception:
        pass
    return default_profile

def save_user_profile(user_id, data):
    """Sauvegarde le profil utilisateur dans Firestore."""
    if not user_id:
        return
    db = init_firebase()
    try:
        doc_ref = db.collection("artifacts").document(APP_ID).collection("users").document(user_id).collection("profile").document("settings")
        doc_ref.set(data, merge=True)
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

# ALIAS pour éviter toute erreur d'importation si tu appelles l'un ou l'autre
save_profile = save_user_profile

def get_athlete_fitness(intervals_id, intervals_api):
    """Récupère les données depuis Intervals.icu."""
    if not intervals_id or not intervals_api:
        return pd.DataFrame()

    url = f"https://intervals.icu/api/v1/athlete/{intervals_id}/activities?oldest={datetime.now().year}-01-01"
    auth_str = base64.b64encode(f"API_KEY:{intervals_api}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_str}"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            # On s'assure que les colonnes numériques sont bien typées
            for col in ['icu_ctl', 'icu_atl', 'icu_tsb']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            return df
    except Exception:
        pass
    return pd.DataFrame()
