#!/usr/bin/env python3
"""
SCOPE Database Build Script
This script sets up the database and populates it with initial data.
"""

import sys
import os
import subprocess
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")
    
    try:
        # Run the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        
        print("✅ SUCCESS!")
        if result.stdout:
            print("Output:")
            print(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR running {script_name}")
        print(f"Exit code: {e.returncode}")
        print("Error output:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ ERROR: Script {script_name} not found!")
        return False
    
    return True

def check_database_exists():
    """Check if the database file exists"""
    db_path = 'events.db'
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"📁 Database file exists: {db_path} ({size:,} bytes)")
        return True
    else:
        print(f"📁 Database file not found: {db_path}")
        return False

def main():
    """Main build function"""
    print("🚀 SCOPE Database Build Script")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we're in the right directory
    if not os.path.exists('createEventsDatabase.py'):
        print("❌ ERROR: createEventsDatabase.py not found in current directory!")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    # Step 1: Create database schema
    if not run_script('createEventsDatabase.py', 'Database Schema Creation'):
        print("\n❌ Database creation failed. Aborting build.")
        sys.exit(1)
    
    # Step 2: Generate fake data
    if not run_script('fake_data_generator.py', 'Fake Data Generation'):
        print("\n❌ Fake data generation failed.")
        sys.exit(1)
    
    # Step 3: Verify database
    print(f"\n{'='*60}")
    print("🔍 Verification")
    print(f"{'='*60}")
    
    if check_database_exists():
        print("✅ Database build completed successfully!")
        print("\n📊 Next steps:")
        print("1. Run the Flask application: python app.py")
        print("2. Open your browser and navigate to: http://localhost:5000")
        print("3. Login with the default credentials (check app.py for details)")
    else:
        print("❌ Database file was not created successfully!")
        sys.exit(1)
    
    print(f"\n✨ Build completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
