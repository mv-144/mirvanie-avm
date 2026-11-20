import streamlit as st
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Mirvanie AVM", page_icon="🏠", layout="wide")
st.title("🏠 Mirvanie - Algorithme d'Estimation (AVM)")
st.write("Renseignez les caractéristiques du bien pour obtenir une estimation basée sur les micro-zones de Côte d'Ivoire.")

# Chargement de la grille de prix
@st.cache_data
def load_zones():
    try:
        df = pd.read_excel('mirvanie_grille_complete.xlsx', sheet_name='Zones')
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

df_zones = load_zones()

if not df_zones.empty:
    # --- FORMULAIRE DE SAISIE ---
    with st.form("estimation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📍 Localisation & Type")
            communes = sorted(df_zones['localisation'].unique())
            loc_choisie = st.selectbox("Adresse (Micro-zone) :", communes)
            
            types_dispo = sorted(df_zones[df_zones['localisation'] == loc_choisie]['type_bien'].unique())
            type_choisi = st.selectbox("Type de bien :", types_dispo)
            
            surface = st.number_input("Surface (m²) :", min_value=10, max_value=10000, value=100, step=10)
            
            st.subheader("🛠️ Configuration")
            nb_pieces = st.number_input("Nombre de pièces :", min_value=0, max_value=50, value=3)
            nb_chambres = st.number_input("Nombre de chambres :", min_value=0, max_value=20, value=2)
            nb_sdb = st.number_input("Nombre de salles de bain :", min_value=0, max_value=10, value=1)
            etage = st.number_input("Étage (0 si villa/maison) :", min_value=0, max_value=50, value=0)

        with col2:
            st.subheader("📅 État & Équipements")
            annee_construction = st.number_input("Année de construction :", min_value=1900, max_value=2026, value=2015)
            etat_bien = st.selectbox("État du bien :", ["Neuf", "Bon état", "À rénover"])
            
            cour_jardin = st.checkbox("Possède une cour / un jardin")
            stationnement = st.number_input("Nombre de places de stationnement :", min_value=0, max_value=10, value=1)
            
            equipements = st.multiselect("Équipements supplémentaires :", 
                                         ["Piscine", "Climatisation", "Ascenseur", "Groupe électrogène", "Cuisine équipée", "Sécurité 24h/24"])
            
            document_foncier = st.selectbox("Document foncier :", 
                                            ["Titre Foncier / ACD", "Lettre d'attribution", "Non renseigné"])

        # Bouton de soumission
        submit = st.form_submit_button("💰 Calculer l'estimation", use_container_width=True)

    # --- ALGORITHME D'ESTIMATION ---
    if submit:
        # 1. Récupération du prix de base au m²
        resultat_zone = df_zones[(df_zones['localisation'] == loc_choisie) & (df_zones['type_bien'] == type_choisi)]
        
        if not resultat_zone.empty:
            prix_min_m2 = resultat_zone.iloc[0]['prix_min_m2']
            prix_max_m2 = resultat_zone.iloc[0]['prix_max_m2']
            prix_median_m2 = (prix_min_m2 + prix_max_m2) / 2
            
            # Prix de base
            prix_base = prix_median_m2 * surface
            
            # 2. Application des coefficients (Modificateurs)
            coefficients = {}
            
            # Document foncier
            if document_foncier == "Titre Foncier / ACD":
                coefficients["Document Foncier (Sécurisé)"] = 0.10
            elif document_foncier == "Lettre d'attribution":
                coefficients["Document Foncier (Risque)"] = -0.05
            else:
                coefficients["Document Foncier (Non renseigné)"] = -0.10
                
            # État du bien
            if etat_bien == "Neuf":
                coefficients["État (Neuf)"] = 0.15
            elif etat_bien == "À rénover":
                coefficients["État (À rénover)"] = -0.20
                
            # Équipements
            if "Piscine" in equipements:
                coefficients["Piscine"] = 0.10
            bonus_equip = 0
            for eq in ["Climatisation", "Ascenseur", "Cuisine équipée"]:
                if eq in equipements:
                    bonus_equip += 0.05
            if bonus_equip > 0:
                coefficients["Équipements de confort"] = min(bonus_equip, 0.15) # Plafonné à 15%
                
            # Stationnement
            if stationnement > 0:
                coefficients["Stationnement"] = min(stationnement * 0.03, 0.09)
                
            # Cour / Jardin
            if cour_jardin:
                coefficients["Cour / Jardin"] = 0.05
                
            # Étage (si appartement)
            if type_choisi == "Appartement":
                if etage == 0:
                    coefficients["Rez-de-chaussée"] = 0.02
                elif etage > 3 and "Ascenseur" not in equipements:
                    coefficients["Étage élevé sans ascenseur"] = -0.05

            # 3. Calcul du prix final
            total_coefficients = sum(coefficients.values())
            prix_final = prix_base * (1 + total_coefficients)
            
            # 4. Affichage des résultats
            st.success("### 📊 Résultat de l'estimation Mirvanie")
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric(label="Prix de base (Zone)", value=f"{prix_base:,.0f} FCFA")
                st.metric(label="Impact des caractéristiques", value=f"{total_coefficients * 100:+.1f} %")
            with col_res2:
                st.metric(label="Estimation Finale", value=f"{prix_final:,.0f} FCFA", delta=f"{(prix_final - prix_base):,.0f} FCFA")
            
            # Fourchette de confiance (±10%)
            st.info(f"📉 **Fourchette basse (-10%)** : {prix_final * 0.90:,.0f} FCFA  |  📈 **Fourchette haute (+10%)** : {prix_final * 1.10:,.0f} FCFA")
            
            # Détail des coefficients (Transparence = Confiance)
            with st.expander("🔍 Voir le détail du calcul (Transparence)"):
                st.write("Voici comment votre bien se situe par rapport au prix médian de la zone :")
                for k, v in coefficients.items():
                    if v > 0:
                        st.write(f"- {k} : **+{v*100}%**")
                    elif v < 0:
                        st.write(f"- {k} : **{v*100}%**")
                
                st.write(f"**Calcul :** {prix_median_m2:,.0f} FCFA/m² (médiane zone) × {surface} m² = {prix_base:,.0f} FCFA")
                st.write(f"**Ajustement total :** {total_coefficients * 100:+.1f} %")