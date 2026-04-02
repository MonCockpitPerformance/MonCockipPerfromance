import streamlit as st
import requests
import base64
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, auth
import re
import xml.etree.ElementTree as ET
import numpy as np
from datetime import datetime

# --- INITIALISATION FIREBASE ---
def init_firebase():
    """Initialise Firebase avec les secrets Streamlit Cloud."""
    if not firebase_admin._apps:
        try:
            # On cherche la section [firebase] dans tes secrets
            fb_conf = st.secrets["firebase"]
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
    """Charge le profil depuis Firestore."""
    db, _ = init_firebase()
    if not db: return {}
    doc_ref = db.collection("profiles").document(user_id)
    try:
        doc = doc_ref.get()
        if doc.exists:
            profile = doc.to_dict()
            if "race_plan" not in profile: profile["race_plan"] = []
            if "checkpoints" not in profile: profile["checkpoints"] = []
            return profile
    except:
        pass
    return {"intervals_id": "", "api_key": "", "betrail_index": 50.0, "race_plan": [], "checkpoints": []}

def save_user_profile(user_id, data):
    """Sauvegarde le profil (merge)."""
    db, _ = init_firebase()
    if db and user_id:
        db.collection("profiles").document(user_id).set(data, merge=True)

save_profile = save_user_profile

# --- RÉCUPÉRATION INTERVALS.ICU ---
@st.cache_data(ttl=600)
def get_athlete_fitness(intervals_id, api_key):
    if not intervals_id or not api_key:
        return pd.DataFrame()
    url = f"https://intervals.icu/api/v1/athlete/{intervals_id}/activities?oldest=2026-01-01"
    auth_str = base64.b64encode(f"API_KEY:{api_key}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_str}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty and 'start_date_local' in df.columns:
                df['date'] = pd.to_datetime(df['start_date_local'])
                for col in ['icu_ctl', 'icu_atl', 'icu_tsb']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                return df.sort_values('date')
    except:
        pass
    return pd.DataFrame()

# --- TA LOGIQUE GPX D'ORIGINE ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0-a))

def parse_gpx_file(file):
    try:
        file_content = file.read()
        root = ET.fromstring(file_content)
        ns_match = re.match(r'\{(.*)\}', root.tag)
        ns = {'gpx': ns_match.group(1)} if ns_match else {'gpx': 'http://www.topografix.com/GPX/1/1'}
        data, total_dist, total_gain, last_lat, last_lon, last_ele = [], 0.0, 0.0, None, None, None
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat, lon = float(trkpt.get('lat')), float(trkpt.get('lon'))
            ele_tag = trkpt.find('gpx:ele', ns)
            ele = float(ele_tag.text) if ele_tag is not None else 0
            if last_lat is not None:
                total_dist += haversine(last_lat, last_lon, lat, lon)
                diff = ele - last_ele
                if diff > 0: total_gain += diff
            data.append({"distance": round(total_dist, 3), "elevation": round(ele, 1)})
            last_lat, last_lon, last_ele = lat, lon, ele
        st.success("✅ GPX analysé avec succès !")
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erreur GPX : {e}")
        return pd.DataFrame()

# --- TA LOGIQUE BETRAIL D'ORIGINE ---
def parse_betrail_paste(raw_text):
    if not raw_text: return []
    races = []
    lines = [l.strip() for l in str(raw_text).split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        if "/" in lines[i] or "CLOCK" in lines[i]:
            try:
                races.append({
                    "Date": lines[i+3], 
                    "Course": lines[i+1], 
                    "Détails": f"{lines[i+4]} / {lines[i+5]}", 
                    "Rang": lines[i], 
                    "Perf": lines[i+7].replace(',', '.')
                })
                i += 8
            except: i += 1
        else: i += 1
    return races
