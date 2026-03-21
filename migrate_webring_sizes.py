#!/usr/bin/env python3
"""
generate 960px and 256px versions of existing images.
run once to create webring-compatible versions.
"""

import sqlite3
import os
from app import (
    optimize_image,
    UPLOAD_FOLDER,
    WEBRING_SMALL_FOLDER,
    WEBRING_TINY_FOLDER,
    WEBRING_SMALL_WIDTH,
    WEBRING_TINY_WIDTH
)

def migrate_images():
    # ensure directories exist
    os.makedirs(WEBRING_SMALL_FOLDER, exist_ok=True)
    os.makedirs(WEBRING_TINY_FOLDER, exist_ok=True)

    # get all images
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    images = conn.execute('SELECT * FROM post_images ORDER BY id').fetchall()
    conn.close()

    total = len(images)
    success_small = 0
    success_tiny = 0

    print(f"found {total} images to migrate")
    print("=" * 50)

    for i, image in enumerate(images, 1):
        filename = image['filename']
        original_path = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(original_path):
            print(f"[{i}/{total}] skip: {filename} (original not found)")
            continue

        # generate webring_small version
        webring_small_path = os.path.join(WEBRING_SMALL_FOLDER, filename)
        if not os.path.exists(webring_small_path):
            if optimize_image(original_path, webring_small_path, WEBRING_SMALL_WIDTH):
                success_small += 1
                print(f"[{i}/{total}] ✓ small: {filename}")
            else:
                print(f"[{i}/{total}] ✗ small: {filename}")

        # generate webring_tiny version
        webring_tiny_path = os.path.join(WEBRING_TINY_FOLDER, filename)
        if not os.path.exists(webring_tiny_path):
            if optimize_image(original_path, webring_tiny_path, WEBRING_TINY_WIDTH):
                success_tiny += 1
                print(f"[{i}/{total}] ✓ tiny: {filename}")
            else:
                print(f"[{i}/{total}] ✗ tiny: {filename}")

    print("=" * 50)
    print(f"migration complete!")
    print(f"  webring_small: {success_small}/{total}")
    print(f"  webring_tiny: {success_tiny}/{total}")

if __name__ == '__main__':
    migrate_images()
