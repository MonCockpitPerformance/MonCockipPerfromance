import streamlit as st
import pandas as pd
import os
import sys

# --- CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.data import load_profile, save_user_profile

def render(user_id):
    st.header("👤 Profil Athlète Expert")
    
    # 1. Chargement des données Firestore
    prof = load_profile(user_id)

    # --- STYLE & HEADER ---
    betrail_idx = prof.get('betrail_index', 50.0)
    sessions_target = prof.get('weekly_sessions_target', 3)
    
    st.info(f"""
    💡 **Analyse du Coach** : 
    Avec un indice BeTrail de **{betrail_idx}**, tes plans sont calibrés sur une base de **{sessions_target} séances** par semaine.
    """)

    # --- FORMULAIRE DE MODIFICATION ---
    with st.form("profile_form_expert"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔗 Connexions Externes")
            prof['intervals_id'] = st.text_input(
                "ID Intervals.icu (ex: i12345)", 
                value=prof.get('intervals_id', ""),
                help="Trouve ton ID dans les paramètres Intervals.icu"
            )
            prof['api_key'] = st.text_input(
                "Clé API Intervals", 
                value=prof.get('api_key', ""), 
                type="password",
                help="Clé nécessaire pour synchroniser tes activités"
            )
            
            st.markdown("---")
            st.subheader("🏆 Indices de Performance")
            prof['betrail_index'] = st.number_input(
                "Indice BeTrail actuel", 
                value=float(betrail_idx), 
                step=0.1,
                help="Ton indice de performance global sur BeTrail"
            )
            prof['utmb_index'] = st.number_input(
                "UTMB Index (Performance)", 
                value=int(prof.get('utmb_index', 0)),
                help="Ton score UTMB Index"
            )
            prof['betrail_url'] = st.text_input(
                "URL Profil BeTrail", 
                value=prof.get('betrail_url', ""),
                placeholder="https://betrail.run/athlete/..."
            )

        with col2:
            st.subheader("🛣️ Records Route")
            prof['rec_10k'] = st.text_input("Record 10km (HH:MM:SS)", value=prof.get('rec_10k', "00:45:00"))
            prof['rec_semi'] = st.text_input("Record Semi (HH:MM:SS)", value=prof.get('rec_semi', "01:40:00"))
            prof['rec_marathon'] = st.text_input("Record Marathon (HH:MM:SS)", value=prof.get('rec_marathon', "03:45:00"))
            
            st.markdown("---")
            st.subheader("🏔️ Expérience Trail")
            prof['trail_max_km'] = st.number_input("Distance Max parcourue (km)", value=int(prof.get('trail_max_km', 20)))
            prof['trail_max_dplus'] = st.number_input("D+ Max parcouru (m)", value=int(prof.get('trail_max_dplus', 1000)))
            
            st.markdown("---")
            st.subheader("⚙️ Préférences de Charge")
            prof['weekly_sessions_target'] = st.slider(
                "Objectif séances / semaine", 
                1, 7, 
                value=int(sessions_target),
                help="Nombre de jours où tu peux t'entraîner."
            )

        st.divider()
        
        # --- ZONE DE COLLAGE BETRAIL ---
        st.subheader("🏛️ Historique & Data")
        st.caption("Données utilisées par l'IA pour comprendre ton profil d'endurance.")
        
        prof['betrail_raw_data'] = st.text_area(
            "Historique de courses (Copier-Coller BeTrail)", 
            value=prof.get('betrail_raw_data', ""),
            height=150,
            placeholder="Date | Nom de la course | Distance | D+ | Score...",
            help="Colle ici le tableau de tes résultats BeTrail pour une analyse historique complète."
        )

        prof['nolio_token'] = st.text_input(
            "Token API Nolio", 
            value=prof.get('nolio_token', ""), 
            type="password",
            help="Pour l'export automatique des séances vers Nolio."
        )
        
        # --- BOUTON DE SAUVEGARDE ---
        submitted = st.form_submit_button("💾 Enregistrer mon profil Expert", use_container_width=True)

    # --- ACTION APRÈS CLIC ---
    if submitted:
        # Nettoyage basique des entrées
        if isinstance(prof['betrail_index'], (int, float)):
            prof['betrail_index'] = round(float(prof['betrail_index']), 1)
            
        save_user_profile(user_id, prof)
        st.success("✅ Profil mis à jour ! Le coach Gemini utilise désormais ces données pour affiner ses conseils.")
        st.rerun()

    # --- LIENS EXTERNES ---
    st.divider()
    st.caption("Accès rapide à tes plateformes :")
    cols_links = st.columns(3)
    
    betrail_url = prof.get('betrail_url') if prof.get('betrail_url') else "https://betrail.run"
    cols_links[0].link_button("📊 BeTrail", betrail_url, use_container_width=True)
    cols_links[1].link_button("🏔️ UTMB World", "https://utmb.world/", use_container_width=True)
    cols_links[2].link_button("⚡ Intervals.icu", "https://intervals.icu/", use_container_width=True)

if __name__ == "__main__":
    # Test
    render("athlete_default")
