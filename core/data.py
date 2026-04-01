import streamlit as st
import pandas as pd
import requests
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime

APP_ID = "cockpit-perf-v2"

def init_firebase():
    """Initialise Firebase Admin SDK."""
    if not firebase_admin._apps:
        try:
            fb_conf = st.secrets["firebase_service_account"]
            creds_dict = dict(fb_conf)
            raw_key = creds_dict.get("private_key", "").strip()
            if raw_key.startswith('"'): raw_key = raw_key[1:-1]
            creds_dict["private_key"] = raw_key.replace("\\n", "\n")
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Firebase Init Error: {e}")
    return firestore.client(), auth

def load_profile(user_id):
    """Charge le profil utilisateur via le chemin strict."""
    db, _ = init_firebase()
    default = {"betrail_index": 50.0, "intervals_id": "", "intervals_api": "", "race_plan": []}
    if not user_id or not db: return default
    try:
        doc = db.collection("artifacts").document(APP_ID).collection("users").document(user_id).collection("profile").document("settings").get()
        return {**default, **doc.to_dict()} if doc.exists else default
    except: return default

def save_user_profile(user_id, data):
    """Sauvegarde le profil."""
    db, _ = init_firebase()
    if user_id and db:
        db.collection("artifacts").document(APP_ID).collection("users").document(user_id).collection("profile").document("settings").set(data, merge=True)

def get_athlete_fitness(intervals_id, intervals_api):
    """Récupère les données Intervals.icu."""
    if not intervals_id or not intervals_api: return pd.DataFrame()
    url = f"https://intervals.icu/api/v1/athlete/{intervals_id}/activities?oldest={datetime.now().year}-01-01"
    auth_str = base64.b64encode(f"API_KEY:{intervals_api}".encode()).decode()
    try:
        res = requests.get(url, headers={"Authorization": f"Basic {auth_str}"}, timeout=15)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            for m in ['icu_ctl', 'icu_atl', 'icu_tsb']:
                if m in df.columns: df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0.0)
            return df
    except: pass
    return pd.DataFrame()
