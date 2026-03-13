#!/usr/bin/env python3
"""
Environmental Monitoring System - Web Interface
Provides live visual readings, threat scores, and event history
"""

from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for, Response
from flask_session import Session
from datetime import datetime, timedelta
import pytz
import os
import re
import json
import sqlite3
import threading
import time
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

# ==================== ROUTES ====================

@app.route("/")
def index():
    """Main dashboard page"""
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
def dashboard():
    """Live monitoring dashboard"""
    return render_template('dashboard.html',
                         current_time=datetime.now().isoformat())

@app.route("/history")
def history():
    """Event history page"""
    events = get_recent_events(100)
    stats = get_threat_statistics(24)
    return render_template('history.html',
                         events=events,
                         stats=stats,
                         current_time=datetime.now().isoformat())

@app.route("/analytics")
def analytics():
    """Analytics and charts page"""
    timeline = get_threat_timeline(24)
    stats = get_threat_statistics(24)
    return render_template('analytics.html',
                         timeline=json.dumps(timeline),
                         stats=stats,
                         current_time=datetime.now().isoformat())

@app.route("/targets")
def targets_view():
    """Target tracking view"""
    targets = get_target_history(30)
    return render_template('targets.html',
                         targets=targets,
                         current_time=datetime.now().isoformat())

@app.route("/settings")
def settings():
    """Settings page"""
    return render_template('settings.html',
                         current_time=datetime.now().isoformat())

# ==================== API ROUTES ====================

@app.route("/api/live")
def api_live():
    """Get latest live data"""
    return jsonify(live_data.get_latest())

@app.route("/api/events/recent")
def api_recent_events():
    """Get recent events"""
    limit = request.args.get('limit', 50, type=int)
    events = get_recent_events(limit)
    return jsonify(events)

@app.route("/api/stats")
def api_stats():
    """Get statistics"""
    hours = request.args.get('hours', 24, type=int)
    stats = get_threat_statistics(hours)
    return jsonify(stats)

@app.route("/api/timeline")
def api_timeline():
    """Get timeline data for charts"""
    hours = request.args.get('hours', 24, type=int)
    timeline = get_threat_timeline(hours)
    return jsonify(timeline)

@app.route("/api/history/<metric>")
def api_history(metric):
    """Get historical data for a specific metric"""
    minutes = request.args.get('minutes', 60, type=int)
    data = live_data.get_history(metric, minutes)
    
    # Format for charts
    formatted = [{
        'timestamp': ts.isoformat(),
        'value': val
    } for ts, val in data]
    
    return jsonify(formatted)

@app.route("/api/targets")
def api_targets():
    """Get recent target data"""
    minutes = request.args.get('minutes', 30, type=int)
    targets = get_target_history(minutes)
    return jsonify(targets)

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

@app.route("/api/events/stream")
def events_stream():
    """Server-Sent Events stream for real-time updates"""
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
                # Send latest data as fallback
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