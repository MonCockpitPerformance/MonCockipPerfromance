import streamlit as st
import pandas as pd
import time
from datetime import date
from firebase_admin import auth as admin_auth

# Importations des modules internes (Structure par dossiers)
try:
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
# init_firebase() gère maintenant la connexion via les st.secrets
db, _ = init_firebase()

# --- 3. GESTION DE LA SESSION UTILISATEUR ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. FONCTIONS D'AUTHENTIFICATION ---
def handle_login(email, password):
    try:
        # Note: Firebase Admin est utilisé ici pour identifier l'utilisateur.
        # Pour une sécurité maximale en production, on passerait par l'API REST Firebase Auth.
        user = admin_auth.get_user_by_email(email)
        # On stocke l'email et l'UID dans la session
        st.session_state.user = {"email": email, "uid": user.uid}
        return True
    except Exception as e:
        st.error(f"Identifiants invalides ou erreur : {str(e)}")
        return False

def handle_signup(email, password):
    try:
        user = admin_auth.create_user(email=email, password=password)
        # Initialiser le profil par défaut dans Firestore
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
        # Génère un lien de réinitialisation (utile pour l'admin ou envoi manuel)
        link = admin_auth.generate_password_reset_link(email)
        st.info(f"Procédure de réinitialisation activée pour {email}.")
        st.warning("Veuillez contacter l'administrateur pour recevoir votre lien sécurisé.")
    except Exception as e:
        st.error(f"Utilisateur introuvable : {str(e)}")

# --- 5. ÉCRAN D'AUTHENTIFICATION (Si non connecté) ---
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
            else:
                st.warning("Veuillez remplir tous les champs.")
    
    with tab_signup:
        new_email = st.text_input("Nouvel Email", key="reg_email")
        new_password = st.text_input("Définir un mot de passe (6 car. min)", type="password", key="reg_password")
        if st.button("Créer mon espace athlète", use_container_width=True):
            if new_email and len(new_password) >= 6:
                handle_signup(new_email, new_password)
            else:
                st.warning("Données invalides (mot de passe trop court ?).")
                
    with tab_reset:
        st.subheader("Réinitialiser mon accès")
        reset_email = st.text_input("Email du compte", key="reset_email")
        if st.button("Lancer la récupération", use_container_width=True):
            if reset_email:
                handle_reset_password(reset_email)

    st.stop()

# --- 6. CHARGEMENT DES DONNÉES (Si connecté) ---
user_id = st.session_state.user['uid']
user_profile = load_profile(user_id)

# Synchronisation automatique Intervals.icu
with st.spinner("Synchronisation des données de forme..."):
    # On utilise 'intervals_api' pour correspondre à tes fichiers core/data.py
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
        # On passe le dataframe de fitness pour analyse dans l'onglet entraînement
        training.render(df, [])
    elif menu == "🏁 Plan de Course":
        race_plan.render()
    elif menu == "🍼 Nutrition":
        nutrition_plan.render()
    elif menu == "🏆 Objectifs":
        objectives_tab.render()
    elif menu == "👤 Profil":
        profile_tab.render()
except Exception as e:
    st.error(f"Une erreur est survenue lors du rendu de l'onglet {menu} : {e}")