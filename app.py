#!/usr/bin/env python3
"""
Environmental Monitoring System - Web Interface
Provides live visual readings, threat scores, and event history
"""

from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for, Response
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import pytz
import os
import re
import json
import sqlite3
import threading
import time
import math
import random
from dotenv import load_dotenv
import queue
from collections import deque
import numpy as np

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'events.db')

# Initialize extensions
Session(app)

# Start time for uptime calculation
START_TIME = datetime.now()

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('events.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_environment_settings():
    """Get all environment settings from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT environment_id, name, description, color, icon
            FROM environment_settings
            ORDER BY environment_id
        """)
        
        settings = cursor.fetchall()
        return {row['environment_id']: dict(row) for row in settings}
    except Exception as e:
        app.logger.error(f"Error fetching environment settings: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def update_environment_setting(environment_id, name, description=None):
    """Update environment name and optionally description"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if description:
            cursor.execute("""
                UPDATE environment_settings 
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE environment_id = ?
            """, (name, description, environment_id))
        else:
            cursor.execute("""
                UPDATE environment_settings 
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE environment_id = ?
            """, (name, environment_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        app.logger.error(f"Error updating environment setting: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ==================== LIVE DATA STORE ====================

# Global data store for live readings
class LiveDataStore:
    """Thread-safe storage for latest sensor readings"""
    
    def __init__(self, max_history=100):
        self.lock = threading.Lock()
        self.max_history = max_history
        self.latest = {}
        self.history = {
            'threat': deque(maxlen=max_history),
            'quality': deque(maxlen=max_history),
            'people': deque(maxlen=max_history),
            'noise': deque(maxlen=max_history),
            'aqi': deque(maxlen=max_history),
            'voc': deque(maxlen=max_history),
            'pm25': deque(maxlen=max_history)
        }
        self.timestamps = deque(maxlen=max_history)
        self.event_queue = queue.Queue(maxsize=50)
        self.connected_clients = 0
        self.paused = False
        self.paused_data = None  # Store data when paused
        self.paused_environments = set()  # Track which environments are paused
        self.environment_paused_data = {}  # Store paused data for each environment
        
        # Multi-environment support - load from database if available
        db_settings = get_environment_settings()
        
        # Default environment configuration
        default_environments = {
            'primary': {
                'name': 'Primary Environment',
                'description': 'Main monitoring area',
                'color': '#007bff',
                'icon': 'bi-house',
                'data': {},
                'threat_score': 0,
                'last_update': None
            },
            'secondary': {
                'name': 'Secondary Environment', 
                'description': 'Secondary monitoring area',
                'color': '#28a745',
                'icon': 'bi-building',
                'data': {},
                'threat_score': 0,
                'last_update': None
            },
            'warehouse': {
                'name': 'Warehouse Environment',
                'description': 'Warehouse and storage area',
                'color': '#ffc107',
                'icon': 'bi-box-seam',
                'data': {},
                'threat_score': 0,
                'last_update': None
            },
            'outdoor': {
                'name': 'Outdoor Environment',
                'description': 'Outdoor perimeter monitoring',
                'color': '#17a2b8',
                'icon': 'bi-tree',
                'data': {},
                'threat_score': 0,
                'last_update': None
            }
        }
        
        # Override with database settings if available
        for env_id, default_config in default_environments.items():
            if env_id in db_settings:
                db_config = db_settings[env_id]
                default_config['name'] = db_config.get('name', default_config['name'])
                default_config['description'] = db_config.get('description', default_config['description'])
                # Keep color and icon from defaults unless explicitly stored in DB
        
        self.environments = default_environments
        self.current_environment = 'primary'
        self.highest_threat_environment = 'primary'
    
    def update(self, data, environment_id=None):
        """Update with latest sensor data for specific environment"""
        with self.lock:
            # If paused globally, don't update the data
            if self.paused:
                return
            
            # Determine which environment to update
            if environment_id is None:
                environment_id = self.current_environment
            
            if environment_id not in self.environments:
                environment_id = 'primary'
            
            # If this specific environment is paused, don't update it
            if environment_id in self.paused_environments:
                return
            
            # Update environment-specific data
            self.environments[environment_id]['data'] = data.copy()
            self.environments[environment_id]['threat_score'] = data.get('threat', {}).get('overall_threat', 0)
            self.environments[environment_id]['last_update'] = datetime.now()
            
            # Update highest threat environment
            self._update_highest_threat_environment()
            
            # Update legacy data for backward compatibility
            self.latest = data
            self.timestamps.append(datetime.now())
            
            # Update history
            if 'threat' in data and data['threat']:
                self.history['threat'].append(data['threat'].get('overall_threat', 0))
            if 'quality' in data and data['quality']:
                self.history['quality'].append(data['quality'].get('quality_score', 0))
            if 'radar' in data and data['radar']:
                self.history['people'].append(data['radar'].get('target_count', 0))
            if 'sound' in data and data['sound']:
                self.history['noise'].append(data['sound'].get('db', 0))
            if 'odor' in data and data['odor']:
                self.history['aqi'].append(data['odor'].get('air_quality_index', 0))
                self.history['voc'].append(data['odor'].get('voc_ppm', 0))
                self.history['pm25'].append(data['odor'].get('pm25', 0))
    
    def get_latest(self):
        """Get latest readings"""
        with self.lock:
            if self.paused and self.paused_data:
                return self.paused_data.copy()
            return self.latest.copy()
    
    def pause_environment(self, environment_id):
        """Pause data updates for specific environment"""
        with self.lock:
            if environment_id in self.environments:
                self.paused_environments.add(environment_id)
                # Store current data for this environment
                self.environment_paused_data[environment_id] = self.environments[environment_id]['data'].copy()
                return True
            return False
    
    def resume_environment(self, environment_id):
        """Resume data updates for specific environment"""
        with self.lock:
            self.paused_environments.discard(environment_id)
            # Clear stored paused data for this environment
            self.environment_paused_data.pop(environment_id, None)
            return True
    
    def is_environment_paused(self, environment_id):
        """Check if data updates are paused for specific environment"""
        with self.lock:
            return environment_id in self.paused_environments
    
    def pause(self):
        """Pause data updates and store current data"""
        with self.lock:
            self.paused = True
            self.paused_data = self.latest.copy()
    
    def resume(self):
        """Resume data updates"""
        with self.lock:
            self.paused = False
            self.paused_data = None
    
    def is_paused(self):
        """Check if data updates are paused"""
        with self.lock:
            return self.paused
    
    def get_history(self, metric, minutes=60):
        """Get historical data for a metric"""
        with self.lock:
            if metric not in self.history:
                return []
            
            # Convert to list and pair with timestamps
            values = list(self.history[metric])
            timestamps = list(self.timestamps)[-len(values):]
            
            # Filter by time if needed
            if minutes and timestamps:
                cutoff = datetime.now() - timedelta(minutes=minutes)
                filtered = [(ts, val) for ts, val in zip(timestamps, values) 
                           if ts > cutoff]
                return filtered
            
            return list(zip(timestamps, values))
    
    def add_event(self, event):
        """Add an event to the queue"""
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            # Remove oldest event and add new one
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(event)
            except:
                pass
    
    def _update_highest_threat_environment(self):
        """Update which environment has the highest threat level"""
        max_threat = -1
        highest_env = 'primary'
        
        for env_id, env_data in self.environments.items():
            current_threat = env_data.get('threat_score', 0)
            if current_threat > max_threat:
                max_threat = current_threat
                highest_env = env_id
        
        self.highest_threat_environment = highest_env
    
    def get_environment_data(self, environment_id=None):
        """Get data for specific environment"""
        with self.lock:
            if environment_id is None:
                environment_id = self.current_environment
            
            if environment_id not in self.environments:
                environment_id = 'primary'
            
            # If this environment is paused, return the paused data
            if environment_id in self.paused_environments and environment_id in self.environment_paused_data:
                return self.environment_paused_data[environment_id].copy()
            
            return self.environments[environment_id]['data'].copy()
    
    def get_all_environments(self):
        """Get all environments data"""
        with self.lock:
            return {k: v.copy() for k, v in self.environments.items()}
    
    def set_current_environment(self, environment_id):
        """Set the current active environment"""
        with self.lock:
            if environment_id in self.environments:
                self.current_environment = environment_id
                return True
            return False
    
    def get_current_environment(self):
        """Get current environment ID"""
        with self.lock:
            return self.current_environment
    
    def get_highest_threat_environment(self):
        """Get environment with highest threat level"""
        with self.lock:
            return self.highest_threat_environment

# Initialize live data store
live_data = LiveDataStore()

fake_data_cache = {
    'data': None,
    'timestamp': None,
    'cache_duration': 1  # Cache for 1 second for more frequent updates
}

def get_cached_fake_data():
    """Get cached fake data or generate new data if expired"""
    global fake_data_cache
    current_time = datetime.now()
    
    # If data is paused, return the cached data even if expired
    if live_data.is_paused() and fake_data_cache['data'] is not None:
        return fake_data_cache['data']
    
    # Generate new data if cache is empty or expired
    if (fake_data_cache['data'] is None or 
        fake_data_cache['timestamp'] is None or 
        (current_time - fake_data_cache['timestamp']).total_seconds() > fake_data_cache['cache_duration']):
        
        fake_data_cache['data'] = generate_fake_sensor_data()
        fake_data_cache['timestamp'] = current_time
    
    return fake_data_cache['data']

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('events.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_recent_events(limit=50):
    """Get recent events from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, event_type, threat_level, threat_score, 
                   quality_score, people_count, sound_db, air_aqi, description
            FROM events_log
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        events = cursor.fetchall()
        return [dict(event) for event in events]
    except Exception as e:
        app.logger.error(f"Error fetching events: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_threat_statistics(hours=24):
    """Get threat statistics for time period"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                AVG(threat_score) as avg_threat,
                MAX(threat_score) as max_threat,
                AVG(quality_score) as avg_quality,
                AVG(people_count) as avg_people,
                AVG(sound_db) as avg_noise,
                AVG(air_aqi) as avg_aqi,
                SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN threat_level = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN threat_level = 'ELEVATED' THEN 1 ELSE 0 END) as elevated_count,
                SUM(CASE WHEN threat_level = 'MODERATE' THEN 1 ELSE 0 END) as moderate_count,
                SUM(CASE WHEN threat_level = 'LOW' THEN 1 ELSE 0 END) as low_count
            FROM events_log
            WHERE timestamp >= ?
        """, (cutoff,))
        
        stats = cursor.fetchone()
        return dict(stats) if stats else {}
    except Exception as e:
        app.logger.error(f"Error fetching statistics: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def get_threat_timeline(hours=24):
    """Get threat timeline for charts"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, threat_overall, quality_score, radar_target_count,
                   sound_db, air_aqi, air_voc_ppm, air_pm25
            FROM events
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (cutoff,))
        
        data = cursor.fetchall()
        app.logger.info(f"Timeline query returned {len(data)} rows")
        
        # Rename fields for consistency
        result = []
        for row in data:
            item = dict(row)
            item['threat_score'] = item.pop('threat_overall')
            item['people_count'] = item.pop('radar_target_count')
            result.append(item)
        
        if result:
            app.logger.info(f"First timeline entry: {list(result[0].keys())}")
        
        return result
    except Exception as e:
        app.logger.error(f"Error fetching timeline: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_average_threat_components(hours=24):
    """Get average threat components from all events"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT 
                AVG(proximity_score) as avg_proximity,
                AVG(count_score) as avg_count,
                AVG(behavior_score) as avg_behavior,
                AVG(vital_signs_score) as avg_vital_signs,
                AVG(air_quality_score) as avg_air_quality,
                AVG(noise_score) as avg_noise
            FROM events
            WHERE timestamp >= ?
        """, (cutoff,))
        
        result = cursor.fetchone()
        return dict(result) if result else {}
    except Exception as e:
        app.logger.error(f"Error fetching average threat components: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def get_target_history(minutes=30):
    """Get recent target data"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        
        cursor.execute("""
            SELECT t.*, e.timestamp as event_timestamp
            FROM targets t
            JOIN events e ON t.event_id = e.id
            WHERE e.timestamp >= ?
            ORDER BY e.timestamp DESC
        """, (cutoff,))
        
        targets = cursor.fetchall()
        return [dict(target) for target in targets]
    except Exception as e:
        app.logger.error(f"Error fetching targets: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_environment_settings():
    """Get all environment settings from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT environment_id, name, description, color, icon
            FROM environment_settings
            ORDER BY environment_id
        """)
        
        settings = cursor.fetchall()
        return {row['environment_id']: dict(row) for row in settings}
    except Exception as e:
        app.logger.error(f"Error fetching environment settings: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def update_environment_setting(environment_id, name, description=None):
    """Update environment name and optionally description"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if description:
            cursor.execute("""
                UPDATE environment_settings 
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE environment_id = ?
            """, (name, description, environment_id))
        else:
            cursor.execute("""
                UPDATE environment_settings 
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE environment_id = ?
            """, (name, environment_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        app.logger.error(f"Error updating environment setting: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ==================== FAKE DATA GENERATION ====================

def generate_fake_sensor_data(environment_id=None):
    """Generate fake sensor data for demonstration with environment variations"""
    
    # Environment-specific variations
    env_multipliers = {
        'primary': {'people_base': 2, 'threat_base': 30, 'noise_base': 40},
        'secondary': {'people_base': 1, 'threat_base': 20, 'noise_base': 35},
        'warehouse': {'people_base': 3, 'threat_base': 40, 'noise_base': 60},
        'outdoor': {'people_base': 1, 'threat_base': 25, 'noise_base': 45}
    }
    
    if environment_id is None:
        environment_id = live_data.get_current_environment()
    
    env_config = env_multipliers.get(environment_id, env_multipliers['primary'])
    
    # People count and targets
    people_count = random.randint(0, 5)
    targets = []
    active_targets = 0
    abnormal_count = 0
    
    for i in range(people_count):
        activity = random.choice(['stationary', 'sitting', 'walking', 'running'])
        if activity in ['walking', 'running']:
            active_targets += 1
            
        abnormal = random.random() < 0.2
        if abnormal:
            abnormal_count += 1
            
        targets.append({
            'id': f"T{random.randint(1,99):02d}",
            'target_id': f"T{random.randint(1,99):02d}",
            'distance': round(random.uniform(1.0, 8.0), 2),  # Start from 1m instead of 0.5m
            'target_distance': round(random.uniform(1.0, 8.0), 2),
            'angle': round(random.uniform(-60, 60), 1),
            'target_angle': round(random.uniform(-60, 60), 1),
            'activity': activity,
            'target_activity': activity,
            'abnormal_breathing': abnormal,
            'target_abnormal_breathing': abnormal,
            'target_velocity': round(random.uniform(0, 2.0), 2) if activity in ['walking', 'running'] else 0,
            'target_breathing_rate': round(random.uniform(12, 20), 1) if random.random() < 0.7 else None,
            'target_confidence': round(random.uniform(0.7, 0.95), 2),
            'event_timestamp': (datetime.now() - timedelta(seconds=random.randint(0, 300))).isoformat()
        })
    
    # Threat data
    threat_score = random.uniform(10, 95)
    if threat_score > 80:
        threat_level = "CRITICAL"
    elif threat_score > 60:
        threat_level = "HIGH"
    elif threat_score > 40:
        threat_level = "ELEVATED"
    elif threat_score > 20:
        threat_level = "MODERATE"
    else:
        threat_level = "LOW"
    
    # Air quality with auto-alarm logic and extreme value handling
    voc = random.uniform(20, 250)
    pm25 = random.randint(5, 120)
    aqi = (voc / 100 * 50) + (pm25 / 35 * 50)
    
    # Auto-alarm if air quality is high enough OR extreme values
    air_quality_alarm = aqi > 200 or voc > 300 or pm25 > 150
    
    # Extreme air quality can set off alarm regardless of other factors
    if air_quality_alarm:
        threat_score = max(threat_score, 85)  # Minimum threat level for air quality alarm
    
    odor_types = ['clean_air', 'human_activity', 'moderate_odor', 'strong_chemical', 'dust_or_smoke']
    odor_type = random.choice(odor_types)
    odor_confidence = random.uniform(0.7, 0.95)
    odor_intensity = random.uniform(1, 8)
    
    # Sound with extreme value handling
    sound_db = random.uniform(30, 95)
    sound_events = ['quiet', 'background', 'conversation', 'crowd', 'door_slam', 'impact']
    sound_event = random.choice(sound_events)
    sound_spike = random.random() < 0.1
    sound_baseline = sound_db - random.uniform(5, 15)
    
    # Extreme noise can set off alarm regardless of other factors
    noise_alarm = sound_db > 110 or sound_spike and sound_db > 100
    if noise_alarm:
        threat_score = max(threat_score, 90)  # Minimum threat level for noise alarm
    
    # Generate behavior score first (includes proximity)
    behavior_score = random.uniform(0, 100)
    
    # Component threats with updated weights and logic
    components = {
        'proximity': {
            'score': random.uniform(0, 100), 
            'weight': 0.15, 
            'confidence': random.uniform(0.7, 0.95)
        },
        'count': {
            'score': random.uniform(0, 100), 
            'weight': 0.15, 
            'confidence': random.uniform(0.7, 0.95)
        },
        'behavior': {
            'score': behavior_score,  # This now includes proximity
            'weight': 0.30,  # Reduced to accommodate proximity
            'confidence': random.uniform(0.7, 0.95)
        },
        'vital_signs': {
            # Vital signs only matter if behavior is setting off errors
            'score': behavior_score if behavior_score > 70 else random.uniform(0, 30), 
            'weight': 0.15, 
            'confidence': random.uniform(0.7, 0.95)
        },
        'air_quality': {
            'score': min(100, (aqi / 200) * 100),  # Scale AQI to 0-100
            'weight': 0.15, 
            'confidence': random.uniform(0.7, 0.95)
        },
        'noise': {
            'score': min(100, ((sound_db - 30) / 70) * 100),  # Scale dB to 0-100
            'weight': 0.10, 
            'confidence': random.uniform(0.7, 0.95)
        }
    }
    
    # Calculate overall threat score from components first
    calculated_threat = sum(comp['score'] * comp['weight'] for comp in components.values())
    
    # Use the calculated threat as the primary score, with some random variation
    threat_score = calculated_threat + random.uniform(-5, 5)
    threat_score = max(0, min(100, threat_score))  # Clamp to 0-100 range
    
    # Update threat level based on final score
    if threat_score > 80:
        threat_level = "CRITICAL"
    elif threat_score > 60:
        threat_level = "HIGH"
    elif threat_score > 40:
        threat_level = "ELEVATED"
    elif threat_score > 20:
        threat_level = "MODERATE"
    else:
        threat_level = "LOW"
    
    # Temporal dynamics
    trends = ['stable', 'worsening', 'rapidly_worsening', 'improving', 'rapidly_improving']
    temporal_trend = random.choice(trends)
    temporal_slope = random.uniform(-2, 2)
    temporal_acceleration = random.uniform(-0.2, 0.2)
    persistence_factor = random.uniform(1.0, 1.8)
    
    # Trajectory
    trajectory_5min = min(100, threat_score + random.uniform(-10, 20))
    trajectory_15min = min(100, threat_score + random.uniform(-20, 35))
    trajectory_30min = min(100, threat_score + random.uniform(-30, 50))
    
    return {
        'fake_mode': True,
        'people_count': people_count,
        'active_targets': active_targets,
        'abnormal_count': abnormal_count,
        'targets': targets,
        'threat': {
            'overall_threat': threat_score,
            'level': threat_level,
            'temporal': {
                'trend': temporal_trend,
                'slope': temporal_slope,
                'persistence': persistence_factor
            },
            'trajectory': {
                '5min': trajectory_5min,
                '15min': trajectory_15min,
                '30min': trajectory_30min
            },
            'components': components
        },
        'radar': {
            'target_count': people_count,
            'targets': targets
        },
        'odor': {
            'air_quality_index': aqi,
            'voc_ppm': voc,
            'pm25': pm25,
            'odor_type': odor_type
        },
        'sound': {
            'db': sound_db,
            'event': sound_event,
            'spike': sound_spike
        },
        'quality': {
            'quality_score': aqi,
            'category': odor_type,
            'trend': temporal_trend
        },
        'voc': voc,
        'pm25': pm25,
        'aqi': aqi,
        'odor_type': odor_type,
        'odor_confidence': odor_confidence,
        'odor_intensity': odor_intensity,
        'sound_db': sound_db,
        'sound_event': sound_event,
        'sound_spike': sound_spike,
        'sound_baseline': sound_baseline,
        'air_quality_alarm': air_quality_alarm,
        'noise_alarm': noise_alarm,
        'uptime': (datetime.now() - START_TIME).total_seconds(),
        'data_rate': random.uniform(10, 50),
        'packet_count': random.randint(1000, 9999),
        'last_update': datetime.now().strftime('%H:%M:%S.%f')[:-3],
        'components': components  # Add components to the returned data
    }

# Initialize the cache with pre-populated data
fake_data_cache['data'] = generate_fake_sensor_data()
fake_data_cache['timestamp'] = datetime.now()

def get_realtime_sensor_data():
    """Get real sensor data from database"""
    try:
        # Connect to the events database
        conn = sqlite3.connect('events.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the most recent event data
        cursor.execute("""
            SELECT * FROM events 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        latest_event = cursor.fetchone()
        conn.close()
        
        if latest_event:
            # Parse the JSON data from the database
            event_data = json.loads(latest_event['data']) if latest_event['data'] else {}
            
            # Structure the data to match the expected format
            real_data = {
                'fake_mode': False,
                'people_count': event_data.get('radar', {}).get('target_count', 0),
                'active_targets': len(event_data.get('targets', [])),
                'abnormal_count': event_data.get('radar', {}).get('abnormal_breathing_count', 0),
                'threat': event_data.get('threat', {}),
                'quality': event_data.get('quality', {}),
                'radar': event_data.get('radar', {}),
                'sound': event_data.get('sound', {}),
                'odor': event_data.get('odor', {}),
                'targets': event_data.get('targets', []),
                'last_update': latest_event['timestamp'],
                'sensor_status': event_data.get('sensor_status', {
                    'radar': False,
                    'pms5003': False,
                    'mq135': False,
                    'sound': False
                })
            }
            return real_data
        else:
            # No real data available - return empty structure
            return {
                'fake_mode': False,
                'people_count': 0,
                'active_targets': 0,
                'abnormal_count': 0,
                'threat': {'overall_threat': 0, 'level': 'LOW'},
                'quality': {'quality_score': 0},
                'radar': {'target_count': 0},
                'sound': {'db': 0},
                'odor': {'air_quality_index': 0, 'voc_ppm': 0, 'pm25': 0},
                'targets': [],
                'last_update': datetime.now().strftime('%H:%M:%S'),
                'sensor_status': {
                    'radar': False,
                    'pms5003': False,
                    'mq135': False,
                    'sound': False
                },
                'no_data': True  # Flag to indicate no real data available
            }
            
    except Exception as e:
        app.logger.error(f"Error getting real sensor data: {e}")
        # Return empty structure on error
        return {
            'fake_mode': False,
            'people_count': 0,
            'active_targets': 0,
            'abnormal_count': 0,
            'threat': {'overall_threat': 0, 'level': 'LOW'},
            'quality': {'quality_score': 0},
            'radar': {'target_count': 0},
            'sound': {'db': 0},
            'odor': {'air_quality_index': 0, 'voc_ppm': 0, 'pm25': 0},
            'targets': [],
            'last_update': datetime.now().strftime('%H:%M:%S'),
            'sensor_status': {
                'radar': False,
                'pms5003': False,
                'mq135': False,
                'sound': False
            },
            'no_data': True,
            'error': str(e)
        }

def generate_recent_logs(count=10):
    """Generate recent log entries"""
    logs = []
    messages = [
        f"SYSTEM: Sensor array synchronized",
        f"RADAR: Target acquired - distance 2.3m",
        f"AIR: VOC spike detected - 145ppm",
        f"THREAT: Level updated to MODERATE",
        f"SOUND: Audio spike at 82dB",
        f"VITAL: Abnormal breathing detected - Target T04",
        f"SYSTEM: Data packet received - 1024 bytes",
        f"RADAR: Target lost - exiting sector 7",
        f"AIR: Air quality normalizing",
        f"THREAT: Trajectory updated - improving",
        f"RADAR: Multiple targets detected - count: 3",
        f"AIR: PM2.5 levels elevated - 45μg/m³",
        f"SOUND: Background noise stable at 52dB",
        f"VITAL: All vitals normal",
        f"SYSTEM: Database sync complete"
    ]
    
    for i in range(count):
        timestamp = (datetime.now() - timedelta(seconds=i*30)).strftime('%H:%M:%S')
        logs.append({
            'timestamp': timestamp,
            'message': random.choice(messages)
        })
    return logs

# ==================== AUTHENTICATION FUNCTIONS ====================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required for this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def create_user(username, password, email, role='user'):
    """Create a new user account"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        cursor.execute("SELECT id FROM users WHERE emailAddress = ?", (email,))
        if cursor.fetchone():
            return False, "Email already exists"
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password, emailAddress, role, dateJoined, accountStatus)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password_hash, email, role, datetime.now().isoformat(), 'active'))
        
        conn.commit()
        return True, "User created successfully"
    except Exception as e:
        app.logger.error(f"Error creating user: {e}")
        return False, f"Error: {e}"
    finally:
        if conn:
            conn.close()

def authenticate_user(username, password):
    """Authenticate user credentials"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, password, emailAddress, role, accountStatus
            FROM users
            WHERE username = ? OR emailAddress = ?
        """, (username, username))
        
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            if user['accountStatus'] == 'active':
                return dict(user)
            else:
                return None  # Account inactive
        return None
    except Exception as e:
        app.logger.error(f"Error authenticating user: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Get user information by ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, emailAddress, role, accountStatus, lastLogin
            FROM users
            WHERE id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        app.logger.error(f"Error fetching user: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_last_login(user_id):
    """Update user's last login time"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET lastLogin = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id))
        
        conn.commit()
    except Exception as e:
        app.logger.error(f"Error updating last login: {e}")
    finally:
        if conn:
            conn.close()

def get_all_users():
    """Get all users for admin management"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, emailAddress, role, accountStatus, dateJoined, lastLogin
            FROM users
            ORDER BY dateJoined DESC
        """)
        
        users = cursor.fetchall()
        return [dict(user) for user in users]
    except Exception as e:
        app.logger.error(f"Error fetching users: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_user_status(user_id, status):
    """Update user account status"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET accountStatus = ?
            WHERE id = ?
        """, (status, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        app.logger.error(f"Error updating user status: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_user(user_id):
    """Delete a user account"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        app.logger.error(f"Error deleting user: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ==================== AUTHENTICATION ROUTES ====================

@app.route("/login", methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['emailAddress']
            session['role'] = user['role']
            session.permanent = True
            
            update_last_login(user['id'])
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route("/logout")
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        # Create user
        success, message = create_user(username, password, email)
        if success:
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')

@app.route("/profile")
@login_required
def profile():
    """User profile page"""
    # Get environment data for consistency
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', 
                         user=user,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

@app.route("/users")
@admin_required
def users():
    """User management page for admins"""
    # Get environment data for consistency
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    all_users = get_all_users()
    return render_template('users.html', 
                         users=all_users,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

@app.route("/users/create", methods=['POST'])
@admin_required
def create_user_route():
    """Create new user (admin only)"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')
    
    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('users'))
    
    success, message = create_user(username, password, email, role)
    if success:
        flash(f'User {username} created successfully!', 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('users'))

@app.route("/users/<int:user_id>/status", methods=['POST'])
@admin_required
def update_user_status_route(user_id):
    """Update user status (admin only)"""
    status = request.form.get('status')
    if status in ['active', 'inactive', 'suspended']:
        if update_user_status(user_id, status):
            flash(f'User status updated to {status}.', 'success')
        else:
            flash('Failed to update user status.', 'error')
    else:
        flash('Invalid status.', 'error')
    
    return redirect(url_for('users'))

@app.route("/users/<int:user_id>/delete", methods=['POST'])
@admin_required
def delete_user_route(user_id):
    """Delete user (admin only)"""
    # Prevent self-deletion
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users'))
    
    if delete_user(user_id):
        flash('User deleted successfully.', 'success')
    else:
        flash('Failed to delete user.', 'error')
    
    return redirect(url_for('users'))

# ==================== PROTECTED ROUTES ====================

def index():
    """Main dashboard page"""
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
@login_required
def dashboard():
    """Live monitoring dashboard with multi-environment support"""
    # Get fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    # Get all environments data
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    # Generate fake data for all environments if in fake mode
    if fake_mode:
        for env_id in all_environments.keys():
            env_data = generate_fake_sensor_data(env_id)
            live_data.update(env_data, env_id)
        
        # Refresh environments data after updates
        all_environments = live_data.get_all_environments()
        # Ensure highest threat environment is updated after all environments are processed
        live_data._update_highest_threat_environment()
        highest_threat_env = live_data.get_highest_threat_environment()
        
        # Get current environment data for display
        data = live_data.get_environment_data(current_env)
    else:
        # Try to get real data from database
        data = live_data.get_environment_data(current_env)
        if not data:
            data = {'no_data': True}
    
    # Extract top-level variables for template compatibility
    template_data = {
        'fake_mode': fake_mode,
        'current_time': datetime.now().isoformat(),
        'environments': all_environments,
        'current_environment': current_env,
        'highest_threat_environment': highest_threat_env,
        'people_count': data.get('people_count', 0),
        'active_targets': data.get('active_targets', 0),
        'abnormal_count': data.get('abnormal_count', 0),
        'components': data.get('components', {}),
        'aqi': data.get('aqi', 0),
        'voc': data.get('voc', 0),
        'pm25': data.get('pm25', 0),
        'odor_type': data.get('odor_type', 'clean_air'),
        'odor_confidence': data.get('odor_confidence', 0.8),
        'odor_intensity': data.get('odor_intensity', 3.0),
        'sound_db': data.get('sound_db', 0),
        'sound_event': data.get('sound_event', 'quiet'),
        'sound_spike': data.get('sound_spike', False),
        'sound_baseline': data.get('sound_baseline', 40.0),
        'air_quality_alarm': data.get('air_quality_alarm', False),
        'noise_alarm': data.get('noise_alarm', False),
        'uptime': data.get('uptime', (datetime.now() - START_TIME).total_seconds()),
        'data_rate': data.get('data_rate', 0),
        'packet_count': data.get('packet_count', 0),
        # Pass the full data structures for JavaScript
        'threat': data.get('threat', {}),
        'radar': data.get('radar', {}),
        'odor': data.get('odor', {}),
        'sound': data.get('sound', {}),
        'quality': data.get('quality', {}),
        'no_data': data.get('no_data', False),
        'sensor_status': data.get('sensor_status', {
            'radar': False,
            'pms5003': False,
            'mq135': False,
            'sound': False
        })
    }
    
    return render_template('dashboard.html', **template_data)

@app.route("/sensors")
@login_required
def sensors():
    """Person tracking sensor dashboard"""
    # Get fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    # Get environment data for consistency
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    if fake_mode:
        # Use cached fake data for consistency
        data = get_cached_fake_data()
    else:
        # Try to get real data from database
        data = get_realtime_sensor_data()
        if not data:
            data = {'no_data': True}
    
    # Extract top-level variables for template compatibility
    template_data = {
        'fake_mode': fake_mode,
        'recent_logs': generate_recent_logs(),  # This is fine to be random
        'last_update': data.get('last_update', datetime.now().strftime('%H:%M:%S')),
        'people_count': data.get('people_count', 0),
        'active_targets': data.get('active_targets', 0),
        'abnormal_count': data.get('abnormal_count', 0),
        'targets': data.get('targets', []),
        'threat_score': data.get('threat', {}).get('overall_threat', 0),
        'threat_level': data.get('threat', {}).get('level', 'UNKNOWN'),
        'temporal_trend': data.get('threat', {}).get('temporal', {}).get('trend', 'stable'),
        'temporal_slope': data.get('threat', {}).get('temporal', {}).get('slope', 0),
        'temporal_acceleration': data.get('threat', {}).get('temporal', {}).get('acceleration', 0),
        'persistence_factor': data.get('threat', {}).get('temporal', {}).get('persistence', 1.0),
        'trajectory_5min': data.get('threat', {}).get('trajectory', {}).get('5min', 0),
        'trajectory_15min': data.get('threat', {}).get('trajectory', {}).get('15min', 0),
        'trajectory_30min': data.get('threat', {}).get('trajectory', {}).get('30min', 0),
        'components': data.get('components', {}),
        'aqi': data.get('aqi', 0),
        'voc': data.get('voc', 0),
        'pm25': data.get('pm25', 0),
        'odor_type': data.get('odor_type', 'clean_air'),
        'odor_confidence': data.get('odor_confidence', 0.8),
        'odor_intensity': data.get('odor_intensity', 3.0),
        'sound_db': data.get('sound_db', 0),
        'sound_event': data.get('sound_event', 'quiet'),
        'sound_spike': data.get('sound_spike', False),
        'sound_baseline': data.get('sound_baseline', 40.0),
        'air_quality_alarm': data.get('air_quality_alarm', False),
        'noise_alarm': data.get('noise_alarm', False),
        'uptime': data.get('uptime', (datetime.now() - START_TIME).total_seconds()),
        'data_rate': data.get('data_rate', 0),
        'packet_count': data.get('packet_count', 0),
        'no_data': data.get('no_data', False),
        'sensor_status': data.get('sensor_status', {
            'radar': False,
            'pms5003': False,
            'mq135': False,
            'sound': False
        }),
        # Pass the full data structures for JavaScript
        'threat': data.get('threat', {}),
        'radar': data.get('radar', {}),
        'quality': data.get('quality', {}),
        # Add environment data for consistency
        'environments': all_environments,
        'current_environment': current_env,
        'highest_threat_environment': highest_threat_env
    }
    
    return render_template('sensors.html', **template_data)

@app.route("/history")
@login_required
def history():
    """Event history page"""
    # Get environment data for consistency
    fake_mode = session.get('fake_mode', True)
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    events = get_recent_events(100)
    stats = get_threat_statistics(24)
    
    # Generate timeline data (events per hour for last 24h)
    timeline_data = [0] * 24
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM events_log
            WHERE datetime(timestamp) > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour
        """)
        hour_counts = cursor.fetchall()
        for row in hour_counts:
            hour = int(row['hour'])
            timeline_data[hour] = row['count']
    except Exception as e:
        app.logger.error(f"Error generating timeline: {e}")
    finally:
        if conn:
            conn.close()
    
    return render_template('history.html',
                         events=events,
                         stats=stats,
                         timeline_data=timeline_data,
                         current_date=datetime.now().strftime('%Y-%m-%d'),
                         current_time=datetime.now().isoformat(),
                         fake_mode=fake_mode,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

@app.route("/test/analytics")
def test_analytics():
    """Test analytics page without login"""
    timeline = get_threat_timeline(24)
    stats = get_threat_statistics(24)
    return render_template('analytics.html',
                         timeline=json.dumps(timeline),
                         stats=stats,
                         current_time=datetime.now().isoformat(),
                         fake_mode=True,
                         environments={'primary': {'name': 'Test Environment', 'color': '#007bff', 'icon': 'bi-house'}},
                         current_environment='primary',
                         highest_threat_environment=None)

@app.route("/test/history")
def test_history():
    """Test history page without login"""
    events = get_recent_events(100)
    stats = get_threat_statistics(24)
    
    # Generate timeline data (events per hour for last 24h)
    timeline_data = [0] * 24
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM events_log
            WHERE datetime(timestamp) > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour
        """)
        hour_counts = cursor.fetchall()
        for row in hour_counts:
            hour = int(row['hour'])
            timeline_data[hour] = row['count']
    except Exception as e:
        app.logger.error(f"Error generating timeline: {e}")
    finally:
        if conn:
            conn.close()
    
    return render_template('history.html',
                         events=events,
                         stats=stats,
                         timeline_data=timeline_data,
                         current_date=datetime.now().strftime('%Y-%m-%d'),
                         current_time=datetime.now().isoformat(),
                         fake_mode=True,
                         environments={'primary': {'name': 'Test Environment', 'color': '#007bff', 'icon': 'bi-house'}},
                         current_environment='primary',
                         highest_threat_environment=None)

@app.route("/analytics")
@login_required
def analytics():
    """Analytics and charts page"""
    # Get environment data for consistency
    fake_mode = session.get('fake_mode', True)
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    timeline = get_threat_timeline(24)
    stats = get_threat_statistics(24)
    return render_template('analytics.html',
                         timeline=json.dumps(timeline),
                         stats=stats,
                         current_time=datetime.now().isoformat(),
                         fake_mode=fake_mode,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

@app.route("/targets")
@login_required
def targets_view():
    """Person tracking view"""
    fake_mode = session.get('fake_mode', True)
    
    # Get environment data for consistency
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    if fake_mode:
        # Use cached fake data for consistency
        data = get_cached_fake_data()
        targets = data.get('targets', [])
    else:
        # Get real target data from database
        targets = get_target_history(30)
    
    return render_template('targets.html',
                         targets=targets,
                         current_time=datetime.now().isoformat(),
                         fake_mode=fake_mode,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

@app.route("/settings")
@login_required
def settings():
    """Settings page"""
    # Get environment data for consistency
    fake_mode = session.get('fake_mode', True)
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    return render_template('settings.html',
                         current_time=datetime.now().isoformat(),
                         database_path=app.config.get('DATABASE_PATH', 'N/A'),
                         other_config_values=app.config.get('OTHER_CONFIG_VALUES', 'N/A'),
                         fake_mode=fake_mode,
                         environments=all_environments,
                         current_environment=current_env,
                         highest_threat_environment=highest_threat_env)

# ==================== API ROUTES ====================

@app.route("/api/targets")
def api_targets():
    """Get recent target data"""
    minutes = request.args.get('minutes', 30, type=int)
    
    # Check fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Use cached fake data for consistency
        data = get_cached_fake_data()
        targets = data.get('targets', [])
    else:
        # Get real target data from database
        targets = get_target_history(minutes)
    
    return jsonify(targets)

@app.route("/api/events/recent")
def api_recent_events():
    """Get recent events"""
    limit = request.args.get('limit', 50, type=int)
    
    # Check fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Use cached fake data for consistency - generate events based on cached data
        data = get_cached_fake_data()
        events = []
        event_types = ['NORMAL', 'MOTION', 'SOUND_SPIKE', 'THREAT_CHANGE', 'PERSON_DETECTED']
        
        # Generate events based on current cached data
        for i in range(limit):
            events.append({
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(0, 120))).isoformat(),
                'event_type': random.choice(event_types),
                'threat_level': data.get('threat', {}).get('level', 'LOW'),
                'threat_score': data.get('threat', {}).get('overall_threat', 0),
                'people_count': data.get('people_count', 0),
                'sound_db': data.get('sound_db', 40),
                'air_aqi': data.get('aqi', 50)
            })
    else:
        events = get_recent_events(limit)
    
    return jsonify(events)

@app.route("/api/toggle_fake_mode", methods=['POST'])
@login_required
def toggle_fake_mode():
    """Toggle fake data mode in session"""
    try:
        data = request.get_json()
        fake_mode = data.get('fake_mode', False)
        
        # Update session
        session['fake_mode'] = fake_mode
        
        return jsonify({'success': True, 'fake_mode': fake_mode})
    except Exception as e:
        app.logger.error(f"Error toggling fake mode: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/pause", methods=['POST'])
@login_required
def pause_data():
    """Pause data updates"""
    try:
        live_data.pause()
        return jsonify({'success': True, 'paused': True})
    except Exception as e:
        app.logger.error(f"Error pausing data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/resume", methods=['POST'])
@login_required
def resume_data():
    """Resume data updates"""
    try:
        live_data.resume()
        return jsonify({'success': True, 'paused': False})
    except Exception as e:
        app.logger.error(f"Error resuming data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/pause_status")
def pause_status():
    """Get current pause status"""
    try:
        is_paused = live_data.is_paused()
        return jsonify({'paused': is_paused})
    except Exception as e:
        app.logger.error(f"Error getting pause status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/environment/<environment_id>/pause", methods=['POST'])
@login_required
def pause_environment(environment_id):
    """Pause data updates for specific environment"""
    try:
        if live_data.pause_environment(environment_id):
            return jsonify({
                'success': True, 
                'environment_id': environment_id,
                'paused': True
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid environment ID'}), 400
    except Exception as e:
        app.logger.error(f"Error pausing environment {environment_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/environment/<environment_id>/resume", methods=['POST'])
@login_required
def resume_environment(environment_id):
    """Resume data updates for specific environment"""
    try:
        if live_data.resume_environment(environment_id):
            return jsonify({
                'success': True, 
                'environment_id': environment_id,
                'paused': False
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid environment ID'}), 400
    except Exception as e:
        app.logger.error(f"Error resuming environment {environment_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/environment/<environment_id>/pause_status")
def environment_pause_status(environment_id):
    """Get pause status for specific environment"""
    try:
        is_paused = live_data.is_environment_paused(environment_id)
        return jsonify({
            'environment_id': environment_id,
            'paused': is_paused
        })
    except Exception as e:
        app.logger.error(f"Error getting environment pause status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/config", methods=['GET', 'POST'])
@login_required
def api_config():
    """Handle system settings"""
    global fake_data_cache
    
    if request.method == 'GET':
        # Get current settings
        return jsonify({
            'data_refresh_rate': fake_data_cache['cache_duration'],
            'dashboard_refresh_rate': session.get('dashboard_refresh_rate', 5)
        })
    
    elif request.method == 'POST':
        # Update settings
        try:
            data = request.get_json()
            data_refresh_rate = data.get('data_refresh_rate', 5)
            dashboard_refresh_rate = data.get('dashboard_refresh_rate', 5)
            
            # Validate inputs
            if not (1 <= data_refresh_rate <= 60):
                return jsonify({'success': False, 'error': 'Data refresh rate must be between 1 and 60 seconds'})
            
            if not (1 <= dashboard_refresh_rate <= 60):
                return jsonify({'success': False, 'error': 'Dashboard refresh rate must be between 1 and 60 seconds'})
            
            # Update fake data cache duration globally
            fake_data_cache['cache_duration'] = data_refresh_rate
            
            # Store dashboard refresh rate in session
            session['dashboard_refresh_rate'] = dashboard_refresh_rate
            
            app.logger.info(f"Settings updated: data_refresh_rate={data_refresh_rate}s, dashboard_refresh_rate={dashboard_refresh_rate}s")
            
            return jsonify({
                'success': True,
                'data_refresh_rate': data_refresh_rate,
                'dashboard_refresh_rate': dashboard_refresh_rate
            })
            
        except Exception as e:
            app.logger.error(f"Error updating settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/update", methods=['POST'])
def api_update():
    """Endpoint for the main system to push updates"""
    if request.method == 'POST':
        data = request.json
        live_data.update(data)
        
        # Check for significant events to add to queue
        threat = data.get('threat', {})
        if threat and threat.get('overall_threat', 0) > 60:
            live_data.add_event({
                'timestamp': datetime.now().isoformat(),
                'type': 'THREAT_UPDATE',
                'level': threat.get('level'),
                'score': threat.get('overall_threat')
            })
        
        return jsonify({'status': 'ok'})

@app.route("/api/live")
def api_live():
    """Get current live sensor data"""
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Get current environment data
        current_env = live_data.get_current_environment()
        data = live_data.get_environment_data(current_env)
        
        # If no data exists, generate some for the current environment
        if not data or not data.get('people_count'):
            data = generate_fake_sensor_data(current_env)
            live_data.update(data, current_env)
            data = live_data.get_environment_data(current_env)
    else:
        data = get_realtime_sensor_data()
        # Don't fall back to fake data - return empty data when no real data available
    
    return jsonify(data)

@app.route("/api/environments")
def api_environments():
    """Get all environments data"""
    return jsonify(live_data.get_all_environments())

@app.route("/api/environment/current", methods=['GET', 'POST'])
def api_current_environment():
    """Get or set current environment"""
    if request.method == 'GET':
        return jsonify({
            'current': live_data.get_current_environment(),
            'highest_threat': live_data.get_highest_threat_environment()
        })
    elif request.method == 'POST':
        try:
            data = request.get_json()
            environment_id = data.get('environment_id')
            
            if live_data.set_current_environment(environment_id):
                return jsonify({
                    'success': True, 
                    'current': environment_id,
                    'highest_threat': live_data.get_highest_threat_environment()
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid environment ID'}), 400
        except Exception as e:
            app.logger.error(f"Error setting current environment: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/environment/<environment_id>/data")
def api_environment_data(environment_id):
    """Get data for specific environment"""
    fake_mode = session.get('fake_mode', True)
    
    try:
        if fake_mode:
            # Get fake environment data
            data = live_data.get_environment_data(environment_id)
        else:
            # Get real environment data
            data = live_data.get_environment_data(environment_id)
        return jsonify(data or {})
    except Exception as e:
        app.logger.error(f"Error getting environment data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/environment/<environment_id>/settings", methods=['POST'])
@login_required
def update_environment_settings(environment_id):
    """Update environment settings (name, description)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Environment name is required'}), 400
        
        # Validate environment_id
        if environment_id not in live_data.environments:
            return jsonify({'success': False, 'error': 'Invalid environment ID'}), 400
        
        # Update database
        success = update_environment_setting(environment_id, name, description if description else None)
        
        if success:
            # Update live data store with new name and description
            with live_data.lock:
                if environment_id in live_data.environments:
                    live_data.environments[environment_id]['name'] = name
                    if description:
                        live_data.environments[environment_id]['description'] = description
            
            app.logger.info(f"Updated environment {environment_id}: name='{name}', description='{description}'")
            return jsonify({
                'success': True, 
                'message': 'Environment settings updated successfully',
                'environment_id': environment_id,
                'name': name,
                'description': description
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update environment settings'}), 500
            
    except Exception as e:
        app.logger.error(f"Error updating environment settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/timeline")
def api_timeline():
    """Get threat timeline data for analytics"""
    hours = request.args.get('hours', 24, type=int)
    timeline = get_threat_timeline(hours)
    return jsonify(timeline)

@app.route("/api/components")
def api_components():
    """Get average threat components for radar chart"""
    hours = request.args.get('hours', 24, type=int)
    components = get_average_threat_components(hours)
    return jsonify(components)

@app.route("/api/test-notification", methods=['POST'])
def api_test_notification():
    """Test notification channels (fake data mode only)"""
    # Only allow in fake data mode
    fake_mode = session.get('fake_mode', True)
    if not fake_mode:
        return jsonify({'success': False, 'error': 'Test notifications only available in fake data mode'})
    
    try:
        data = request.get_json()
        channel = data.get('channel', 'all')
        message = data.get('message', 'Test notification from Environmental Monitoring System')
        
        # Import fake data generator
        from fake_data_generator import FakeDataGenerator
        generator = FakeDataGenerator()
        
        if channel == 'all':
            results = generator.send_test_notifications(message)
        elif channel == 'email':
            results = {'email': generator.send_test_email(message)}
        elif channel == 'teams':
            results = {'teams': generator.send_test_teams(message)}
        elif channel == 'sms':
            results = {'sms': generator.send_test_sms(message)}
        else:
            return jsonify({'success': False, 'error': f'Unknown channel: {channel}'})
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        app.logger.error(f"Error testing notifications: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/events/stream")
def events_stream():
    """Server-Sent Events stream for real-time updates"""
    # Check fake mode outside the generator (in request context)
    fake_mode = session.get('fake_mode', True)
    dashboard_refresh_rate = session.get('dashboard_refresh_rate', 5)
    
    def generate():
        last_event_time = time.time()
        last_data_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Send heartbeat every 30 seconds
            if current_time - last_event_time > 30:
                yield f"event: heartbeat\ndata: {json.dumps({'time': datetime.now().isoformat()})}\n\n"
                last_event_time = current_time
            
            # Check for new events
            try:
                event = live_data.event_queue.get(timeout=0.1)
                yield f"event: {event.get('type', 'update')}\ndata: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send latest data at dashboard refresh rate intervals
                if current_time - last_data_time >= dashboard_refresh_rate:
                    if fake_mode:
                        # Generate fresh data for ALL environments to keep monitoring up-to-date
                        all_envs = live_data.get_all_environments()
                        for env_id in all_envs.keys():
                            env_data = generate_fake_sensor_data(env_id)
                            live_data.update(env_data, env_id)
                        
                        # Get current environment data for the stream
                        data = live_data.get_environment_data(live_data.get_current_environment())
                    else:
                        data = get_realtime_sensor_data()
                    
                    if data:
                        yield f"event: update\ndata: {json.dumps(data)}\n\n"
                    last_data_time = current_time
                else:
                    # Sleep briefly to prevent high CPU usage
                    time.sleep(0.1)
    
    return Response(generate(), mimetype="text/event-stream")

# ==================== TEMPLATE FILTERS ====================

@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format datetime string"""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except:
        return value

@app.template_filter('time_ago')
def time_ago(value):
    """Convert datetime to 'time ago' string"""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"
    except:
        return value

@app.template_filter('threat_color')
def threat_color(level):
    """Get color class for threat level"""
    colors = {
        'LOW': 'success',
        'MODERATE': 'info',
        'ELEVATED': 'warning',
        'HIGH': 'danger',
        'CRITICAL': 'dark'
    }
    return colors.get(level, 'secondary')

@app.template_filter('threat_icon')
def threat_icon(level):
    """Get icon for threat level"""
    icons = {
        'LOW': 'bi-emoji-smile',
        'MODERATE': 'bi-emoji-neutral',
        'ELEVATED': 'bi-exclamation-triangle',
        'HIGH': 'bi-exclamation-diamond',
        'CRITICAL': 'bi-x-octagon'
    }
    return icons.get(level, 'bi-question')

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)