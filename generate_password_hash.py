#!/usr/bin/env python3
"""
script to generate a password hash for your admin password
run this once to generate the hash, then put it in your .env file
"""

from werkzeug.security import generate_password_hash
import getpass

def generate_admin_password_hash():
    """generate a password hash for the admin password"""

    print("=== password hash generator ===")
    print("this will generate a secure hash of your password.")

    # get password from user (hidden input)
    password = getpass.getpass("enter your admin password: ")
    confirm_password = getpass.getpass("confirm your admin password: ")

    if password != confirm_password:
        print("❌ passwords don't match. please try again.")
        return

    if len(password) < 8:
        print("❌ password should be at least 8 characters long.")
        return

    # generate the hash
    password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    print("\n✅ password hash generated successfully!")
    print("\n" + "="*60)
    print("add this line to your .env file:")
    print("="*60)
    print(f"ADMIN_PASSWORD_HASH='{password_hash}'")
    print("="*60)

    print(f"\nHash length: {len(password_hash)} characters")

if __name__ == "__main__":
    generate_admin_password_hash()