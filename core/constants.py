# --- CONFIGURATION GÉNÉRALE ---
APP_NAME = "Gemini Trail Coach"
VERSION = "2.5.0-EXPERT"

# --- ZONES DE FORME (TSB) ---
TSB_ZONES = {
    "RISQUE": {"min": -999, "max": -30, "color": "#ef4444", "label": "🔥 Risque de blessure / Surentraînement"},
    "OPTIMAL": {"min": -30, "max": -10, "color": "#10b981", "label": "🚀 Zone de progression optimale"},
    "NEUTRE": {"min": -10, "max": 5, "color": "#9ca3af", "label": "⚖️ Maintien / Transition"},
    "FRAIS": {"min": 5, "max": 100, "color": "#3b82f6", "label": "🌊 Zone d'affûtage / Fraîcheur"}
}

# --- MESSAGES COACHING IA ---
COACH_PROMPTS = {
    "system_instruction": """
    Tu es un coach expert en Trail Running et Ultra-Trail. 
    Tu analyses les données de charge (CTL, ATL, TSB) et les performances BeTrail.
    Ton ton est motivant, technique et précis. 
    Tu dois toujours privilégier la santé de l'athlète et la progressivité.
    """,
    "strategy_recovery": "Ton corps a besoin de repos. Priorise le sommeil et une séance très légère en Zone 1.",
    "strategy_build": "C'est le moment de charger. Ajoute du dénivelé ou une séance de fractionné en côte.",
    "strategy_taper": "L'objectif approche. Réduis le volume de 40% mais garde un peu d'intensité courte."
}

# --- MAPPING SPORTS ---
SPORTS_MAP = {
    "Run": "Course à pied",
    "TrailRun": "Trail",
    "Ride": "Cyclisme",
    "VirtualRide": "Home Trainer",
    "Swim": "Natation",
    "WeightTraining": "Renforcement"
}
