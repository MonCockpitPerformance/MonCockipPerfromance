import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys

# --- FIX DES CHEMINS POUR LE CLOUD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importations des modules internes
try:
    # On importe uniquement les fonctions existantes dans ton core/data.py
    from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    
    # On importe les autres modules de logique
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    
    # On importe les vues (onglets)
    # Note : Vérifie que ces fichiers existent bien dans ton dossier /tabs
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    
except ImportError as e:
    st.error(f"Erreur d'importation des modules : {e}")
    st.info("Astuce : Vérifiez que 'get_nolio_sessions' n'est plus appelé dans vos fichiers de l'onglet 'tabs/'.")
    st.stop()

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Performance Cockpit v2.0",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INITIALISATION FIREBASE ---
# On essaie d'initialiser, sinon on affiche une erreur propre
try:
    db, auth = init_firebase()
except Exception as e:
    st.error(f"Erreur de connexion Firebase : {e}")
    st.stop()

# --- 3. GESTION DE LA SESSION UTILISATEUR ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. LOGIQUE D'AUTH SIMPLIFIÉE ---
# (À adapter selon ton système Firebase Auth réel)
def handle_login(email, password):
    # Simulation ou appel Firebase Admin si configuré
    st.session_state.user = {"email": email, "uid": "user_id_placeholder"}
    return True

# --- 5. ÉCRAN D'AUTHENTIFICATION ---
if st.session_state.user is None:
    st.title("🔐 Connexion au Cockpit")
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    if st.button("🚀 Entrer dans le Cockpit"):
        if handle_login(email, password):
            st.rerun()
    st.stop()

# --- 6. CHARGEMENT DES DONNÉES ---
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)

# Récupération des données Intervals.icu
with st.spinner("Synchronisation des données Intervals.icu..."):
    df = get_athlete_fitness(
        user_profile.get('intervals_id'), 
        user_profile.get('intervals_api') or user_profile.get('api_key')
    )

# --- 7. BARRE LATÉRALE ---
with st.sidebar:
    st.write(f"Connecté : **{st.session_state.user['email']}**")
    menu = st.radio("Navigation", ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "👤 Profil"])
    if st.button("🚪 Déconnexion"):
        st.session_state.user = None
        st.rerun()

# --- 8. RENDU DES ONGLETS ---
if menu == "📊 Dashboard":
    dashboard.render(df)
elif menu == "📅 Entraînement":
    # On passe le DataFrame et une liste vide pour les sessions si Nolio est désactivé
    training.render(df, []) 
elif menu == "🏁 Plan de Course":
    race_plan.render()
elif menu == "👤 Profil":
    profile_tab.render(user_id)
