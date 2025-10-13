import sqlite3

# Path to your SQLite database
db_path = "/home/vedant/Desktop/Axon/backend/db.sqlite3"

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Example: Create a customers table and insert one row
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    amount_spent REAL NOT NULL
)
""")

cursor.execute("INSERT INTO customers (name, country, amount_spent) VALUES (?, ?, ?)", 
               ("Alice", "India", 1500.0))
cursor.execute("INSERT INTO customers (name, country, amount_spent) VALUES (?, ?, ?)", 
               ("Bob", "USA", 2500.0))
cursor.execute("INSERT INTO customers (name, country, amount_spent) VALUES (?, ?, ?)", 
               ("Charlie", "UK", 1200.0))

conn.commit()
conn.close()

print("Sample data inserted!")
