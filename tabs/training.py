import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
from core.data import load_profile, parse_betrail_paste
from core.logic import get_ai_response

# --- 0. CONFIGURATION DES ÉMOJIS ---
ACTIVITY_ICONS = {
    'Ride': '🚴', 'Cyclisme sur route': '🚴', 'VirtualRide': '🚴',
    'Run': '🏃', 'Course à pied': '🏃', 'TrailRun': '🏔️', 'Trail': '🏔️',
    'WeightTraining': '🏋️', 'Musculation': '🏋️', 'RockClimbing': '🧗',
    'Swim': '🏊', 'Yoga': '🧘', 'default': '🏃'
}

# --- 1. FORMATTERS ---
def format_duration(seconds):
    if not seconds or pd.isna(seconds) or seconds == 0: return "--:--"
    return str(timedelta(seconds=int(seconds)))

def format_distance(meters):
    if not meters or pd.isna(meters) or meters == 0: return "-- km"
    return f"{meters/1000:.1f} km"

def format_dplus(meters):
    if not meters or pd.isna(meters) or meters == 0: return "-- D+"
    return f"+{int(meters)} m"

# --- 2. UI: CARTE D'ACTIVITÉ ---
def render_activity_card(title, activity_type, duration="--", distance="--", dplus="--", source="Réalisé", is_today=False):
    primary_type = activity_type if isinstance(activity_type, str) else 'default'
    icon = ACTIVITY_ICONS.get(primary_type, ACTIVITY_ICONS['default'])
    
    source_colors = {
        '✅ Réalisé': {'border': '#00C851', 'bg': '#071a0e', 'label': 'RÉALISÉ'},
        '🏛️ Nolio': {'border': '#3d5afe', 'bg': '#0d1117', 'label': 'NOLIO'},
        '✨ IA': {'border': '#ff9100', 'bg': '#1a1408', 'label': 'IA'}
    }
    
    c = source_colors.get(source, {'border': '#333', 'bg': '#111', 'label': 'INFO'})
    border_style = "2px solid #FF4B4B" if is_today else f"1px solid {c['border']}"

    html_content = f"""
    <div style="border: {border_style}; background-color: {c['bg']}; padding: 10px; border-radius: 10px; margin-bottom: 10px; color: white;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <span style="font-size: 18px;">{icon}</span>
            <span style="font-size: 9px; font-weight: 800; color: {c['border']}; border: 1px solid {c['border']}; padding: 1px 4px; border-radius: 3px;">
                {c['label']}
            </span>
        </div>
        <div style="font-weight: 600; font-size: 12px; margin-bottom: 8px; line-height:1.2; height: 30px; overflow: hidden;">{title}</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; border-top: 1px solid #333; padding-top: 5px;">
            <div style="font-size: 11px; font-weight: bold;">{duration}</div>
            <div style="font-size: 11px; font-weight: bold; color: #FF9F43;">{distance}</div>
            <div style="font-size: 10px; color: #888;">{dplus}</div>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# --- 3. RENDER PRINCIPAL ---
def render(df, nolio_placeholder=None):
    # Gestion de l'argument optionnel pour éviter le plantage du cockpit
    user_id = st.session_state.get('user', {}).get('uid') if st.session_state.get('user') else None
    
    if not user_id:
        st.warning("Veuillez vous connecter pour voir votre entraînement.")
        return
        
    prof = load_profile(user_id)
    
    # 1. BANDEAU OBJECTIF
    race_date_raw = prof.get('next_race_date') or prof.get('date_objectif')
    race_name = prof.get('next_race_name', 'Objectif')
    
    if race_date_raw:
        try:
            if isinstance(race_date_raw, (date, datetime)):
                race_date = race_date_raw
            else:
                race_date = datetime.strptime(str(race_date_raw), "%Y-%m-%d").date()
            
            days_to_go = (race_date - date.today()).days
            if days_to_go >= 0:
                st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #1e1e1e, #141a2a); border-left: 5px solid #FF4B4B; padding: 15px; border-radius: 10px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        <div><span style="color: #888; font-size: 0.8em; text-transform: uppercase;">Prochain Objectif</span><br><b style="font-size: 1.2em; color: white;">🏆 {race_name}</b></div>
                        <div style="text-align: right;"><span style="font-size: 2.2em; font-weight: 900; color: #FF4B4B;">J-{days_to_go}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        except: pass

    # 2. RÉCUPÉRATION DONNÉES NOLIO & BETRAIL
    start_week = date.today() - timedelta(days=2)
    end_week = date.today() + timedelta(days=4)
    
    nolio_sessions = []
    if prof.get('nolio_token'):
        try:
            nolio_sessions = get_nolio_sessions(prof['nolio_token'], start_week.isoformat(), end_week.isoformat())
        except:
            pass

    raw_betrail = prof.get('betrail_raw_data', "")
    betrail_data = parse_betrail_paste(raw_betrail)

    # 3. PLANNING HEBDOMADAIRE (Sur 7 colonnes)
    st.subheader("🗓️ Planning Hebdomadaire")
    cols = st.columns(7)
    
    # Pré-traitement des dates pour Intervals.icu
    if df is not None and not df.empty:
        df['date_parsed'] = pd.to_datetime(df['date']).dt.date

    for i, col in enumerate(cols):
        current_date = start_week + timedelta(days=i)
        is_today = current_date == date.today()
        
        with col:
            # Header Date
            bg = "#1E1E1E" if is_today else "#111"
            label_today = "AUJOURD'HUI" if is_today else ""
            
            st.markdown(f"""
                <div style="background-color: {bg}; border: 1px solid {'#FF4B4B' if is_today else '#333'}; padding: 5px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 10px; color: #888;">{current_date.strftime('%a %d')}</div>
                    <div style="font-size: 10px; font-weight: bold; color: {'#FF4B4B' if is_today else 'white'};">{label_today}</div>
                </div>
            """, unsafe_allow_html=True)

            # A. REALISÉ (Intervals.icu)
            if df is not None and not df.empty:
                day_data = df[df['date_parsed'] == current_date]
                for _, p in day_data.iterrows():
                    render_activity_card(
                        title=p.get('name', 'Activité'),
                        activity_type=p.get('type', 'Run'),
                        duration=format_duration(p.get('moving_time', 0)),
                        distance=format_distance(p.get('distance', 0)),
                        dplus=format_dplus(p.get('elevation_gain', 0)),
                        source="✅ Réalisé", is_today=is_today
                    )

            # B. PRÉVU (Nolio)
            if nolio_sessions:
                day_nolio = [s for s in nolio_sessions if str(s.get('date'))[:10] == current_date.isoformat()]
                for s in day_nolio:
                    render_activity_card(
                        title=s.get('title', 'Séance'),
                        activity_type=s.get('sport', 'Run'),
                        duration=format_duration(s.get('duration_planned', 0)),
                        distance=format_distance(s.get('distance_planned', 0)),
                        dplus=format_dplus(s.get('elevation_gain_planned', 0)),
                        source="🏛️ Nolio", is_today=is_today
                    )

    st.divider()

    # 4. CHAT IA AVEC CONTEXTE COMPLET
    st.subheader("🤖 Coach IA Gemini")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Affichage de l'historique
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Analyse ma semaine ou propose un ajustement..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse de tes données en cours..."):
                # Calcul des métriques de forme (Intervals.icu)
                metrics = {'ctl': 0, 'atl': 0, 'tsb': 0}
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    metrics['ctl'] = int(last_row.get('icu_ctl', 0))
                    metrics['atl'] = int(last_row.get('icu_atl', 0))
                    metrics['tsb'] = int(last_row.get('icu_tsb', metrics['ctl'] - metrics['atl']))

                # Appel de l'IA (Logic.py)
                response = get_ai_response(
                    prompt, 
                    prof, 
                    metrics, 
                    df.tail(10).to_dict('records') if df is not None else [], 
                    nolio_sessions, 
                    betrail_data
                )
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    pass
