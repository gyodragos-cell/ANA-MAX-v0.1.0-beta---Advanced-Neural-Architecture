#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path("ANA_MAX/data/events.db")
conn = sqlite3.connect(DB)
cur = conn.cursor()

def count(t):
    try:
        return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except:
        return 0

tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]

print("\n=== ANA MAX DATABASE DASHBOARD ===")
print("Tables:", len(tables))

for t in tables:
    print(f"{t}: {count(t)} rows")

print("\nTop events:")
try:
    rows = cur.execute(
        "SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY COUNT(*) DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(r)
except:
    print("No events table.")

conn.close()
