import sqlite3

conn = sqlite3.connect('events.db')
cursor = conn.cursor()

cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

if 'events_log' in tables:
    cursor.execute('SELECT COUNT(*) FROM events_log')
    print('Events in events_log:', cursor.fetchone()[0])
    
    cursor.execute('SELECT * FROM events_log LIMIT 3')
    sample = cursor.fetchall()
    print('Sample events:', sample)

conn.close()
