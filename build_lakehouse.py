import duckdb
import os
import requests

# --- CONFIG ---
DATA_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
LOCAL_FILE = "data/yellow_tripdata_2024-01.parquet"
DB_FILE = "lakehouse.duckdb"

os.makedirs("data", exist_ok=True)

# --- STEP 1: Download raw data (Bronze source) ---
if not os.path.exists(LOCAL_FILE):
    print("Downloading NYC taxi data...")
    r = requests.get(DATA_URL, stream=True)
    with open(LOCAL_FILE, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")
else:
    print("File already exists, skipping download.")

con = duckdb.connect(DB_FILE)

# --- STEP 2: BRONZE — raw load, no changes ---
con.execute("""
    CREATE OR REPLACE TABLE bronze_taxi_trips AS
    SELECT * FROM read_parquet(?)
""", [LOCAL_FILE])

# --- STEP 3: SILVER — clean types, drop nulls/bad rows, sane column names ---
con.execute("""
    CREATE OR REPLACE TABLE silver_taxi_trips AS
    SELECT
        VendorID                      AS vendor_id,
        tpep_pickup_datetime          AS pickup_time,
        tpep_dropoff_datetime         AS dropoff_time,
        passenger_count,
        trip_distance,
        PULocationID                  AS pickup_zone_id,
        DOLocationID                  AS dropoff_zone_id,
        payment_type,
        fare_amount,
        tip_amount,
        total_amount
    FROM bronze_taxi_trips
    WHERE fare_amount > 0
      AND trip_distance > 0
      AND passenger_count IS NOT NULL
""")

# --- STEP 4: GOLD — business-ready, aggregation-friendly, agent-facing table ---
con.execute("""
    CREATE OR REPLACE TABLE gold_taxi_trips AS
    SELECT
        vendor_id,
        pickup_time,
        dropoff_time,
        DATE(pickup_time)                              AS trip_date,
        EXTRACT(HOUR FROM pickup_time)                 AS pickup_hour,
        passenger_count,
        trip_distance,
        pickup_zone_id,
        dropoff_zone_id,
        payment_type,
        fare_amount,
        tip_amount,
        total_amount,
        ROUND(tip_amount / NULLIF(fare_amount, 0), 3)  AS tip_ratio
    FROM silver_taxi_trips
""")

# --- STEP 5: Verify ---
for table in ["bronze_taxi_trips", "silver_taxi_trips", "gold_taxi_trips"]:
    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count:,} rows")

con.close()
print("\nDone. lakehouse.duckdb ready with bronze/silver/gold layers.")