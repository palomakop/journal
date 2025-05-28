import sqlite3
import os
from datetime import date, timedelta

# Create database connection
connection = sqlite3.connect('database.db')

# Create upload directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('uploads/optimized', exist_ok=True)

# Execute schema to create tables
with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

# Calculate dates for sample posts (recent dates, working backwards)
today = date.today()
first_post_date = today - timedelta(days=1)  # Yesterday
second_post_date = today  # Today

# Insert sample posts with all required columns
cur.execute("""INSERT INTO posts (title, content, post_date, is_private, image_filename, image_alt_text) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            ('First Post', 'Content for the first post', first_post_date.isoformat(), 0, None, None)
            )

cur.execute("""INSERT INTO posts (title, content, post_date, is_private, image_filename, image_alt_text) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            ('Second Post', 'Content for the second post', second_post_date.isoformat(), 0, None, None)
            )

connection.commit()
connection.close()

print("Database initialized successfully!")
print("Created directories: uploads/, uploads/optimized/")
print("Inserted 2 sample posts")
print("\nNext steps:")
print("1. Install Pillow for image optimization: pip install Pillow==10.4.0")
print("2. Start your Flask application")