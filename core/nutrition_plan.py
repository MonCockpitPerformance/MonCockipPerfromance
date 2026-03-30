import streamlit as st
import pandas as pd
import os
from core.data import load_profile, save_profile
from core.race_plan import format_duration

def load_products_from_excel():
    """
    Charge le référentiel produit depuis Data/produits.xlsx.
    Structure attendue : Marque, Saveur, Type de produit, Portion en g, Type apport, Apport produit.
    """
    file_path = "Data/produits.xlsx"
    if os.path.exists(file_path):
        try:
            df = pd.read_excel(file_path)
            # Nettoyage des noms de colonnes
            df.columns = [c.strip() for c in df.columns]
            # Création d'un nom unique pour le sélecteur
            df['nom_complet'] = df['Marque'].astype(str) + " - " + df['Saveur'].astype(str)
            
            products = {}
            for name, group in df.groupby('nom_complet'):
                first_row = group.iloc[0]
                prod_data = {
                    "glucides": 0.0, "sel": 0.0, "proteines": 0.0, "calories": 0.0,
                    "type": str(first_row['Type de produit']).lower(),
                    "portion_g": float(first_row['Portion en g']) if 'Portion en g' in first_row else 1.0
                }
                # Extraction des différents apports
                for _, row in group.iterrows():
                    apport = str(row['Type apport']).lower()
                    val = row['Apport produit']
                    if 'glucides' in apport: prod_data["glucides"] = val
                    elif 'sel' in apport: prod_data["sel"] = val
                    elif 'prot' in apport: prod_data["proteines"] = val
                    elif 'cal' in apport: prod_data["calories"] = val
                products[name] = prod_data
            return products
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier produits Excel : {e}")
    return {}

def render_compact_row(label, current, target_per_h, duration_h, unit, key, coeff=1.0, min_v=0.0, max_v=500.0, step=1.0, is_water=False, flasques=0):
    """
    Rendu d'une ligne d'apport avec jauge dynamique et sélecteurs de cibles.
    """
    # Calcul de la cible totale sur la durée du segment
    final_target = (target_per_h * duration_h) * coeff
    
    # Calcul de la progression
    progress = min(1.0, current / final_target) if final_target > 0.01 else 0.0
    
    # Statut visuel
    status_color = "🟢" if current >= final_target * 0.95 else "⚠️"
    if current > final_target * 1.25: status_color = "🔵" # Surplus significatif

    st.markdown(f"**{label}**")
    col_inp, col_jauge, col_txt = st.columns([1.2, 2.5, 1.8])
    
    with col_inp:
        new_target_h = st.number_input(
            label=f"target_{key}",
            min_value=float(min_v),
            max_value=float(max_v),
            value=float(target_per_h),
            step=float(step),
            key=f"val_{key}",
            label_visibility="collapsed"
        )
        st.caption(f"{unit}/h")
    
    with col_jauge:
        st.write("") # Espacement pour aligner la barre
        st.progress(progress)
        if is_water:
            new_flasques = st.number_input("Flasques 500ml", 0, 10, int(flasques), key=f"fla_{key}")
        else:
            new_flasques = None
    
    with col_txt:
        st.markdown(f"{status_color} **{current:.2f}** /{final_target:.2f} {unit}")
        if is_water:
            st.caption(f"Volume total: {current:.1f}L")

    return new_target_h, new_flasques

def render():
    st.header("🍼 Plan de Nutrition & Hydratation")
    
    # 1. AUTH & PROFIL
    user_id = st.session_state.get("uid") or (st.session_state.get("user", {}).get("uid") if st.session_state.get("user") else None)
    if not user_id:
        st.warning("Veuillez vous connecter pour gérer votre nutrition.")
        return

    profile = load_profile(user_id)
    # On supporte l'ancienne et la nouvelle structure de stockage des plans
    race_plans = profile.get("race_plans", {})
    
    if not race_plans:
        st.info("Aucun plan de course (GPX) détecté. Créez d'abord un plan dans l'onglet 'Plan de Course'.")
        return

    # 2. SELECTION DE LA COURSE
    selected_plan_name = st.selectbox("Course ciblée", list(race_plans.keys()))
    race_data = race_plans[selected_plan_name]
    
    # 3. EXTRACTION DES RAVITOS
    checkpoints = sorted(race_data.get("checkpoints", []), key=lambda x: x['distance'])
    ravitos = [cp for cp in checkpoints if "Ravito" in cp.get('type', '')]
    
    if not ravitos:
        st.warning("Aucun point de type 'Ravito' n'a été défini dans votre Plan de Course.")
        return

    # 4. CHARGEMENT BASE PRODUITS
    product_db = load_products_from_excel()
    if not product_db:
        st.info("Le référentiel 'Data/produits.xlsx' est manquant. Seuls les calculs théoriques seront disponibles.")

    # Initialisation de la structure nutrition si inexistante
    if "nutrition" not in race_data:
        race_data["nutrition"] = {}
    
    prev_dist = 0.0
    shopping_list = {}

    # 5. BOUCLE SUR LES RAVITOS
    for i, ravito in enumerate(ravitos):
        cp_id = f"rav_{i}_{ravito['name'].replace(' ', '_')}"
        
        # Initialisation config par défaut pour ce ravito
        if cp_id not in race_data["nutrition"]:
            race_data["nutrition"][cp_id] = {
                "t_carbs_h": 60.0, 
                "t_salt_h": 0.5, 
                "t_cal_h": 250.0, 
                "t_water_h": 0.6, 
                "flasques": 2,
                "items": [], 
                "temp": 20
            }
        
        conf = race_data["nutrition"][cp_id]
        
        # Calcul de la durée du segment jusqu'à ce ravito
        dist_seg = ravito['distance'] - prev_dist
        base_pace = race_data.get("base_pace", 10.0)
        seg_fatigue = ravito.get('fatigue_coeff', 100) / 100.0
        dur_h = (dist_seg * base_pace * seg_fatigue) / 60.0

        # Coefficient de chaleur (ajustement théorique)
        heat_coeff = 1.0 + (max(0, conf.get("temp", 20) - 20) * 0.03) 
        
        # Calcul des totaux actuels via les produits sélectionnés
        items = conf.get("items", [])
        total_carbs = sum(it.get('glucides_total', 0) for it in items)
        total_salt = sum(it.get('sel_total', 0) for it in items)
        total_cal = sum(it.get('calories_total', 0) for it in items)
        
        # Calcul Eau : Flasques + Eau des boissons/poudres
        water_from_flasques = conf.get("flasques", 0) * 0.5
        water_from_products = 0.0
        for it in items:
            if it['nom'] in product_db:
                p_type = product_db[it['nom']]['type']
                if "boisson" in p_type or "poudre" in p_type:
                    water_from_products += (it['qty'] * product_db[it['nom']]['portion_g'] / 1000.0)
        
        total_water = water_from_flasques + water_from_products

        # Mise à jour Shopping List
        for it in items:
            shopping_list[it['nom']] = shopping_list.get(it['nom'], 0.0) + it['qty']

        # RENDU UI DU RAVITO
        exp_label = f"📍 {ravito['name']} (KM {ravito['distance']}) — Temps estimé : {format_duration(dur_h*60)}"
        with st.expander(exp_label, expanded=True):
            
            c_info, c_temp = st.columns([3, 1])
            with c_temp:
                new_temp = st.select_slider("🌡️ Température", [10, 15, 20, 25, 30, 35, 40], conf.get("temp", 20), key=f"t_{cp_id}")
                if new_temp != conf.get("temp"):
                    conf["temp"] = new_temp
                    save_profile(user_id, {"race_plans": race_plans})
                    st.rerun()
            
            with c_info:
                st.caption(f"Ajustement besoins : x{heat_coeff:.2f} | Segment : {dist_seg:.1f} km")

            changed = False
            
            # Lignes d'apports
            w_h, nb_f = render_compact_row(
                "💧 Eau (Litre)", total_water, conf.get("t_water_h", 0.6), dur_h, "L", f"w_{cp_id}", 
                coeff=heat_coeff, min_v=0.1, max_v=2.0, step=0.1, is_water=True, flasques=conf.get("flasques", 2)
            )
            if w_h != conf.get("t_water_h") or nb_f != conf.get("flasques"):
                conf["t_water_h"] = w_h
                conf["flasques"] = nb_f
                changed = True

            st.markdown("---")
            
            s_h, _ = render_compact_row("🧂 Sel (Gramme)", total_salt, conf.get("t_salt_h", 0.5), dur_h, "g", f"s_{cp_id}", coeff=heat_coeff, min_v=0, max_v=3, step=0.1)
            if s_h != conf.get("t_salt_h"):
                conf["t_salt_h"] = s_h
                changed = True
                
            c_h, _ = render_compact_row("🍞 Glucides (Gramme)", total_carbs, conf.get("t_carbs_h", 60), dur_h, "g", f"c_{cp_id}", min_v=0, max_v=120, step=5)
            if c_h != conf.get("t_carbs_h"):
                conf["t_carbs_h"] = c_h
                changed = True

            cal_h, _ = render_compact_row("🔥 Calories (Kcal)", total_cal, conf.get("t_cal_h", 250), dur_h, "kcal", f"cal_{cp_id}", min_v=0, max_v=600, step=10)
            if cal_h != conf.get("t_cal_h"):
                conf["t_cal_h"] = cal_h
                changed = True
            
            if changed:
                save_profile(user_id, {"race_plans": race_plans})
                st.rerun()

            # Gestion des produits
            st.markdown("#### 🛠️ Pack Nutrition")
            if product_db:
                ca, cb, cc = st.columns([3, 1, 1.5])
                with ca:
                    sel_p = st.selectbox("Ajouter un produit", list(product_db.keys()), key=f"sp_{cp_id}")
                with cb:
                    q = st.number_input("Qté", 0.5, 12.0, 1.0, 0.5, key=f"q_{cp_id}")
                with cc:
                    st.write("") 
                    if st.button("➕ Ajouter", key=f"btn_{cp_id}", use_container_width=True):
                        p = product_db[sel_p]
                        items.append({
                            "nom": sel_p, "qty": q,
                            "glucides_total": p["glucides"] * q, 
                            "sel_total": p["sel"] * q,
                            "calories_total": p["calories"] * q
                        })
                        save_profile(user_id, {"race_plans": race_plans})
                        st.rerun()

            if items:
                for idx, it in enumerate(items):
                    cx, cy = st.columns([5, 1])
                    cx.caption(f"• {it['nom']} (x{it['qty']})")
                    if cy.button("🗑️", key=f"del_{cp_id}_{idx}"):
                        items.pop(idx)
                        save_profile(user_id, {"race_plans": race_plans})
                        st.rerun()

        prev_dist = ravito['distance']

    # 6. RECAPITULATIF GLOBAL
    if shopping_list:
        st.divider()
        st.subheader("🛒 Liste de Courses (Total)")
        shop_df = pd.DataFrame([{"Produit": p, "Quantité Totale": q} for p, q in shopping_list.items()])
        st.table(shop_df)

if __name__ == "__main__":
    render()
