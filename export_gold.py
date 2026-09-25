import duckdb

con = duckdb.connect("lakehouse.duckdb", read_only=True)
con.execute("COPY gold_taxi_trips TO 'gold_taxi_trips.csv' (HEADER, DELIMITER ',')")
con.close()
print("Exported gold_taxi_trips.csv")