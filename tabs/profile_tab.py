import streamlit as st
import pandas as pd
from core.data import load_profile, save_user_profile

def render(user_id):
    st.header("👤 Profil Athlète Expert")
    
    # 1. Chargement des données Firestore
    # On s'assure de récupérer un dictionnaire, même vide
    prof = load_profile(user_id)
    if not prof:
        prof = {}

    # --- STYLE & HEADER ---
    betrail_idx = prof.get('betrail_index', 50.0)
    sessions_target = prof.get('weekly_sessions_target', 3)
    st.info(f"💡 **Analyse du Coach** : Avec un indice BeTrail de **{betrail_idx}**, tes plans sont calibrés sur une base de **{sessions_target} séances** par semaine.")

    # --- FORMULAIRE DE MODIFICATION ---
    with st.form("profile_form_expert"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔗 Connexion Intervals.icu")
            # Utilisation de clés explicites pour éviter tout conflit de nommage
            intervals_id = st.text_input(
                "ID Athlète (ex: i12345)", 
                value=prof.get('intervals_id', ""),
                help="Votre ID commençant par 'i' (ex: i54321) trouvé dans Settings > API Access"
            )
            api_key = st.text_input(
                "Clé API Intervals", 
                value=prof.get('api_key', ""), 
                type="password",
                help="La clé API générée sur Intervals.icu"
            )

            st.markdown("### 🏆 Indices de Performance")
            betrail_index = st.number_input("Indice BeTrail actuel", value=float(prof.get('betrail_index', 50.0)), step=0.1)
            utmb_index = st.number_input("UTMB Index (Performance)", value=int(prof.get('utmb_index', 0)))
            betrail_url = st.text_input("URL Profil BeTrail", value=prof.get('betrail_url', ""))

        with col2:
            st.markdown("### 🛣️ Records Route")
            rec_10k = st.text_input("Record 10km", value=prof.get('rec_10k', "00:45:00"))
            rec_semi = st.text_input("Record Semi", value=prof.get('rec_semi', "01:40:00"))
            rec_marathon = st.text_input("Record Marathon", value=prof.get('rec_marathon', "03:45:00"))
            
            st.markdown("### 🏔️ Expérience Trail")
            trail_max_km = st.number_input("Distance Max (km)", value=int(prof.get('trail_max_km', 20)))
            trail_max_dplus = st.number_input("D+ Max (m)", value=int(prof.get('trail_max_dplus', 1000)))
            
            st.markdown("### ⚙️ Préférences")
            weekly_sessions_target = st.slider("Objectif séances / semaine", 1, 7, value=int(prof.get('weekly_sessions_target', 3)))

        st.divider()
        
        # --- ZONE DE COLLAGE BETRAIL ---
        st.markdown("### 🏆 Historique BeTrail (Copier-Coller)")
        st.caption("Sélectionne tes courses sur BeTrail > Copier > Coller ci-dessous.")
        betrail_raw_data = st.text_area(
            "Données brutes BeTrail", 
            value=prof.get('betrail_raw_data', ""),
            height=150,
            help="Colle ici le tableau de tes résultats BeTrail."
        )

        st.markdown("### 🏛️ Connexion Nolio")
        nolio_token = st.text_input("Token API Nolio", value=prof.get('nolio_token', ""), type="password")
        
        # --- BOUTON DE SAUVEGARDE ---
        submitted = st.form_submit_button("💾 Enregistrer mon profil Expert")

    # --- ACTION APRÈS CLIC ---
    if submitted:
        # On reconstruit le dictionnaire proprement avec .strip() pour les identifiants
        updated_prof = {
            "intervals_id": intervals_id.strip(),
            "api_key": api_key.strip(),
            "betrail_index": betrail_index,
            "utmb_index": utmb_index,
            "betrail_url": betrail_url.strip(),
            "rec_10k": rec_10k,
            "rec_semi": rec_semi,
            "rec_marathon": rec_marathon,
            "trail_max_km": trail_max_km,
            "trail_max_dplus": trail_max_dplus,
            "weekly_sessions_target": weekly_sessions_target,
            "betrail_raw_data": betrail_raw_data,
            "nolio_token": nolio_token.strip()
        }
        
        try:
            save_user_profile(user_id, updated_prof)
            st.success("✅ Profil mis à jour ! Redémarrage du cockpit...")
            import time
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde : {e}")

    # --- LIENS EXTERNES ---
    st.divider()
    cols_links = st.columns(3)
    cols_links[0].link_button("📊 BeTrail", prof.get('betrail_url') if prof.get('betrail_url') else "https://betrail.run", use_container_width=True)
    cols_links[1].link_button("🏔️ UTMB World", "https://utmb.world/", use_container_width=True)
    cols_links[2].link_button("⚡ Intervals.icu", "https://intervals.icu/", use_container_width=True)

if __name__ == "__main__":
    pass
