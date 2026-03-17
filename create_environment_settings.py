#!/usr/bin/env python3
"""
Create environment settings table for persistent environment names
"""

import sqlite3
import os

def create_environment_settings_table():
    """Create table for storing environment settings"""
    db_path = os.getenv('DATABASE_PATH', '../users.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create environment_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environment_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                environment_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#007bff',
                icon TEXT DEFAULT 'bi-house',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default environment settings
        default_environments = [
            ('primary', 'Primary Environment', 'Main monitoring area', '#007bff', 'bi-house'),
            ('secondary', 'Secondary Environment', 'Secondary monitoring area', '#28a745', 'bi-building'),
            ('warehouse', 'Warehouse Environment', 'Warehouse and storage area', '#ffc107', 'bi-box-seam'),
            ('outdoor', 'Outdoor Environment', 'Outdoor perimeter monitoring', '#17a2b8', 'bi-tree')
        ]
        
        for env in default_environments:
            cursor.execute('''
                INSERT OR IGNORE INTO environment_settings 
                (environment_id, name, description, color, icon) 
                VALUES (?, ?, ?, ?, ?)
            ''', env)
        
        conn.commit()
        print("Environment settings table created successfully!")
        
        # Verify the data
        cursor.execute('SELECT * FROM environment_settings')
        settings = cursor.fetchall()
        print(f"Current environment settings:")
        for setting in settings:
            print(f"  {setting}")
            
    except Exception as e:
        print(f"Error creating environment settings table: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_environment_settings_table()
