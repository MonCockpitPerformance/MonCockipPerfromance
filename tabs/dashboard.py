import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# --- CONFIGURATION DES CHEMINS (CRITIQUE POUR STREAMLIT CLOUD) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS DEPUIS CORE ---
try:
    from core.data import (
        load_profile, 
        get_ia_coaching_feedback, 
        get_coaching_strategy,
        parse_betrail_paste
    )
except ImportError as e:
    st.error(f"❌ Erreur d'importation des modules : {e}")
    st.stop()

# Import du rendu UI personnalisé
try:
    from core.ui import render_sport_metric
except ImportError:
    render_sport_metric = None

def render(df):
    # --- 1. CONTEXTE ET AUTHENTIFICATION ---
    user_id = st.session_state.get('uid') or (st.session_state.get('user', {}).get('uid') if st.session_state.get('user') else "athlete_default")
    
    prof = load_profile(user_id)
    st.title("🚀 Cockpit Performance")

    # --- 2. TRAITEMENT DES DONNÉES INTERVALS.ICU ---
    if df is None or df.empty:
        st.info("📊 En attente de synchronisation Intervals.icu...")
        st.caption("Vérifiez vos identifiants dans l'onglet Profil.")
        return

    # Nettoyage et préparation temporelle
    df_clean = df.copy()
    if 'date' not in df_clean.columns and 'start_date_local' in df_clean.columns:
        df_clean['date'] = pd.to_datetime(df_clean['start_date_local'])
    
    # On s'assure que les colonnes nécessaires existent, sinon on initialise à 0
    for col in ['icu_ctl', 'icu_atl', 'icu_training_load']:
        if col not in df_clean.columns:
            df_clean[col] = 0
            
    df_clean = df_clean.fillna(0).sort_values('date')
    
    # Extraction des métriques clés (dernière ligne de données)
    last_row = df_clean.iloc[-1]
    ctl = int(last_row.get('icu_ctl', 0))
    atl = int(last_row.get('icu_atl', 0))
    tsb = int(ctl - atl)
    
    # Calcul des tendances sur 7 jours
    recent_tss = df_clean['icu_training_load'].tail(7).sum()
    prev_tss = df_clean['icu_training_load'].iloc[-14:-7].sum()
    delta_tss = int(recent_tss - prev_tss)

    # --- 3. SECTION COACHING & STRATÉGIE ---
    strat_label = get_coaching_strategy(df_clean)
    strat_color = "#10b981" if "Optimal" in strat_label else ("#f59e0b" if "Surcharge" in strat_label else "#3b82f6")
    
    st.markdown(f"""
    <div style="background: {strat_color}22; padding: 15px; border-radius: 10px; border-left: 5px solid {strat_color}; margin-bottom: 20px;">
        <h4 style="margin:0; color:{strat_color};">🎯 Focus actuel : {strat_label}</h4>
    </div>
    """, unsafe_allow_html=True)

    # Affichage des KPIs via métriques circulaires (si disponibles) ou standards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if render_sport_metric: 
            render_sport_metric(ctl, "Condition (CTL)", "#3b82f6", 0, 150)
        else: 
            st.metric("CTL", ctl)
        
    with col2:
        if render_sport_metric: 
            render_sport_metric(atl, "Fatigue (ATL)", "#a855f7", 0, 180)
        else: 
            st.metric("ATL", atl)
        
    with col3:
        tsb_color = "#10b981" if -30 <= tsb <= -10 else ("#ef4444" if tsb < -30 else "#3b82f6")
        if render_sport_metric: 
            render_sport_metric(tsb, "Forme (TSB)", tsb_color, -50, 50)
        else: 
            st.metric("TSB", tsb)

    with col4:
        st.metric("Charge 7j", f"{int(recent_tss)}", f"{delta_tss:+d} TSS", delta_color="normal")
        st.caption("Tendance vs S-1")

    # --- 4. GRAPHIQUE DE PERFORMANCE (PMC) ---
    st.markdown("### 📈 Analyse de Charge & Volume")
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    # Zone optimale de TSB (Freshness)
    fig.add_hrect(y0=-30, y1=-10, fillcolor="#10b981", opacity=0.1, line_width=0, row=1, col=1)

    # Trace ATL (Fatigue)
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_atl'],
        name="Fatigue (ATL)",
        line=dict(color='#a855f7', width=1),
        fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.05)'
    ), row=1, col=1)

    # Trace CTL (Condition)
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_ctl'],
        name="Condition (CTL)",
        line=dict(color='#3b82f6', width=3),
    ), row=1, col=1)

    # Trace TSS (Bars)
    fig.add_trace(go.Bar(
        x=df_clean['date'], y=df_clean['icu_training_load'],
        name="Charge (TSS)",
        marker_color='rgba(255, 255, 255, 0.2)',
        marker_line_width=0
    ), row=1, col=1, secondary_y=True)

    # Trace TSB (Balance)
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_ctl'] - df_clean['icu_atl'],
        name="Forme (TSB)",
        line=dict(color='#ffffff', width=2),
        fill='tozeroy', fillcolor='rgba(255, 255, 255, 0.05)'
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. ANALYSE IA & PALMARÈS ---
    st.markdown("---")
    col_ai, col_bt = st.columns([1.2, 0.8])

    with col_ai:
        st.subheader("🤖 Coach IA Ultra")
        feedback = get_ia_coaching_feedback(df_clean)
        st.markdown(f"""
        <div style="background: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #334155;">
            <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">{feedback}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_bt:
        st.subheader("🏆 BeTrail")
        raw_bt = prof.get('betrail_raw_data') or prof.get('betrail_paste')
        if raw_bt:
            races = parse_betrail_paste(raw_bt)
            if races:
                for r in races:
                    st.markdown(f"**{r['date']}** - {r['nom']}")
                    st.caption(f"🏁 {r['resultat']} | 📈 Perf: {r['performance']}")
            else:
                st.info("Format BeTrail non reconnu.")
        else:
            st.info("Collez vos données BeTrail dans l'onglet Profil pour voir votre palmarès ici.")

if __name__ == "__main__":
    pass
