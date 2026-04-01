import streamlit as st
import os
import sys
import pandas as pd
import time
from datetime import date
import requests

# --- 1. DEBUG INITIAL (Pour voir où ça bloque) ---
# Ces messages s'afficheront sur ton écran Streamlit
st.write("1. Imports système (os, sys, requests) OK")

# --- 2. CONFIGURATION DES CHEMINS ---
try:
    # On définit le chemin racine pour trouver les dossiers 'core' et 'tabs'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    st.write("2. Configuration des chemins système OK")
except Exception as e:
    st.error(f"Erreur de configuration des chemins : {e}")

# --- 3. IMPORTS DES MODULES LOCAUX ---
try:
    # On importe les fonctions depuis core/logic.py et core/data.py
    from core.logic import get_training_status, calculate_race_prediction, get_ai_response
    from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    
    # Imports des onglets et plans
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    
    st.write("3. Importation des modules locaux (core & tabs) OK")
except Exception as e:
    st.error(f"❌ Erreur d'importation des fichiers : {e}")
    st.info("Vérifiez que les fichiers existent dans /core/ et /tabs/")
    st.stop()

# --- 4. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Performance Cockpit", 
    page_icon="🏃‍♂️", 
    layout="wide"
)

# --- 5. INITIALISATION FIREBASE ---
try:
    # On initialise la base de données via data.py
    db = init_firebase() 
    # On récupère l'API Key pour la connexion login
    API_KEY = st.secrets["firebase_service_account"]["api_key"]
    st.write("4. Initialisation Firebase & API Key OK")
except Exception as e:
    st.error(f"Erreur de connexion Firebase : {e}")
    st.stop()

# --- 6. GESTION DE LA SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None

def verify_password(email, password):
    """Vérifie les identifiants via l'API REST Firebase."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

# --- ÉCRAN DE CONNEXION ---
if st.session_state.user is None:
    st.title("🏃‍♂️ Performance Cockpit - Connexion")
    
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Votre Email")
        pwd = st.text_input("Votre Mot de passe", type="password")
        
        if st.button("Se connecter", use_container_width=True):
            auth_data = verify_password(email, pwd)
            if auth_data:
                st.session_state.user = {
                    "email": email, 
                    "uid": auth_data['localId']
                }
                st.success("Connexion réussie !")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Identifiants incorrects. Veuillez réessayer.")
    st.stop()

# --- 7. CHARGEMENT DES DONNÉES UTILISATEUR ---
user_id = st.session_state.user['uid']
# On charge le profil depuis Firestore
user_profile = load_profile(user_id)

# Barre latérale de navigation
with st.sidebar:
    st.title("🏃‍♂️ Cockpit")
    st.write(f"Utilisateur : {st.session_state.user['email']}")
    st.divider()
    
    menu = st.radio(
        "Navigation", 
        ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "🍼 Nutrition", "🏆 Objectifs", "👤 Profil"]
    )
    
    st.divider()
    if st.button("🚪 Déconnexion"):
        st.session_state.user = None
        st.rerun()

# Récupération des données Intervals.icu
df_fitness = get_athlete_fitness(
    user_profile.get('intervals_id'), 
    user_profile.get('intervals_api')
)

# --- 8. RENDU DES ONGLETS (TABS) ---
try:
    if menu == "📊 Dashboard":
        dashboard.render(df_fitness, user_profile)
        
    elif menu == "📅 Entraînement":
        training.render(df_fitness)
        
    elif menu == "🏁 Plan de Course":
        race_plan.render(user_id, user_profile)
        
    elif menu == "🍼 Nutrition":
        nutrition_plan.render(user_profile)
        
    elif menu == "🏆 Objectifs":
        objectives_tab.render(user_id)
        
    elif menu == "👤 Profil":
        profile_tab.render(user_id, user_profile)

except Exception as e:
    st.error(f"Une erreur est survenue dans l'affichage de l'onglet {menu}")
    st.exception(e)
