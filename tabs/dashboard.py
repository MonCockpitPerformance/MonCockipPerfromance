import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# --- CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS DEPUIS CORE ---
try:
    from core.data import load_profile, parse_betrail_paste
    from core.logic import get_ia_coaching_feedback, get_coaching_strategy
except ImportError as e:
    st.error(f"❌ Erreur d'importation des modules core : {e}")
    st.stop()

# Import du rendu UI personnalisé (si disponible)
try:
    from core.ui import render_sport_metric
except ImportError:
    render_sport_metric = None

def render(df):
    # --- 1. CONTEXTE ET AUTHENTIFICATION ---
    user_id = st.session_state.get('uid') or "athlete_default"
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
    
    # Assurer la présence des colonnes critiques
    cols_required = {
        'icu_ctl': 'Condition',
        'icu_atl': 'Fatigue',
        'icu_training_load': 'Charge'
    }
    for col in cols_required:
        if col not in df_clean.columns:
            df_clean[col] = 0
            
    df_clean = df_clean.fillna(0).sort_values('date')
    
    # Extraction des métriques actuelles (Dernière ligne)
    last_row = df_clean.iloc[-1]
    ctl = float(last_row.get('icu_ctl', 0))
    atl = float(last_row.get('icu_atl', 0))
    tsb = ctl - atl
    
    # Calcul des tendances TSS (7j vs 7j précédents)
    recent_tss = df_clean['icu_training_load'].tail(7).sum()
    prev_tss = df_clean['icu_training_load'].iloc[-14:-7].sum()
    delta_tss = int(recent_tss - prev_tss)

    # --- 3. SECTION COACHING & STRATÉGIE ---
    current_metrics = {'ctl': ctl, 'atl': atl, 'tsb': tsb}
    # Récupération de l'objet stratégie depuis logic.py
    strat_data = get_coaching_strategy(current_metrics)
    
    st.markdown(f"""
    <div style="background: {strat_data['color']}22; padding: 18px; border-radius: 12px; border-left: 6px solid {strat_data['color']}; margin-bottom: 25px;">
        <h3 style="margin:0; color:{strat_data['color']}; font-size: 1.2rem;">{strat_data['status']}</h3>
        <p style="margin:5px 0 0 0; color: #e2e8f0; font-size: 1rem;">{strat_data['advice']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Affichage des KPIs (Metrics)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if render_sport_metric: 
            render_sport_metric(int(ctl), "Condition (CTL)", "#3b82f6", 0, 150)
        else: 
            st.metric("Condition (CTL)", int(ctl))
        
    with col2:
        if render_sport_metric: 
            render_sport_metric(int(atl), "Fatigue (ATL)", "#a855f7", 0, 180)
        else: 
            st.metric("Fatigue (ATL)", int(atl))
        
    with col3:
        # Couleur dynamique pour le TSB
        tsb_color = "#10b981" if -30 <= tsb <= -10 else ("#ef4444" if tsb < -30 else "#3b82f6")
        if render_sport_metric: 
            render_sport_metric(int(tsb), "Forme (TSB)", tsb_color, -50, 50)
        else: 
            st.metric("Forme (TSB)", int(tsb), delta=None)

    with col4:
        st.metric("Charge 7j", f"{int(recent_tss)}", f"{delta_tss:+d} TSS", delta_color="normal")
        st.caption("Volume vs S-1")

    # --- 4. GRAPHIQUE PMC (Performance Management Chart) ---
    st.markdown("### 📈 Analyse de Charge & Volume")
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    # Zone optimale de progression TSB (Fond vert léger)
    fig.add_hrect(y0=-30, y1=-10, fillcolor="#10b981", opacity=0.08, line_width=0, row=1, col=1)

    # Courbe ATL (Fatigue) - Violet
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_atl'],
        name="Fatigue (ATL)",
        line=dict(color='#a855f7', width=1.5),
        fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.05)'
    ), row=1, col=1)

    # Courbe CTL (Condition) - Bleu
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=df_clean['icu_ctl'],
        name="Condition (CTL)",
        line=dict(color='#3b82f6', width=3.5),
    ), row=1, col=1)

    # Barres de charge (TSS) - Gris transparent
    fig.add_trace(go.Bar(
        x=df_clean['date'], y=df_clean['icu_training_load'],
        name="Charge (TSS)",
        marker_color='rgba(200, 200, 200, 0.2)',
        marker_line_width=0
    ), row=1, col=1, secondary_y=True)

    # Courbe TSB (Balance de forme) - Pointillés blancs
    tsb_history = df_clean['icu_ctl'] - df_clean['icu_atl']
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=tsb_history,
        name="Forme (TSB)",
        line=dict(color='rgba(255, 255, 255, 0.6)', width=1.5, dash='dot'),
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        yaxis2=dict(showgrid=False)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. ANALYSE IA & PALMARÈS ---
    st.markdown("---")
    col_ai, col_bt = st.columns([1.3, 0.7])

    with col_ai:
        st.subheader("🤖 Coach IA Ultra")
        # On passe le DataFrame complet pour l'analyse de tendance
        feedback = get_ia_coaching_feedback(df_clean)
        
        st.markdown(f"""
        <div style="background: #1e293b; padding: 22px; border-radius: 16px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 1.5rem; margin-right: 10px;">🧠</span>
                <strong style="color: #60a5fa;">Analyse du Coach :</strong>
            </div>
            <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; font-style: italic;">"{feedback}"</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Optionnel : Bouton pour poser une question spécifique
        if st.button("💬 Demander un conseil personnalisé"):
            st.info("Le mode Chat sera disponible dès que vous aurez configuré votre clé API.")

    with col_bt:
        st.subheader("🏆 Palmarès BeTrail")
        # On cherche les données BeTrail
        raw_bt = prof.get('betrail_raw_data') or prof.get('betrail_paste')
        if raw_bt:
            races = parse_betrail_paste(raw_bt)
            if races:
                for r in races[:4]: # Top 4
                    with st.container():
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.1);">
                            <div style="display:flex; justify-content: space-between;">
                                <strong>{r['nom']}</strong>
                                <span style="color: #f59e0b;">{r['performance']}</span>
                            </div>
                            <small style="color: #94a3b8;">{r['date']} • {r['resultat']}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Données BeTrail non reconnues.")
        else:
            st.info("Collez vos données BeTrail dans le profil.")

if __name__ == "__main__":
    pass
