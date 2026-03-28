#!/usr/bin/env python3
"""
SCOPE - Web Interface (Heroku Deployment)
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
import google.generativeai as genai
import io
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration for Heroku
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'events.db')

# Heroku-specific configuration
if 'DYNO' in os.environ:
    # Running on Heroku
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Initialize session
Session(app)

# Database initialization for Heroku
def init_database():
    """Initialize database for Heroku deployment"""
    conn = None
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                environment_id TEXT DEFAULT 'primary',
                threat_level TEXT,
                threat_score REAL,
                quality_score REAL,
                people_count INTEGER,
                sound_db REAL,
                air_aqi REAL,
                event_type TEXT,
                description TEXT
            )
        ''')
        
        # Create default admin user if not exists
        cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            admin_password = generate_password_hash('admin123')
            cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                         ('admin', admin_password, 'admin'))
        
        conn.commit()
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

# Initialize database on startup
init_database()

# Fake data generation for demo
def generate_fake_data():
    """Generate fake sensor data for demonstration"""
    import random
    
    # Generate fake threat score
    threat_score = random.uniform(0, 100)
    if threat_score < 20:
        threat_level = "LOW"
        threat_color = "🟢"
    elif threat_score < 40:
        threat_level = "MODERATE"
        threat_color = "🟡"
    elif threat_score < 60:
        threat_level = "ELEVATED"
        threat_color = "🟠"
    elif threat_score < 80:
        threat_level = "HIGH"
        threat_color = "🔴"
    else:
        threat_level = "CRITICAL"
        threat_color = "⚫"
    
    # Generate fake environmental data
    data = {
        'timestamp': datetime.now(pytz.UTC).isoformat(),
        'threat_score': round(threat_score, 1),
        'threat_level': threat_level,
        'threat_color': threat_color,
        'quality_score': round(random.uniform(60, 95), 1),
        'people_count': random.randint(0, 10),
        'sound_db': round(random.uniform(30, 80), 1),
        'air_aqi': round(random.uniform(10, 100), 1),
        'air_voc_ppm': round(random.uniform(10, 100), 1),
        'air_pm25': round(random.uniform(5, 50), 1),
        'sensor_status': {
            'radar': True,
            'pms5003': True,
            'mq135': True,
            'sound': True
        },
        'targets': [
            {
                'id': 1,
                'x': random.uniform(-5, 5),
                'y': random.uniform(-5, 5),
                'velocity': random.uniform(0, 2),
                'confidence': random.uniform(0.7, 1.0),
                'activity': random.choice(['normal', 'walking', 'running', 'still']),
                'breathing_rate': random.uniform(12, 20)
            }
        ] if random.random() > 0.3 else []
    }
    
    return data

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        conn = None
        try:
            conn = sqlite3.connect(app.config['DATABASE_PATH'])
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[3]
                session.permanent = False
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                
        except Exception as e:
            flash('Login error. Please try again.', 'error')
        finally:
            if conn:
                conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/scenarios')
@login_required
def scenarios():
    return render_template('scenarios.html')

@app.route('/documentation')
@login_required
def documentation():
    return render_template('scope-docs.html')

@app.route('/api/data')
def api_data():
    """API endpoint for real-time data"""
    data = generate_fake_data()
    return jsonify(data)

@app.route('/api/events')
def api_events():
    """API endpoint for historical events"""
    conn = None
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, threat_level, threat_score, quality_score, 
                   people_count, sound_db, air_aqi, event_type, description
            FROM events_log 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''')
        events = cursor.fetchall()
        
        events_list = []
        for event in events:
            events_list.append({
                'timestamp': event[0],
                'threat_level': event[1],
                'threat_score': event[2],
                'quality_score': event[3],
                'people_count': event[4],
                'sound_db': event[5],
                'air_aqi': event[6],
                'event_type': event[7],
                'description': event[8]
            })
        
        return jsonify({'events': events_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/simulate_event', methods=['POST'])
@login_required
def api_simulate_event():
    """Simulate an event for demonstration"""
    data = request.get_json()
    event_type = data.get('event_type', 'test')
    description = data.get('description', 'Test event')
    
    conn = None
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Generate fake data for the event
        fake_data = generate_fake_data()
        
        cursor.execute('''
            INSERT INTO events_log 
            (timestamp, environment_id, threat_level, threat_score, quality_score, 
             people_count, sound_db, air_aqi, event_type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(pytz.UTC).isoformat(),
            'primary',
            fake_data['threat_level'],
            fake_data['threat_score'],
            fake_data['quality_score'],
            fake_data['people_count'],
            fake_data['sound_db'],
            fake_data['air_aqi'],
            event_type,
            description
        ))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Event simulated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
