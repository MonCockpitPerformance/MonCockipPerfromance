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
from datetime import datetime

# --- UTILITAIRES DE SÉCURITÉ ---
def ensure_dataframe(df_input):
    """Garantit qu'on manipule toujours un DataFrame Pandas valide."""
    if df_input is None:
        return pd.DataFrame()
    if isinstance(df_input, pd.DataFrame):
        return df_input
    try:
        return pd.DataFrame(df_input)
    except:
        return pd.DataFrame()

# --- INITIALISATION FIREBASE ---
def init_firebase():
    """Initialise Firebase Admin SDK avec les secrets Streamlit."""
    if not firebase_admin._apps:
        try:
            if "firebase" not in st.secrets:
                return None, None
            
            fb_conf = st.secrets["firebase"]
            
            # Nettoyage de la clé privée
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
    try:
        return firestore.client(), auth
    except:
        return None, None

# --- GESTION DU PROFIL ---
def load_profile(user_id):
    """Charge le profil utilisateur depuis la collection 'profiles'."""
    db, _ = init_firebase()
    default_profile = {
        "intervals_id": "",
        "api_key": "",
        "betrail_index": 50.0,
        "weekly_sessions_target": 3,
        "race_plan": [],
        "checkpoints": [],
        "betrail_paste": "",
        "weight": 70.0
    }
    
    if not db: 
        return default_profile
    
    try:
        doc_ref = db.collection("profiles").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            profile = doc.to_dict()
            # Fusion avec les valeurs par défaut
            for key, val in default_profile.items():
                if key not in profile:
                    profile[key] = val
            return profile
    except Exception as e:
        st.warning(f"Note: Chargement du profil par défaut (Erreur: {e})")
    
    return default_profile

def save_user_profile(user_id, data):
    """Sauvegarde ou met à jour le profil utilisateur."""
    db, _ = init_firebase()
    if not db: return
    try:
        doc_ref = db.collection("profiles").document(user_id)
        doc_ref.set(data, merge=True)
    except Exception as e:
        st.error(f"Erreur sauvegarde profil : {e}")

save_profile = save_user_profile

# --- RÉCUPÉRATION INTERVALS.ICU ---
@st.cache_data(ttl=600)
def get_athlete_fitness(intervals_id, api_key):
    """Récupère les données Fitness depuis Intervals.icu."""
    if not intervals_id or not api_key:
        return pd.DataFrame()

    year = datetime.now().year
    url = f"https://intervals.icu/api/v1/athlete/{intervals_id}/activities?oldest={year}-01-01"
    
    auth_str = f"API_KEY:{api_key}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_auth}"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Normalisation des dates
                if 'start_date_local' in df.columns:
                    df['date'] = pd.to_datetime(df['start_date_local'])
                elif 'start_date' in df.columns:
                    df['date'] = pd.to_datetime(df['start_date'])
                
                # Conversion numérique forcée des métriques ICU
                metrics = ['icu_ctl', 'icu_atl', 'icu_tsb', 'icu_training_load']
                for m in metrics:
                    if m in df.columns:
                        df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0.0)
                    else:
                        df[m] = 0.0
                
                return df.sort_values('date')
    except Exception as e:
        st.error(f"Erreur Intervals.icu : {e}")
    
    return pd.DataFrame()

# --- TRAITEMENT GPX ---
def haversine(lat1, lon1, lat2, lon2):
    """Calcul de distance entre deux points GPS en km."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0-a))

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
        last_lat, last_lon, last_ele = None, None, None
        
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            ele_tag = trkpt.find('gpx:ele', ns)
            ele = float(ele_tag.text) if ele_tag is not None else 0.0
            
            if last_lat is not None:
                d = haversine(last_lat, last_lon, lat, lon)
                total_dist += d
                diff = ele - last_ele
                if diff > 0: total_gain += diff
            
            data.append({"distance": round(total_dist, 3), "elevation": round(ele, 1)})
            last_lat, last_lon, last_ele = lat, lon, ele
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erreur GPX : {e}")
        return pd.DataFrame()

# --- PARSING BETRAIL ---
def parse_betrail_paste(raw_text):
    """Analyse le copier-coller brut de BeTrail."""
    if not raw_text or len(str(raw_text).strip()) < 10:
        return []
    
    races = []
    lines = [l.strip() for l in str(raw_text).split('\n') if l.strip()]
    date_pattern = r"(\d{2}/\d{2}/\d{4})"
    
    i = 0
    while i < len(lines):
        match = re.search(date_pattern, lines[i])
        if match:
            try:
                date_course = match.group(1)
                nom_course = lines[i-1] if i > 0 else "Course"
                
                perf = 0.0
                # On cherche la performance sur les lignes suivantes
                for j in range(i, min(i+10, len(lines))):
                    cleaned_val = lines[j].replace('%', '').replace(',', '.').strip()
                    try:
                        val = float(cleaned_val)
                        if 30 < val < 110: # Range logique de performance BeTrail
                            perf = val
                            break
                    except:
                        continue
                
                races.append({
                    "date": date_course,
                    "nom": nom_course,
                    "performance": perf,
                    "resultat": "Finisher"
                })
                i += 3 
            except:
                i += 1
        else:
            i += 1
            
    return races
