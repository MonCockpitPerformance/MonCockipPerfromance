import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys
import requests

# --- 1. CONFIGURATION DES CHEMINS ---
# On s'assure que Python trouve les modules dans le dossier 'core'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- 2. IMPORTS DES MODULES LOCAUX ---
try:
    # Import des fonctions de calcul (Cerveau)
    from core.logic import get_training_status, calculate_race_prediction, get_ai_response
    
    # Import des fonctions de données (Magasinier)
    from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    
    # Imports des modules de tabs (Interface)
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    
except ImportError as e:
    st.error(f"❌ Erreur d'importation des modules : {e}")
    st.stop()

# --- 3. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Performance Cockpit v2.0",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style UI Custom pour un look sombre et pro
st.markdown("""
    <style>
        .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; }
        [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
        .metric-card { background: #1c2128; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- 4. INITIALISATION FIREBASE ---
try:
    # On initialise la connexion (via data.py)
    db = init_firebase() 
    # API KEY nécessaire pour l'authentification REST
    API_KEY = st.secrets["firebase_service_account"]["api_key"]
except Exception as e:
    st.error(f"Erreur de configuration Firebase : {e}")
    st.stop()

# --- 5. FONCTIONS D'AUTHENTIFICATION ---
def verify_password(email, password):
    """Vérifie les identifiants via l'API Google Firebase."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

# --- 6. GESTION DE LA SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None

# ÉCRAN DE CONNEXION (Si non connecté)
if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🏃‍♂️ Cockpit Performance</h1>", unsafe_allow_html=True)
        email = st.text_input("Email", key="login_email")
        pwd = st.text_input("Mot de passe", type="password", key="login_pwd")
        
        if st.button("Se connecter", use_container_width=True):
            auth_data = verify_password(email, pwd)
            if auth_data:
                st.session_state.user = {
                    "email": email, 
                    "uid": auth_data['localId']
                }
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    st.stop()

# --- 7. CHARGEMENT DES DONNÉES UTILISATEUR ---
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)

# Récupération des données Intervals.icu
@st.cache_data(ttl=600)
def fetch_fitness_data(uid, api_key):
    return get_athlete_fitness(uid, api_key)

df_fitness = fetch_fitness_data(
    user_profile.get('intervals_id'), 
    user_profile.get('intervals_api')
)

# --- 8. BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.title("Menu")
    st.write(f"Connecté : **{st.session_state.user['email']}**")
    
    menu = st.radio(
        "Navigation",
        ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "🍼 Nutrition", "🏆 Objectifs", "👤 Profil"]
    )
    
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- 9. RENDU DES ONGLETS ---
try:
    if menu == "📊 Dashboard":
        # On passe les données au dashboard pour affichage
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
    st.error(f"Erreur d'affichage dans l'onglet {menu}")
    st.exception(e)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption(f"v2.0.2 | {date.today().year} Performance Lab")
