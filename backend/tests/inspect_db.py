import sqlite3

conn = sqlite3.connect("data/arc_vision.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]
print(f"Total Tables in SQLite: {len(tables)}")
for t in sorted(tables):
    if not t.startswith("sqlite_"):
        cursor.execute(f"SELECT count(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        print(f"  Table '{t}': {cnt} rows")
