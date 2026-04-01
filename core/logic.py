import pandas as pd
import numpy as np
import requests
import time

def get_training_status(fitness_df):
    """Analyse l'état de forme actuel."""
    if fitness_df is None or (hasattr(fitness_df, 'empty') and fitness_df.empty):
        return {"ctl": 0, "tsb": 0, "status": "Données non disponibles"}
    try:
        last_row = fitness_df.iloc[-1]
        ctl = float(last_row.get('icu_ctl', 0))
        tsb = float(last_row.get('icu_tsb', 0))
        if tsb < -25: status = "🚨 Risque de Fatigue"
        elif tsb < -10: status = "🔥 Entraînement Intensif"
        elif tsb < 5: status = "📈 Phase Productive"
        elif tsb < 15: status = "✨ Affûtage / Frais"
        else: status = "💤 Désentraînement"
        return {"ctl": round(ctl, 1), "tsb": round(tsb, 1), "status": status}
    except:
        return {"ctl": 0, "tsb": 0, "status": "Erreur de calcul"}

def calculate_race_prediction(km, d_plus, betrail_index):
    """Prédit le temps de course."""
    idx = float(betrail_index or 50.0)
    effort_km = float(km) + (float(d_plus) / 100.0)
    ref_speed = (idx / 50.0) * 7.5
    time_h = effort_km / ref_speed if ref_speed > 0 else 0
    return {
        "hours": time_h, 
        "effort_km": round(effort_km, 1), 
        "speed_kmh": round(float(km)/time_h, 2) if time_h > 0 else 0
    }

def get_ai_response(user_query, athlete_context, system_prompt=None):
    """Appelle l'API Gemini (L'environnement injecte la clé)."""
    api_key = "" 
    model_name = "gemini-2.5-flash-preview-09-2025"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    if not system_prompt:
        system_prompt = "Tu es un coach expert en Trail Running."
    payload = {
        "contents": [{"parts": [{"text": f"Contexte: {athlete_context}\nQuestion: {user_query}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }
    for delay in [1, 2, 4]:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429: time.sleep(delay)
        except: time.sleep(delay)
    return "L'IA est indisponible."
