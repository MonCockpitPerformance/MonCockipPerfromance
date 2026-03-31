import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys
import requests

# --- 1. CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- 2. IMPORTS DES MODULES LOCAUX ---
try:
    from core.logic import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    from firebase_admin import auth as admin_auth
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

# Style UI Custom
st.markdown("""
    <style>
        .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; }
        [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [aria-selected="true"] { border-bottom: 2px solid #FF4B4B !important; }
        .metric-card { background: #1c2128; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- 4. INITIALISATION FIREBASE ---
try:
    db, firebase_config = init_firebase() 
    # Récupération sécurisée de l'API KEY pour l'auth REST
    API_KEY = st.secrets["firebase"]["api_key"]
except Exception as e:
    st.error(f"Erreur de configuration Firebase : {e}")
    st.stop()

# --- 5. FONCTIONS D'AUTHENTIFICATION ---

def verify_password(email, password):
    """Vérifie les identifiants via l'API REST de Firebase."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def handle_login(email, password):
    if not email or not password:
        st.warning("Veuillez remplir tous les champs.")
        return False
        
    auth_data = verify_password(email, password)
    if auth_data:
        st.session_state.user = {
            "email": email, 
            "uid": auth_data['localId'],
            "token": auth_data['idToken']
        }
        return True
    else:
        st.error("Email ou mot de passe incorrect.")
        return False

def handle_signup(email, password):
    try:
        # 1. Création du compte dans Firebase Auth (Admin SDK)
        user = admin_auth.create_user(email=email, password=password)
        
        # 2. Initialisation du profil par défaut via la logique métier
        default_profile = {
            "email": email,
            "betrail_index": 50.0,
            "intervals_id": "",
            "intervals_api": "",
            "weight": 70,
            "race_plan": [],
            "created_at": time.time()
        }
        # Utilise la fonction de logic.py pour garantir le bon chemin Firestore
        save_user_profile(user.uid, default_profile)
        
        st.success("Compte créé avec succès !")
        return True
    except Exception as e:
        st.error(f"Erreur d'inscription : {str(e)}")
        return False

# --- 6. GESTION DE LA SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None

# ÉCRAN DE CONNEXION / INSCRIPTION
if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🏃‍♂️ Cockpit Performance</h1>", unsafe_allow_html=True)
        tab_l, tab_s = st.tabs(["Connexion", "Inscription"])
        
        with tab_l:
            email = st.text_input("Email", key="login_email")
            pwd = st.text_input("Mot de passe", type="password", key="login_pwd")
            if st.button("Se connecter", use_container_width=True):
                if handle_login(email, pwd): 
                    st.rerun()
        
        with tab_s:
            new_email = st.text_input("Email", key="reg_email")
            new_pwd = st.text_input("Mot de passe", type="password", key="reg_pwd")
            if st.button("Créer un compte", use_container_width=True):
                if len(new_pwd) >= 6: 
                    if handle_signup(new_email, new_pwd):
                        time.sleep(1)
                else: 
                    st.warning("Le mot de passe doit faire 6 caractères minimum.")
    st.stop()

# --- 7. CHARGEMENT DONNÉES & NAVIGATION ---
user_id = st.session_state.user['uid']
# On charge le profil depuis Firestore (via logic.py)
user_profile = load_profile(user_id)

@st.cache_data(ttl=600)
def fetch_fitness(uid, api_key):
    # Appel de la fonction dans logic.py
    return get_athlete_fitness(uid, api_key)

# Sidebar
with st.sidebar:
    st.title("Menu")
    st.write(f"Utilisateur : **{st.session_state.user['email']}**")
    menu = st.radio(
        "Navigation",
        ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "🍼 Nutrition", "🏆 Objectifs", "👤 Profil"]
    )
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# Données Fitness (Intervals.icu)
df_fitness = fetch_fitness(
    user_profile.get('intervals_id'), 
    user_profile.get('intervals_api')
)

# --- 8. RENDU DES ONGLETS ---
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
    st.error(f"Erreur d'affichage dans l'onglet {menu}")
    st.exception(e)

st.sidebar.markdown("---")
st.sidebar.caption(f"v2.0.2 | {date.today().year} Performance Lab")
