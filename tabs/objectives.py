import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys

# --- CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.data import init_firebase

def load_objectives(user_id):
    """Charge la liste des objectifs depuis Firestore."""
    db, _ = init_firebase()
    app_id = st.session_state.get('app_id', 'default-app-id')
    
    # Chemin conforme aux règles de sécurité
    doc_ref = db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("objectives")
    
    try:
        docs = doc_ref.stream()
        objs = []
        for d in docs:
            data = d.to_dict()
            data['id'] = d.id
            objs.append(data)
        # Tri par date (les plus proches en premier)
        return sorted(objs, key=lambda x: x.get('date', '9999-12-31'))
    except Exception as e:
        st.error(f"Erreur lors du chargement des objectifs : {e}")
        return []

def save_objective(user_id, obj_data):
    """Enregistre un nouvel objectif dans Firestore."""
    db, _ = init_firebase()
    app_id = st.session_state.get('app_id', 'default-app-id')
    db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("objectives").add(obj_data)

def delete_objective(user_id, obj_id):
    """Supprime un objectif spécifique."""
    db, _ = init_firebase()
    app_id = st.session_state.get('app_id', 'default-app-id')
    db.collection("artifacts").document(app_id).collection("users").document(user_id).collection("objectives").document(obj_id).delete()

def render(user_id):
    st.header("🏆 Mes Objectifs & Courses")
    
    if not user_id or user_id == "athlete_default":
        st.warning("⚠️ Connectez-vous ou configurez votre profil pour sauvegarder vos objectifs.")

    # --- FORMULAIRE D'AJOUT ---
    with st.expander("➕ Ajouter un nouvel objectif", expanded=False):
        with st.form("add_objective_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nom de la course", placeholder="Ex: UTMB, Marathon de Paris...")
                type_course = st.selectbox("Type", ["Trail", "Route", "Cyclisme", "Triathlon", "Autre"])
                date_course = st.date_input("Date de l'événement", min_value=datetime.now())
            
            with col2:
                dist = st.number_input("Distance (km)", min_value=1, step=1)
                dplus = st.number_input("Dénivelé (m D+)", min_value=0, step=100)
                priority = st.select_slider(
                    "Priorité", 
                    options=[1, 2, 3], 
                    format_func=lambda x: {1: "⭐ A (Majeur)", 2: "⭐⭐ B (Intermédiaire)", 3: "⭐⭐⭐ C (Prépa)"}[x],
                    help="A: Objectif principal de l'année. C: Course d'entraînement."
                )

            submitted = st.form_submit_button("Ajouter l'objectif", use_container_width=True)
            if submitted and name:
                new_obj = {
                    "name": name,
                    "type": type_course,
                    "date": date_course.isoformat(),
                    "km": dist,
                    "dplus": dplus,
                    "priority": priority,
                    "created_at": datetime.now().isoformat()
                }
                save_objective(user_id, new_obj)
                st.success(f"Objectif '{name}' ajouté avec succès !")
                st.rerun()

    # --- LISTE DES OBJECTIFS ---
    st.subheader("🗓️ Calendrier de la saison")
    objs = load_objectives(user_id)

    if not objs:
        st.info("Aucun objectif défini. Ajoute ta première course pour que l'IA adapte ton plan !")
    else:
        for o in objs:
            # Container stylisé pour chaque course
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                
                try:
                    d_obj = datetime.fromisoformat(o['date'])
                    days_left = (d_obj.date() - datetime.now().date()).days
                    date_display = d_obj.strftime('%d/%m/%Y')
                    
                    # Couleur selon urgence/proximité
                    status_color = "#ef4444" if days_left < 7 else ("#f59e0b" if days_left < 30 else "#ffffff")
                except:
                    date_display = "Date invalide"
                    days_left = "?"
                    status_color = "#ffffff"
                
                c1.markdown(f"**{o.get('name', 'Sans nom')}**")
                c1.caption(f"🏷️ {o.get('type', 'Course')}")
                
                c2.write(f"📅 {date_display}")
                c2.markdown(f"<span style='color:{status_color}; font-weight:bold;'>{days_left}j restants</span>", unsafe_allow_html=True)
                
                c3.write(f"📏 {o.get('km', 0)}km | 📈 {o.get('dplus', 0)}m")
                priority_labels = {1: "Majeur (A)", 2: "Interm. (B)", 3: "Prépa (C)"}
                c3.caption(f"🚩 Priorité: {priority_labels.get(o.get('priority', 3))}")
                
                if c4.button("🗑️", key=f"del_{o['id']}", help="Supprimer cet objectif"):
                    delete_objective(user_id, o['id'])
                    st.toast(f"Objectif {o.get('name')} supprimé.")
                    st.rerun()

    # --- ANALYSE DE LA SAISON ---
    if objs:
        st.divider()
        with st.expander("📊 Aperçu de la charge cumulée"):
            total_km = sum(o.get('km', 0) for o in objs)
            total_dplus = sum(o.get('dplus', 0) for o in objs)
            st.write(f"Tu as **{len(objs)}** objectifs prévus cette saison.")
            st.write(f"Volume total en compétition : **{total_km} km** et **{total_dplus} m D+**.")

    st.info("💡 **Note** : Ces objectifs sont transmis au coach IA pour qu'il puisse anticiper tes phases d'affûtage (Tapering) et tes blocs de charge dans l'onglet Entraînement.")

if __name__ == "__main__":
    # Pour test local
    render("athlete_default")
