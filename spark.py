import os
import sys

# ============================================================================
# 1. CONFIGURATION SYSTÈME
# ============================================================================
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-17'
os.environ['HADOOP_HOME'] = r'C:\hadoop'
os.environ['SPARK_HOME'] = (
    r'C:\Users\Administrateur\Desktop\Rory\Projet_big_data'
    r'\venv_bigdata\Lib\site-packages\pyspark'
)

current_path = os.environ.get('PATH', '')
clean_path = current_path.replace(
    r'C:\Program Files\Common Files\Oracle\Java\javapath;', ''
)

os.environ['PATH'] = (
    r'C:\Windows\System32;'
    r'C:\Windows;'
    r'C:\Windows\System32\Wbem;'
    r'C:\Program Files\Java\jdk-17\bin;'
    r'C:\hadoop\bin;'
    r'C:\Users\Administrateur\Desktop\Rory\Projet_big_data\venv_bigdata\Lib\site-packages\pyspark\bin;'
    f'{clean_path}'
)

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'
os.environ['_JAVA_OPTIONS'] = '-Xmx512m -Xms512m'

# ============================================================================
# 2. IMPORTS
# ============================================================================
from pyspark.sql import SparkSession
from pyspark.sql.functions import(col, from_json, expr, sha2, when, lit,struct, split, upper, to_timestamp, current_timestamp, coalesce
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, ArrayType
)




# ============================================================================
# 3. INITIALISATION SPARK
# ============================================================================
spark = SparkSession.builder \
    .appName("GrandLyon_Traffic_Secure_Pipeline") \
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
        "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0"
    ) \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.sql.shuffle.partitions", "10") \
    .config("spark.driver.memory", "1g") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("✨ Spark initialisé avec succès !")

# ============================================================================
# 4. SCHÉMA JSON
# ============================================================================
schema_traffic = StructType([
    StructField("properties", StructType([
        StructField("twgid", StringType(), True),
        StructField("code", StringType(), True),
        StructField("id_fournisseur", StringType(), True),
        StructField("libelle", StringType(), True),
        StructField("nom", StringType(), True),
        StructField("etat", StringType(), True),
        StructField("vitesse", StringType(), True),
        StructField("longueur", DoubleType(), True),
        StructField("last_update", StringType(), True)
    ]), True),
    StructField("geometry", StructType([
        StructField("type", StringType(), True),
        StructField(
            "coordinates",
            ArrayType(ArrayType(DoubleType())),
            True
        )
    ]), True)
])

# ============================================================================
# 5. LECTURE KAFKA (Option 'latest' activée)
# ============================================================================
df_kafka = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "127.0.0.1:9092") \
    .option("subscribe", "lyon-trafic-neuf") \
    .option("startingOffsets", "latest") \
    .load()

# ============================================================================
# 6. PARSING JSON - Corrigé pour cibler la racine directement
# ============================================================================
df_parsed = df_kafka \
    .selectExpr("CAST(value AS STRING) as json_payload") \
    .withColumn("parsed_json", from_json(col("json_payload"), schema_traffic)) \
    .select(
        col("parsed_json.properties.twgid"),
        col("parsed_json.properties.code"),
        col("parsed_json.properties.id_fournisseur"),
        col("parsed_json.properties.libelle"),
        col("parsed_json.properties.nom"),
        col("parsed_json.properties.etat"),
        col("parsed_json.properties.vitesse"),
        col("parsed_json.properties.longueur"),
        col("parsed_json.properties.last_update"),
        col("parsed_json.geometry.type").alias("geo_type"),
        col("parsed_json.geometry.coordinates")
    )

# ============================================================================
# 7. NETTOYAGE ET NORMALISATION
# ============================================================================
etat_clean = upper(col("etat"))
df_clean = df_parsed.select(

    # ID SEGMENT
    when(col("twgid").isNotNull() & (col("twgid") != ""), col("twgid"))
    .when(col("code").isNotNull() & (col("code") != ""), col("code"))
    .when(col("id_fournisseur").isNotNull() & (col("id_fournisseur") != ""), col("id_fournisseur"))
    .otherwise(expr("concat('SEG_', regexp_replace(coalesce(libelle, nom, 'INCONNU'), ' ', '_'))"))
    .alias("id_segment"),

    # NOM AXE
    expr("coalesce(libelle, nom, 'Axe inconnu')").alias("nom_axe"),

    # STATUT BRUT
    etat_clean.alias("statut_brut"),

    # VITESSE RÉELLE
    when(col("vitesse").isNotNull() & col("vitesse").contains(" "),
         split(col("vitesse"), " ")[0].cast("double"))
    .when(col("vitesse").isNotNull() & (col("vitesse") != ""),
         col("vitesse").cast("double"))
    .when(etat_clean == "V", 50.0)
    .when(etat_clean == "O", 25.0)
    .when(etat_clean == "R", 10.0)
    .when(etat_clean == "NOIR", 0.0)
    .when(etat_clean == "GRIS", lit(None).cast("double"))
    .otherwise(lit(None).cast("double"))
    .alias("vitesse_reelle"),

    # DISTANCE
    col("longueur").alias("distance_metres"),

    # TIMESTAMP SOURCE
    col("last_update").cast("timestamp").alias("horodatage_source"),

    # GÉOMÉTRIE
    # Option GeoJSON natif (recommandée si tu veux créer un index 2dsphere dans MongoDB)
struct(
    col("geo_type").alias("type"),
    col("coordinates").alias("coordinates")
).alias("geometry")
)

# ============================================================================
# 8. TRADUCTION CODES TRAFIC
# ============================================================================
df_clean = df_clean.withColumn(
    "statut_trafic",
    when(col("statut_brut") == "V", "Fluide")
    .when(col("statut_brut") == "O", "Dense")
    .when(col("statut_brut") == "R", "Saturé")
    .when(col("statut_brut") == "NOIR", "Route coupée")
    .when(col("statut_brut") == "GRIS", "Données indisponibles")
    .otherwise("Inconnu")
).drop("statut_brut")

# ============================================================================
# 9. DÉDUPLICATION TEMPORELLE
# ============================================================================
# 2. FILTRAGE : On conserve uniquement les lignes ayant un horodatage valide
df_valid = df_clean.filter(col("horodatage_source").isNotNull())

# 3. DÉDUPLICATION & WATERMARK sur des données 100% valides
df_final = df_valid \
    .withWatermark("horodatage_source", "10 minutes") \
    .dropDuplicates(["id_segment", "horodatage_source"])

# ============================================================================
# 10. ÉCRITURE VERS MONGODB - foreachBatch
# ============================================================================
def write_batch_sync(batch_df, batch_id):
    print(f"📦 Traitement du micro-batch : {batch_id}")

    batch_df.persist()

    # Collection standard
    batch_df.write \
        .format("mongodb") \
        .option("connection.uri", "mongodb://127.0.0.1:27017") \
        .option("database", "lyon_traffic_db") \
        .option("collection", "congestions") \
        .mode("append") \
        .save()

    # Collection sécurisée
    df_secure = batch_df \
        .withColumn("id_segment_secure", sha2(col("id_segment"), 256)) \
        .drop("id_segment")

    df_secure.write \
        .format("mongodb") \
        .option("connection.uri", "mongodb://127.0.0.1:27017") \
        .option("database", "lyon_traffic_db") \
        .option("collection", "congestions_secure") \
        .mode("append") \
        .save()

    batch_df.unpersist()
    print(f"✅ Batch {batch_id} synchronisé avec succès dans les 2 collections !")

# ============================================================================
# 11. LANCEMENT DU STREAM
# ============================================================================
query = df_final.writeStream \
    .foreachBatch(write_batch_sync) \
    .option(
        "checkpointLocation",
        r"C:\Users\Administrateur\Desktop\Rory\Projet_big_data\chk_global"
    ) \
    .start()

print("🚀 Pipeline Big Data Temps Réel ACTIVÉ !")
print("📡 En attente des flux de données Kafka structurés...")

# ============================================================================
# 12. MAINTIEN EN EXÉCUTION
# ============================================================================
query.awaitTermination()