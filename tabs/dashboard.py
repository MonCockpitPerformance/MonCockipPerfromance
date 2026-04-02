import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render(df):
    """
    Rendu du tableau de bord avec protections contre les données manquantes
    ou mal formatées provenant de Firebase/Cloud.
    """
    st.title("📊 Cockpit de Performance")

    # --- 1. SÉCURITÉ : Vérification si le DataFrame est exploitable ---
    if df is None or df.empty:
        st.warning("⚠️ Aucune donnée disponible pour le moment.")
        st.info("Vérifiez que vos saisies sont bien enregistrées dans la base de données.")
        return

    # --- 2. PRÉPARATION DES DONNÉES (Nettoyage) ---
    try:
        # Conversion de la colonne Date (essentiel pour les graphiques temporels)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
        else:
            st.error("La colonne 'Date' est manquante dans les données.")
            return

        # Conversion forcée en numérique pour éviter les erreurs de calcul (NaN si erreur)
        cols_numeriques = ['CA', 'Prestations', 'Depenses', 'Objectif']
        for col in cols_numeriques:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                # Création d'une colonne de zéros si elle manque pour ne pas faire planter l'app
                df[col] = 0.0

    except Exception as e:
        st.error(f"Erreur lors de la préparation des données : {e}")
        return

    # --- 3. INDICATEURS CLÉS (KPIs) ---
    st.subheader("Indicateurs Clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_ca = df['CA'].sum()
    total_prestations = df['Prestations'].sum()
    total_depenses = df['Depenses'].sum()
    panier_moyen = total_ca / total_prestations if total_prestations > 0 else 0

    with col1:
        st.metric("Chiffre d'Affaires", f"{total_ca:,.2f} €")
    with col2:
        st.metric("Total Prestations", int(total_prestations))
    with col3:
        st.metric("Dépenses", f"{total_depenses:,.2f} €")
    with col4:
        st.metric("Panier Moyen", f"{panier_moyen:,.2f} €")

    st.divider()

    # --- 4. GRAPHIQUES ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("### Évolution du CA")
        fig_ca = px.line(df, x='Date', y='CA', markers=True, 
                         title="CA au fil du temps",
                         line_shape="spline",
                         color_discrete_sequence=["#00CC96"])
        st.plotly_chart(fig_ca, use_container_width=True)

    with col_right:
        st.write("### Répartition Dépenses vs CA")
        fig_pie = go.Figure(data=[go.Pie(labels=['CA Net', 'Dépenses'], 
                                         values=[total_ca - total_depenses, total_depenses],
                                         hole=.3)])
        fig_pie.update_layout(title_text="Structure financière")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- 5. PERFORMANCE VS OBJECTIFS ---
    if 'Objectif' in df.columns and df['Objectif'].sum() > 0:
        st.write("### Atteinte des Objectifs")
        obj_total = df['Objectif'].sum()
        progression = (total_ca / obj_total) * 100
        
        st.progress(min(progression / 100, 1.0))
        st.write(f"Objectif : {obj_total:,.2f} € | Réalisé : {progression:.1f}%")

    # --- 6. TABLEAU DE DÉTAIL ---
    with st.expander("Voir le détail des données brutes"):
        st.dataframe(df, use_container_width=True)
