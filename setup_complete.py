#!/usr/bin/env python3
"""
SCOPE System Complete Setup Script
This single script contains all functionality from:
- createEventsDatabase.py
- fake_data_generator.py
- Additional setup and verification features

Complete setup for the SCOPE monitoring system including:
- Database creation and population
- User setup
- Environment configuration
- System verification
"""

import sys
import os
import subprocess
import sqlite3
import random
import time
from datetime import datetime, timedelta
import numpy as np
import json

# Configuration
DB_PATH = 'events.db'
DAYS_OF_HISTORY = 7
EVENTS_PER_DAY = 50
TARGETS_PER_EVENT = 2

# Threat levels and their probabilities
THREAT_LEVELS = {
    'LOW': 0.45,
    'MODERATE': 0.25,
    'ELEVATED': 0.15,
    'HIGH': 0.10,
    'CRITICAL': 0.05
}

# Event types and their probabilities
EVENT_TYPES = {
    'CRITICAL_THREAT': 0.03,
    'HIGH_THREAT': 0.05,
    'RAPID_ESCALATION': 0.07,
    'ABNORMAL_VITALS': 0.10,
    'POOR_AIR_QUALITY': 0.15,
    'SOUND_SPIKE': 0.20,
    'PERSON_ENTRY': 0.20,
    'PERSON_EXIT': 0.20,
}

# Activity types
ACTIVITIES = ['stationary', 'sitting', 'walking', 'running', 'transition']

class SCOPESetup:
    """Complete SCOPE system setup with integrated database creation and data generation"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.conn = None
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
    
    def connect_to_database(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close_database(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    # ==================== DATABASE CREATION (from createEventsDatabase.py) ====================
    
    def create_database_schema(self):
        """Create the complete database schema"""
        print("🗄️  Creating database schema...")
        
        # Clear existing database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print("  🗑️  Removed existing database")
        
        # Create new database connection
        self.connect_to_database()
        cursor = self.conn.cursor()
        
        # Environment Settings Table
        environment_settings_fields = [
            "environment_id TEXT PRIMARY KEY",
            "name TEXT NOT NULL",
            "description TEXT",
            "color TEXT DEFAULT '#007bff'",
            "icon TEXT DEFAULT 'bi-house'",
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        environment_settings_create = "CREATE TABLE environment_settings (" + ", ".join(environment_settings_fields) + ")"
        cursor.execute(environment_settings_create)
        
        # Insert default environment settings
        default_environments = [
            ('primary', 'Primary Environment', 'Main monitoring area', '#007bff', 'bi-house'),
            ('secondary', 'Secondary Environment', 'Secondary monitoring area', '#28a745', 'bi-building'),
            ('warehouse', 'Warehouse Environment', 'Warehouse and storage area', '#ffc107', 'bi-box-seam'),
            ('outdoor', 'Outdoor Environment', 'Outdoor perimeter monitoring', '#17a2b8', 'bi-tree')
        ]
        
        for env in default_environments:
            cursor.execute("""
                INSERT OR REPLACE INTO environment_settings 
                (environment_id, name, description, color, icon) 
                VALUES (?, ?, ?, ?, ?)
            """, env)
        
        # Users Table
        users_fields = [
            "username TEXT NOT NULL",
            "password TEXT NOT NULL",
            "dateJoined TEXT",
            "salt TEXT",
            "accountStatus TEXT",
            "role TEXT",
            "twoFactorAuth INTEGER",
            "lastLogin TEXT",
            "emailAddress TEXT",
            "phoneNumber TEXT",
            "name TEXT",
            "dateOfBirth TEXT",
            "gender TEXT",
            "is_active INTEGER DEFAULT 1",
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        users_create = "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(users_fields) + ")"
        cursor.execute(users_create)
        
        # Events Table (Complete SCOPE Data)
        events_fields = [
            "timestamp TEXT NOT NULL",
            "threat_overall REAL",
            "threat_base REAL",
            "threat_level TEXT",
            "threat_color TEXT",
            "threat_response TEXT",
            "threat_confidence REAL",
            "temporal_trend TEXT",
            "temporal_slope REAL",
            "temporal_acceleration REAL",
            "temporal_volatility REAL",
            "temporal_persistence_factor REAL",
            "trajectory_5min REAL",
            "trajectory_15min REAL",
            "trajectory_30min REAL",
            "proximity_score REAL",
            "proximity_raw REAL",
            "proximity_confidence REAL",
            "proximity_weight REAL",
            "count_score REAL",
            "count_raw REAL",
            "count_confidence REAL",
            "count_weight REAL",
            "behavior_score REAL",
            "behavior_raw REAL",
            "behavior_confidence REAL",
            "behavior_weight REAL",
            "vital_signs_score REAL",
            "vital_signs_raw REAL",
            "vital_signs_confidence REAL",
            "vital_signs_weight REAL",
            "air_quality_score REAL",
            "air_quality_raw REAL",
            "air_quality_confidence REAL",
            "air_quality_weight REAL",
            "noise_score REAL",
            "noise_raw REAL",
            "noise_confidence REAL",
            "noise_weight REAL",
            "quality_score REAL",
            "quality_base REAL",
            "quality_category TEXT",
            "quality_icon TEXT",
            "quality_trend TEXT",
            "quality_sound_adjust REAL",
            "quality_air_adjust REAL",
            "quality_occupancy_adjust REAL",
            "sound_db REAL",
            "sound_baseline REAL",
            "sound_spike INTEGER",
            "sound_rate_of_change REAL",
            "sound_event TEXT",
            "sound_confidence REAL",
            "sound_dominant_freq REAL",
            "sound_spectral_energy REAL",
            "sound_spectral_centroid REAL",
            "sound_peak REAL",
            "sound_zero_crossings REAL",
            "sound_spectral_spread REAL",
            "sound_skewness REAL",
            "sound_kurtosis REAL",
            "sound_low_energy REAL",
            "sound_mid_energy REAL",
            "sound_high_energy REAL",
            "air_voc_ppm REAL",
            "air_voc_voltage REAL",
            "air_pm1 INTEGER",
            "air_pm25 INTEGER",
            "air_pm10 INTEGER",
            "air_aqi REAL",
            "air_odor_type TEXT",
            "air_odor_confidence REAL",
            "air_odor_intensity REAL",
            "air_odor_level TEXT",
            "air_odor_trend REAL",
            "air_baseline_intensity REAL",
            "air_odor_anomaly INTEGER",
            "radar_target_count INTEGER",
            "radar_format TEXT",
            "motion_pattern TEXT",
            "motion_activity_level REAL",
            "motion_total_targets INTEGER",
            "motion_active_targets INTEGER",
            "activity_events TEXT",
            "radar_targets TEXT",
            "physical_risk REAL",
            "health_risk REAL",
            "facility_risk REAL",
            "danger_index REAL",
            "comfort_index REAL",
            "urgency_score REAL",
            "sensor_radar_connected INTEGER",
            "sensor_pms_connected INTEGER",
            "sensor_mq135_connected INTEGER",
            "sensor_sound_connected INTEGER",
            "alert_critical_threat INTEGER",
            "alert_high_threat INTEGER",
            "alert_rapid_escalation INTEGER",
            "alert_abnormal_vitals INTEGER",
            "alert_air_quality INTEGER",
            "notes TEXT",
            "environment_id TEXT DEFAULT 'primary'"
        ]
        
        events_create = "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(events_fields) + ")"
        cursor.execute(events_create)
        
        # Targets Table
        targets_fields = [
            "event_id INTEGER",
            "timestamp TEXT NOT NULL",
            "target_id TEXT",
            "target_x REAL",
            "target_y REAL",
            "target_distance REAL",
            "target_angle REAL",
            "target_velocity REAL",
            "target_direction TEXT",
            "target_orientation TEXT",
            "target_confidence REAL",
            "target_activity TEXT",
            "target_activity_confidence REAL",
            "target_breathing_rate REAL",
            "target_breathing_confidence REAL",
            "target_abnormal_breathing INTEGER",
            "target_vx REAL",
            "target_vy REAL",
            "target_ax REAL",
            "target_ay REAL",
            "target_speed REAL"
        ]
        
        targets_create = "CREATE TABLE targets (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(targets_fields) + ")"
        cursor.execute(targets_create)
        
        # Events Log Table
        events_log_fields = [
            "timestamp TEXT NOT NULL",
            "threat_level TEXT",
            "threat_score REAL",
            "quality_score REAL",
            "people_count INTEGER",
            "sound_db REAL",
            "air_aqi REAL",
            "event_type TEXT",
            "description TEXT",
            "temperature REAL"
        ]
        
        events_log_create = "CREATE TABLE events_log (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(events_log_fields) + ")"
        cursor.execute(events_log_create)
        
        # Create Indexes
        cursor.execute("CREATE INDEX idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX idx_events_threat_level ON events(threat_level)")
        cursor.execute("CREATE INDEX idx_events_quality_score ON events(quality_score)")
        cursor.execute("CREATE INDEX idx_targets_event_id ON targets(event_id)")
        cursor.execute("CREATE INDEX idx_targets_target_id ON targets(target_id)")
        cursor.execute("CREATE INDEX idx_events_log_timestamp ON events_log(timestamp)")
        
        self.conn.commit()
        print("  ✅ Database schema created successfully")
        return True
    
    # ==================== FAKE DATA GENERATION (from fake_data_generator.py) ====================
    
    def generate_threat_score(self, base_level=None):
        """Generate realistic threat score based on level"""
        if base_level == 'LOW':
            return random.uniform(5, 25)
        elif base_level == 'MODERATE':
            return random.uniform(25, 45)
        elif base_level == 'ELEVATED':
            return random.uniform(45, 65)
        elif base_level == 'HIGH':
            return random.uniform(65, 85)
        elif base_level == 'CRITICAL':
            return random.uniform(85, 100)
        else:
            r = random.random()
            if r < 0.4:
                return random.uniform(5, 25)
            elif r < 0.65:
                return random.uniform(25, 45)
            elif r < 0.8:
                return random.uniform(45, 65)
            elif r < 0.95:
                return random.uniform(65, 85)
            else:
                return random.uniform(85, 100)
    
    def generate_threat_level(self, score=None):
        """Generate threat level based on score"""
        if score is None:
            score = self.generate_threat_score()
        
        if score < 25:
            return 'LOW'
        elif score < 45:
            return 'MODERATE'
        elif score < 65:
            return 'ELEVATED'
        elif score < 85:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def get_threat_color(self, level):
        """Get threat color emoji"""
        colors = {
            'LOW': '🟢',
            'MODERATE': '🟡',
            'ELEVATED': '🟠',
            'HIGH': '🔴',
            'CRITICAL': '⚫'
        }
        return colors.get(level, '⚪')
    
    def get_quality_category(self, score):
        """Get quality category based on score"""
        if score >= 90:
            return 'EXCELLENT'
        elif score >= 75:
            return 'GOOD'
        elif score >= 60:
            return 'FAIR'
        elif score >= 40:
            return 'POOR'
        else:
            return 'CRITICAL'
    
    def get_quality_icon(self, category):
        """Get quality icon based on category"""
        icons = {
            'EXCELLENT': '🌟',
            'GOOD': '✅',
            'FAIR': '⚠️',
            'POOR': '🔴',
            'CRITICAL': '🚨'
        }
        return icons.get(category, '❓')
    
    def generate_sound_data(self, base_threat=None):
        """Generate realistic sound data"""
        if base_threat is None:
            base_threat = self.generate_threat_score()
        
        # Base sound level with threat influence
        base_db = 30 + (base_threat * 0.5)
        
        # Add random variation
        sound_db = base_db + random.uniform(-10, 10)
        sound_db = max(0, min(120, sound_db))
        
        # Spike detection
        spike = 1 if random.random() < 0.15 else 0
        if spike:
            sound_db = min(120, sound_db + random.uniform(20, 40))
        
        # Event classification
        if sound_db < 40:
            event = 'quiet'
        elif sound_db < 60:
            event = 'conversation'
        elif sound_db < 80:
            event = 'crowd'
        elif sound_db < 100:
            event = 'door_slam'
        elif sound_db < 110:
            event = 'shouting'
        else:
            event = 'impact'
        
        # FFT features
        dominant_freq = random.uniform(100, 4000)
        spectral_energy = random.uniform(0.1, 1.0)
        spectral_centroid = random.uniform(500, 2000)
        peak = random.uniform(0.1, 1.0)
        zero_crossings = int(random.uniform(50, 500))
        spectral_spread = random.uniform(0.1, 1.0)
        skewness = random.uniform(-2, 2)
        kurtosis = random.uniform(-2, 4)
        
        # Energy distribution
        total_energy = spectral_energy
        low_energy = total_energy * random.uniform(0.3, 0.5)
        mid_energy = total_energy * random.uniform(0.3, 0.4)
        high_energy = total_energy - low_energy - mid_energy
        
        return {
            'db': sound_db,
            'baseline': random.uniform(20, 40),
            'spike': spike,
            'rate_of_change': random.uniform(-5, 5),
            'event': event,
            'confidence': random.uniform(0.7, 0.95),
            'dominant_freq': dominant_freq,
            'spectral_energy': spectral_energy,
            'spectral_centroid': spectral_centroid,
            'peak': peak,
            'zero_crossings': zero_crossings,
            'spectral_spread': spectral_spread,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'low_energy': low_energy,
            'mid_energy': mid_energy,
            'high_energy': high_energy
        }
    
    def generate_air_quality_data(self, base_threat=None):
        """Generate realistic air quality data"""
        if base_threat is None:
            base_threat = self.generate_threat_score()
        
        # VOC data
        voc_voltage = random.uniform(0.2, 4.0)
        voc_ppm = voc_voltage * 100  # Rough conversion
        
        # PM data
        pm1 = int(random.uniform(0, 50))
        pm25 = int(random.uniform(0, 100))
        pm10 = int(random.uniform(0, 150))
        
        # Calculate AQI (simplified)
        if pm25 > 35:
            aqi = min(500, int((pm25 - 35) * 4.17 + 50))
        else:
            aqi = int(pm25 * 1.4)
        
        # Odor classification
        odor_types = ['none', 'chemical', 'organic', 'smoke', 'cooking', 'sewage', 'industrial']
        odor_type = random.choice(odor_types)
        
        # Odor intensity and level
        if odor_type == 'none':
            odor_intensity = 0
            odor_level = 'LOW'
        else:
            odor_intensity = random.uniform(1, 10)
            if odor_intensity < 3:
                odor_level = 'LOW'
            elif odor_intensity < 6:
                odor_level = 'MODERATE'
            elif odor_intensity < 8:
                odor_level = 'HIGH'
            else:
                odor_level = 'SEVERE'
        
        # Trend and anomaly detection
        odor_trend = random.uniform(-2, 2)
        baseline_intensity = odor_intensity * random.uniform(0.8, 1.2)
        anomaly = 1 if random.random() < 0.1 else 0
        
        return {
            'voc_ppm': voc_ppm,
            'voc_voltage': voc_voltage,
            'pm1': pm1,
            'pm25': pm25,
            'pm10': pm10,
            'aqi': aqi,
            'type': odor_type,
            'confidence': random.uniform(0.6, 0.9),
            'intensity': odor_intensity,
            'level': odor_level,
            'trend': odor_trend,
            'baseline_intensity': baseline_intensity,
            'anomaly': anomaly
        }
    
    def generate_radar_targets(self, target_count, base_threat=None):
        """Generate realistic radar target data"""
        targets = []
        
        for i in range(target_count):
            target_id = f"T{i:02d}"
            
            # Position (polar coordinates)
            distance = random.uniform(1, 15)
            angle = random.uniform(-180, 180)
            x = distance * np.cos(np.radians(angle))
            y = distance * np.sin(np.radians(angle))
            
            # Velocity and movement
            velocity = random.uniform(0, 2)
            vx = velocity * np.cos(np.radians(angle))
            vy = velocity * np.sin(np.radians(angle))
            
            # Direction
            if abs(vx) > 0.1:
                direction = 'incoming' if vx < 0 else 'outgoing'
            else:
                direction = 'stationary'
            
            # Orientation
            if abs(vx) > 0.1:
                orientation = 'toward' if vx < 0 else 'away'
            else:
                orientation = 'stationary'
            
            # Activity
            activity = random.choice(ACTIVITIES)
            
            # Breathing data (if person is stationary or slow)
            if activity in ['stationary', 'sitting'] and random.random() < 0.3:
                breathing_rate = random.uniform(12, 20)
                abnormal_breathing = 1 if breathing_rate < 10 or breathing_rate > 25 else 0
            else:
                breathing_rate = random.uniform(15, 25)
                abnormal_breathing = 0
            
            return {
                'target_id': target_id,
                'x': x,
                'y': y,
                'distance': distance,
                'angle': angle,
                'velocity': velocity,
                'vx': vx,
                'vy': vy,
                'direction': direction,
                'orientation': orientation,
                'confidence': random.uniform(0.6, 0.95),
                'activity': activity,
                'activity_confidence': random.uniform(0.7, 0.95),
                'breathing_rate': breathing_rate,
                'breathing_confidence': random.uniform(0.5, 0.8),
                'abnormal_breathing': abnormal_breathing,
                'speed': velocity
            }
    
    def generate_temporal_dynamics(self, base_threat):
        """Generate temporal dynamics data"""
        # Trend
        trends = ['stable', 'worsening', 'rapidly_worsening', 'improving', 'rapidly_improving']
        trend = random.choice(trends)
        
        # Slope and acceleration
        if trend == 'stable':
            slope = random.uniform(-0.5, 0.5)
            acceleration = random.uniform(-0.1, 0.1)
        elif 'worsening' in trend:
            slope = random.uniform(0.5, 3)
            acceleration = random.uniform(0.1, 1.0) if 'rapidly' in trend else random.uniform(-0.1, 0.3)
        else:  # improving
            slope = random.uniform(-3, -0.5)
            acceleration = random.uniform(-1.0, -0.1) if 'rapidly' in trend else random.uniform(-0.3, 0.1)
        
        # Volatility
        volatility = random.uniform(5, 25)
        
        # Persistence factor
        persistence = 1.0 + (base_threat / 100) * random.uniform(0, 1.0)
        
        # Trajectory predictions
        trajectory_5min = base_threat + (slope * 5) + (0.5 * acceleration * 25)
        trajectory_15min = base_threat + (slope * 15) + (0.5 * acceleration * 225)
        trajectory_30min = base_threat + (slope * 30) + (0.5 * acceleration * 900)
        
        # Clamp to valid range
        trajectory_5min = max(0, min(100, trajectory_5min))
        trajectory_15min = max(0, min(100, trajectory_15min))
        trajectory_30min = max(0, min(100, trajectory_30min))
        
        return {
            'trend': trend,
            'slope': slope,
            'acceleration': acceleration,
            'volatility': volatility,
            'persistence_factor': persistence,
            'trajectory_5min': trajectory_5min,
            'trajectory_15min': trajectory_15min,
            'trajectory_30min': trajectory_30min
        }
    
    def generate_threat_components(self, base_threat):
        """Generate individual threat component scores"""
        # Proximity threat
        proximity_raw = base_threat * random.uniform(0.8, 1.2)
        proximity_confidence = random.uniform(0.6, 0.9)
        proximity_weight = random.uniform(0.2, 0.4)
        proximity_score = proximity_raw * proximity_weight
        
        # Count threat
        count_raw = base_threat * random.uniform(0.7, 1.3)
        count_confidence = random.uniform(0.7, 0.95)
        count_weight = random.uniform(0.15, 0.35)
        count_score = count_raw * count_weight
        
        # Behavior threat
        behavior_raw = base_threat * random.uniform(0.6, 1.4)
        behavior_confidence = random.uniform(0.5, 0.85)
        behavior_weight = random.uniform(0.1, 0.3)
        behavior_score = behavior_raw * behavior_weight
        
        # Vital signs threat
        vital_signs_raw = base_threat * random.uniform(0.5, 1.5)
        vital_signs_confidence = random.uniform(0.4, 0.8)
        vital_signs_weight = random.uniform(0.1, 0.25)
        vital_signs_score = vital_signs_raw * vital_signs_weight
        
        # Air quality threat
        air_quality_raw = base_threat * random.uniform(0.4, 1.6)
        air_quality_confidence = random.uniform(0.6, 0.9)
        air_quality_weight = random.uniform(0.15, 0.35)
        air_quality_score = air_quality_raw * air_quality_weight
        
        # Noise threat
        noise_raw = base_threat * random.uniform(0.3, 1.7)
        noise_confidence = random.uniform(0.7, 0.95)
        noise_weight = random.uniform(0.1, 0.3)
        noise_score = noise_raw * noise_weight
        
        return {
            'proximity': {
                'raw': proximity_raw,
                'score': proximity_score,
                'confidence': proximity_confidence,
                'weight': proximity_weight
            },
            'count': {
                'raw': count_raw,
                'score': count_score,
                'confidence': count_confidence,
                'weight': count_weight
            },
            'behavior': {
                'raw': behavior_raw,
                'score': behavior_score,
                'confidence': behavior_confidence,
                'weight': behavior_weight
            },
            'vital_signs': {
                'raw': vital_signs_raw,
                'score': vital_signs_score,
                'confidence': vital_signs_confidence,
                'weight': vital_signs_weight
            },
            'air_quality': {
                'raw': air_quality_raw,
                'score': air_quality_score,
                'confidence': air_quality_confidence,
                'weight': air_quality_weight
            },
            'noise': {
                'raw': noise_raw,
                'score': noise_score,
                'confidence': noise_confidence,
                'weight': noise_weight
            }
        }
    
    def generate_quality_metrics(self, base_threat):
        """Generate facility quality metrics"""
        # Base quality inversely related to threat
        base_quality = 100 - base_threat
        
        # Adjustments for different factors
        sound_adjust = random.uniform(-10, 10)
        air_adjust = random.uniform(-15, 15)
        occupancy_adjust = random.uniform(-5, 5)
        
        quality_score = base_quality + sound_adjust + air_adjust + occupancy_adjust
        quality_score = max(0, min(100, quality_score))
        
        return {
            'base': base_quality,
            'score': quality_score,
            'category': self.get_quality_category(quality_score),
            'icon': self.get_quality_icon(self.get_quality_category(quality_score)),
            'trend': random.choice(['improving', 'stable', 'declining']),
            'sound_adjust': sound_adjust,
            'air_adjust': air_adjust,
            'occupancy_adjust': occupancy_adjust
        }
    
    def generate_motion_patterns(self, target_count, base_threat):
        """Generate motion pattern data"""
        # Activity level
        active_targets = int(target_count * random.uniform(0.3, 0.8))
        activity_level = active_targets / max(1, target_count)
        
        # Pattern classification
        if target_count == 0:
            pattern = 'no_detections'
        elif activity_level < 0.2:
            pattern = 'low_activity'
        elif activity_level < 0.5:
            pattern = 'normal_activity'
        elif activity_level < 0.8:
            pattern = 'high_activity'
        else:
            pattern = 'chaotic'
        
        return {
            'pattern': pattern,
            'activity_level': activity_level,
            'total_targets': target_count,
            'active_targets': active_targets
        }
    
    def generate_alerts(self, threat_level, threat_score, air_aqi, vital_signs):
        """Generate alert flags"""
        return {
            'critical_threat': 1 if threat_score > 80 else 0,
            'high_threat': 1 if threat_score > 60 else 0,
            'rapid_escalation': 1 if threat_level in ['HIGH', 'CRITICAL'] and random.random() < 0.3 else 0,
            'abnormal_vitals': 1 if vital_signs and vital_signs < 10 else 0,
            'air_quality': 1 if air_aqi > 150 else 0
        }
    
    def generate_sensor_status(self):
        """Generate sensor connectivity status"""
        return {
            'radar': 1 if random.random() < 0.95 else 0,
            'pms': 1 if random.random() < 0.9 else 0,
            'mq135': 1 if random.random() < 0.85 else 0,
            'sound': 1 if random.random() < 0.95 else 0
        }
    
    def generate_event_record(self, timestamp, environment_id='primary'):
        """Generate a complete event record"""
        # Base threat score
        base_threat = self.generate_threat_score()
        threat_level = self.generate_threat_level(base_threat)
        
        # Generate all components
        temporal = self.generate_temporal_dynamics(base_threat)
        threat_components = self.generate_threat_components(base_threat)
        quality = self.generate_quality_metrics(base_threat)
        sound_data = self.generate_sound_data(base_threat)
        air_data = self.generate_air_quality_data(base_threat)
        
        # Radar data
        target_count = random.randint(0, 8)
        radar_targets = []
        for i in range(target_count):
            radar_targets.append(self.generate_radar_targets(1, base_threat))
        
        motion = self.generate_motion_patterns(target_count, base_threat)
        
        # Alerts
        alerts = self.generate_alerts(
            threat_level, 
            base_threat, 
            air_data['aqi'], 
            None  # Would need vital signs data
        )
        
        # Sensor status
        sensors = self.generate_sensor_status()
        
        # Derived metrics
        physical_risk = (threat_components['proximity']['score'] + 
                       threat_components['count']['score'] + 
                       threat_components['behavior']['score']) / 3
        health_risk = (threat_components['vital_signs']['score'] + 
                      threat_components['air_quality']['score']) / 2
        facility_risk = (threat_components['noise']['score'] + 
                        threat_components['air_quality']['score']) / 2
        danger_index = base_threat * temporal['persistence_factor']
        comfort_index = 100 - (base_threat * 0.5)
        urgency_score = base_threat * (1 + abs(temporal['slope']) / 10)
        
        # Create event record
        event = {
            'timestamp': timestamp.isoformat(),
            'threat_overall': base_threat,
            'threat_base': base_threat,
            'threat_level': threat_level,
            'threat_color': self.get_threat_color(threat_level),
            'threat_response': self.get_threat_response(threat_level),
            'threat_confidence': random.uniform(0.7, 0.95),
            'temporal_trend': temporal['trend'],
            'temporal_slope': temporal['slope'],
            'temporal_acceleration': temporal['acceleration'],
            'temporal_volatility': temporal['volatility'],
            'temporal_persistence_factor': temporal['persistence_factor'],
            'trajectory_5min': temporal['trajectory_5min'],
            'trajectory_15min': temporal['trajectory_15min'],
            'trajectory_30min': temporal['trajectory_30min'],
            'proximity_score': threat_components['proximity']['score'],
            'proximity_raw': threat_components['proximity']['raw'],
            'proximity_confidence': threat_components['proximity']['confidence'],
            'proximity_weight': threat_components['proximity']['weight'],
            'count_score': threat_components['count']['score'],
            'count_raw': threat_components['count']['raw'],
            'count_confidence': threat_components['count']['confidence'],
            'count_weight': threat_components['count']['weight'],
            'behavior_score': threat_components['behavior']['score'],
            'behavior_raw': threat_components['behavior']['raw'],
            'behavior_confidence': threat_components['behavior']['confidence'],
            'behavior_weight': threat_components['behavior']['weight'],
            'vital_signs_score': threat_components['vital_signs']['score'],
            'vital_signs_raw': threat_components['vital_signs']['raw'],
            'vital_signs_confidence': threat_components['vital_signs']['confidence'],
            'vital_signs_weight': threat_components['vital_signs']['weight'],
            'air_quality_score': threat_components['air_quality']['score'],
            'air_quality_raw': threat_components['air_quality']['raw'],
            'air_quality_confidence': threat_components['air_quality']['confidence'],
            'air_quality_weight': threat_components['air_quality']['weight'],
            'noise_score': threat_components['noise']['score'],
            'noise_raw': threat_components['noise']['raw'],
            'noise_confidence': threat_components['noise']['confidence'],
            'noise_weight': threat_components['noise']['weight'],
            'quality_score': quality['score'],
            'quality_base': quality['base'],
            'quality_category': quality['category'],
            'quality_icon': quality['icon'],
            'quality_trend': quality['trend'],
            'quality_sound_adjust': quality['sound_adjust'],
            'quality_air_adjust': quality['air_adjust'],
            'quality_occupancy_adjust': quality['occupancy_adjust'],
            'sound_db': sound_data['db'],
            'sound_baseline': sound_data['baseline'],
            'sound_spike': sound_data['spike'],
            'sound_rate_of_change': sound_data['rate_of_change'],
            'sound_event': sound_data['event'],
            'sound_confidence': sound_data['confidence'],
            'sound_dominant_freq': sound_data['dominant_freq'],
            'sound_spectral_energy': sound_data['spectral_energy'],
            'sound_spectral_centroid': sound_data['spectral_centroid'],
            'sound_peak': sound_data['peak'],
            'sound_zero_crossings': sound_data['zero_crossings'],
            'sound_spectral_spread': sound_data['spectral_spread'],
            'sound_skewness': sound_data['skewness'],
            'sound_kurtosis': sound_data['kurtosis'],
            'sound_low_energy': sound_data['low_energy'],
            'sound_mid_energy': sound_data['mid_energy'],
            'sound_high_energy': sound_data['high_energy'],
            'air_voc_ppm': air_data['voc_ppm'],
            'air_voc_voltage': air_data['voc_voltage'],
            'air_pm1': air_data['pm1'],
            'air_pm25': air_data['pm25'],
            'air_pm10': air_data['pm10'],
            'air_aqi': air_data['aqi'],
            'air_odor_type': air_data['type'],
            'air_odor_confidence': air_data['confidence'],
            'air_odor_intensity': air_data['intensity'],
            'air_odor_level': air_data['level'],
            'air_odor_trend': air_data['trend'],
            'air_baseline_intensity': air_data['baseline_intensity'],
            'air_odor_anomaly': air_data['anomaly'],
            'radar_target_count': target_count,
            'radar_format': 'mmWave',
            'motion_pattern': motion['pattern'],
            'motion_activity_level': motion['activity_level'],
            'motion_total_targets': motion['total_targets'],
            'motion_active_targets': motion['active_targets'],
            'activity_events': json.dumps([sound_data['event']]),
            'radar_targets': json.dumps(radar_targets),
            'physical_risk': physical_risk,
            'health_risk': health_risk,
            'facility_risk': facility_risk,
            'danger_index': danger_index,
            'comfort_index': comfort_index,
            'urgency_score': urgency_score,
            'sensor_radar_connected': sensors['radar'],
            'sensor_pms_connected': sensors['pms'],
            'sensor_mq135_connected': sensors['mq135'],
            'sensor_sound_connected': sensors['sound'],
            'alert_critical_threat': alerts['critical_threat'],
            'alert_high_threat': alerts['high_threat'],
            'alert_rapid_escalation': alerts['rapid_escalation'],
            'alert_abnormal_vitals': alerts['abnormal_vitals'],
            'alert_air_quality': alerts['air_quality'],
            'notes': f"Generated event for {threat_level} threat level",
            'environment_id': environment_id
        }
        
        return event, radar_targets
    
    def get_threat_response(self, level):
        """Get recommended response for threat level"""
        responses = {
            'LOW': 'Continue normal monitoring',
            'MODERATE': 'Increase surveillance frequency',
            'ELEVATED': 'Notify security team',
            'HIGH': 'Security team on standby',
            'CRITICAL': 'Immediate security response required'
        }
        return responses.get(level, 'Monitor situation')
    
    def clear_existing_data(self):
        """Clear existing data from tables"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM targets")
        cursor.execute("DELETE FROM events_log")
        cursor.execute("DELETE FROM events")
        self.conn.commit()
        print("  🗑️  Cleared existing data")
    
    def generate_historical_data(self):
        """Generate historical data for the specified number of days"""
        print("📊 Generating historical data...")
        
        self.clear_existing_data()
        
        # Generate data for each day
        end_time = datetime.now()
        start_time = end_time - timedelta(days=DAYS_OF_HISTORY)
        
        current_time = start_time
        events_generated = 0
        
        while current_time < end_time:
            # Generate events for this day
            day_events = random.randint(EVENTS_PER_DAY - 10, EVENTS_PER_DAY + 10)
            
            for _ in range(day_events):
                # Distribute events throughout the day
                day_progress = (current_time - start_time).total_seconds() / (DAYS_OF_HISTORY * 24 * 3600)
                event_time = start_time + timedelta(days=DAYS_OF_HISTORY) * day_progress + timedelta(seconds=random.uniform(0, 24 * 3600))
                
                # Generate event record
                event, targets = self.generate_event_record(event_time)
                
                # Insert into database
                cursor = self.conn.cursor()
                
                # Insert main event
                cursor.execute("""
                    INSERT INTO events (
                        timestamp, threat_overall, threat_base, threat_level, threat_color,
                        threat_response, threat_confidence, temporal_trend, temporal_slope,
                        temporal_acceleration, temporal_volatility, temporal_persistence_factor,
                        trajectory_5min, trajectory_15min, trajectory_30min, proximity_score,
                        proximity_raw, proximity_confidence, proximity_weight, count_score,
                        count_raw, count_confidence, count_weight, behavior_score,
                        behavior_raw, behavior_confidence, behavior_weight, vital_signs_score,
                        vital_signs_raw, vital_signs_confidence, vital_signs_weight,
                        air_quality_score, air_quality_raw, air_quality_confidence,
                        air_quality_weight, noise_score, noise_raw, noise_confidence,
                        noise_weight, quality_score, quality_base, quality_category,
                        quality_icon, quality_trend, quality_sound_adjust, quality_air_adjust,
                        quality_occupancy_adjust, sound_db, sound_baseline, sound_spike,
                        sound_rate_of_change, sound_event, sound_confidence, sound_dominant_freq,
                        sound_spectral_energy, sound_spectral_centroid, sound_peak,
                        sound_zero_crossings, sound_spectral_spread, sound_skewness,
                        sound_kurtosis, sound_low_energy, sound_mid_energy,
                        sound_high_energy, air_voc_ppm, air_voc_voltage,
                        air_pm1, air_pm25, air_pm10, air_aqi, air_odor_type,
                        air_odor_confidence, air_odor_intensity, air_odor_level,
                        air_odor_trend, air_baseline_intensity, air_odor_anomaly,
                        radar_target_count, radar_format, motion_pattern,
                        motion_activity_level, motion_total_targets, motion_active_targets,
                        activity_events, radar_targets, physical_risk, health_risk,
                        facility_risk, danger_index, comfort_index, urgency_score,
                        sensor_radar_connected, sensor_pms_connected, sensor_mq135_connected,
                        sensor_sound_connected, alert_critical_threat, alert_high_threat,
                        alert_rapid_escalation, alert_abnormal_vitals, alert_air_quality,
                        notes, environment_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event['timestamp'], event['threat_overall'], event['threat_base'], event['threat_level'],
                    event['threat_color'], event['threat_response'], event['threat_confidence'],
                    event['temporal_trend'], event['temporal_slope'], event['temporal_acceleration'],
                    event['temporal_volatility'], event['temporal_persistence_factor'],
                    event['trajectory_5min'], event['trajectory_15min'], event['trajectory_30min'],
                    event['proximity_score'], event['proximity_raw'], event['proximity_confidence'],
                    event['proximity_weight'], event['count_score'], event['count_raw'],
                    event['count_confidence'], event['count_weight'], event['behavior_score'],
                    event['behavior_raw'], event['behavior_confidence'], event['behavior_weight'],
                    event['vital_signs_score'], event['vital_signs_raw'], event['vital_signs_confidence'],
                    event['vital_signs_weight'], event['air_quality_score'], event['air_quality_raw'],
                    event['air_quality_confidence'], event['air_quality_weight'], event['noise_score'],
                    event['noise_raw'], event['noise_confidence'], event['noise_weight'],
                    event['quality_score'], event['quality_base'], event['quality_category'],
                    event['quality_icon'], event['quality_trend'], event['quality_sound_adjust'],
                    event['quality_air_adjust'], event['quality_occupancy_adjust'],
                    event['sound_db'], event['sound_baseline'], event['sound_spike'],
                    event['sound_rate_of_change'], event['sound_event'], event['sound_confidence'],
                    event['sound_dominant_freq'], event['sound_spectral_energy'], event['spectral_centroid'],
                    event['sound_peak'], event['sound_zero_crossings'], event['sound_spectral_spread'],
                    event['sound_skewness'], event['sound_kurtosis'], event['sound_low_energy'],
                    event['sound_mid_energy'], event['sound_high_energy'],
                    event['air_voc_ppm'], event['air_voc_voltage'], event['air_pm1'],
                    event['air_pm25'], event['air_pm10'], event['air_aqi'], event['air_odor_type'],
                    event['air_odor_confidence'], event['air_odor_intensity'], event['air_odor_level'],
                    event['air_odor_trend'], event['air_baseline_intensity'], event['air_odor_anomaly'],
                    event['radar_target_count'], event['radar_format'], event['motion_pattern'],
                    event['motion_activity_level'], event['motion_total_targets'],
                    event['motion_active_targets'], event['activity_events'],
                    event['radar_targets'], event['physical_risk'], event['health_risk'],
                    event['facility_risk'], event['danger_index'], event['comfort_index'],
                    event['urgency_score'], event['sensor_radar_connected'],
                    event['sensor_pms_connected'], event['sensor_mq135_connected'],
                    event['sensor_sound_connected'], event['alert_critical_threat'],
                    event['alert_high_threat'], event['alert_rapid_escalation'],
                    event['alert_abnormal_vitals'], event['alert_air_quality'],
                    event['notes'], event['environment_id']
                ))
                
                # Get the event ID
                event_id = cursor.lastrowid
                
                # Insert targets
                for target in targets:
                    cursor.execute("""
                        INSERT INTO targets (
                            event_id, timestamp, target_id, target_x, target_y, target_distance,
                            target_angle, target_velocity, target_direction, target_orientation,
                            target_confidence, target_activity, target_activity_confidence,
                            target_breathing_rate, target_breathing_confidence,
                            target_abnormal_breathing, target_vx, target_vy, target_ax, target_ay,
                            target_speed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_id, event['timestamp'], target['target_id'], target['x'], target['y'],
                        target['distance'], target['angle'], target['velocity'],
                        target['direction'], target['orientation'], target['confidence'],
                        target['activity'], target['activity_confidence'],
                        target['breathing_rate'], target['breathing_confidence'],
                        target['abnormal_breathing'], target['vx'], target['vy'],
                        target['ax'], target['ay'], target['speed']
                    ))
                
                # Insert into events log
                cursor.execute("""
                    INSERT INTO events_log (
                        timestamp, threat_level, threat_score, quality_score, people_count,
                        sound_db, air_aqi, event_type, description, temperature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event['timestamp'], event['threat_level'], event['threat_overall'],
                    event['quality_score'], event['radar_target_count'],
                    event['sound_db'], event['air_aqi'], 'sensor_data',
                    f"Threat level: {event['threat_level']}", 20.0
                ))
                
                events_generated += 1
                current_time += timedelta(seconds=random.uniform(300, 1800))  # 5-30 minutes between events
            
            current_time += timedelta(days=1)
        
        self.conn.commit()
        print(f"  ✅ Generated {events_generated:,} events over {DAYS_OF_HISTORY} days")
        return True
    
    def create_admin_user(self):
        """Create default admin user if not exists"""
        print("👤 Setting up admin user...")
        
        cursor = self.conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Create admin user with default password
            cursor.execute("""
                INSERT INTO users (
                    username, password, role, is_active, created_at, email
                ) VALUES ('admin', 'admin123', 'admin', 1, datetime('now'), 'admin@scope.local')
            """)
            self.conn.commit()
            print("  ✅ Admin user created: username='admin', password='admin123'")
        else:
            print("  ✅ Admin user already exists")
        
        return True
    
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
            print(f"  ✅ Environment config created: {self.env_config_file}")
            return True
        except Exception as e:
            print(f"  ❌ Error creating config: {e}")
            return False
    
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
        print(f"   • {DAYS_OF_HISTORY} days of historical data")
        print(f"   • {EVENTS_PER_DAY * DAYS_OF_HISTORY:,} generated events")
    
    def setup(self):
        """Main setup function"""
        print("🚀 SCOPE System Complete Setup")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        steps = [
            ("Python Version Check", self.check_python_version),
            ("Dependency Check", self.check_dependencies),
            ("Database Schema Creation", self.create_database_schema),
            ("Historical Data Generation", self.generate_historical_data),
            ("Admin User Setup", self.create_admin_user),
            ("Environment Configuration", self.generate_environment_config),
            ("Database Verification", self.verify_database),
            ("System Tests", self.run_tests)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📍 {step_name}")
            if not step_func():
                print(f"\n❌ Setup failed at: {step_name}")
                return False
        
        self.close_database()
        self.display_summary()
        return True

if __name__ == '__main__':
    setup = SCOPESetup()
    success = setup.setup()
    sys.exit(0 if success else 1)
