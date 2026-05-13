
import duckdb
from pathlib import Path

FOLDER = Path(r"C:\Users\uludoh\Documents\DB-PARQUET\chunks_data")
GLOB   = str(FOLDER / "**" / "*.parquet").replace("\\", "/")

conn = duckdb.connect()

# Test 1: how many parquet files found?
print("Parquet files found:", len(list(FOLDER.rglob("*.parquet"))))

# Test 2: what years are available?
years = conn.execute(f"""
    SELECT DISTINCT ExamYear
    FROM read_parquet('{GLOB}', hive_partitioning=true)
    ORDER BY ExamYear
""").fetchall()
print("Years available:", [r[0] for r in years])

# Test 3: total row count
count = conn.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{GLOB}', hive_partitioning=true)
""").fetchone()[0]
print(f"Total rows: {count:,}")

# Test 4: filtered query — one year only
df = conn.execute(f"""
    SELECT * FROM read_parquet('{GLOB}', hive_partitioning=true)
    WHERE ExamYear = 1980
    LIMIT 5
""").df()
print(df)
conn.close()