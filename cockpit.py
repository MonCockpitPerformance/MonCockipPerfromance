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
    from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
    
    # Importation des vues
    import tabs.dashboard as dashboard
    import tabs.training as training
    import tabs.profile_tab as profile_tab
    import tabs.objectives as objectives_tab
    
except ImportError as e:
    st.error(f"Erreur d'importation des modules : {e}")
    st.stop()

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Performance Cockpit v2.0",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INITIALISATION FIREBASE ---
try:
    db, auth = init_firebase()
except Exception as e:
    st.error(f"Erreur de connexion Firebase : {e}")
    st.stop()

# --- 3. GESTION DE LA SESSION UTILISATEUR ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. LOGIQUE D'AUTH ---
def handle_login(email, password):
    # Simulation (À remplacer par auth.verify_password ou autre selon votre setup)
    st.session_state.user = {"email": email, "uid": "user_id_test"} # Exemple ID stable pour tests
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

# Récupération sécurisée des identifiants API
# On vérifie les deux noms de clés possibles dans Firestore
i_id = user_profile.get('intervals_id', '').strip()
i_key = (user_profile.get('api_key') or user_profile.get('intervals_api', '')).strip()

df_fitness = pd.DataFrame()

if i_id and i_key:
    with st.spinner("Synchronisation avec Intervals.icu..."):
        df_fitness = get_athlete_fitness(i_id, i_key)
else:
    st.warning("⚠️ Identifiants Intervals.icu manquants dans le Profil.")

# --- 7. BARRE LATÉRALE ---
with st.sidebar:
    st.write(f"Connecté : **{st.session_state.user['email']}**")
    menu = st.radio("Navigation", ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "👤 Profil"])
    
    st.divider()
    if st.button("🚪 Déconnexion"):
        st.session_state.user = None
        st.rerun()

# --- 8. RENDU DES ONGLETS ---
if menu == "📊 Dashboard":
    if not df_fitness.empty:
        dashboard.render(df_fitness)
    else:
        st.info("Aucune donnée de fitness à afficher. Vérifiez votre clé API dans l'onglet Profil.")

elif menu == "📅 Entraînement":
    # On passe le DataFrame de fitness (contient CTL/ATL)
    training.render(df_fitness, []) 

elif menu == "🏁 Plan de Course":
    race_plan.render()

elif menu == "👤 Profil":
    # On passe l'ID pour permettre la sauvegarde dans profile_tab
    profile_tab.render(user_id)
