import sqlite3

# Buat atau buka database
conn = sqlite3.connect('accounts.db')
c = conn.cursor()

# Buat tabel akun premium
c.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        duration TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("Database dan tabel 'accounts' berhasil dibuat.")
