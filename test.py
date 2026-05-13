import duckdb
from pathlib import Path

FOLDER = Path(r"C:\Users\uludoh\Documents\DB-PARQUET\chunks_data")
GLOB = str(FOLDER / "**" / "*.parquet").replace("\\", "/")

conn = duckdb.connect()
df = conn.execute(f"""
    SELECT * FROM read_parquet('{GLOB}', hive_partitioning=true)
    WHERE ExamYear = 1980
    LIMIT 1
""").df()

print(list(df.columns))
conn.close()