import streamlit as st
import google.generativeai as genai

def get_ai_response(prompt, profile, metrics, recent_activities, planned_sessions, betrail_history):
    """
    Envoie le contexte complet de l'athlète à Gemini et récupère son analyse.
    """
    # 1. Configuration de l'API (Clé stockée dans st.secrets)
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        return f"⚠️ Erreur de configuration de l'IA : {e}"

    # 2. Construction du "Cerveau" (Le Prompt Système)
    system_context = f"""
    Tu es un coach expert en Trail et Ultra-trail. 
    Ton athlète a un indice BeTrail de {profile.get('betrail_index', 'inconnu')}.
    Son objectif est : {profile.get('next_race_name', 'non défini')}.
    
    Données actuelles :
    - Forme (CTL) : {metrics.get('ctl', 0)}
    - Fatigue (ATL) : {metrics.get('atl', 0)}
    - État (TSB) : {metrics.get('tsb', 0)} (Positif = frais, Négatif = fatigué)
    
    Historique récent : {recent_activities[-3:] if recent_activities else 'Aucune donnée'}
    Séances prévues : {planned_sessions[:3] if planned_sessions else 'Rien de prévu'}
    
    Réponds de manière concise, technique mais motivante. Utilise des emojis sportifs.
    """

    # 3. Appel à Gemini
    try:
        full_prompt = f"{system_context}\n\nL'athlète demande : {prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"❌ Désolé, le coach IA est indisponible : {e}"

def get_ai_plan(profile, goal_date):
    """Fonction optionnelle pour générer un bloc d'entraînement complet."""
    # (Tu pourras l'étoffer plus tard)
    return "Planification en cours de développement..."
```

---

### 🗝️ Important : La Clé API
Pour que ce fichier fonctionne, tu dois avoir une clé API Google (gratuite).
1. Va sur [Google AI Studio](https://aistudio.google.com/).
2. Récupère ta clé.
3. Dans ton dossier de projet, crée (ou ouvre) le fichier `.streamlit/secrets.toml` et ajoute :
   ```toml
   GOOGLE_API_KEY = "TA_CLE_ICI"
