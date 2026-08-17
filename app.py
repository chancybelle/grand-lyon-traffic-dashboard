import streamlit as st
import pandas as pd
from pymongo import MongoClient
import folium
import json
import streamlit.components.v1 as components
import plotly.graph_objects as go

# ============================================================================
# 1. CONFIGURATION DE LA PAGE & AUTO-REFRESH (60 SECONDES)
# ============================================================================
st.set_page_config(
    page_title="Dashboard Trafic Lyon",
    page_icon="🚗",
    layout="wide"
)

# Injection de code JavaScript pour recharger la page automatiquement toutes les 60 secondes
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 60000); // 60000 ms = 60 secondes
    </script>
    """,
    height=0,
    width=0
)

st.title("📊 Métrologie & Supervision du Trafic Routier")
st.subheader("Dashboard Décisionnel en Temps Réel — Métropole de Lyon")
st.caption("Données synchronisées en continu via Spark Streaming & MongoDB (Rafraîchissement automatique : 60s)")
st.markdown("---")

# ============================================================================
# 2. CONFIGURATION DU CODE COULEUR HARMONISÉ AVEC SPARK
# ============================================================================
COULEURS_OFFICIELLES = {
    "Fluide": "#2ece3b",                # Vert
    "Dense": "#ff9f1a",                 # Orange
    "Chargé": "#e74c3c",                # Rouge
    "Route coupée": "#2c3e50",          # Noir / Anthracite
    "Données indisponibles": "#bdc3c7", # Gris clair
    "Inconnu": "#8c95a0"                # Gris Foncé (Sécurité Spark)
}

# ============================================================================
# 3. BARRE LATÉRALE & LÉGENDE DES COULEURS
# ============================================================================
st.sidebar.title("🎮 Contrôle & Filtres")
st.sidebar.write("Gestion du réseau routier de Lyon.")

# Ajout d'une vraie légende HTML propre et claire dans la Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Légende du Trafic")
st.sidebar.markdown(
    f"""
    <div style="display: flex; flex-direction: column; gap: 10px; padding: 12px; background-color: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Fluide']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Fluide</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Dense']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Dense</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Chargé']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Chargé</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Route coupée']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Route coupée</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Données indisponibles']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Données indispo.</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="background-color: {COULEURS_OFFICIELLES['Inconnu']}; width: 16px; height: 16px; border-radius: 50%; display: inline-block;"></span>
            <span style="color: #24292e; font-weight: 500;">Inconnu (Erreur/Null)</span>
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)

# ============================================================================
# 4. CONNEXION MONGODB & CHARGEMENT
# ============================================================================
@st.cache_resource
def init_connection():
    return MongoClient("mongodb://127.0.0.1:27017/")

try:
    client = init_connection()
    db = client["lyon_traffic_db"]
    collection = db["congestions"]
except Exception as e:
    st.error(f"Erreur de connexion à MongoDB : {e}")

def load_data():
    data = list(collection.find())
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

df_traffic = load_data()

# ============================================================================
# 5. TRAITEMENT ET AFFICHAGE DES 3 KPIS D'AIDE À LA DÉCISION
# ============================================================================
if not df_traffic.empty:
    
    vitesse_moyenne = df_traffic['vitesse_reelle'].mean()
    total_axes = df_traffic['id_segment'].nunique()
    axes_critiques = df_traffic[df_traffic['statut_trafic'].isin(['Chargé', 'Route coupée'])]['id_segment'].nunique()
    score_congestion = (axes_critiques / total_axes) * 100 if total_axes > 0 else 0
    
    df_pires = df_traffic[df_traffic['statut_trafic'] == 'Chargé'].sort_values(by='vitesse_reelle', ascending=True)
    pires_axes_noms = df_pires['nom_axe'].dropna().unique()[:5]
    
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.metric(
            label="📉 Score Global de Congestion", 
            value=f"{score_congestion:.1f} %",
            delta="Seuil Critique (>20%)" if score_congestion > 20 else "Normal",
            delta_color="inverse"
        )
        st.caption("Ratio du réseau urbain actuellement saturé ou bloqué.")
        
    with kpi2:
        st.metric(
            label="⚡ Vitesse Moyenne de la Ville", 
            value=f"{vitesse_moyenne:.1f} km/h" if not pd.isna(vitesse_moyenne) else "N/A"
        )
        st.caption("Vitesse moyenne globale calculée sur l'ensemble des capteurs.")
        
    with kpi3:
        st.metric(
            label="🚨 Axes Noirs Actifs", 
            value=f"{len(pires_axes_noms)} majeur(s)"
        )
        st.caption("Nombre de points de blocage critiques identifiés en ce moment.")

    st.markdown("---")

    # ============================================================================
    # 6. CARTOGRAPHIE & GRAPHIQUE CAMEMBERT (CÔTE À CÔTE)
    # ============================================================================
    col_carte, col_pie = st.columns([2, 1])
    
    with col_carte:
        st.write("### 🗺️ Météo du Trafic en Temps Réel")
        
        m = folium.Map(location=[45.75, 4.85], zoom_start=12, tiles="cartodbpositron")
        
        # AJUSTEMENT : On inclut "Inconnu" et "Données indisponibles" si on veut les analyser visuellement
        df_carte = df_traffic[df_traffic['statut_trafic'].isin(['Dense', 'Chargé', 'Route coupée', 'Inconnu'])]
        if df_carte.shape[0] > 200:
            df_carte = df_carte.sort_values(by='horodatage_source', ascending=False).head(200)
        if df_carte.empty:
            df_carte = df_traffic.head(150)

        for _, row in df_carte.iterrows():
            try:
                geo_str = row['geometrie_gps']
                if pd.isna(geo_str) or not geo_str:
                    continue
                
                if isinstance(geo_str, str):
                    geo_str = geo_str.strip()
                    if geo_str.startswith('"') and geo_str.endswith('"'):
                        geo_str = geo_str[1:-1]
                    geo_str = geo_str.replace('\\"', '"')
                    coords = json.loads(geo_str)
                else:
                    coords = geo_str
                
                points_carte = [[float(p[1]), float(p[0])] for p in coords if len(p) >= 2]
                if not points_carte:
                    continue

                couleur = COULEURS_OFFICIELLES.get(row['statut_trafic'], "#bdc3c7")
                vitesse_txt = f"{row['vitesse_reelle']} km/h" if not pd.isna(row['vitesse_reelle']) else "Inconnue"
                texte_popup = f"<b>Axe :</b> {row['nom_axe']}<br><b>Statut :</b> {row['statut_trafic']}<br><b>Vitesse :</b> {vitesse_txt}"
                
                folium.PolyLine(
                    locations=points_carte,
                    color=couleur,
                    weight=5,
                    opacity=0.8,
                    popup=folium.Popup(texte_popup, max_width=300)
                ).add_to(m)
            except Exception:
                continue

        carte_html = m._repr_html_()
        components.html(carte_html, height=450, scrolling=True)

    with col_pie:
        st.write("### 📈 Répartition Globale des Statuts")
        
        stats_statut = df_traffic['statut_trafic'].value_counts()
        labels_presents = stats_statut.index.tolist()
        
        couleurs_pie = [COULEURS_OFFICIELLES.get(label, "#bdc3c7") for label in labels_presents]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels_presents,
            values=stats_statut.values,
            hole=.4,
            marker=dict(colors=couleurs_pie),
            textinfo='percent+label',
            showlegend=False
        )])
        
        # Configuration de la police en sombre (#24292e) pour correspondre au thème clair natif
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#24292e'),
            margin=dict(t=10, b=10, l=10, r=10),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ============================================================================
    # 7. PYRAMIDE D'INFORMATION : TOP 5 DES PIRES AXES & TABLE DÉTAILLÉE
    # ============================================================================
    col_top5, col_table = st.columns([1, 1])
    
    with col_top5:
        st.write("### 🚨 Top 5 des Pires Axes")
        if len(pires_axes_noms) > 0:
            for idx, axe in enumerate(pires_axes_noms):
                vitesse_axe = df_pires[df_pires['nom_axe'] == axe]['vitesse_reelle'].min()
                st.error(f"**{idx+1}. {axe}** — Vitesse critique : **{vitesse_axe:.1f} km/h**")
        else:
            st.success("✅ Aucun axe saturé majeur détecté.")

    with col_table:
        st.write("### 📋 Table des données")
        colonnes_affichage = ['nom_axe', 'statut_trafic', 'vitesse_reelle', 'horodatage_source']
        st.dataframe(
            df_traffic[colonnes_affichage].sort_values(by='horodatage_source', ascending=False),
            use_container_width=True
        )

else:
    st.warning("⏳ En attente des données de Spark Streaming... Assure-toi que MongoDB est bien alimenté.")

if st.button("🔄 Actualiser manuellement"):
    st.rerun()