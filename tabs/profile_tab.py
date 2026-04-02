import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from core.data import load_profile, save_user_profile

def test_intervals_connection(athlete_id, api_key):
    """Teste la connexion à l'API Intervals.icu"""
    if not athlete_id or not api_key:
        return False, "Identifiants manquants."
    
    # L'ID doit commencer par 'i' pour l'API, mais parfois les utilisateurs oublient
    formatted_id = athlete_id.strip()
    url = f"https://intervals.icu/api/v1/athlete/{formatted_id}"
    
    try:
        response = requests.get(
            url, 
            auth=HTTPBasicAuth('athlete', api_key.strip()),
            timeout=10
        )
        if response.status_code == 200:
            return True, "Connexion réussie !"
        elif response.status_code == 403:
            return False, "403 : Clé API invalide ou accès refusé."
        elif response.status_code == 404:
            return False, "404 : ID Athlète introuvable (vérifiez le 'i')."
        else:
            return False, f"Erreur {response.status_code}"
    except Exception as e:
        return False, f"Erreur de connexion : {str(e)}"

def render(user_id):
    st.header("👤 Profil Athlète Expert")
    
    prof = load_profile(user_id)
    if not prof: prof = {}

    # --- INFOS COACH ---
    st.info(f"💡 **Indice BeTrail** : {prof.get('betrail_index', 50.0)} | **Objectif** : {prof.get('weekly_sessions_target', 3)} séances/semaine.")

    with st.form("profile_form_expert"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔗 Connexion Intervals.icu")
            # Nettoyage automatique des entrées
            intervals_id = st.text_input(
                "ID Athlète (ex: i12345)", 
                value=prof.get('intervals_id', ""),
                help="Vérifiez bien le 'i' minuscule devant les chiffres."
            ).strip()
            
            api_key = st.text_input(
                "Clé API Intervals", 
                value=prof.get('api_key', ""), 
                type="password"
            ).strip()

            if st.form_submit_button("🧪 Tester la connexion API"):
                success, msg = test_intervals_connection(intervals_id, api_key)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

            st.markdown("### 🏆 Indices de Performance")
            betrail_index = st.number_input("Indice BeTrail", value=float(prof.get('betrail_index', 50.0)), step=0.1)
            utmb_index = st.number_input("UTMB Index", value=int(prof.get('utmb_index', 0)))
            betrail_url = st.text_input("URL BeTrail", value=prof.get('betrail_url', ""))

        with col2:
            st.markdown("### 🛣️ Records Route")
            rec_10k = st.text_input("Record 10km", value=prof.get('rec_10k', "00:45:00"))
            rec_semi = st.text_input("Record Semi", value=prof.get('rec_semi', "01:40:00"))
            rec_marathon = st.text_input("Record Marathon", value=prof.get('rec_marathon', "03:45:00"))
            
            st.markdown("### 🏔️ Expérience Trail")
            trail_max_km = st.number_input("Distance Max (km)", value=int(prof.get('trail_max_km', 20)))
            trail_max_dplus = st.number_input("D+ Max (m)", value=int(prof.get('trail_max_dplus', 1000)))
            
            st.markdown("### ⚙️ Préférences")
            weekly_sessions_target = st.slider("Séances / semaine", 1, 7, value=int(prof.get('weekly_sessions_target', 3)))

        st.divider()
        
        st.markdown("### 🏆 Historique BeTrail (Copier-Coller)")
        betrail_raw_data = st.text_area("Données brutes", value=prof.get('betrail_raw_data', ""), height=100)

        st.markdown("### 🏛️ Connexion Nolio")
        nolio_token = st.text_input("Token API Nolio", value=prof.get('nolio_token', ""), type="password").strip()
        
        submitted = st.form_submit_button("💾 Enregistrer mon profil Expert")

    if submitted:
        updated_prof = {
            "intervals_id": intervals_id,
            "api_key": api_key,
            "betrail_index": betrail_index,
            "utmb_index": utmb_index,
            "betrail_url": betrail_url,
            "rec_10k": rec_10k,
            "rec_semi": rec_semi,
            "rec_marathon": rec_marathon,
            "trail_max_km": trail_max_km,
            "trail_max_dplus": trail_max_dplus,
            "weekly_sessions_target": weekly_sessions_target,
            "betrail_raw_data": betrail_raw_data,
            "nolio_token": nolio_token
        }
        save_user_profile(user_id, updated_prof)
        st.success("✅ Profil enregistré !")
        st.rerun()

    st.divider()
    cols_links = st.columns(3)
    cols_links[0].link_button("📊 BeTrail", prof.get('betrail_url') or "https://betrail.run", use_container_width=True)
    cols_links[1].link_button("🏔️ UTMB World", "https://utmb.world/", use_container_width=True)
    cols_links[2].link_button("⚡ Intervals.icu", "https://intervals.icu/", use_container_width=True)

if __name__ == "__main__":
    pass
