import streamlit as st
import pandas as pd
from core.data import load_profile, save_user_profile

def render(user_id):
    st.header("👤 Profil Athlète Expert")
    
    # 1. Chargement des données Firestore
    prof = load_profile(user_id)

    # --- STYLE & HEADER ---
    st.info(f"💡 **Analyse du Coach** : Avec un indice BeTrail de **{prof.get('betrail_index', 50.0)}**, tes plans sont calibrés sur une base de **{prof.get('weekly_sessions_target', 3)} séances** par semaine.")

    # --- FORMULAIRE DE MODIFICATION ---
    with st.form("profile_form_expert"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔗 Connexion Intervals.icu")
            prof['intervals_id'] = st.text_input("ID Athlète (ex: i12345)", value=prof.get('intervals_id', ""))
            prof['api_key'] = st.text_input("Clé API Intervals", value=prof.get('api_key', ""), type="password")

            st.markdown("### 🏆 Indices de Performance")
            prof['betrail_index'] = st.number_input("Indice BeTrail actuel", value=float(prof.get('betrail_index', 50.0)), step=0.1)
            prof['utmb_index'] = st.number_input("UTMB Index (Performance)", value=int(prof.get('utmb_index', 0)))
            prof['betrail_url'] = st.text_input("URL Profil BeTrail", value=prof.get('betrail_url', ""))

        with col2:
            st.markdown("### 🛣️ Records Route")
            prof['rec_10k'] = st.text_input("Record 10km", value=prof.get('rec_10k', "00:45:00"))
            prof['rec_semi'] = st.text_input("Record Semi", value=prof.get('rec_semi', "01:40:00"))
            prof['rec_marathon'] = st.text_input("Record Marathon", value=prof.get('rec_marathon', "03:45:00"))
            
            st.markdown("### 🏔️ Expérience Trail")
            prof['trail_max_km'] = st.number_input("Distance Max (km)", value=int(prof.get('trail_max_km', 20)))
            prof['trail_max_dplus'] = st.number_input("D+ Max (m)", value=int(prof.get('trail_max_dplus', 1000)))
            
            st.markdown("### ⚙️ Préférences")
            prof['weekly_sessions_target'] = st.slider("Objectif séances / semaine", 1, 7, value=int(prof.get('weekly_sessions_target', 3)))

        st.divider()
        
        # --- ZONE DE COLLAGE BETRAIL ---
        st.markdown("### 🏆 Historique BeTrail (Copier-Coller)")
        st.caption("Sélectionne tes courses sur BeTrail > Copier > Coller ci-dessous.")
        prof['betrail_raw_data'] = st.text_area(
            "Données brutes BeTrail", 
            value=prof.get('betrail_raw_data', ""),
            height=150,
            help="Colle ici le tableau de tes résultats BeTrail pour que l'IA connaisse ton historique."
        )

        st.markdown("### 🏛️ Connexion Nolio")
        prof['nolio_token'] = st.text_input("Token API Nolio", value=prof.get('nolio_token', ""), type="password")
        
        # --- BOUTON DE SAUVEGARDE ---
        submitted = st.form_submit_button("💾 Enregistrer mon profil Expert")

    # --- ACTION APRÈS CLIC ---
    if submitted:
        save_user_profile(user_id, prof)
        st.success("✅ Profil mis à jour ! Le coach Gemini utilise désormais ces données pour affiner ses conseils.")
        st.rerun()

    # --- LIENS EXTERNES ---
    st.divider()
    cols_links = st.columns(3)
    cols_links[0].link_button("📊 BeTrail", prof.get('betrail_url') if prof.get('betrail_url') else "https://betrail.run", use_container_width=True)
    cols_links[1].link_button("🏔️ UTMB World", "https://utmb.world/", use_container_width=True)
    cols_links[2].link_button("⚡ Intervals.icu", "https://intervals.icu/", use_container_width=True)

if __name__ == "__main__":
    pass