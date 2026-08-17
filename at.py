import json
import time
import random
import pandas as pd
import streamlit as st
import pydeck as pdk
from pymongo import MongoClient
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# =============================================================================
# CONFIGURATION DE LA PAGE
# =============================================================================
st.set_page_config(
    page_title="Smart Traffic Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Rafraîchissement automatique propre (Toutes les 15 secondes par défaut)
# Évite l'utilisation d'une boucle 'while True' qui sature le CPU
refresh_rate = st.sidebar.slider("🔄 Fréquence de rafraîchissement (s)", 5, 60, 15, key="global_refresh_slider")
st_autorefresh(interval=refresh_rate * 1000, key="data_refresh_trigger")

# =============================================================================
# DESIGN SYSTEM PREMIUM (Cyberpunk / Share Tech Mono)
# =============================================================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');

        html, body, [class*="css"] {
            font-family: 'Share Tech Mono', monospace;
            background-color: #13151a;
            color: #c9d1d9;
        }
        .main { background-color: #13151a; }
        h1, h2, h3 { font-family: 'Rajdhani', sans-serif; color: #f0f6fc; }

        .block-container {
            padding-top: 2.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            max-width: 100% !important;
        }

        /* HEADER */
        .dashboard-header {
            background: linear-gradient(90deg, #1a1d24 0%, #1f2330 100%);
            border: 1px solid #2d3142;
            border-radius: 12px;
            padding: 14px 22px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .dashboard-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.7rem;
            font-weight: 700;
            color: #f0f6fc;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .dashboard-subtitle { font-size: 0.70rem; color: #6e7681; margin-top: 2px; }
        .connected-badge {
            display: inline-flex; align-items: center; gap: 6px;
            background: #0d2318; border: 1px solid #238636;
            border-radius: 20px; padding: 4px 12px;
            font-size: 0.70rem; color: #3fb950;
        }
        .dot-green { width:7px; height:7px; border-radius:50%; background:#3fb950;
                     display:inline-block; animation:pulse 2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        .refresh-info { font-size:0.68rem; color:#6e7681; text-align:right; margin-top:3px; }

        /* CARTES MÉTRIQUES PRINCIPALES */
        .stat-card {
            background: #1a1d24;
            border: 1px solid #2d3142;
            border-radius: 10px;
            padding: 14px 16px 10px 16px;
            margin-bottom: 8px;
            position: relative;
            overflow: hidden;
        }
        .stat-card-label {
            font-size: 0.65rem;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 4px;
        }
        .stat-card-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.4rem;
            font-weight: 700;
            line-height: 1;
        }
        .stat-card-sub {
            font-size: 0.65rem;
            color: #6e7681;
            margin-top: 2px;
        }
        .stat-icon {
            position: absolute;
            top: 12px; right: 14px;
            font-size: 1.8rem;
            opacity: 0.6;
        }

        /* CARTES KPI BIENVENUE */
        .kpi-card {
            background: #1a1d24;
            border: 1px solid #2d3142;
            border-radius: 8px;
            padding: 9px 13px;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1;
        }
        .kpi-label { font-size:0.63rem; color:#8b949e; text-transform:uppercase; letter-spacing:0.1em; margin-top:3px; }
        .kpi-sub { font-size:0.60rem; color:#6e7681; margin-top:2px; }

        /* SECTION TITLE */
        .section-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.82rem; font-weight: 600;
            color: #8b949e; text-transform: uppercase;
            letter-spacing: 0.14em;
            margin: 12px 0 7px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid #21262d;
        }

        /* PALETTE DE COULEURS CONSTANTES */
        .c-fluide  { color: #2ea043; } 
        .c-dense   { color: #e3b341; } 
        .c-charge  { color: #f0883e; } 
        .c-coupe   { color: #f85149; } 
        .c-inconnu { color: #6e7681; } 
        .c-total   { color: #58a6ff; }
        .c-ok      { color: #2ea043; }
        .c-warn    { color: #f0883e; }
        .c-danger  { color: #f85149; }

        /* SIDEBAR SOMBRE */
        section[data-testid="stSidebar"] {
            background-color: #13151a !important;
            border-right: 1px solid #21262d !important;
        }
        section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

        /* TABLEAU OPTIMISÉ */
        .stDataFrame { background: #1a1d24; border: 1px solid #2d3142; border-radius: 8px; }
        hr { border-color: #21262d !important; margin: 10px 0 !important; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# DICTIONNAIRES DE CONFIGURATION & DIAPO MAPPING
# =============================================================================
COLOR_MAP_PYDECK = {
    "Fluide": [46, 160, 67, 230],                 # Vert
    "Dense": [227, 179, 65, 230],                 # Jaune
    "Chargé": [240, 136, 62, 230],                # Orange
    "Route coupée": [248, 81, 73, 230],           # Rouge
    "Données indisponibles": [110, 118, 129, 150], # Gris
    "Inconnu": [110, 118, 129, 120]               # Gris foncé
}

MAPPING_ETATS_SOURCE = {
    'v': 'Fluide',
    'o': 'Dense',
    'r': 'Chargé',
    'n': 'Route coupée',
    'g': 'Données indisponibles'
}

TOUS_STATUTS = ["Fluide", "Dense", "Chargé", "Route coupée", "Données indisponibles", "Inconnu"]
SEUIL_CRITIQUE_KMH = 10.0

# =============================================================================
# FONCTIONS REQUISES POUR PYDECK & VISU
# =============================================================================
def get_color(statut):
    return COLOR_MAP_PYDECK.get(statut, [110, 118, 129, 120])

def extraire_chemin(coords):
    if not isinstance(coords, list) or len(coords) == 0:
        return None
    if isinstance(coords[0], list) and len(coords[0]) >= 2:
        return coords
    if isinstance(coords[0], (int, float)) and len(coords) >= 2:
        return [coords, coords]
    return None

def badge_taux(v):
    return "c-ok" if v >= 70 else "c-warn" if v >= 40 else "c-danger"

def badge_congestion(v):
    return "c-ok" if v <= 20 else "c-warn" if v <= 50 else "c-danger"

def sparkline_svg(color="#2ea043", n=20):
    pts = [random.randint(10, 40) for _ in range(n)]
    w, h = 120, 30
    xs = [i * w / (n-1) for i in range(n)]
    ys = [h - (p / 50 * h) for p in pts]
    path = " ".join([f"{'M' if i==0 else 'L'}{xs[i]:.1f},{ys[i]:.1f}" for i in range(n)])
    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
        <path d="{path}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.8"/>
    </svg>'''

# =============================================================================
# CONNEXION CACHÉE MONGODB
# =============================================================================
@st.cache_resource
def get_mongo_client():
    # Connexion persistante pour éviter de saturer MongoDB
    return MongoClient("mongodb://127.0.0.1:27017")

def load_data(limit_records=3000):
    try:
        client = get_mongo_client()
        db = client["lyon_traffic_db"]
        collection = db["congestions"]
        
        cursor = collection.find().sort("horodatage_source", -1).limit(limit_records)
        raw = list(cursor)
        rows = []
        
        for doc in raw:
            # Gestion de la géométrie GPS / Coordonnées complexes
            coords = doc.get("coordonnees")
            if not coords:
                try:
                    gps = doc.get("geometrie_gps", "")
                    coords = json.loads(gps.replace("(", "[").replace(")", "]")) if gps else None
                except Exception:
                    coords = None
            
            lon, lat = None, None
            if coords and isinstance(coords, list) and len(coords) > 0:
                first = coords[0]
                if isinstance(first, list) and len(first) >= 2:
                    lon, lat = first[0], first[1]
                elif isinstance(first, (int, float)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
            
            # Harmonisation et nettoyage strict du statut de trafic (Lien Diapo)
            statut_brut = str(doc.get("statut_trafic", "Inconnu")).strip()
            statut_propre = MAPPING_ETATS_SOURCE.get(statut_brut.lower(), statut_brut if statut_brut in TOUS_STATUTS else "Inconnu")
            
            # Règle Métier : Masquage vitesse si Données indisponibles (Gris)
            vitesse = doc.get("vitesse_reelle")
            if statut_propre == "Données indisponibles":
                vitesse = None
                
            horodatage = doc.get("horodatage_source", "N/A")
            distance = doc.get("distance_metres")
            try:
                distance = float(distance) if distance is not None else None
            except Exception:
                distance = None
                
            rows.append({
                "nom_axe":           doc.get("nom_axe", "Axe inconnu"),
                "code_axe":          doc.get("code_axe", ""),
                "statut_trafic":     statut_propre,
                "vitesse_reelle":    vitesse,
                "vitesse_affichee":  f"{int(vitesse)} km/h" if vitesse is not None else "N/A",
                "distance_metres":   distance,
                "horodatage_source": str(horodatage)[:19].replace("T", " "),
                "coordonnees":       coords,
                "lon": lon, "lat": lat,
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Erreur d'accès base MongoDB : {e}")
        return pd.DataFrame()

# =============================================================================
# CONTRÔLES SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### 🚦 Lyon Trafic Pro")
    st.markdown("---")
    statuts_filter = st.multiselect("Filtrer les statuts", TOUS_STATUTS, default=TOUS_STATUTS)
    limit = st.slider("Nombre maximal de segments", 500, 5000, 2500)
    st.markdown("---")
    st.markdown("🟢 Fluide · 🟡 Dense · 🟠 Chargé · 🔴 Coupé · ⚫ Inconnu")
    st.markdown("---")
    st.caption("Pipeline Connecté: Kafka ➡️ Spark Streaming ➡️ MongoDB")

# CHARGEMENT UNIQUE DU FRAME (SANS BOUCLE WHILE INFECTIEUSE)
df = load_data(limit_records=limit)
now = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')

# =============================================================================
# CONSTRUIRE LE RENDU SI LES DONNÉES SONT PRÉSENTES
# =============================================================================
if df.empty:
    st.warning("📡 Base MongoDB connectée. En attente du démarrage de ton cluster d'analyse Spark...")
else:
    # Application du filtre sidebar
    if "statut_trafic" in df.columns:
        df = df[df["statut_trafic"].isin(statuts_filter)]

    total      = len(df)
    nb_fluide  = len(df[df["statut_trafic"] == "Fluide"])
    nb_dense   = len(df[df["statut_trafic"] == "Dense"])
    nb_charge  = len(df[df["statut_trafic"] == "Chargé"])
    nb_coupe   = len(df[df["statut_trafic"] == "Route coupée"])
    nb_inconnu = len(df[df["statut_trafic"].isin(["Inconnu", "Données indisponibles"])])
    
    taux_fluide     = round(nb_fluide / total * 100, 1) if total > 0 else 0
    taux_dense      = round(nb_dense / total * 100, 1) if total > 0 else 0
    taux_charge     = round(nb_charge / total * 100, 1) if total > 0 else 0
    taux_congestion = round((nb_dense + nb_charge) / total * 100) if total > 0 else 0
    
    df_v = df[df["vitesse_reelle"].notna()]
    vitesse_moy = round(df_v["vitesse_reelle"].mean(), 1) if not df_v.empty else 0

    # ===== HEADER =====
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <div class="dashboard-title">🚦 Smart Traffic Dashboard</div>
            <div class="dashboard-subtitle">Surveillance du trafic en temps réel — Métropole du Grand Lyon</div>
        </div>
        <div style="text-align:right">
            <div class="connected-badge"><span class="dot-green"></span> NODE CONNECTÉ (WINDOWS)</div>
            <div class="refresh-info">Mise à jour automatique : {now} · {len(df)} segments</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== 5 CARTES MÉTRIQUES PRINCIPALES =====
    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "ZONES FLUIDES",       nb_fluide, f"{taux_fluide}% du total",  "🚗", "#2ea043", sparkline_svg("#2ea043")),
        (c2, "ZONES DENSES",        nb_dense,  f"{taux_dense}% du total",   "🚙", "#e3b341", sparkline_svg("#e3b341")),
        (c3, "ZONES CHARGÉES",      nb_charge, f"{taux_charge}% du total",  "🚕", "#f0883e", sparkline_svg("#f0883e")),
        (c4, "VITESSE MOYENNE",     f"{vitesse_moy}", "km/h actuelle",      "🏎️", "#58a6ff", sparkline_svg("#58a6ff")),
        (c5, "NOMBRE TOTAL ZONES",  total,     "Actives actuellement",      "🗺️", "#a371f7", sparkline_svg("#a371f7")),
    ]
    for col, label, val, sub, icon, color, sparkline in cards:
        with col:
            st.markdown(f"""
            <div class='stat-card' style='border-top: 3px solid {color};'>
                <div class='stat-card-label' style='color:{color}'>{label}</div>
                <div class='stat-card-value' style='color:{color}'>{val}</div>
                <div class='stat-card-sub'>{sub}</div>
                <div style='margin-top:8px'>{sparkline}</div>
                <div class='stat-icon'>{icon}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== COEUR VISUEL : DONUT + TOP5 À GAUCHE | PYDECK CARTE COMPLÈTE À DROITE =====
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # Donut Répartition
        st.markdown("<div class='section-title'>📊 Répartition analytique du réseau</div>", unsafe_allow_html=True)
        labels  = ["Fluide", "Dense", "Chargé", "Coupé", "Inconnu"]
        values  = [nb_fluide, nb_dense, nb_charge, nb_coupe, nb_inconnu]
        colors  = ["#2ea043", "#e3b341", "#f0883e", "#f85149", "#3d3d42"]
        
        fig_donut = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color='#13151a', width=2)),
            textinfo='percent',
            textfont=dict(size=11, color='white'),
            hovertemplate='<b>%{label}</b><br>%{value} zones<br>%{percent}<extra></extra>',
        ))
        fig_donut.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            showlegend=True,
            legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=11, color='#c9d1d9'), bgcolor='rgba(0,0,0,0)'),
            annotations=[dict(text=f"<b>{total}</b><br>zones", x=0.5, y=0.5, font_size=15, font_color='#f0f6fc', showarrow=False)]
        )
        # Utilisation de clés fixes pour stopper le bug de rechargement Plotly
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False}, key="stable_donut_widget")

        # Top 5 Congestions
        st.markdown("<div class='section-title'>🔥 Top 5 des axes saturés</div>", unsafe_allow_html=True)
        df_congest = df[df["statut_trafic"].isin(["Dense", "Chargé"])].copy()
        if df_congest.empty:
            st.info("Aucune zone congestionnée détectée actuellement.")
        else:
            top5 = df_congest.groupby("nom_axe").size().reset_index(name="nb_segments")
            top5 = top5.nlargest(5, "nb_segments")
            top5["nom_court"] = top5["nom_axe"].apply(lambda x: x[:25] + "…" if len(x) > 25 else x)
            
            fig_top5 = go.Figure(go.Bar(
                x=top5["nb_segments"],
                y=top5["nom_court"],
                orientation='h',
                marker=dict(color=top5["nb_segments"], colorscale=[[0, "#e3b341"], [0.5, "#f0883e"], [1, "#f85149"]], showscale=False),
                text=top5["nb_segments"],
                textposition='outside',
                textfont=dict(color='#c9d1d9', size=11),
                hovertemplate='<b>%{y}</b><br>%{x} segments<extra></extra>',
            ))
            fig_top5.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=5, b=5, l=5, r=40),
                height=310,
                xaxis=dict(showgrid=False, color='#6e7681'),
                yaxis=dict(showgrid=False, color='#c9d1d9', autorange="reversed"),
                font=dict(family='Share Tech Mono', size=11, color='#c9d1d9')
            )
            st.plotly_chart(fig_top5, use_container_width=True, config={'displayModeBar': False}, key="stable_top5_widget")

    with col_right:
        # Cartographie Vectorielle Ultra-Précise Pydeck
        st.markdown("<div class='section-title'>🗺️ Cartographie Vectorielle temps réel GPS</div>", unsafe_allow_html=True)
        df_map = df.dropna(subset=["coordonnees"]).copy()
        df_map["path"] = df_map["coordonnees"].apply(extraire_chemin)
        df_map = df_map.dropna(subset=["path"])
        
        if df_map.empty:
            st.info("Aucune coordonnée exploitable pour le traçage vectoriel.")
        else:
            df_map["color"] = df_map["statut_trafic"].apply(get_color)
            
            path_layer = pdk.Layer(
                "PathLayer",
                data=df_map,
                get_path="path",
                get_color="color",
                get_width=6,
                width_min_pixels=3,
                width_max_pixels=10,
                pickable=True,
                auto_highlight=True,
            )
            # Centrage optimal sur l'hypercentre de Lyon
            view_state = pdk.ViewState(latitude=45.758, longitude=4.832, zoom=12.5, pitch=0)
            
            st.pydeck_chart(pdk.Deck(
                layers=[path_layer],
                initial_view_state=view_state,
                tooltip={
                    "html": "<b style='color:#ffffff'>{nom_axe}</b><br/><span style='color:#cbd5e1;'>État : {statut_trafic}</span><br/><span style='color:#cbd5e1;'>Vitesse : {vitesse_affichee}</span>",
                    "style": {"backgroundColor": "#1a1d24", "color": "#ffffff", "fontSize": "12px", "borderRadius": "6px", "border": "1px solid #2d3142"}
                },
                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            ), use_container_width=True, height=640)

    st.markdown("---")

    # ===== MULTI-KPI COMPACTS =====
    nb_critiques = len(df_v[df_v["vitesse_reelle"] < SEUIL_CRITIQUE_KMH])
    df_d = df[df["distance_metres"].notna()]
    dist_totale  = round(df_d["distance_metres"].sum() / 1000, 1) if not df_d.empty else 0
    dist_congest = round(df_d[df_d["statut_trafic"].isin(["Dense","Chargé"])]["distance_metres"].sum() / 1000, 1) if not df_d.empty else 0
    
    st.markdown("<div class='section-title'>📊 Indicateurs d'Infrastructures Généraux</div>", unsafe_allow_html=True)
    kpi_cols = st.columns(6)
    kpis = [
        (f"{taux_fluide}%",       "Réseau Fluide",      badge_taux(taux_fluide),               None),
        (f"{taux_congestion}%",   "Taux Congestion",    badge_congestion(taux_congestion),     "Dense & Chargé"),
        (f"{vitesse_moy} km/h",   "Vitesse globale",    "c-ok" if vitesse_moy >= 30 else "c-warn", None),
        (f"{nb_critiques}",       "Axes Critiques",     "c-danger" if nb_critiques > 0 else "c-ok", f"< {int(SEUIL_CRITIQUE_KMH)} km/h"),
        (f"{dist_totale} km",     "Couverture Totale",  "c-total",                             None),
        (f"{dist_congest} km",    "Longueur Engorgée",  "c-warn",                              None),
    ]
    for i, (val, label, cls, sub) in enumerate(kpis):
        sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
        with kpi_cols[i]:
            st.markdown(f"<div class='kpi-card'><div class='kpi-value {cls}'>{val}</div><div class='kpi-label'>{label}</div>{sub_html}</div>", unsafe_allow_html=True)

    # ===== ALERTES EN DIRECT =====
    st.markdown("<div class='section-title'>🔔 Hub d'alertes temps réel</div>", unsafe_allow_html=True)
    alertes = []
    if nb_charge > 0:
        axe_c = df[df["statut_trafic"] == "Chargé"]["nom_axe"].iloc[0] if not df[df["statut_trafic"] == "Chargé"].empty else "—"
        alertes.append(("🔴", "c-danger", "#f85149", "Saturation Critique", axe_c[:22], nb_charge, "tronçons impactés"))
    if nb_dense > 0:
        axe_d = df[df["statut_trafic"] == "Dense"]["nom_axe"].iloc[0] if not df[df["statut_trafic"] == "Dense"].empty else "—"
        alertes.append(("🟠", "c-warn", "#e3b341", "Trafif Ralenti", axe_d[:22], nb_dense, "tronçons denses"))
    if nb_coupe > 0:
        axe_co = df[df["statut_trafic"] == "Route coupée"]["nom_axe"].iloc[0] if not df[df["statut_trafic"] == "Route coupée"].empty else "—"
        alertes.append(("🛑", "c-danger", "#f85149", "Axe Clos", axe_co[:22], nb_coupe, "fermetures totales"))
    
    if not alertes:
        alertes.append(("🟢", "c-ok", "#2ea043", "Réseau Nominal", "Flux Libres", "0", "aucune anomalie"))

    alert_cols = st.columns(len(alertes[:4]))
    for i, (emoji, cls, border, titre, axe, valeur, sous_label) in enumerate(alertes[:4]):
        with alert_cols[i]:
            st.markdown(f"""
            <div class='kpi-card' style='border-left: 3px solid {border}; padding: 10px 12px;'>
                <div style='display:flex; align-items:center; gap:8px'>
                    <span style='font-size:1.3rem'>{emoji}</span>
                    <div style='flex:1'>
                        <div class='kpi-label' style='margin-bottom:2px'>{titre}</div>
                        <div class='kpi-value {cls}' style='font-size:1.4rem; line-height:1.1'>{valeur}</div>
                        <div class='kpi-sub'>{sous_label}</div>
                        <div class='kpi-sub' style='color:#6e7681; font-size:0.58rem; margin-top:2px'>{axe}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== TABLEAU COMPLET AUDIT MONGODB =====
    st.markdown("<div class='section-title'>📋 Log Registre Système NoSQL (MongoDB Data)</div>", unsafe_allow_html=True)
    cols_display = [c for c in ["nom_axe", "statut_trafic", "vitesse_reelle", "distance_metres", "horodatage_source"] if c in df.columns]
    if cols_display:
        st.dataframe(
            df[cols_display].rename(columns={
                "nom_axe": "Désignation Axe", "statut_trafic": "Statut de Flux",
                "vitesse_reelle": "Vitesse Réelle (km/h)", "distance_metres": "Linéaire (m)",
                "horodatage_source": "Horodatage Capture"
            }).head(20),
            use_container_width=True,
            height=260
        )