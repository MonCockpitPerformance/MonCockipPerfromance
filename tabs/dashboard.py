import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import date, datetime
from core.data import load_profile, get_ia_coaching_feedback, get_coaching_strategy

# Essayer d'importer le rendu stylisé des jauges (si défini dans ui.py)
try:
    from core.ui import render_sport_metric
except ImportError:
    render_sport_metric = None

def render(df):
    # --- CHARGEMENT DU CONTEXTE ---
    # Récupération de l'UID utilisateur (compatible avec différents systèmes de session)
    user_id = st.session_state.get('uid') or (st.session_state.get('user', {}).get('uid') if st.session_state.get('user') else None)
    
    if not user_id:
        st.warning("Veuillez vous connecter pour voir le dashboard.")
        return
        
    prof = load_profile(user_id)
    
    st.title("🚀 Cockpit Performance")

    # --- SÉCURITÉ : VÉRIFICATION DES DONNÉES ---
    if df is None or df.empty:
        st.warning("Données Intervals.icu non disponibles. Connectez votre compte dans l'onglet Profil.")
        return

    # Nettoyage et préparation des données
    df_clean = df.copy()
    if 'date' not in df_clean.columns and 'start_date_local' in df_clean.columns:
        df_clean['date'] = pd.to_datetime(df_clean['start_date_local'])
    
    df_clean = df_clean.fillna(0).sort_values('date')
    last_row = df_clean.iloc[-1]
    
    ctl = int(last_row.get('icu_ctl', 0))
    atl = int(last_row.get('icu_atl', 0))
    tsb = ctl - atl

    # --- 1. STRATÉGIE ET MÉTRIQUES (KPI) ---
    st.subheader("💡 Coaching Stratégique")
    
    # Correction : On passe le DF aux fonctions comme défini dans data.py
    strat_label = get_coaching_strategy(df_clean)
    st.success(f"🎯 Stratégie actuelle : {strat_label}")

    c1, c2, c3 = st.columns(3)
    if render_sport_metric:
        with c1: render_sport_metric(ctl, "Condition (CTL)", "#3b82f6", 0, 100)
        with c2: render_sport_metric(atl, "Fatigue (ATL)", "#a855f7", 0, 150)
        with c3: 
            # Couleur dynamique pour le TSB selon les zones Intervals
            if tsb < -30: color = "#ef4444" # Risque
            elif tsb < -10: color = "#10b981" # Optimal
            elif tsb < 5: color = "#3b82f6" # Frais
            else: color = "#f59e0b" # Transition
            render_sport_metric(tsb, "Forme (TSB)", color, -40, 40)
    else:
        c1.metric("Condition (CTL)", ctl, help="Charge d'entraînement long terme")
        c2.metric("Fatigue (ATL)", atl, help="Charge d'entraînement court terme")
        c3.metric("Forme (TSB)", tsb, delta=tsb, delta_color="normal", help="Équilibre fraîcheur/fatigue")

    # --- 2. GRAPHIQUE DOUBLE ETAGE (STYLE INTERVALS/GARMIN) ---
    st.markdown("### 📈 Analyse de la Condition Physique")
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.65, 0.35]
    )

    # --- ETAGE 1 : CONDITION & FATIGUE (CTL/ATL) ---
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_atl'],
        name="Fatigue (ATL)",
        line=dict(color='#a855f7', width=1.5),
        opacity=0.5,
        fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.05)'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_ctl'],
        name="Condition (CTL)",
        line=dict(color='#3b82f6', width=3),
    ), row=1, col=1)

    # --- ETAGE 2 : FORME (TSB) AVEC ZONES ---
    df_clean['tsb_curve'] = df_clean['icu_ctl'] - df_clean['icu_atl']
    
    # Zones de fond pour le TSB (Intervals standard)
    fig.add_hrect(y0=-100, y1=-30, fillcolor="rgba(239, 68, 68, 0.15)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=-30, y1=-10, fillcolor="rgba(16, 185, 129, 0.2)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=-10, y1=5, fillcolor="rgba(156, 163, 175, 0.1)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=5, y1=100, fillcolor="rgba(59, 130, 246, 0.15)", line_width=0, row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['tsb_curve'],
        name="Forme (TSB)",
        line=dict(color='#ffffff', width=2),
        fill='tozeroy', fillcolor='rgba(255,255,255,0.05)'
    ), row=2, col=1)

    # --- MARQUEURS OBJECTIFS ---
    race_date_raw = prof.get('next_race_date') or prof.get('date_objectif')
    race_name = prof.get('next_race_name') or prof.get('nom_objectif') or "Course"

    if race_date_raw:
        try:
            target_date = pd.to_datetime(str(race_date_raw))
            fig.add_vline(
                x=target_date, 
                line_width=2, line_dash="dash", line_color="#ef4444",
                annotation_text=f"🚩 {race_name}",
                annotation_position="top right"
            )
        except:
            pass

    # --- DESIGN FINAL ---
    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_yaxes(title_text="CTL / ATL", row=1, col=1)
    fig.update_yaxes(title_text="TSB", row=2, col=1, range=[-50, 30])
    fig.update_xaxes(showgrid=False)

    st.plotly_chart(fig, use_container_width=True)

    # --- 3. SYNTHÈSE BETRAIL ---
    st.markdown("---")
    st.subheader("🏆 Expérience & Palmarès (BeTrail)")

    # Correction : Utilisation du nom de champ correct
    raw_data = prof.get('betrail_raw_data') or prof.get('betrail_paste')
    if raw_data:
        from core.data import parse_betrail_paste
        courses = parse_betrail_paste(raw_data)
        
        if courses:
            race_df = pd.DataFrame(courses)
            st.dataframe(
                race_df, 
                use_container_width=True, hide_index=True,
                column_config={
                    "Perf": st.column_config.ProgressColumn("Efficacité", min_value=0, max_value=100, format="%d%%")
                }
            )
        else:
            st.warning("⚠️ Impossible d'analyser le texte BeTrail. Vérifiez le format du copier-coller.")
    else:
        st.info("💡 Pour voir ton palmarès, copie-colle tes courses depuis BeTrail dans l'onglet Profil.")

    # --- 4. DIAGNOSTIC IA ---
    st.markdown("---")
    # Correction : On passe le DF complet
    feedback = get_ia_coaching_feedback(df_clean)
    st.info(f"✨ **Analyse de l'IA :** {feedback}")

if __name__ == "__main__":
    pass
