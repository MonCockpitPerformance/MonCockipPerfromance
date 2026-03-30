import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

# --- IMPORTS CORE ---
# On assume que la logique métier est déportée pour garder le dashboard lisible
try:
    from core.logic import get_ia_coaching_feedback, get_coaching_strategy, parse_betrail_paste
    from core.ui import render_sport_metric
except ImportError:
    render_sport_metric = None

def render(df, prof):
    """
    Rendu optimisé du Cockpit Performance.
    df: Données Intervals.icu (Fitness, Fatigue, Charge)
    prof: Profil utilisateur avec les données BeTrail
    """
    st.title("🚀 Cockpit Performance")

    if df is None or df.empty:
        st.warning("⚠️ Aucune donnée disponible. Connectez votre API Intervals.icu dans le profil.")
        return

    # --- PRÉPARATION DES DONNÉES ---
    df_plot = df.copy()
    date_col = 'start_date_local' if 'start_date_local' in df_plot.columns else 'date'
    df_plot['date'] = pd.to_datetime(df_plot[date_col])
    df_plot = df_plot.sort_values('date')

    # Métriques instantanées
    last = df_plot.iloc[-1]
    metrics = {
        'ctl': int(last.get('icu_ctl', 0)),
        'atl': int(last.get('icu_atl', 0)),
        'tsb': int(last.get('icu_ctl', 0) - last.get('icu_atl', 0)),
        'tss_7d': int(df_plot['icu_training_load'].tail(7).sum()),
        'prev_tss': int(df_plot['icu_training_load'].iloc[-14:-7].sum())
    }

    # --- BANNIÈRE STRATÉGIQUE ---
    strat = get_coaching_strategy(metrics)
    st.markdown(f"""
        <div style="background:{strat['color']}22; border-left:5px solid {strat['color']}; padding:15px; border-radius:10px; margin-bottom:20px;">
            <h4 style="margin:0; color:{strat['color']};">🎯 {strat['status']}</h4>
            <p style="margin:5px 0 0 0; font-size:0.9rem; color:#e2e8f0;">{strat['advice']}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if render_sport_metric: render_sport_metric(metrics['ctl'], "Fitness (CTL)", "#3b82f6", 0, 150)
        else: st.metric("Fitness (CTL)", metrics['ctl'])
    with col2:
        if render_sport_metric: render_sport_metric(metrics['atl'], "Fatigue (ATL)", "#a855f7", 0, 180)
        else: st.metric("Fatigue (ATL)", metrics['atl'])
    with col3:
        tsb_color = "#10b981" if -30 <= metrics['tsb'] <= -10 else "#ef4444"
        if render_sport_metric: render_sport_metric(metrics['tsb'], "Forme (TSB)", tsb_color, -50, 50)
        else: st.metric("Forme (TSB)", metrics['tsb'])
    with col4:
        diff = metrics['tss_7d'] - metrics['prev_tss']
        st.metric("Charge 7j", metrics['tss_7d'], f"{diff:+d}", delta_color="normal" if abs(diff) < 100 else "inverse")

    # --- PMC CHART ---
    st.subheader("📈 Performance Management Chart")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    
    # Fitness & Fatigue
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['icu_atl'], name="ATL", line=dict(color='#a855f7', width=1), fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.1)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['icu_ctl'], name="CTL", line=dict(color='#3b82f6', width=3)), row=1, col=1)
    fig.add_trace(go.Bar(x=df_plot['date'], y=df_plot['icu_training_load'], name="TSS", marker_color='rgba(255,255,255,0.1)'), row=1, col=1, secondary_y=True)
    
    # Forme (TSB)
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['icu_ctl']-df_plot['icu_atl'], name="TSB", line=dict(color='#f59e0b', width=2), fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.05)'), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=0, b=0), legend=dict(orientation="h", y=1.1), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # --- FOOTER : IA & BETRAIL ---
    st.divider()
    c1, c2 = st.columns([1.2, 0.8])
    
    with c1:
        st.subheader("🤖 Coach IA")
        st.info(get_ia_coaching_feedback(df_plot))
        if st.button("💬 Ouvrir le Chat"): st.toast("Arrive bientôt !")

    with c2:
        st.subheader("🏆 BeTrail")
        raw_bt = prof.get('betrail_raw_data') or prof.get('betrail_paste')
        if raw_bt:
            for r in parse_betrail_paste(raw_bt)[:4]:
                st.markdown(f"""
                    <div style="background:#1e293b; padding:8px 12px; border-radius:8px; margin-bottom:6px; border:1px solid #334155;">
                        <div style="display:flex; justify-content:space-between;"><b>{r['nom']}</b> <span style="color:#f59e0b;">{r['performance']}</span></div>
                        <small style="color:#94a3b8;">{r['date']} • {r['resultat']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Configurez BeTrail dans l'onglet Profil.")
