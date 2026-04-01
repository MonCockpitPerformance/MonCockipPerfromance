import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys
import requests

# Configuration chemins
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports corrigés
from core.logic import get_training_status, calculate_race_prediction, get_ai_response
from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile

# Configuration Page
st.set_page_config(page_title="Performance Cockpit", page_icon="🏃‍♂️", layout="wide")

# Initialisation Firebase & Auth
db, fb_auth = init_firebase()
API_KEY = st.secrets["firebase_service_account"]["api_key"]

def verify_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    return res.json() if res.status_code == 200 else None

if "user" not in st.session_state: st.session_state.user = None

# Écran de Connexion
if st.session_state.user is None:
    st.title("🏃‍♂️ Cockpit Performance")
    email = st.text_input("Email")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        data = verify_password(email, pwd)
        if data:
            st.session_state.user = {"email": email, "uid": data['localId']}
            st.rerun()
    st.stop()

# Chargement données
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)
df_fitness = get_athlete_fitness(user_profile.get('intervals_id'), user_profile.get('intervals_api'))

# Interface principale
st.sidebar.title("Menu")
menu = st.sidebar.radio("Navigation", ["📊 Dashboard", "👤 Profil"])

if menu == "📊 Dashboard":
    st.header("Tableau de bord")
    status = get_training_status(df_fitness)
    st.metric("Condition (CTL)", status['ctl'])
    st.write(f"Statut : {status['status']}")

elif menu == "👤 Profil":
    st.header("Mon Profil")
    new_idx = st.number_input("Index Betrail", value=user_profile.get('betrail_index', 50.0))
    if st.button("Sauvegarder"):
        user_profile['betrail_index'] = new_idx
        save_user_profile(user_id, user_profile)
        st.success("Profil mis à jour !")
