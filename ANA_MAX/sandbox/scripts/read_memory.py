import sqlite3
import pprint
conn = sqlite3.connect('ana_memory.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
for t in tables:
    print(t[0])
    c.execute(f"SELECT * FROM {t[0]} LIMIT 5;")
    pprint.pprint(c.fetchall())
