#!/usr/bin/env python3
"""
Script to promote a specific user to admin role by username
Usage: python promote_admin.py <username>
"""

import sqlite3
import sys
from datetime import datetime

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
        print("🔧 User Promotion Script")
        print("=" * 40)
        print("Usage: python promote_admin.py <username>")
        print("       python promote_admin.py --list")
        print("")
        print("Examples:")
        print("  python promote_admin.py john_doe")
        print("  python promote_admin.py --list")
        print("")
        
        # List all users if no arguments
        list_all_users()
        return
    
    command = sys.argv[1]
    
    if command == '--list':
        list_all_users()
        return
    
    username = command
    
    print(f"🔧 Promoting user '{username}' to admin...")
    print("=" * 50)
    
    success = promote_user_to_admin(username)
    
    if success:
        print("\n✅ Promotion completed successfully!")
        print(f"📝 User '{username}' now has admin privileges.")
        print("🌐 They can now access user management and create new accounts.")
    else:
        print("\n❌ Promotion failed!")
        print("💡 Check the username and try again.")

if __name__ == "__main__":
    main()
