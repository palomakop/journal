import sqlite3
import os
from datetime import date, timedelta

def init_database():
    """Initialize database with updated schema for multiple images support"""
    
    # Create database connection
    connection = sqlite3.connect('database.db')
    
    # Create upload directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('uploads/optimized', exist_ok=True)
    
    # Create tables with new schema
    print("Creating database tables...")
    
    # Drop existing tables if they exist
    connection.execute('DROP TABLE IF EXISTS post_images')
    connection.execute('DROP TABLE IF EXISTS posts')
    
    # Create posts table (without image columns)
    connection.execute('''
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            post_date DATE NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_private BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    # Create post_images table
    connection.execute('''
        CREATE TABLE post_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            alt_text TEXT,
            sort_order INTEGER DEFAULT 0,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
        )
    ''')
    
    print("Tables created successfully!")
    
    # Calculate dates for sample posts (recent dates, working backwards)
    today = date.today()
    first_post_date = today - timedelta(days=1)  # Yesterday
    second_post_date = today  # Today
    
    cur = connection.cursor()
    
    # Insert sample posts with all required columns (keeping original simple content)
    cur.execute("""INSERT INTO posts (title, content, post_date, is_private) 
                   VALUES (?, ?, ?, ?)""",
                ('First Post', 'Content for the first post', first_post_date.isoformat(), 0)
                )

    cur.execute("""INSERT INTO posts (title, content, post_date, is_private) 
                   VALUES (?, ?, ?, ?)""",
                ('Second Post', 'Content for the second post', second_post_date.isoformat(), 0)
                )
    
    connection.commit()
    connection.close()
    
    print("\n" + "="*50)
    print("DATABASE INITIALIZATION COMPLETE!")
    print("="*50)
    print("✅ Created database: database.db")
    print("✅ Created directories: uploads/, uploads/optimized/")
    print("✅ Inserted 2 sample posts")
    print("\nDatabase is ready for multiple images support!")
    print("Upload images through the web interface to test the new functionality.")

if __name__ == '__main__':
    init_database()