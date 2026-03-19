#!/usr/bin/env python3
"""
SCOPE System Setup Script
Complete setup for the SCOPE monitoring system including:
- Database creation and population
- Environment configuration
- User setup
- System verification
"""

import sys
import os
import subprocess
import sqlite3
from datetime import datetime
import json

class SCOPESetup:
    def __init__(self):
        self.db_path = 'events.db'
        self.env_config_file = 'environment_config.json'
        
    def run_command(self, command, description, check=True):
        """Run a command and handle output"""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {command}")
        print(f"{'='*60}")
        
        try:
            if isinstance(command, str):
                command = command.split()
            
            result = subprocess.run(command, 
                                  capture_output=True, 
                                  text=True, 
                                  check=check)
            
            print("✅ SUCCESS!")
            if result.stdout:
                print("Output:")
                print(result.stdout)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ ERROR: Command failed with exit code {e.returncode}")
            if e.stderr:
                print("Error output:")
                print(e.stderr)
            return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    def check_python_version(self):
        """Check Python version compatibility"""
        print("🐍 Checking Python version...")
        if sys.version_info >= (3, 7):
            print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            return True
        else:
            print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} is not supported")
            print("Please upgrade to Python 3.7 or higher")
            return False
    
    def check_dependencies(self):
        """Check if required packages are installed"""
        print("📦 Checking dependencies...")
        
        required_packages = [
            'flask',
            'flask-session',
            'numpy',
            'google-generativeai',
            'matplotlib',
            'scikit-learn'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} - NOT INSTALLED")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install -r requirements.txt")
            return False
        
        return True
    
    def create_database(self):
        """Create and populate the database"""
        print("🗄️  Creating database...")
        
        # Run database creation
        if not self.run_command('python createEventsDatabase.py', 'Database Schema Creation'):
            return False
        
        # Run fake data generation
        if not self.run_command('python fake_data_generator.py', 'Fake Data Generation'):
            return False
        
        return True
    
    def verify_database(self):
        """Verify database structure and data"""
        print("🔍 Verifying database...")
        
        if not os.path.exists(self.db_path):
            print(f"❌ Database file not found: {self.db_path}")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['users', 'environment_settings', 'events', 'targets', 'events_log']
            
            print(f"📋 Tables found: {', '.join(tables)}")
            
            for table in expected_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  ✅ {table}: {count:,} records")
                else:
                    print(f"  ❌ {table}: MISSING")
                    return False
            
            conn.close()
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            return False
    
    def create_admin_user(self):
        """Create default admin user if not exists"""
        print("👤 Setting up admin user...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if admin exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                # Create admin user
                cursor.execute("""
                    INSERT INTO users (username, email, role, is_active, created_at)
                    VALUES ('admin', 'admin@scope.local', 'admin', 1, datetime('now'))
                """)
                conn.commit()
                print("✅ Admin user created: username='admin', password='admin123'")
            else:
                print("✅ Admin user already exists")
            
            conn.close()
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error creating admin user: {e}")
            return False
    
    def generate_environment_config(self):
        """Generate environment configuration file"""
        print("⚙️  Creating environment configuration...")
        
        config = {
            "environments": {
                "primary": {
                    "name": "Primary Zone",
                    "description": "Main monitoring area",
                    "color": "#007bff",
                    "icon": "bi-house-fill"
                },
                "secondary": {
                    "name": "Secondary Zone", 
                    "description": "Secondary monitoring area",
                    "color": "#28a745",
                    "icon": "bi-building"
                },
                "warehouse": {
                    "name": "Warehouse",
                    "description": "Storage facility monitoring",
                    "color": "#ffc107", 
                    "icon": "bi-box-seam"
                },
                "outdoor": {
                    "name": "Outdoor Area",
                    "description": "External perimeter monitoring",
                    "color": "#dc3545",
                    "icon": "bi-tree"
                }
            }
        }
        
        try:
            with open(self.env_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Environment config created: {self.env_config_file}")
            return True
        except Exception as e:
            print(f"❌ Error creating config: {e}")
            return False
    
    def run_tests(self):
        """Run basic system tests"""
        print("🧪 Running system tests...")
        
        # Test database connection
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            print("✅ Database connection test passed")
        except:
            print("❌ Database connection test failed")
            return False
        
        # Test Python imports
        try:
            import flask
            import numpy
            print("✅ Import tests passed")
        except ImportError as e:
            print(f"❌ Import test failed: {e}")
            return False
        
        return True
    
    def display_summary(self):
        """Display setup summary"""
        print(f"\n{'='*60}")
        print("🎉 SCOPE System Setup Complete!")
        print(f"{'='*60}")
        
        # Database info
        if os.path.exists(self.db_path):
            size = os.path.getsize(self.db_path)
            print(f"📁 Database: {self.db_path} ({size:,} bytes)")
        
        print(f"⚙️  Config: {self.env_config_file}")
        
        print(f"\n🚀 To start the application:")
        print(f"   python app.py")
        print(f"\n🌐 Then open your browser to:")
        print(f"   http://localhost:5000")
        print(f"\n👤 Default login:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"\n📊 Features available:")
        print(f"   • Real-time sensor monitoring")
        print(f"   • Multi-environment tracking")
        print(f"   • Threat level alerts")
        print(f"   • Analytics and reporting")
        print(f"   • User management")
        print(f"   • Dark mode toggle")
    
    def setup(self):
        """Main setup function"""
        print("🚀 SCOPE System Setup")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        steps = [
            ("Python Version Check", self.check_python_version),
            ("Dependency Check", self.check_dependencies),
            ("Database Creation", self.create_database),
            ("Database Verification", self.verify_database),
            ("Admin User Setup", self.create_admin_user),
            ("Environment Config", self.generate_environment_config),
            ("System Tests", self.run_tests)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📍 {step_name}")
            if not step_func():
                print(f"\n❌ Setup failed at: {step_name}")
                return False
        
        self.display_summary()
        return True

if __name__ == '__main__':
    setup = SCOPESetup()
    success = setup.setup()
    sys.exit(0 if success else 1)
