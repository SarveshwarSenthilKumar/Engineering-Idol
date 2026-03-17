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
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', '../users.db')

# Initialize extensions
Session(app)

# Start time for uptime calculation
START_TIME = datetime.now()

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
    
    def update(self, data):
        """Update with latest sensor data"""
        with self.lock:
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
            return self.latest.copy()
    
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

# Initialize live data store
live_data = LiveDataStore()

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
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
            SELECT timestamp, threat_score, quality_score, people_count
            FROM events_log
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (cutoff,))
        
        data = cursor.fetchall()
        return [dict(row) for row in data]
    except Exception as e:
        app.logger.error(f"Error fetching timeline: {e}")
        return []
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

# ==================== FAKE DATA GENERATION ====================

def generate_fake_sensor_data():
    """Generate fake sensor data for demonstration"""
    
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
            'distance': round(random.uniform(1.0, 8.0), 2),  # Start from 1m instead of 0.5m
            'angle': round(random.uniform(-60, 60), 1),
            'activity': activity,
            'abnormal_breathing': abnormal
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
    
    # Calculate overall threat score from components
    calculated_threat = sum(comp['score'] * comp['weight'] for comp in components.values())
    threat_score = max(threat_score, calculated_threat)  # Use the higher of calculated or random
    
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
        'sound_db': sound_db,
        'sound_event': sound_event,
        'sound_spike': sound_spike,
        'air_quality_alarm': air_quality_alarm,
        'noise_alarm': noise_alarm,
        'uptime': (datetime.now() - START_TIME).total_seconds(),
        'data_rate': random.uniform(10, 50),
        'packet_count': random.randint(1000, 9999),
        'last_update': datetime.now().strftime('%H:%M:%S.%f')[:-3],
        'components': components  # Add components to the returned data
    }

def get_realtime_sensor_data():
    """Get real sensor data from database"""
    # This would query your actual database for the latest readings
    # For now, return fake data as fallback
    data = generate_fake_sensor_data()
    data['fake_mode'] = False
    return data

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
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@app.route("/users")
@admin_required
def users():
    """User management page for admins"""
    all_users = get_all_users()
    return render_template('users.html', users=all_users)

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

@app.route("/")
def index():
    """Main dashboard page"""
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
@login_required
def dashboard():
    """Live monitoring dashboard"""
    return render_template('dashboard.html',
                         current_time=datetime.now().isoformat())

@app.route("/sensors")
@login_required
def sensors():
    """Person tracking sensor dashboard"""
    # Get fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Generate fake data for demonstration
        data = generate_fake_sensor_data()
    else:
        # Try to get real data from database
        data = get_realtime_sensor_data()
    
    # Add fake mode flag to template
    data['fake_mode'] = fake_mode
    
    # Add recent logs
    data['recent_logs'] = generate_recent_logs()
    data['last_update'] = datetime.now().strftime('%H:%M:%S')
    
    return render_template('sensors.html', **data)

@app.route("/history")
@login_required
def history():
    """Event history page"""
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
                         current_time=datetime.now().isoformat())

@app.route("/analytics")
@login_required
def analytics():
    """Analytics and charts page"""
    timeline = get_threat_timeline(24)
    stats = get_threat_statistics(24)
    return render_template('analytics.html',
                         timeline=json.dumps(timeline),
                         stats=stats,
                         current_time=datetime.now().isoformat())

@app.route("/targets")
@login_required
def targets_view():
    """Person tracking view"""
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Generate fake target data
        targets = []
        people_count = random.randint(1, 5)
        
        for i in range(people_count):
            activity = random.choice(['stationary', 'sitting', 'walking', 'running'])
            abnormal = random.random() < 0.2
            
            targets.append({
                'target_id': f"T{random.randint(1,99):02d}",
                'target_distance': round(random.uniform(1.0, 8.0), 2),
                'target_angle': round(random.uniform(-60, 60), 1),
                'target_velocity': round(random.uniform(0, 2.0), 2) if activity in ['walking', 'running'] else 0,
                'target_activity': activity,
                'target_breathing_rate': round(random.uniform(12, 20), 1) if random.random() < 0.7 else None,
                'target_abnormal_breathing': abnormal,
                'target_confidence': round(random.uniform(0.7, 0.95), 2),
                'event_timestamp': (datetime.now() - timedelta(seconds=random.randint(0, 300))).isoformat()
            })
    else:
        # Get real target data from database
        targets = get_target_history(30)
    
    return render_template('targets.html',
                         targets=targets,
                         current_time=datetime.now().isoformat())

@app.route("/settings")
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html',
                         current_time=datetime.now().isoformat(),
                         database_path=app.config.get('DATABASE_PATH', 'N/A'),
                         other_config_values=app.config.get('OTHER_CONFIG_VALUES', 'N/A'))

# ==================== API ROUTES ====================

@app.route("/api/targets")
def api_targets():
    """Get recent target data"""
    minutes = request.args.get('minutes', 30, type=int)
    
    # Check fake mode from session (default to True for demo)
    fake_mode = session.get('fake_mode', True)
    
    if fake_mode:
        # Generate fake target data
        targets = []
        people_count = random.randint(1, 5)
        
        for i in range(people_count):
            activity = random.choice(['stationary', 'sitting', 'walking', 'running'])
            abnormal = random.random() < 0.2
            
            targets.append({
                'target_id': f"T{random.randint(1,99):02d}",
                'target_distance': round(random.uniform(1.0, 8.0), 2),
                'target_angle': round(random.uniform(-60, 60), 1),
                'target_velocity': round(random.uniform(0, 2.0), 2) if activity in ['walking', 'running'] else 0,
                'target_activity': activity,
                'target_breathing_rate': round(random.uniform(12, 20), 1) if random.random() < 0.7 else None,
                'target_abnormal_breathing': abnormal,
                'target_confidence': round(random.uniform(0.7, 0.95), 2),
                'event_timestamp': (datetime.now() - timedelta(seconds=random.randint(0, 300))).isoformat()
            })
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
        # Generate fake events
        events = []
        event_types = ['NORMAL', 'MOTION', 'SOUND_SPIKE', 'THREAT_CHANGE', 'PERSON_DETECTED']
        threat_levels = ['LOW', 'MODERATE', 'ELEVATED', 'HIGH', 'CRITICAL']
        
        for i in range(limit):
            events.append({
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(0, 120))).isoformat(),
                'event_type': random.choice(event_types),
                'threat_level': random.choice(threat_levels),
                'threat_score': random.randint(0, 100),
                'people_count': random.randint(0, 5),
                'sound_db': round(random.uniform(30, 80), 1),
                'air_aqi': random.randint(20, 150)
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
        data = generate_fake_sensor_data()
    else:
        data = live_data.get_latest()
        if not data:
            data = generate_fake_sensor_data()
    
    return jsonify(data)

@app.route("/api/timeline")
def api_timeline():
    """Get timeline data for analytics"""
    hours = request.args.get('hours', 24, type=int)
    return jsonify(get_threat_timeline(hours))

@app.route("/api/events/stream")
def events_stream():
    """Server-Sent Events stream for real-time updates"""
    # Check fake mode outside the generator (in request context)
    fake_mode = session.get('fake_mode', True)
    
    def generate():
        last_event_time = time.time()
        while True:
            # Send heartbeat every 30 seconds
            if time.time() - last_event_time > 30:
                yield f"event: heartbeat\ndata: {json.dumps({'time': datetime.now().isoformat()})}\n\n"
                last_event_time = time.time()
            
            # Check for new events
            try:
                event = live_data.event_queue.get(timeout=1)
                yield f"event: {event.get('type', 'update')}\ndata: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send latest data as fallback, using the fake_mode captured above
                if fake_mode:
                    # Generate fake data for dashboard
                    data = generate_fake_sensor_data()
                else:
                    data = live_data.get_latest()
                
                if data:
                    yield f"event: update\ndata: {json.dumps(data)}\n\n"
    
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