import streamlit as st
import requests
import base64
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, auth
import re
import json
import xml.etree.ElementTree as ET
import numpy as np

# --- INITIALISATION FIREBASE ---
def init_firebase():
    """Initialise Firebase Admin SDK avec les secrets Streamlit."""
    if not firebase_admin._apps:
        try:
            fb_conf = st.secrets["firebase"]
            # Nettoyage de la clé privée (gestion des guillemets et sauts de ligne)
            raw_key = fb_conf.get("private_key", "").strip()
            if raw_key.startswith('"') and raw_key.endswith('"'):
                raw_key = raw_key[1:-1]
            private_key = raw_key.replace("\\n", "\n")
            
            creds_dict = {
                "type": fb_conf["type"],
                "project_id": fb_conf["project_id"],
                "private_key_id": fb_conf["private_key_id"],
                "private_key": private_key,
                "client_email": fb_conf["client_email"],
                "client_id": fb_conf["client_id"],
                "auth_uri": fb_conf["auth_uri"],
                "token_uri": fb_conf["token_uri"],
                "auth_provider_x509_cert_url": fb_conf["auth_provider_x509_cert_url"],
                "client_x509_cert_url": fb_conf["client_x509_cert_url"]
            }
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation Firebase : {e}")
            return None, None
    return firestore.client(), auth

# --- GESTION DU PROFIL ---
def load_profile(user_id):
    """Charge le profil utilisateur depuis la collection 'profiles'."""
    db, _ = init_firebase()
    if not db: return {}
    
    doc_ref = db.collection("profiles").document(user_id)
    try:
        doc = doc_ref.get()
        if doc.exists:
            profile = doc.to_dict()
            # Assurer la présence des listes pour éviter les erreurs de rendu
            if "race_plan" not in profile: profile["race_plan"] = []
            if "checkpoints" not in profile: profile["checkpoints"] = []
            return profile
    except Exception as e:
        st.error(f"Erreur chargement profil : {e}")
    
    # Valeurs par défaut si nouveau compte ou erreur
    return {
        "intervals_id": "",
        "api_key": "",
        "betrail_index": 50.0,
        "weekly_sessions_target": 3,
        "race_plan": [],
        "checkpoints": []
    }

def save_user_profile(user_id, data):
    """Sauvegarde ou met à jour le profil utilisateur (merge=True)."""
    db, _ = init_firebase()
    if not db: return
    doc_ref = db.collection("profiles").document(user_id)
    try:
        doc_ref.set(data, merge=True)
    except Exception as e:
        st.error(f"Erreur sauvegarde profil : {e}")

# Alias pour compatibilité avec les anciens modules
save_profile = save_user_profile

# --- RÉCUPÉRATION INTERVALS.ICU ---
@st.cache_data(ttl=600)
def get_athlete_fitness(intervals_id, api_key):
    """Récupère les données Fitness (CTL/ATL/TSB) depuis Intervals.icu."""
    if not intervals_id or not api_key:
        return pd.DataFrame()

    url = f"https://intervals.icu/api/v1/athlete/{intervals_id}/activities?oldest=2026-01-01"
    
    auth_str = f"API_KEY:{api_key}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_auth}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            if not df.empty and 'start_date_local' in df.columns:
                df['date'] = pd.to_datetime(df['start_date_local'])
                for col in ['icu_ctl', 'icu_atl', 'icu_tsb']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                return df.sort_values('date')
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- TRAITEMENT GPX POUR PROFIL ALTIMÉTRIQUE ---
def parse_gpx_file(file):
    """Extrait la distance et l'élévation d'un fichier GPX."""
    try:
        file_content = file.read()
        root = ET.fromstring(file_content)
        ns_match = re.match(r'\{(.*)\}', root.tag)
        ns = {'gpx': ns_match.group(1)} if ns_match else {'gpx': 'http://www.topografix.com/GPX/1/1'}
        
        data = []
        total_dist = 0.0
        total_gain = 0.0
        total_loss = 0.0
        last_lat, last_lon, last_ele = None, None, None
        
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            ele_tag = trkpt.find('gpx:ele', ns)
            ele = float(ele_tag.text) if ele_tag is not None else 0
            
            if last_lat is not None:
                d = haversine(last_lat, last_lon, lat, lon)
                total_dist += d
                diff = ele - last_ele
                if diff > 0: total_gain += diff
                else: total_loss += abs(diff)
            
            data.append({"distance": round(total_dist, 3), "elevation": round(ele, 1)})
            last_lat, last_lon, last_ele = lat, lon, ele
        
        if not data: return pd.DataFrame()
        st.success(f"✅ GPX analysé : {total_dist:.2f}km | +{int(total_gain)}m")
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erreur GPX : {e}")
        return pd.DataFrame()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0-a))

# --- RÉCUPÉRATION NOLIO ---
def get_nolio_sessions(api_token, start_date, end_date):
    if not api_token: return []
    url = f"https://api.nolio.io/athelte/session/?start={start_date}&end={end_date}"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else []
    except Exception: return []

# --- PARSING BETRAIL ---
def parse_betrail_paste(raw_text):
    if not raw_text or len(str(raw_text).strip()) < 10: return []
    races = []
    lines = [l.strip() for l in str(raw_text).split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        if "/" in lines[i] or "CLOCK" in lines[i]:
            try:
                cursor = i + 1
                nom = lines[cursor]
                cursor += 1
                if lines[cursor].lower() in ['ultra', 'long', 'short', 'medium']: cursor += 1
                date_course = lines[cursor]
                cursor += 1
                distance, dplus = lines[cursor], lines[cursor+1]
                cursor += 4
                perf = lines[cursor]
                races.append({"Date": date_course, "Course": nom, "Détails": f"{distance} / {dplus}", "Perf": perf.replace(',', '.')})
                i = cursor + 1
            except: i += 1
        else: i += 1
    return races

# --- NOUVELLES FONCTIONS DE COACHING (POUR RÉPARER LE BUG) ---
def get_ia_coaching_feedback(df):
    """Génère un conseil basé sur les données Intervals.icu (Utilisé par dashboard.py)."""
    if df.empty:
        return "Connectez votre compte Intervals.icu dans l'onglet Profil pour recevoir votre analyse personnalisée."
    
    last_ctl = df['icu_ctl'].iloc[-1] if 'icu_ctl' in df.columns else 0
    last_tsb = df['icu_tsb'].iloc[-1] if 'icu_tsb' in df.columns else 0
    
    if last_tsb < -20:
        status = "Attention à la fatigue (TSB très bas)."
    elif last_tsb > 5:
        status = "Phase de fraîcheur, prêt pour un bloc intense ou une course."
    else:
        status = "Charge d'entraînement équilibrée."
        
    return f"Analyse Flash : Votre Fitness (CTL) est de {last_ctl:.0f}. {status}"

def get_coaching_strategy(df):
    """Définit la stratégie actuelle (Utilisé par dashboard.py)."""
    if df.empty:
        return "En attente de données..."
    return "Optimisation de l'endurance aérobie."
