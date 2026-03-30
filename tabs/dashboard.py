import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# --- CONFIGURATION DES CHEMINS ---
# On s'assure que le dossier 'core' est accessible peu importe d'où est lancé le script
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS DEPUIS CORE ---
try:
    from core.data import load_profile, parse_betrail_paste
    from core.logic import get_ia_coaching_feedback, get_coaching_strategy
except ImportError as e:
    st.error(f"❌ Erreur critique d'importation : {e}")
    st.stop()

# Import du rendu UI personnalisé (Jauge/Metric avancée)
try:
    from core.ui import render_sport_metric
except ImportError:
    render_sport_metric = None

def render(df):
    """
    Rendu principal du Dashboard.
    df: DataFrame provenant de l'API Intervals.icu
    """
    # --- 1. CONTEXTE ET AUTHENTIFICATION ---
    user_id = st.session_state.get('uid') or "athlete_default"
    prof = load_profile(user_id)
    
    st.title("🚀 Cockpit Performance")

    # --- 2. TRAITEMENT DES DONNÉES ---
    if df is None or df.empty:
        st.info("📊 En attente de synchronisation avec Intervals.icu...")
        st.caption("Vérifiez vos identifiants (ID et Clé API) dans l'onglet Profil.")
        return

    # Nettoyage et préparation temporelle
    df_clean = df.copy()
    
    # Gestion de la colonne date (Intervals utilise souvent 'start_date_local')
    date_col = 'start_date_local' if 'start_date_local' in df_clean.columns else 'date'
    if date_col in df_clean.columns:
        df_clean['date'] = pd.to_datetime(df_clean[date_col])
    else:
        st.error("Format de données inconnu (colonne date manquante).")
        return

    # Assurer la présence des colonnes de performance
    # icu_ctl = Fitness, icu_atl = Fatigue, icu_training_load = TSS
    mapping = {
        'icu_ctl': 'Fitness',
        'icu_atl': 'Fatigue',
        'icu_training_load': 'Charge'
    }
    for col in mapping.keys():
        if col not in df_clean.columns:
            df_clean[col] = 0
            
    df_clean = df_clean.fillna(0).sort_values('date')
    
    # Extraction des métriques actuelles (Dernière ligne)
    last_row = df_clean.iloc[-1]
    ctl = float(last_row.get('icu_ctl', 0))
    atl = float(last_row.get('icu_atl', 0))
    tsb = ctl - atl # Forme
    
    # Calcul des tendances TSS (Volume)
    # Somme des 7 derniers jours vs 7 jours précédents
    recent_tss = df_clean['icu_training_load'].tail(7).sum()
    prev_tss = df_clean['icu_training_load'].iloc[-14:-7].sum()
    delta_tss = int(recent_tss - prev_tss)

    # --- 3. SECTION COACHING & STRATÉGIE ---
    current_metrics = {'ctl': ctl, 'atl': atl, 'tsb': tsb}
    strat_data = get_coaching_strategy(current_metrics)
    
    # Bannière d'état dynamique
    st.markdown(f"""
    <div style="background: {strat_data.get('color', '#334155')}22; padding: 18px; border-radius: 12px; border-left: 6px solid {strat_data.get('color', '#334155')}; margin-bottom: 25px;">
        <h3 style="margin:0; color:{strat_data.get('color', '#ffffff')}; font-size: 1.2rem; display: flex; align-items: center;">
            <span style="margin-right:10px;">🎯</span> {strat_data.get('status', 'Analyse en cours')}
        </h3>
        <p style="margin:8px 0 0 0; color: #e2e8f0; font-size: 1rem; line-height: 1.4;">{strat_data.get('advice', 'Continuez vos efforts.')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Affichage des KPIs
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
        # Couleur dynamique pour le TSB (Forme)
        # Optimal entre -10 et -30 pour progresser
        tsb_color = "#10b981" if -30 <= tsb <= -10 else ("#ef4444" if tsb < -30 else "#3b82f6")
        if render_sport_metric: 
            render_sport_metric(int(tsb), "Forme (TSB)", tsb_color, -50, 50)
        else: 
            st.metric("Forme (TSB)", int(tsb))

    with col4:
        st.metric("Charge 7j", f"{int(recent_tss)}", f"{delta_tss:+d} vs S-1", 
                  delta_color="normal" if abs(delta_tss) < 100 else "inverse")
        st.caption("Volume total hebdomadaire")

    # --- 4. GRAPHIQUE PMC (Performance Management Chart) ---
    st.markdown("### 📈 Analyse de Charge & Volume")
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )

    # Zone optimale TSB (Sweet spot progression)
    fig.add_hrect(y0=-30, y1=-10, fillcolor="#10b981", opacity=0.1, line_width=0, row=1, col=1, annotation_text="Zone de progression")

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
        line=dict(color='#3b82f6', width=4),
    ), row=1, col=1)

    # Barres de charge (TSS) - Secondaire
    fig.add_trace(go.Bar(
        x=df_clean['date'], y=df_clean['icu_training_load'],
        name="Charge (TSS)",
        marker_color='rgba(255, 255, 255, 0.15)',
        marker_line_width=0
    ), row=1, col=1, secondary_y=True)

    # Courbe TSB (Balance)
    tsb_history = df_clean['icu_ctl'] - df_clean['icu_atl']
    fig.add_trace(go.Scatter(
        x=df_clean['date'], y=tsb_history,
        name="Forme (TSB)",
        line=dict(color='#f59e0b', width=2),
        fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.05)'
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_yaxes(title_text="CTL / ATL", row=1, col=1)
    fig.update_yaxes(title_text="TSS", secondary_y=True, row=1, col=1, showgrid=False)
    fig.update_yaxes(title_text="TSB", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # --- 5. ANALYSE IA & PALMARÈS ---
    st.markdown("---")
    col_ai, col_bt = st.columns([1.2, 0.8])

    with col_ai:
        st.subheader("🤖 Coach IA")
        # On passe le DataFrame pour l'analyse temporelle
        feedback = get_ia_coaching_feedback(df_clean)
        
        st.markdown(f"""
        <div style="background: #1e293b; padding: 22px; border-radius: 16px; border: 1px solid #334155;">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 1.5rem; margin-right: 12px;">🧠</span>
                <strong style="color: #60a5fa; font-size: 1.1rem;">Analyse du Coach :</strong>
            </div>
            <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; font-style: italic;">
                "{feedback}"
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💬 Poser une question au coach"):
            st.session_state.current_tab = "IA Chat" # Si vous avez un onglet dédié
            st.rerun()

    with col_bt:
        st.subheader("🏆 Palmarès BeTrail")
        # Extraction des données BeTrail stockées dans le profil
        raw_bt = prof.get('betrail_raw_data') or prof.get('betrail_paste')
        
        if raw_bt:
            races = parse_betrail_paste(raw_bt)
            if races:
                for r in races[:5]: # Top 5 courses
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.1);">
                        <div style="display:flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: #f1f5f9;">{r.get('nom', 'Course')}</span>
                            <span style="color: #f59e0b; font-weight: bold; font-family: monospace;">{r.get('performance', '-')}</span>
                        </div>
                        <div style="display:flex; justify-content: space-between; margin-top: 4px;">
                            <span style="color: #94a3b8; font-size: 0.85rem;">{r.get('date', '')}</span>
                            <span style="color: #60a5fa; font-size: 0.85rem;">{r.get('resultat', '')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Données BeTrail non reconnues. Copiez-collez le tableau complet depuis BeTrail.")
        else:
            st.info("ℹ️ Ajoutez vos résultats BeTrail dans l'onglet **Profil** pour voir votre palmarès ici.")

if __name__ == "__main__":
    # Pour test unitaire si nécessaire
    pass
