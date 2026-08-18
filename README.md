# Smart Traffic System — Grand Lyon

Ce projet met en place une plateforme d’analyse et de visualisation du trafic routier en temps réel pour la métropole du **Grand Lyon**.

Le système ingère des données de trafic, les transmet via **Apache Kafka**, les traite avec **PySpark Streaming**, les stocke dans **MongoDB Atlas** et les restitue à travers un tableau de bord interactif développé avec **Streamlit**.

---

## Architecture technique

La chaîne de traitement repose sur l’architecture Big Data suivante :

`[ Flux de données / API / Capteurs ] ➡️ [ Apache Kafka ] ➡️ [ PySpark Streaming ] ➡️ [ MongoDB Atlas ] ➡️ [ Dashboard Streamlit ]`

### Ingestion

Des scripts **Python** récupèrent ou simulent les données de trafic et les publient dans les topics **Apache Kafka**.

### Traitement et analytics

**PySpark / Spark Streaming** assure le traitement des données en flux continu, notamment :

* le nettoyage et la préparation des données ;
* l’agrégation des données de trafic ;
* le calcul des métriques de vitesse et de congestion ;
* la classification des zones selon leur niveau de trafic.

### Stockage

Les données traitées sont stockées dans **MongoDB Atlas**, une base de données NoSQL permettant de conserver les informations récentes ainsi que l’historique du trafic.

### Visualisation

Une application **Streamlit** permet de consulter les données de manière interactive avec :

* des cartes géographiques basées sur **Folium / Leaflet** ;
* des graphiques analytiques avec **Plotly** ;
* un rafraîchissement automatique des données pour une visualisation quasi temps réel.

---

## Configuration et installation

### 1. Prérequis

Avant de lancer le projet, assurez-vous d’avoir :

* **Python 3.9+**
* une instance **Apache Kafka** active ;
* **MongoDB** en local ou un cluster **MongoDB Atlas** ;
* **Apache Spark / PySpark** correctement configuré ;
* les variables d’environnement nécessaires configurées.

### 2. Création et activation de l’environnement virtuel

#### Windows — PowerShell

```powershell
python -m venv venv_bigdata
.\venv_bigdata\Scripts\Activate.ps1
```

#### Linux / macOS

```bash
python3 -m venv venv_bigdata
source venv_bigdata/bin/activate
```

### 3. Installation des dépendances

Une fois l’environnement virtuel activé, installez les dépendances du projet :

```bash
pip install -r requirements.txt
```

---

## Variables d’environnement

Pour éviter d’exposer les identifiants MongoDB directement dans le code source, utilisez la variable d’environnement `MONGO_URI`.

### Linux / macOS / Git Bash

```bash
export MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/lyon_traffic_db"
```

### Windows — PowerShell

```powershell
$env:MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/lyon_traffic_db"
```

> Ne partagez jamais publiquement votre véritable URI MongoDB, votre mot de passe ou toute autre information d’authentification. Pensez également à ajouter vos fichiers `.env` au `.gitignore` s’ils sont utilisés.

---

## Exécution du projet

Les différents composants doivent être démarrés dans l’ordre suivant.

### 1. Lancer le producteur Kafka

```bash
python producer_trafic.py
```

Le producteur récupère ou génère les données de trafic et les publie dans Kafka.

### 2. Démarrer le traitement PySpark Streaming

Vérifiez que l’environnement virtuel est activé, puis lancez :

```bash
python process.py
```

ou, sous Windows :

```powershell
.\venv_bigdata\Scripts\python.exe process.py
```

Le processus Spark consomme les messages Kafka, les transforme et enregistre les résultats dans MongoDB.

### 3. Lancer le tableau de bord Streamlit

```bash
streamlit run dashboard.py
```

L’application sera alors accessible depuis votre navigateur.

---

## Fonctionnalités du Dashboard

### KPI en temps réel

Le tableau de bord affiche notamment :

* le nombre de zones fluides ;
* le nombre de zones ralenties ;
* le nombre de zones bloquées ;
* la vitesse moyenne du réseau.

### Cartographie interactive

Une carte interactive permet de visualiser les différents tronçons routiers et leur niveau de congestion grâce à un code couleur associé au statut du trafic.

### Analyse des ralentissements

Des graphiques  permettent d’analyser la répartition du trafic ainsi que les zones présentant les ralentissements les plus importants.

### Rafraîchissement dynamique

Le dashboard est conçu pour actualiser régulièrement les données afin de fournir une vision actualisée de l’état du trafic.

---

## Stack technologique

| Technologie                   | Rôle                                                   |
| ----------------------------- | ------------------------------------------------------ |
| **Python**                    | Développement des scripts et de la logique applicative |
| **Apache Kafka**              | Ingestion et transmission des flux de données          |
| **PySpark / Spark Streaming** | Traitement distribué des données en temps réel         |
| **MongoDB Atlas**             | Stockage NoSQL des données de trafic                   |
| **Streamlit**                 | Développement du tableau de bord interactif            |
| **Folium / Leaflet**          | Cartographie interactive                               |
| **Plotly**                    | Visualisation et analyse des données                   |

---

## Flux de données

```text
Sources de données trafic
          │
          ▼
   Producteur Python
          │
          ▼
     Apache Kafka
          │
          ▼
 PySpark / Spark Streaming
          │
          ├── Nettoyage
          ├── Transformation
          ├── Agrégation
          └── Calcul des métriques
          │
          ▼
     MongoDB Atlas
          │
          ▼
   Dashboard Streamlit
          │
          ├── KPI
          ├── Carte interactive
          └── Graphiques analytiques
```

---

## Sécurité

Les informations sensibles, notamment les identifiants MongoDB, ne doivent pas être écrites directement dans le code source.

Le projet privilégie l’utilisation de **variables d’environnement** afin de séparer la configuration sensible du code applicatif.

---

## Objectif du projet

Ce projet illustre la mise en œuvre d’une **architecture Big Data orientée traitement de données en temps réel**, depuis l’ingestion des flux jusqu’à leur visualisation.

Il permet notamment de mettre en pratique :

**Kafka → Streaming → Traitement distribué → NoSQL → Data Visualization**

et de démontrer l’utilisation conjointe de plusieurs technologies de l’écosystème **Big Data**.
