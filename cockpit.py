import streamlit as st
import pandas as pd
import time
from datetime import date
import os
import sys
from firebase_admin import auth as admin_auth

# --- FIX DES CHEMINS POUR LE CLOUD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importations des modules internes
try:
    # On importe uniquement ce qui existe réellement dans core/data.py
    from core.data import init_firebase, load_profile, get_athlete_fitness, save_user_profile
    import core.race_plan as race_plan
    import core.nutrition_plan as nutrition_plan
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
db, _ = init_firebase()

# --- 3. GESTION DE LA SESSION UTILISATEUR ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. FONCTIONS D'AUTHENTIFICATION ---
def handle_login(email, password):
    try:
        user = admin_auth.get_user_by_email(email)
        st.session_state.user = {"email": email, "uid": user.uid}
        return True
    except Exception as e:
        st.error(f"Identifiants invalides ou erreur : {str(e)}")
        return False

def handle_signup(email, password):
    try:
        user = admin_auth.create_user(email=email, password=password)
        save_user_profile(user.uid, {
            "email": email,
            "created_at": time.time(),
            "intervals_id": "",
            "intervals_api": ""
        })
        st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
        return True
    except Exception as e:
        st.error(f"Erreur lors de la création du compte : {str(e)}")
        return False

def handle_reset_password(email):
    try:
        link = admin_auth.generate_password_reset_link(email)
        st.info(f"Procédure de réinitialisation activée pour {email}.")
        st.warning("Veuillez contacter l'administrateur pour recevoir votre lien.")
    except Exception as e:
        st.error(f"Utilisateur introuvable : {str(e)}")

# --- 5. ÉCRAN D'AUTHENTIFICATION ---
if st.session_state.user is None:
    st.title("🔐 Connexion au Cockpit")
    
    tab_login, tab_signup, tab_reset = st.tabs(["Se connecter", "Créer un compte", "Accès perdu"])
    
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("🚀 Entrer dans le Cockpit", use_container_width=True):
            if email and password:
                if handle_login(email, password):
                    st.rerun()
    
    with tab_signup:
        new_email = st.text_input("Nouvel Email", key="reg_email")
        new_password = st.text_input("Définir un mot de passe (6 car. min)", type="password", key="reg_password")
        if st.button("Créer mon espace athlète", use_container_width=True):
            if new_email and len(new_password) >= 6:
                handle_signup(new_email, new_password)
                
    with tab_reset:
        reset_email = st.text_input("Email du compte", key="reset_email")
        if st.button("Lancer la récupération", use_container_width=True):
            if reset_email:
                handle_reset_password(reset_email)

    st.stop()

# --- 6. CHARGEMENT DES DONNÉES ---
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)

# Synchronisation automatique Intervals.icu
with st.spinner("Synchronisation des données de forme..."):
    # On récupère les données de fitness (le dataframe df)
    df = get_athlete_fitness(
        user_profile.get('intervals_id'), 
        user_profile.get('intervals_api') or user_profile.get('api_key')
    )

# --- 7. BARRE LATÉRALE ET NAVIGATION ---
with st.sidebar:
    st.write(f"Athlète : **{st.session_state.user['email']}**")
    st.divider()
    menu = st.radio(
        "Navigation", 
        ["📊 Dashboard", "📅 Entraînement", "🏁 Plan de Course", "🍼 Nutrition", "🏆 Objectifs", "👤 Profil"]
    )
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- 8. RENDU DES ONGLETS ---
try:
    if menu == "📊 Dashboard":
        dashboard.render(df)
    elif menu == "📅 Entraînement":
        # On passe le dataframe df. Si tu as besoin de sessions spécifiques, 
        # elles devraient être gérées à l'intérieur du module training via core.logic
        training.render(df, [])
    elif menu == "🏁 Plan de Course":
        race_plan.render()
    elif menu == "🍼 Nutrition":
        nutrition_plan.render()
    elif menu == "🏆 Objectifs":
        try:
            objectives_tab.render(user_id)
        except TypeError:
            objectives_tab.render()
    elif menu == "👤 Profil":
        try:
            profile_tab.render(user_id)
        except TypeError:
            profile_tab.render()
except Exception as e:
    st.error(f"Une erreur est survenue lors du rendu de l'onglet {menu} : {e}")
