import streamlit as st
import pandas as pd  # L'alias 'pd' est défini ici
import plotly.express as px

# Configuration de la page pour le test
st.set_page_config(page_title="Debug Import", layout="wide")

st.title("🛠 Test de Diagnostic des Modules")

try:
    # Test d'importation et utilisation de pandas
    data = {'Test': [1, 2, 3], 'Valeurs': [10, 20, 30]}
    df = pd.DataFrame(data)
    st.success("✅ Pandas est correctement importé sous l'alias 'pd' !")
    st.write("Aperçu des données de test :")
    st.dataframe(df)
    
    # Test de Plotly
    fig = px.bar(df, x='Test', y='Valeurs', title="Test Graphique")
    st.plotly_chart(fig)

except Exception as e:
    st.error(f"❌ Erreur détectée : {e}")
    st.info("Conseil : Vérifiez que 'pandas' est bien écrit dans votre fichier requirements.txt")

st.divider()
st.subheader("Structure des dossiers détectée")
import os
st.code(f"Répertoire courant : {os.getcwd()}\nContenu : {os.listdir('.')}")
