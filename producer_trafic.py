import os
import time
import json
import requests

from kafka import KafkaProducer
from requests.auth import HTTPBasicAuth

# ============================================================================
# CONFIGURATION KAFKA
# ============================================================================

KAFKA_SERVER = os.getenv("KAFKA_SERVER", "127.0.0.1:9092")
TOPIC_NAME = "lyon-trafic-neuf"

# ============================================================================
# IDENTIFIANTS STOCKÉS DANS LES VARIABLES D'ENVIRONNEMENT
# ============================================================================

USER_LYON = os.getenv("LYON_USER")
PASSWORD_LYON = os.getenv("LYON_PASSWORD")

if not USER_LYON or not PASSWORD_LYON:
    raise ValueError(
        "Variables LYON_USER et LYON_PASSWORD introuvables."
    )

# ============================================================================
# CONNEXION KAFKA
# ============================================================================

print(" Connexion au cluster Kafka...")

try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_SERVER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=5
    )

    print(" Kafka connecté.")

except Exception as e:
    print(f" Erreur Kafka : {e}")
    raise

# ============================================================================
# API GRAND LYON
# ============================================================================

URL_API_LYON = (
    "https://data.grandlyon.com/geoserver/metropole-de-lyon/ows"
    "?SERVICE=WFS"
    "&VERSION=2.0.0"
    "&request=GetFeature"
    "&typename=metropole-de-lyon:pvo_patrimoine_voirie.pvotrafic"
    "&SRSNAME=EPSG:4171"
    "&outputFormat=application/json"
    "&count=3500"
)

# ============================================================================
# INGESTION TEMPS RÉEL
# ============================================================================

def lancer_ingestion():

    compteur_flux = 0

    print(" Producer démarré")

    while True:

        try:

            print("\n Interrogation Grand Lyon...")

            response = requests.get(
                URL_API_LYON,
                auth=HTTPBasicAuth(USER_LYON, PASSWORD_LYON),
                timeout=30
            )

            if response.status_code == 200:

                payload = response.json()

                features = payload.get("features", [])

                compteur_flux += 1

                print(
                    f"📥 Flux #{compteur_flux} : "
                    f"{len(features)} segments récupérés"
                )

                for feature in features:
                    producer.send(
                        TOPIC_NAME,
                        value=feature
                    )

                producer.flush()

                print(
                    f" {len(features)} événements envoyés vers Kafka"
                )

            elif response.status_code == 401:

                print(" Authentification Grand Lyon refusée")

            else:

                print(
                    f" Erreur HTTP : {response.status_code}"
                )

        except Exception as e:

            print(f" Erreur : {e}")

        print(" Pause 60 secondes...")
        time.sleep(60)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    lancer_ingestion()