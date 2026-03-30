import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys

# --- CONFIGURATION DES CHEMINS ---
# S'assure que le dossier racine est dans le path pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- MODIFICATION DES IMPORTS DANS COCKPIT.PY ---
try:
    # On remplace 'core.data' par 'core.logic'
    from core.logic import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    from firebase_admin import auth as admin_auth
except ImportError as e:
    st.error(f"❌ Erreur d'importation des modules critiques : {e}")
    st.info("Assurez-vous que le fichier s'appelle bien 'logic.py' dans le dossier 'core'.")
    st.stop()

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Performance Cockpit v2.0",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style Global pour masquer les menus Streamlit inutiles et améliorer l'UI
st.markdown("""
    <style>
        .reportview-container { background: #0e1117; }
        [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
        .stButton>button { border-radius: 8px; font-weight: 600; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #161b22; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #888;
        }
        .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALISATION FIREBASE ---
try:
    db, _ = init_firebase()
except Exception as e:
    st.error(f"Erreur d'initialisation Firebase : {e}")
    st.stop()

# --- 3. GESTION DE LA SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. FONCTIONS D'AUTHENTIFICATION ---
def handle_login(email, password):
    try:
        # Note: Dans une app réelle, on utiliserait Firebase Client SDK pour vérifier le password.
        # Ici on utilise Admin SDK pour récupérer l'UID via l'email.
        user = admin_auth.get_user_by_email(email)
        st.session_state.user = {"email": email, "uid": user.uid}
        return True
    except Exception as e:
        st.error("Identifiants incorrects ou utilisateur inexistant.")
        return False

def handle_signup(email, password):
    try:
        user = admin_auth.create_user(email=email, password=password)
        # Création du profil initial
        default_profile = {
            "email": email,
            "created_at": time.time(),
            "intervals_id": "",
            "intervals_api": "",
            "nolio_token": "",
            "next_race_name": "Ma première course",
            "weight": 70,
            "height": 175
        }
        save_user_profile(user.uid, default_profile)
        st.success("Compte créé ! Connectez-vous maintenant.")
        return True
    except Exception as e:
        st.error(f"Erreur de création : {str(e)}")
        return False

# --- 5. ÉCRAN D'ACCÈS ---
if st.session_state.user is None:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.image("https://em-content.zobj.net/source/apple/354/running-shoe_1f45f.png", width=80)
        st.title("Cockpit Performance")
        st.caption("Accédez à votre analyse d'entraînement augmentée par l'IA.")
        
        tab_login, tab_signup = st.tabs(["Se connecter", "Nouveau compte"])
        
        with tab_login:
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            if st.button("🚀 Entrer", use_container_width=True):
                if email and password:
                    if handle_login(email, password):
                        st.rerun()
        
        with tab_signup:
            new_email = st.text_input("Email", key="s_email")
            new_pass = st.text_input("Mot de passe (6+)", type="password", key="s_pass")
            if st.button("Créer mon profil", use_container_width=True):
                if len(new_pass) >= 6:
                    handle_signup(new_email, new_pass)
    st.stop()

# --- 6. CHARGEMENT DES DONNÉES ATHLÈTE ---
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)

@st.cache_data(ttl=600) # Cache de 10 minutes pour éviter de saturer l'API
def fetch_fitness_data(uid, api_key):
    if not uid or not api_key:
        return None
    return get_athlete_fitness(uid, api_key)

with st.sidebar:
    st.markdown(f"### 🏃‍♂️ {st.session_state.user['email']}")
    st.divider()
    menu = st.radio(
        "Navigation Principal", 
        ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "🍼 Nutrition", "🏆 Objectifs", "👤 Profil"],
        index=0
    )
    st.divider()
    
    # Indicateur de statut de synchronisation
    has_intervals = bool(user_profile.get('intervals_id') and (user_profile.get('intervals_api') or user_profile.get('api_key')))
    if has_intervals:
        st.success("✅ Intervals.icu connecté")
    else:
        st.warning("⚠️ Intervals.icu déconnecté")
        
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# Récupération des données Fitness
df_fitness = fetch_fitness_data(
    user_profile.get('intervals_id'), 
    user_profile.get('intervals_api') or user_profile.get('api_key')
)

# --- 7. RENDU DES PAGES ---
try:
    if menu == "📊 Dashboard":
        dashboard.render(df_fitness)
        
    elif menu == "📅 Entraînement":
        # On passe le dataframe de fitness pour que l'onglet puisse calculer CTL/ATL
        training.render(df_fitness)
        
    elif menu == "🏁 Plan de Course":
        race_plan.render()
        
    elif menu == "🍼 Nutrition":
        nutrition_plan.render()
        
    elif menu == "🏆 Objectifs":
        objectives_tab.render()
        
    elif menu == "👤 Profil":
        profile_tab.render()
        
except Exception as e:
    st.error(f"⚠️ Erreur d'affichage dans '{menu}'")
    st.exception(e) # Affiche le détail de l'erreur pour le debug

# --- 8. FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption(f"v2.0.1 | {date.today().year} Performance Lab")
