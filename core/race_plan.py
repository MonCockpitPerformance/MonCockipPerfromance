import streamlit as st
import pd as pd
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
from core.data import load_profile, save_profile, parse_gpx_file

@st.cache_data
def calculate_accumulated_elevation(df_gpx_json, target_dist):
    """
    Calcule le D+ et D- cumulés jusqu'à une distance donnée.
    Utilise le cache pour éviter de recalculer sur des fichiers GPX lourds.
    """
    if not df_gpx_json:
        return 0, 0
    try:
        df_gpx = pd.read_json(df_gpx_json)
        if df_gpx.empty:
            return 0, 0
        
        # On filtre jusqu'au point de distance cible
        df_segment = df_gpx[df_gpx['distance'] <= target_dist].copy()
        if len(df_segment) < 2:
            return 0, 0
        
        df_segment['diff'] = df_segment['elevation'].diff().fillna(0)
        pos = df_segment[df_segment['diff'] > 0]['diff'].sum()
        neg = df_segment[df_segment['diff'] < 0]['diff'].abs().sum()
        
        return int(pos), int(neg)
    except:
        return 0, 0

def decimal_to_pace_str(decimal_min):
    """
    Convertit une allure décimale en format texte.
    Exemple: 8.5 -> 8'30"
    """
    if decimal_min <= 0: return "0'00\""
    minutes = int(decimal_min)
    seconds = int(round((decimal_min - minutes) * 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}'{seconds:02d}\""

def pace_str_to_decimal(pace_str):
    """
    Convertit une chaîne (8'30) ou un flottant (8.5) en décimal.
    """
    try:
        if isinstance(pace_str, (int, float)):
            return float(pace_str)
        if "'" in pace_str:
            parts = pace_str.replace('"', '').split("'")
            return int(parts[0]) + (int(parts[1]) / 60)
        return float(pace_str)
    except:
        return 10.0

def format_duration(minutes):
    """
    Formate une durée en minutes en format lisible Hh MMmin.
    """
    if minutes < 60:
        return f"{int(minutes)}min"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h{mins:02d}"

def estimate_recommended_pace(profile):
    """
    Estime une allure recommandée (min/km) selon l'index BeTrail ou profil.
    """
    # Valeur par défaut prudente
    base_pace = 9.0 
    
    # Tentative d'ajustement selon l'index BeTrail si présent
    betrail = profile.get('betrail_performance_index')
    if betrail:
        try:
            val = float(betrail)
            if val > 60: base_pace = 7.5
            elif val > 50: base_pace = 8.5
            elif val > 40: base_pace = 10.0
            else: base_pace = 12.0
        except:
            pass
    return base_pace

def get_all_objectives(profile):
    """
    Récupère la liste exhaustive des noms de courses possibles.
    """
    objs = []
    
    # 1. Depuis les dictionnaires spécifiques
    for key in ["objectifs", "objectives", "race_plans"]:
        data = profile.get(key, {})
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get("nom") or item.get("name") or item.get("Course")
                    if name: objs.append(str(name))
        elif isinstance(data, dict):
            objs += list(data.keys())
    
    # 2. Nettoyage et dédoublonnage
    return sorted(list(set([o.strip() for o in objs if o])))

def render():
    st.header("🗺️ Plan de Course & Simulateur")
    
    user_id = st.session_state.get("uid") or (st.session_state.get("user", {}).get("uid") if st.session_state.get("user") else None)
    if not user_id:
        st.warning("Veuillez vous connecter pour accéder au plan de course.")
        return

    profile = load_profile(user_id)
    race_plans = profile.get("race_plans", {})

    # --- SÉLECTION DE LA COURSE ---
    objectives = get_all_objectives(profile)
    
    if not objectives:
        st.info("Aucun objectif détecté. Créez un plan manuellement.")
        new_plan = st.text_input("Nom de la course", key="new_plan_name")
        if st.button("Lancer la planification"):
            if new_plan:
                st.session_state.selected_race = new_plan
                st.rerun()
        return

    # Gestion de la sélection persistante en session
    if "selected_race" not in st.session_state or st.session_state.selected_race not in objectives:
        st.session_state.selected_race = objectives[0]

    c_sel, c_add = st.columns([3, 1])
    selected_race = c_sel.selectbox("Course à planifier", objectives, index=objectives.index(st.session_state.selected_race))
    st.session_state.selected_race = selected_race
    
    if c_add.button("➕ Nouveau"):
        st.session_state.selected_race = "Nouveau Plan"
        st.rerun()

    if st.session_state.selected_race == "Nouveau Plan":
        name = st.text_input("Nom de la course")
        if st.button("Valider"):
            st.session_state.selected_race = name
            st.rerun()
        return

    current_race = st.session_state.selected_race
    
    # Initialisation de la structure de données
    if current_race not in race_plans:
        race_plans[current_race] = {
            "checkpoints": [],
            "gpx_data": None,
            "gpx_filename": None,
            "base_pace": float(estimate_recommended_pace(profile)),
            "start_time": "08:00"
        }
        save_profile(user_id, {"race_plans": race_plans})

    race_data = race_plans[current_race]
    
    # Chargement GPX
    df_gpx = pd.DataFrame()
    if race_data.get("gpx_data"):
        try:
            df_gpx = pd.read_json(race_data["gpx_data"])
        except:
            st.error("Erreur de format GPX sauvegardé.")

    # --- VISUALISATION ---
    st.subheader(f"📊 Analyse : {current_race}")
    
    if not df_gpx.empty:
        checkpoints = sorted(race_data.get("checkpoints", []), key=lambda x: x['distance'])
        
        # Profil altimétrique Plotly
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_gpx['distance'], y=df_gpx['elevation'],
            fill='tozeroy', mode='lines', line=dict(color='#2ecc71', width=2),
            fillcolor='rgba(46, 204, 113, 0.1)', name='Altitude'
        ))

        # Annotations pour les points de passage
        for cp in checkpoints:
            # Trouver l'altitude exacte au KM donné
            idx = (df_gpx['distance'] - cp['distance']).abs().idxmin()
            alt = df_gpx.loc[idx, 'elevation']
            
            fig.add_annotation(
                x=cp['distance'], y=alt, text=cp['name'], showarrow=True,
                ay=-30, arrowhead=2, bgcolor="rgba(0,0,0,0.8)", bordercolor="#2ecc71"
            )
            fig.add_vline(x=cp['distance'], line_width=1, line_dash="dash", line_color="rgba(255,255,255,0.3)")

        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=10, b=0),
                         xaxis_title="Distance (km)", yaxis_title="Altitude (m)")
        st.plotly_chart(fig, use_container_width=True)

        # --- PARAMÈTRES DE VITESSE ---
        st.markdown("### 📋 Paramètres de Vitesse")
        c1, c2 = st.columns(2)
        
        saved_time_str = race_data.get("start_time", "08:00")
        start_time = c1.time_input("Heure de départ", value=datetime.strptime(saved_time_str, "%H:%M").time())
        if start_time.strftime("%H:%M") != saved_time_str:
            race_data["start_time"] = start_time.strftime("%H:%M")
            save_profile(user_id, {"race_plans": race_plans})

        current_base_pace = float(race_data.get("base_pace", 9.0))
        base_pace_input = c2.number_input("Allure de base (min/km)", 3.0, 15.0, current_base_pace, 0.1)
        c2.info(f"Équivalent : **{decimal_to_pace_str(base_pace_input)} / km**")

        if base_pace_input != current_base_pace:
            race_data["base_pace"] = base_pace_input
            save_profile(user_id, {"race_plans": race_plans})

        # --- TABLEAU DE MARCHE ---
        st.markdown("### ⏱️ Temps de Passage")
        data_table = []
        current_time = datetime.combine(date.today(), start_time)
        prev_dist = 0.0
        df_json = df_gpx.to_json()
        
        for cp in checkpoints:
            dist_segment = cp['distance'] - prev_dist
            coeff = cp.get('fatigue_coeff', 100) / 100.0
            actual_pace = base_pace_input * coeff
            
            travel_time = dist_segment * actual_pace
            current_time += timedelta(minutes=travel_time)
            
            d_plus, _ = calculate_accumulated_elevation(df_json, cp['distance'])
            
            data_table.append({
                "Type": cp['type'], "Nom": cp['name'], "KM": cp['distance'],
                "D+": f"{d_plus}m", "Tps Seg.": format_duration(travel_time),
                "Coeff": f"{int(coeff*100)}%", "Allure": decimal_to_pace_str(actual_pace),
                "Passage": current_time.strftime("%H:%M")
            })
            prev_dist = cp['distance']
        
        if data_table:
            st.table(pd.DataFrame(data_table))
            
            # Ajustements rapides
            with st.expander("🛠️ Ajuster l'état de fatigue par section"):
                for i, cp in enumerate(checkpoints):
                    c_val = cp.get('fatigue_coeff', 100)
                    new_coeff = st.select_slider(
                        f"{cp['name']} (KM {cp['distance']})",
                        options=[80, 85, 90, 95, 100, 105, 110, 115, 120, 130, 140, 150],
                        value=c_val,
                        key=f"fat_{current_race}_{i}"
                    )
                    if new_coeff != c_val:
                        race_data["checkpoints"][i]['fatigue_coeff'] = new_coeff
                        save_profile(user_id, {"race_plans": race_plans})
                        st.rerun()

    # --- CONFIGURATION / IMPORT ---
    st.divider()
    c_file, c_cp = st.columns(2)
    
    with c_file:
        st.subheader("📁 Import GPX")
        uploaded_file = st.file_uploader("Fichier GPX", type=["gpx"], key="gpx_up")
        if uploaded_file:
            if race_data.get("gpx_filename") != uploaded_file.name:
                df_new = parse_gpx_file(uploaded_file)
                if not df_new.empty:
                    race_data["gpx_data"] = df_new.to_json()
                    race_data["gpx_filename"] = uploaded_file.name
                    save_profile(user_id, {"race_plans": race_plans})
                    st.success("Tracé chargé !")
                    st.rerun()

    with c_cp:
        st.subheader("📍 Points de passage")
        if not df_gpx.empty:
            cp_n = st.text_input("Nom")
            cp_d = st.number_input("Kilomètre", 0.0, float(df_gpx['distance'].max()), step=0.1)
            cp_t = st.selectbox("Type", ["🍲 Ravito", "🏃 Passage", "🏁 Arrivée"])
            if st.button("Ajouter le point"):
                race_data["checkpoints"].append({
                    "name": cp_n, "distance": round(cp_d, 2), "type": cp_t, "fatigue_coeff": 100
                })
                save_profile(user_id, {"race_plans": race_plans})
                st.rerun()
            
            # Option de suppression du dernier point
            if race_data["checkpoints"]:
                if st.button("🗑️ Supprimer le dernier point"):
                    race_data["checkpoints"].pop()
                    save_profile(user_id, {"race_plans": race_plans})
                    st.rerun()
        else:
            st.info("Importez un GPX pour ajouter des points.")

if __name__ == "__main__":
    render()
