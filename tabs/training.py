import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import os
import sys

# --- CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.data import load_profile, get_nolio_sessions, parse_betrail_paste
from core.logic import get_ai_response

# --- CONFIGURATION DES ÉMOJIS ---
ACTIVITY_ICONS = {
    'Ride': '🚴', 'Cyclisme sur route': '🚴', 'VirtualRide': '🚴',
    'Run': '🏃', 'Course à pied': '🏃', 'TrailRun': '🏔️', 'Trail': '🏔️',
    'WeightTraining': '🏋️', 'Musculation': '🏋️', 'RockClimbing': '🧗',
    'Swim': '🏊', 'Yoga': '🧘', 'default': '🏃'
}

# --- FORMATTERS ---
def format_duration(seconds):
    if not seconds or seconds == 0: return "--:--"
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if td.days > 0:
        return f"{td.days}j {hours}h"
    return f"{hours:02d}:{minutes:02d}"

def format_distance(meters):
    if not meters or meters == 0: return "-- km"
    return f"{meters/1000:.1f} km"

def format_dplus(meters):
    if not meters or meters == 0: return "-- D+"
    return f"+{int(meters)}m"

# --- UI: CARTE D'ACTIVITÉ ---
def render_activity_card(title, activity_type, duration="--", distance="--", dplus="--", source="Réalisé", is_today=False):
    primary_type = activity_type if isinstance(activity_type, str) else 'default'
    icon = ACTIVITY_ICONS.get(primary_type, ACTIVITY_ICONS['default'])
    
    source_colors = {
        '✅ Réalisé': {'border': '#00C851', 'bg': 'rgba(0, 200, 81, 0.05)', 'label': 'RÉALISÉ'},
        '🏛️ Nolio': {'border': '#3d5afe', 'bg': 'rgba(61, 90, 254, 0.05)', 'label': 'PRÉVU'},
        '✨ IA': {'border': '#ff9100', 'bg': 'rgba(255, 145, 0, 0.05)', 'label': 'IA'}
    }
    
    c = source_colors.get(source, {'border': '#333', 'bg': '#111', 'label': 'INFO'})
    border_style = "2px solid #FF4B4B" if is_today else f"1px solid {c['border']}"

    html_content = f"""
    <div style="border: {border_style}; background-color: {c['bg']}; padding: 12px; border-radius: 12px; margin-bottom: 12px; color: white; transition: transform 0.2s;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 20px;">{icon}</span>
            <span style="font-size: 9px; font-weight: 800; color: {c['border']}; border: 1px solid {c['border']}; padding: 2px 5px; border-radius: 4px; letter-spacing: 0.5px;">
                {c['label']}
            </span>
        </div>
        <div style="font-weight: 600; font-size: 13px; margin-bottom: 10px; line-height:1.3; min-height: 34px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            {title}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; align-items: center;">
            <div style="font-size: 11px; font-weight: 700;">{duration}</div>
            <div style="font-size: 11px; font-weight: 700; color: #FF9F43; text-align: center;">{distance}</div>
            <div style="font-size: 10px; color: #aaa; text-align: right;">{dplus}</div>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# --- RENDER PRINCIPAL ---
def render(df_intervals):
    user_id = st.session_state.get('uid') or (st.session_state.get('user', {}).get('uid') if st.session_state.get('user') else None)
    
    if not user_id:
        st.warning("Veuillez vous connecter pour voir votre entraînement.")
        return
        
    prof = load_profile(user_id)
    
    # 1. BANDEAU OBJECTIF
    race_date_raw = prof.get('next_race_date') or prof.get('date_objectif')
    race_name = prof.get('next_race_name', 'Prochain Objectif')
    
    if race_date_raw:
        try:
            if isinstance(race_date_raw, (date, datetime)):
                race_date = race_date_raw.date() if isinstance(race_date_raw, datetime) else race_date_raw
            else:
                race_date = datetime.strptime(str(race_date_raw), "%Y-%m-%d").date()
            
            days_to_go = (race_date - date.today()).days
            if days_to_go >= 0:
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1e1e1e 0%, #141a2a 100%); border-left: 5px solid #FF4B4B; padding: 20px; border-radius: 12px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                        <div>
                            <span style="color: #888; font-size: 0.85em; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;">Compte à rebours</span><br>
                            <b style="font-size: 1.4em; color: white;">🏆 {race_name}</b>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 2.8em; font-weight: 900; color: #FF4B4B; line-height: 1;">J-{days_to_go}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            pass

    # 2. RÉCUPÉRATION DONNÉES NOLIO & BETRAIL
    # On affiche une fenêtre de 7 jours glissants centrée sur aujourd'hui
    start_week = date.today() - timedelta(days=2)
    end_week = date.today() + timedelta(days=4)
    
    nolio_sessions = []
    if prof.get('nolio_token'):
        try:
            nolio_sessions = get_nolio_sessions(prof['nolio_token'], start_week.isoformat(), end_week.isoformat())
        except:
            st.error("Erreur de connexion à Nolio.")

    raw_betrail = prof.get('betrail_raw_data', "")
    betrail_data = parse_betrail_paste(raw_betrail)

    # 3. PLANNING HEBDOMADAIRE
    st.subheader("🗓️ Vue Hebdomadaire")
    cols = st.columns(7)
    
    for i, col in enumerate(cols):
        current_date = start_week + timedelta(days=i)
        is_today = current_date == date.today()
        
        with col:
            # Header Date stylisé
            bg_header = "rgba(255, 75, 75, 0.15)" if is_today else "rgba(255, 255, 255, 0.05)"
            border_header = "#FF4B4B" if is_today else "transparent"
            
            st.markdown(f"""
                <div style="background-color: {bg_header}; border: 1px solid {border_header}; padding: 8px 5px; border-radius: 10px; text-align: center; margin-bottom: 12px;">
                    <div style="font-size: 10px; color: {'#FF4B4B' if is_today else '#888'}; font-weight: 800; text-transform: uppercase;">{current_date.strftime('%a')}</div>
                    <div style="font-size: 16px; font-weight: 900; color: white;">{current_date.strftime('%d')}</div>
                </div>
            """, unsafe_allow_html=True)

            # A. REALISÉ (Intervals.icu)
            if df_intervals is not None and not df_intervals.empty:
                # Filtrage sur la date
                df_intervals['date_only'] = pd.to_datetime(df_intervals['date']).dt.date
                day_data = df_intervals[df_intervals['date_only'] == current_date]
                
                for _, p in day_data.iterrows():
                    render_activity_card(
                        title=p.get('name', 'Activité'),
                        activity_type=p.get('type', 'Run'),
                        duration=format_duration(p.get('moving_time', 0)),
                        distance=format_distance(p.get('distance', 0)),
                        dplus=format_dplus(p.get('elevation_gain', 0)),
                        source="✅ Réalisé", 
                        is_today=is_today
                    )

            # B. PRÉVU (Nolio)
            if nolio_sessions:
                day_nolio = [s for s in nolio_sessions if str(s.get('date'))[:10] == current_date.isoformat()]
                for s in day_nolio:
                    render_activity_card(
                        title=s.get('title', 'Séance prévue'),
                        activity_type=s.get('sport', 'Run'),
                        duration=format_duration(s.get('duration_planned', 0)),
                        distance=format_distance(s.get('distance_planned', 0)),
                        dplus=format_dplus(s.get('elevation_gain_planned', 0)),
                        source="🏛️ Nolio", 
                        is_today=is_today
                    )

    st.divider()

    # 4. CHAT IA AVEC CONTEXTE COMPLET
    st.subheader("🤖 Assistant Coach Gemini")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Affichage de l'historique
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ex: Analyse ma fatigue ou ajuste ma séance de demain..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse des datas (Nolio + Intervals + BeTrail)..."):
                # Calcul des métriques de forme (Last Known)
                metrics = {'ctl': 0, 'atl': 0, 'tsb': 0}
                if df_intervals is not None and not df_intervals.empty:
                    # On prend la dernière ligne qui a des données de fitness
                    fitness_data = df_intervals.dropna(subset=['icu_ctl'])
                    if not fitness_data.empty:
                        last_row = fitness_data.iloc[-1]
                        metrics['ctl'] = int(last_row.get('icu_ctl', 0))
                        metrics['atl'] = int(last_row.get('icu_atl', 0))
                        metrics['tsb'] = int(last_row.get('icu_tsb', 0))

                # Historique récent Intervals (7 derniers jours)
                recent_activities = []
                if df_intervals is not None:
                    recent_activities = df_intervals.tail(7).to_dict('records')

                # Appel de l'IA via core.logic
                response = get_ai_response(
                    prompt=prompt,
                    profile=prof,
                    metrics=metrics,
                    recent_activities=recent_activities,
                    planned_sessions=nolio_sessions,
                    betrail_history=betrail_data
                )
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    pass
