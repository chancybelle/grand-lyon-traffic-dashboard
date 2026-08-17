import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pymongo import MongoClient
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURATION & DESIGN PRO (STYLE SAAS)
# ==========================================
st.set_page_config(
    page_title="Smart Traffic Dashboard - Grand Lyon",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-rafraîchissement du dashboard toutes les 30 secondes
st_autorefresh(interval=30 * 1000, limit=2000, key="traffic_dashboard_autorefresh")

# Style CSS Global (Sidebar pro, cartes KPI fixes, etc.)
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.0rem;
            padding-bottom: 1rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }
        
        .stApp { background-color: #0B0E14; }
        
        /* Style de la sidebar */
        [data-testid="stSidebar"] {
            background-color: #0F172A;
        }
        
        /* Transformation du menu radio en style SaaS */
        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 8px;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label {
            padding: 12px 16px !important;
            border-radius: 8px !important;
            color: #94A3B8 !important;
            font-weight: 500 !important;
            transition: all 0.2s ease;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background-color: #1E293B;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #2563EB !important;
            color: #FFFFFF !important;
        }

        /* Conteneurs / Cartes KPI avec taille strictement identique */
        .kpi-card {
            background-color: #131B2E;
            border: 1px solid #1E293B;
            padding: 14px 16px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            margin-bottom: 10px;
            height: 118px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .kpi-title { 
            font-size: 10px; 
            font-weight: 700; 
            color: #64748B; 
            margin: 0; 
            text-transform: uppercase; 
            letter-spacing: 0.5px;
            line-height: 1.2;
        }
        .kpi-value { font-size: 22px; font-weight: 800; margin: 0; color: #F8FAFC; }
        .kpi-sub { font-size: 11px; color: #64748B; margin: 0; }
        
        .badge-live { background-color: #064E3B; color: #34D399; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
        .badge-timer { background-color: #1E293B; color: #94A3B8; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# Charte graphique officielle du Trafic
PALETTE_COULEURS = {
    "Fluide": "#059669",        
    "Dense": "#D97706",         
    "Congestionné": "#B45309",  
    "Bloqué": "#DC2626",        
    "Coupé": "#1F2937",         
    "Inconnu": "#9CA3AF"        
}

# ==========================================
# 2. CHARGEMENT DES DONNÉES MONGODB SÉCURISÉ
# ==========================================
# Priorité : st.secrets (Streamlit Cloud) -> os.environ -> session_state
def get_mongo_uri():
    if "MONGO_URI" in st.secrets:
        return st.secrets["MONGO_URI"]
    elif "mongo_uri" in st.session_state and st.session_state["mongo_uri"]:
        return st.session_state["mongo_uri"]
    return os.getenv("MONGO_URI", "")

@st.cache_data(ttl=15)
def load_latest_traffic_data(uri):
    if not uri:
        return pd.DataFrame(), None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["lyon_traffic_db"]
        collection = db["congestions"]
        
        latest_doc = collection.find_one(sort=[("horodatage_source", -1)])
        if not latest_doc:
            return pd.DataFrame(), None
            
        latest_timestamp = latest_doc.get("horodatage_source")
        cursor = collection.find({"horodatage_source": latest_timestamp}, {"_id": 0})
        df = pd.DataFrame(list(cursor))
        
        return df, latest_timestamp
    except Exception as e:
        return pd.DataFrame(), None

active_uri = get_mongo_uri()

# ==========================================
# 3. BARRE LATÉRALE (NAVIGATION & FILTRES & CONNEXION)
# ==========================================
with st.sidebar:
    st.markdown("### 🚦 Smart Traffic System")
    st.caption("Pipeline : Kafka ➡️ PySpark ➡️ MongoDB")
    st.write("---")
    
    # Configuration sécurisée de la connexion (Optionnelle si Secrets est configuré)
    st.markdown("#### 🔐 CONNEXION MONGODB")
    input_uri = st.text_input(
        "URI MongoDB Atlas :", 
        value=active_uri, 
        type="password",
        help="Automatiquement chargé depuis Secrets en ligne ou modifiable ici"
    )
    if input_uri != active_uri:
        st.session_state["mongo_uri"] = input_uri
        st.rerun()

    st.write("---")

    menu_selection = st.radio(
        "Navigation",
        [" Vue d'ensemble", " Carte en temps réel", " Alertes", " Statistiques", " Données"],
        label_visibility="collapsed"
    )
    
    st.write("---")
    st.markdown("#### FILTRES")

    df_raw, dernier_horodatage = load_latest_traffic_data(active_uri)

    axes_disponibles = ["Tous les axes"] + sorted(df_raw["nom_axe"].dropna().unique().tolist()) if not df_raw.empty else ["Tous les axes"]
    selected_axe = st.selectbox("Zone / Axe :", axes_disponibles)
    
    statuts_disponibles = ["Tous les états"] + list(PALETTE_COULEURS.keys())
    selected_statut = st.selectbox("État du trafic :", statuts_disponibles)
    
    if st.button(" Réinitialiser"):
        st.rerun()

    st.markdown('<div class="sidebar-footer" style="position: fixed; bottom: 20px; color: #64748B; font-size: 0.8em;">© 2026 Smart Traffic System</div>', unsafe_allow_html=True)

# Message explicatif si aucune URI n'est configurée
if not active_uri:
    st.warning("⚠️ Veuillez renseigner votre URI MongoDB Atlas dans les Secrets Streamlit ou le panneau latéral (Sidebar).")
    st.stop()

# Filtrage local
df = df_raw.copy()
if not df.empty:
    if selected_axe != "Tous les axes":
        df = df[df["nom_axe"] == selected_axe]
    if selected_statut != "Tous les états":
        df = df[df["statut_trafic"] == selected_statut]

# ==========================================
# 4. EN-TÊTE PRO (TITRE + STATUT + TIMER)
# ==========================================
header_col1, header_col2 = st.columns([7, 3])

with header_col1:
    st.markdown("<h2 style='margin:0; padding:0; font-weight:800; letter-spacing:0.5px;'>SMART TRAFFIC DASHBOARD</h2>", unsafe_allow_html=True)
    st.markdown("<p style='margin:2px 0 10px 0; color:#64748B;'>Surveillance du trafic urbain en temps réel — Grand Lyon</p>", unsafe_allow_html=True)

with header_col2:
    time_str = datetime.now().strftime('%H:%M:%S')
    badge_status = "● CONNECTÉ À MONGODB" if not df_raw.empty else "○ EN ATTENTE DE DONNÉES"
    st.markdown(
        f"""<div style='text-align: right; padding-top: 5px;'>
            <span class='badge-live'>{badge_status}</span>
            &nbsp;&nbsp;
            <span class='badge-timer'> {time_str}</span>
        </div>""", 
        unsafe_allow_html=True
    )

st.write("---")

# ==========================================
# 5. BLOCS KPI PRINCIPAUX (5 COLONNES)
# ==========================================
total_segments = len(df_raw)
count_fluide = len(df_raw[df_raw["statut_trafic"] == "Fluide"]) if not df_raw.empty else 0
count_dense = len(df_raw[df_raw["statut_trafic"].isin(["Dense", "Congestionné"])]) if not df_raw.empty else 0
count_bloque = len(df_raw[df_raw["statut_trafic"] == "Bloqué"]) if not df_raw.empty else 0
vitesse_moyenne = round(df_raw["vitesse_reelle"].dropna().mean(), 1) if not df_raw.empty and "vitesse_reelle" in df_raw.columns else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    pct = round((count_fluide / total_segments) * 100, 1) if total_segments > 0 else 0
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #059669;">
            <p class="kpi-title">ZONES FLUIDES</p>
            <div class="kpi-value">{count_fluide}</div>
            <p class="kpi-sub">{pct}% du réseau</p>
        </div>
    """, unsafe_allow_html=True)

with kpi2:
    pct = round((count_dense / total_segments) * 100, 1) if total_segments > 0 else 0
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #D97706;">
            <p class="kpi-title">ZONES RALENTIES</p>
            <div class="kpi-value">{count_dense}</div>
            <p class="kpi-sub">{pct}% du réseau</p>
        </div>
    """, unsafe_allow_html=True)

with kpi3:
    pct = round((count_bloque / total_segments) * 100, 1) if total_segments > 0 else 0
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #DC2626;">
            <p class="kpi-title">ZONES BLOQUÉES</p>
            <div class="kpi-value">{count_bloque}</div>
            <p class="kpi-sub">{pct}% du réseau</p>
        </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #38BDF8;">
            <p class="kpi-title">VITESSE MOYENNE</p>
            <div class="kpi-value">{vitesse_moyenne} <span style="font-size:14px; font-weight:normal;">km/h</span></div>
            <p class="kpi-sub">Capteurs actifs</p>
        </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #8B5CF6;">
            <p class="kpi-title">TOTAL TRONÇONS</p>
            <div class="kpi-value">{total_segments}</div>
            <p class="kpi-sub">Supervisés en direct</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 6. GRILLE MILIEU : DONUT & CARTE LEAFLET
# ==========================================
col_left, col_right = st.columns([3, 7])

with col_left:
    st.markdown("### RÉPARTITION DU TRAFIC")
    if not df_raw.empty:
        tous_statuts = list(PALETTE_COULEURS.keys())
        counts = df_raw["statut_trafic"].value_counts()
        
        df_pie = pd.DataFrame({
            "statut_trafic": tous_statuts,
            "count": [counts.get(s, 0) for s in tous_statuts]
        })
        
        df_pie = df_pie[df_pie["count"] > 0]
        
        fig_pie = px.pie(
            df_pie, values="count", names="statut_trafic", hole=0.65,
            color="statut_trafic", color_discrete_map=PALETTE_COULEURS
        )
        fig_pie.update_traces(textinfo='percent', textfont_size=12)
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFFFFF", margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.markdown("### CARTE DES ZONES EN TEMPS RÉEL")
    map_center = [45.7578, 4.8320]
    zoom_level = 12
    
    if selected_axe != "Tous les axes" and not df.empty:
        sample_geom = df.iloc[0].get("geometry")
        if isinstance(sample_geom, dict) and "coordinates" in sample_geom:
            coords = sample_geom["coordinates"]
            if sample_geom.get("type") == "LineString":
                map_center = [coords[0][1], coords[0][0]]
                zoom_level = 14

    m = folium.Map(location=map_center, zoom_start=zoom_level, tiles="CartoDB positron")
    
    if not df.empty:
        for _, row in df.iterrows():
            geom = row.get("geometry")
            statut = row.get("statut_trafic", "Inconnu")
            nom = row.get("nom_axe", "Axe inconnu")
            vitesse = row.get("vitesse_reelle", "N/A")
            color = PALETTE_COULEURS.get(statut, "#9CA3AF")
            
            if isinstance(geom, dict) and "coordinates" in geom:
                coords_raw = geom["coordinates"]
                geom_type = geom.get("type")
                popup_text = f"<b>Axe :</b> {nom}<br><b>Statut :</b> {statut}<br><b>Vitesse :</b> {vitesse} km/h"
                
                # Gestion des LineString
                if geom_type == "LineString":
                    line_coords = [[c[1], c[0]] for c in coords_raw]
                    folium.PolyLine(locations=line_coords, color=color, weight=4, opacity=0.85, popup=popup_text).add_to(m)
                    
                    if selected_axe != "Tous les axes":
                        folium.Marker(
                            location=line_coords[0],
                            popup=popup_text,
                            icon=folium.Icon(color="red", icon="search", prefix="fa")
                        ).add_to(m)
                
                # Gestion des MultiLineString
                elif geom_type == "MultiLineString":
                    for sub_coords in coords_raw:
                        line_coords = [[c[1], c[0]] for c in sub_coords]
                        folium.PolyLine(locations=line_coords, color=color, weight=4, opacity=0.85, popup=popup_text).add_to(m)
                        
                        if selected_axe != "Tous les axes":
                            folium.Marker(
                                location=line_coords[0],
                                popup=popup_text,
                                icon=folium.Icon(color="red", icon="search", prefix="fa")
                            ).add_to(m)
                        
    st_folium(m, width=700, height=280, returned_objects=[])

# ==========================================
# 7. SECTION BASSE : TOP 5 & TABLEAU PLEINE LARGEUR
# ==========================================
st.markdown("---")

st.markdown("### TOP 5 DES AXES LES PLUS LENTS")
if not df_raw.empty:
    df_slow = df_raw[df_raw["vitesse_reelle"].notnull()].sort_values("vitesse_reelle", ascending=True).head(5)
    fig_bar = px.bar(
        df_slow, x="vitesse_reelle", y="nom_axe", orientation="h",
        color_discrete_sequence=["#DC2626"],
        labels={"vitesse_reelle": "Vitesse (km/h)", "nom_axe": "Axe"}
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF", margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(autorange="reversed"),
        height=320
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

st.markdown("### DONNÉES EN TEMPS RÉEL (MONGODB)")
if not df.empty:
    cols_to_show = [c for c in ["nom_axe", "statut_trafic", "vitesse_reelle", "distance_metres", "horodatage_source"] if c in df.columns]
    st.dataframe(df[cols_to_show], use_container_width=True, height=400)
else:
    st.info("Aucune donnée disponible.")