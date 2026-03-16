#!/usr/bin/env python3
"""
Script to promote a specific user to admin role by username
If user doesn't exist, offers to create a new user with admin privileges
Usage: python promote_admin.py <username>
"""

import sqlite3
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

def get_user_input(prompt, field_name, required=True):
    """Get user input with validation"""
    while True:
        value = input(f"  {prompt}: ").strip()
        if not value and required:
            print(f"  ❌ {field_name} is required!")
            continue
        if value and field_name == "Email" and "@" not in value:
            print("  ❌ Please enter a valid email address!")
            continue
        if value and field_name == "Password" and len(value) < 6:
            print("  ❌ Password must be at least 6 characters!")
            continue
        return value

def create_new_user(username):
    """Create a new user with admin privileges"""
    print(f"\n🔧 Creating new admin user '{username}'...")
    print("=" * 50)
    
    print("📝 Please provide the following details:")
    email = get_user_input("Email address", "Email")
    password = get_user_input("Password (min 6 characters)", "Password")
    name = get_user_input("Full name (optional)", "Name", required=False)
    phone = get_user_input("Phone number (optional)", "Phone", required=False)
    
    # Confirm details
    print(f"\n📋 User Details Summary:")
    print(f"  Username: {username}")
    print(f"  Email: {email}")
    print(f"  Name: {name or 'Not provided'}")
    print(f"  Phone: {phone or 'Not provided'}")
    print(f"  Role: admin")
    print(f"  Status: active")
    
    confirm = input(f"\n✅ Create this user? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ User creation cancelled.")
        return False
    
    # Create user in database
    database_path = 'events.db'
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE emailAddress = ?", (email,))
        if cursor.fetchone():
            print(f"❌ Email '{email}' is already in use!")
            return False
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password, emailAddress, role, accountStatus, 
                              dateJoined, name, phoneNumber, lastLogin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, password_hash, email, 'admin', 'active', 
              datetime.now().isoformat(), name, phone, datetime.now().isoformat()))
        
        conn.commit()
        
        print(f"✅ Successfully created admin user '{username}'!")
        print(f"📅 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 User can now login with admin privileges.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def promote_user_to_admin(username):
    """Promote a user to admin role"""
    
    database_path = 'events.db'
    
    try:
        # Connect to database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, username, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User '{username}' not found in database.")
            print("\n📋 Available users:")
            cursor.execute("SELECT id, username, role FROM users")
            users = cursor.fetchall()
            for u in users:
                status = "👑 ADMIN" if u[2] == 'admin' else "👤 USER"
                print(f"  • ID: {u[0]}, Username: {u[1]}, Role: {status}")
            
            # Ask if user wants to create a new user
            create_new = input(f"\n❓ Create new admin user '{username}'? (y/N): ").strip().lower()
            if create_new in ['y', 'yes']:
                return create_new_user(username)
            else:
                print("❌ Operation cancelled.")
                return False
        
        user_id, current_username, current_role = user
        
        # Check if already admin
        if current_role == 'admin':
            print(f"✅ User '{username}' is already an admin.")
            return True
        
        # Promote to admin
        cursor.execute("""
            UPDATE users 
            SET role = 'admin', 
                lastLogin = ?
            WHERE username = ?
        """, (datetime.now().isoformat(), username))
        
        conn.commit()
        
        print(f"✅ Successfully promoted '{username}' to admin role!")
        print(f"📅 Promotion timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show updated user info
        cursor.execute("SELECT id, username, role, accountStatus FROM users WHERE username = ?", (username,))
        updated_user = cursor.fetchone()
        print(f"👤 Updated user: ID={updated_user[0]}, Username='{updated_user[1]}', Role='{updated_user[2]}', Status='{updated_user[3]}'")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def list_all_users():
    """List all users in the database"""
    
    database_path = 'events.db'
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, emailAddress, role, accountStatus, dateJoined 
            FROM users 
            ORDER BY id
        """)
        users = cursor.fetchall()
        
        print("\n📋 All Users:")
        print("-" * 80)
        print(f"{'ID':<4} {'Username':<15} {'Email':<25} {'Role':<8} {'Status':<10} {'Joined':<20}")
        print("-" * 80)
        
        for user in users:
            role_icon = "👑" if user[3] == 'admin' else "👤"
            status_icon = "✅" if user[4] == 'active' else "⚠️"
            
            print(f"{user[0]:<4} {user[1]:<15} {user[2]:<25} {role_icon} {user[3]:<7} {status_icon} {user[4]:<9} {user[5][:19]:<20}")
        
        print("-" * 80)
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        
    finally:
        if conn:
            conn.close()

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("🔧 User Promotion/Creation Script")
        print("=" * 40)
        print("Usage: python promote_admin.py <username>")
        print("       python promote_admin.py --list")
        print("")
        print("Examples:")
        print("  python promote_admin.py john_doe")
        print("  python promote_admin.py --list")
        print("")
        print("Features:")
        print("  • Promotes existing users to admin")
        print("  • Creates new admin users if they don't exist")
        print("  • Interactive user creation with validation")
        print("")
        
        # List all users if no arguments
        list_all_users()
        return
    
    command = sys.argv[1]
    
    if command == '--list':
        list_all_users()
        return
    
    username = command
    
    print(f"🔧 Managing admin access for user '{username}'...")
    print("=" * 50)
    
    success = promote_user_to_admin(username)
    
    if success:
        print("\n✅ Operation completed successfully!")
        print(f"📝 User '{username}' now has admin privileges.")
        print("🌐 They can now access user management and create new accounts.")
    else:
        print("\n❌ Operation failed!")
        print("💡 Check the username and try again.")

if __name__ == "__main__":
    main()
