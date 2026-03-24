#!/usr/bin/env python3
"""
Migration script to regenerate webring thumbnails with new sizes from config.yaml
Run this after changing webring_small_width or webring_tiny_width in config.yaml
"""

import os
import yaml
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# enable HEIC/HEIF support
register_heif_opener()


def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found")
        return None


def get_int_config(config, key, default):
    """Get config value as integer, handling string values from YAML"""
    value = config.get(key, default)
    if value is None:
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        try:
            if '*' in value or '+' in value or '-' in value:
                if all(c in '0123456789 +-*()' for c in value):
                    return int(eval(value))
            else:
                return int(value)
        except (ValueError, SyntaxError):
            print(f"Warning: Could not parse config value '{key}': {value}, using default: {default}")
            return default

    return default


def optimize_image(input_path, output_path, max_width):
    """
    Resize image to max_width while maintaining aspect ratio and strip metadata.
    Based on the optimize_image function from app.py
    """
    try:
        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)

            # convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # calculate new dimensions
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # save optimized image without any EXIF data
            img.save(output_path, 'JPEG', quality=85, optimize=True, exif=b"")
            return True
    except Exception as e:
        print(f"Error optimizing {input_path}: {e}")
        return False


def migrate_thumbnails():
    """Regenerate all webring thumbnails with new sizes from config"""

    # load config
    config = load_config()
    if not config:
        return

    # get configuration values
    upload_folder = config.get('upload_folder', 'uploads')
    webring_small_folder = config.get('webring_small_folder', 'uploads/webring_small')
    webring_tiny_folder = config.get('webring_tiny_folder', 'uploads/webring_tiny')
    webring_small_width = get_int_config(config, 'webring_small_width', 960)
    webring_tiny_width = get_int_config(config, 'webring_tiny_width', 256)

    print(f"Configuration:")
    print(f"  Upload folder: {upload_folder}")
    print(f"  Webring small width: {webring_small_width}px")
    print(f"  Webring tiny width: {webring_tiny_width}px")
    print()

    # check if upload folder exists
    if not os.path.exists(upload_folder):
        print(f"Error: Upload folder '{upload_folder}' does not exist")
        return

    # create thumbnail folders if they don't exist
    os.makedirs(webring_small_folder, exist_ok=True)
    os.makedirs(webring_tiny_folder, exist_ok=True)

    # get all image files from upload folder
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.heif'}
    image_files = [
        f for f in os.listdir(upload_folder)
        if os.path.isfile(os.path.join(upload_folder, f)) and
        os.path.splitext(f.lower())[1] in allowed_extensions
    ]

    if not image_files:
        print("No image files found in upload folder")
        return

    print(f"Found {len(image_files)} images to process")
    print()

    # process each image
    success_count = 0
    error_count = 0

    for i, filename in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Processing {filename}...")

        input_path = os.path.join(upload_folder, filename)
        small_path = os.path.join(webring_small_folder, filename)
        tiny_path = os.path.join(webring_tiny_folder, filename)

        # regenerate small version
        small_success = optimize_image(input_path, small_path, webring_small_width)

        # regenerate tiny version
        tiny_success = optimize_image(input_path, tiny_path, webring_tiny_width)

        if small_success and tiny_success:
            print(f"  ✓ Generated small and tiny thumbnails")
            success_count += 1
        else:
            print(f"  ✗ Failed to generate thumbnails")
            error_count += 1

    print()
    print("=" * 50)
    print(f"Migration complete!")
    print(f"  Success: {success_count} images")
    print(f"  Errors: {error_count} images")


if __name__ == '__main__':
    print("=" * 50)
    print("Webring Thumbnail Migration Script")
    print("=" * 50)
    print()

    try:
        migrate_thumbnails()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
