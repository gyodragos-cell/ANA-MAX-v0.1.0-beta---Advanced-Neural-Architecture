import sqlite3
conn = sqlite3.connect('ANA_MAX/data/events.db')
for row in conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"):
    print(row[0])
conn.close()
