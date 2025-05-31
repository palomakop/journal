import sqlite3
import os

def fix_migration():
    """Fix the migration to properly preserve field data"""
    
    # Backup existing database
    os.system('cp database.db database_backup.db')
    print("Created backup: database_backup.db")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get existing posts with images (if any exist)
    try:
        cursor.execute("""
            SELECT id, post_date, title, content, is_private, image_filename, image_alt_text 
            FROM posts 
            WHERE image_filename IS NOT NULL
        """)
        posts_with_images = cursor.fetchall()
    except sqlite3.OperationalError:
        # If image columns don't exist, skip this
        posts_with_images = []
    
    # Get all posts data - CAREFULLY PRESERVE THE CORRECT FIELD ORDER
    cursor.execute("""
        SELECT id, created, post_date, title, content, is_private
        FROM posts
        ORDER BY id
    """)
    all_posts = cursor.fetchall()
    
    print(f"Found {len(all_posts)} posts to migrate")
    for post in all_posts[:3]:  # Show first 3 for verification
        print(f"Post {post[0]}: date={post[2]}, title='{post[3][:30]}...', private={post[5]}")
    
    # Create new tables
    cursor.execute('DROP TABLE IF EXISTS post_images')
    cursor.execute('DROP TABLE IF EXISTS posts_new')
    
    # Create new posts table without image columns
    cursor.execute("""
        CREATE TABLE posts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            post_date DATE NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_private BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    
    # Create post_images table
    cursor.execute("""
        CREATE TABLE post_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            alt_text TEXT,
            sort_order INTEGER DEFAULT 0,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
        )
    """)
    
    # Insert all posts into new table - PRESERVE CORRECT FIELD ORDER
    for post in all_posts:
        id_val, created_val, post_date_val, title_val, content_val, is_private_val = post
        cursor.execute("""
            INSERT INTO posts_new (id, created, post_date, title, content, is_private)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_val, created_val, post_date_val, title_val, content_val, is_private_val))
    
    # Insert images into post_images table (if any existed)
    for post in posts_with_images:
        post_id, _, _, _, _, image_filename, image_alt_text = post
        if image_filename:
            cursor.execute("""
                INSERT INTO post_images (post_id, filename, alt_text, sort_order)
                VALUES (?, ?, ?, 0)
            """, (post_id, image_filename, image_alt_text))
    
    # Drop old posts table and rename new one
    cursor.execute('DROP TABLE posts')
    cursor.execute('ALTER TABLE posts_new RENAME TO posts')
    
    conn.commit()
    
    # Verify the migration worked
    cursor.execute('SELECT id, post_date, title, is_private FROM posts ORDER BY id')
    migrated_posts = cursor.fetchall()
    
    print("\nMigration completed! Verification:")
    for post in migrated_posts:
        print(f"Post {post[0]}: date={post[1]}, title='{post[2][:30]}...', private={post[3]}")
    
    conn.close()
    
    print(f"\nSuccessfully migrated {len(all_posts)} posts")
    if posts_with_images:
        print(f"Migrated {len(posts_with_images)} posts with images")

if __name__ == '__main__':
    fix_migration()