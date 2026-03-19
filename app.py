#!/usr/bin/env python3
"""
SCOPE - Web Interface
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

# Optional imports for PDF generation
try:
    import weasyprint
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PDF generation not available. Install weasyprint and matplotlib for full functionality.")

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
    
    def get_all_environments(self, fake_mode=True):
        """Get all environments data"""
        with self.lock:
            result = {}
            for env_id, env_data in self.environments.items():
                env_copy = env_data.copy()
                # Add online status based on fake mode
                env_copy['online'] = fake_mode
                result[env_id] = env_copy
            return result
    
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
    'cache_duration': 3  # Cache for 3 seconds for less frequent, more natural updates
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
                   sound_db, air_aqi, threat_level
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

# ==================== AI REPORT GENERATION ====================

# Initialize Gemini AI
gemini_api_key = os.getenv('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'))
else:
    gemini_model = None

def generate_ai_summary(events_data, stats_data, time_period="weekly"):
    """Generate AI-powered summary of SCOPE data"""
    if not gemini_model:
        return "AI summary not available - Gemini API key not configured"
    
    try:
        # Get current date for the report
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        # Prepare detailed event data for AI analysis with attack types
        events_summary = ""
        attack_type_analysis = ""
        if events_data and len(events_data) > 0:
            events_summary = "\n\nDETAILED EVENT DATA (SAMPLE):\n"
            attack_types = {}
            
            # Include first 15 events as representative sample
            for i, event in enumerate(events_data[:15]):
                timestamp = event.get('timestamp', 'N/A')
                threat_score = event.get('threat_score', event.get('threat_overall', 0))
                people_count = event.get('people_count', event.get('radar_target_count', 0))
                sound_db = event.get('sound_db', 0)
                air_aqi = event.get('air_aqi', 0)
                threat_level = event.get('threat_level', 'UNKNOWN')
                event_type = event.get('event_type', 'UNKNOWN')
                description = event.get('description', '')
                
                events_summary += f"Event {i+1}: {timestamp}\n"
                events_summary += f"  - Threat Score: {threat_score}/100 ({threat_level})\n"
                events_summary += f"  - Event Type: {event_type}\n"
                events_summary += f"  - People Count: {people_count}\n"
                events_summary += f"  - Noise Level: {sound_db} dB\n"
                events_summary += f"  - Air Quality Index: {air_aqi}\n"
                events_summary += f"  - Description: {description}\n\n"
                
                # Track attack types for analysis
                if event_type != 'UNKNOWN':
                    attack_types[event_type] = attack_types.get(event_type, 0) + 1
            
            # Add attack type analysis
            if attack_types:
                attack_type_analysis = "\n\nATTACK/EVENT TYPE ANALYSIS:\n"
                for event_type, count in sorted(attack_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(events_data)) * 100
                    attack_type_analysis += f"- {event_type}: {count} events ({percentage:.1f}%)\n"
        
        # Prepare additional statistics for deeper analysis
        max_threat = stats_data.get('max_threat', 0)
        min_threat = stats_data.get('min_threat', 0) if 'min_threat' in stats_data else 0
        critical_ratio = (stats_data.get('critical_count', 0) / max(stats_data.get('total_events', 1), 1)) * 100
        high_ratio = (stats_data.get('high_count', 0) / max(stats_data.get('total_events', 1), 1)) * 100
        
        # Prepare data for AI with enhanced prompt and no token limits
        prompt = f"""
        As an expert safety and security analyst, conduct an extremely comprehensive and detailed analysis of the following {time_period} SCOPE monitoring data from a school facility. Provide an exhaustive, data-driven professional summary for school administration that demonstrates deep understanding of all security metrics, attack patterns, and operational insights.

        COMPREHENSIVE SECURITY STATISTICS:
        - Total Monitoring Events: {stats_data.get('total_events', 0)}
        - Average Threat Score: {stats_data.get('avg_threat', 0):.1f}/100
        - Maximum Threat Score: {max_threat:.1f}/100
        - Minimum Threat Score: {min_threat:.1f}/100
        - Average People Count: {stats_data.get('avg_people', 0):.1f}
        - Average Noise Level: {stats_data.get('avg_noise', 0):.1f} dB
        - Average Air Quality Index: {stats_data.get('avg_aqi', 0):.0f}
        - Critical Events: {stats_data.get('critical_count', 0)} ({critical_ratio:.1f}% of total)
        - High Threat Events: {stats_data.get('high_count', 0)} ({high_ratio:.1f}% of total)
        - Elevated Events: {stats_data.get('elevated_count', 0)}
        - Moderate Events: {stats_data.get('moderate_count', 0)}
        - Low Events: {stats_data.get('low_count', 0)}

        THREAT LEVEL ANALYSIS:
        - Critical: {stats_data.get('critical_count', 0)} events - Immediate action required
        - High: {stats_data.get('high_count', 0)} events - Urgent attention needed
        - Elevated: {stats_data.get('elevated_count', 0)} events - Monitor closely
        - Moderate: {stats_data.get('moderate_count', 0)} events - Normal monitoring
        - Low: {stats_data.get('low_count', 0)} events - All clear
        {events_summary}
        {attack_type_analysis}

        COMPREHENSIVE ANALYTICAL REQUIREMENTS:
        Provide an extremely detailed analysis covering all aspects of the facility's security and SCOPE monitoring:

        1. **Executive Summary** (5-6 sentences): Provide a comprehensive high-level overview of the facility's security status, highlighting the most significant findings, overall risk assessment, and critical security concerns that require immediate attention.

        2. **Detailed Threat Analysis**: Conduct an in-depth analysis of threat patterns, including:
           - Peak threat periods and time-based patterns
           - Correlation between threat levels and facility factors
           - Threat escalation patterns and triggers
           - Geographic or location-based threat concentrations
           - Any concerning trends, anomalies, or unusual patterns
           - Threat frequency and intensity analysis

        3. **Attack/Event Type Analysis**: Provide detailed analysis of security events and attack patterns:
           - Most common types of security events or attacks
           - Severity levels by attack type
           - Time-based patterns for different attack types
           - Success/failure rates of different attack attempts
           - Emerging or new attack patterns
           - Correlation between attack types and facility conditions

        4. **Facility Impact Assessment**: Evaluate how facility factors affect security:
           - Air quality impact on threat levels and detection accuracy
           - Noise level correlations with security events
           - People count patterns and crowd-related security risks
           - Environmental conditions that facilitate or deter security threats
           - Seasonal or time-based environmental patterns affecting security

        5. **Comprehensive Risk Assessment**: Identify and analyze specific security risks:
           - Immediate critical risks requiring urgent action
           - Medium-term risks that need monitoring and mitigation
           - Long-term strategic security concerns
           - Probability and potential impact assessment for each risk
           - Risk interdependencies and cascading effects
           - Vulnerability assessment based on threat patterns

        6. **Operational Security Insights**: Provide detailed observations about security operations:
           - Peak security activity times and staffing implications
           - Operational inefficiencies in security monitoring
           - Equipment or system performance issues
           - Response time analysis for security events
           - Resource allocation effectiveness
           - Training and procedural gaps identified through event analysis

        7. **Positive Security Performance Metrics**: Highlight effective security measures:
           - Successful threat prevention or mitigation
           - Areas where security systems performed exceptionally well
           - Improvements made during the reporting period
           - Effective security protocols and procedures
           - Staff performance highlights
           - Technology and system successes

        8. **Strategic Security Recommendations** (7-10 specific, actionable items): Provide detailed, prioritized recommendations for:
           - Immediate security improvements and urgent actions
           - Long-term security enhancements and infrastructure investments
           - Operational procedure modifications and protocol updates
           - Staff training requirements and skill development
           - Technology upgrades and system improvements
           - Monitoring system enhancements and coverage improvements
           - Emergency response and incident response improvements
           - Physical security enhancements
           - Cybersecurity integration with physical security
           - Community and stakeholder engagement strategies

        Format the response exactly as follows:

        # SCOPE Security Weekly Summary - {date_range}

        **Prepared By:** SCOPE  
        **Date:** {current_date}

        ## Executive Summary
        [Provide comprehensive executive summary here]

        ## Detailed Threat Analysis
        [Provide exhaustive threat analysis with specific data points, trends, and patterns]

        ## Attack/Event Type Analysis
        [Provide detailed analysis of security events and attack patterns]

        ## Facility Impact Assessment
        [Provide detailed assessment of facility factors affecting security]

        ## Comprehensive Risk Assessment
        [Identify specific risks with probability, impact, and mitigation strategies]

        ## Operational Security Insights
        [Provide detailed insights about security operations and performance]

        ## Positive Security Performance Metrics
        [Highlight areas of excellent security performance and improvements]

        ## Strategic Security Recommendations
        [Provide 7-10 detailed, prioritized, actionable security recommendations]

        Use highly professional, analytical language appropriate for school board, security leadership, and administrative review. Include specific data points, percentages, time-based trends, and actionable intelligence. Be extremely detailed and thorough in your analysis. Use markdown formatting with ## for section headers and ** for bold text.
        """
        
        # Configure model for longer responses
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 8192,  # Increased token limit
        }
        
        response = gemini_model.generate_content(prompt, generation_config=generation_config)
        return response.text
        
    except Exception as e:
        app.logger.error(f"Error generating AI summary: {e}")
        return f"AI summary generation failed: {str(e)}"

def generate_ai_recommendations(events_data, stats_data, time_period="weekly"):
    """Generate AI-powered air quality analysis recommendations"""
    if not gemini_model:
        return "AI recommendations not available - Gemini API key not configured"
    
    try:
        # Prepare data for AI
        prompt = f"""
        As an expert air quality analyst, analyze the following {time_period} SCOPE monitoring data from a school facility and provide concise, actionable recommendations for improving air quality.

        KEY SCOPE STATISTICS:
        - Average Threat Score: {stats_data.get('avg_threat', 0):.1f}/100
        - Average People Count: {stats_data.get('avg_people', 0):.1f}
        - Average Noise Level: {stats_data.get('avg_noise', 0):.1f} dB
        - Average Air Quality Index: {stats_data.get('avg_aqi', 0):.0f}
        - Total Events: {stats_data.get('total_events', 0)}
        - Critical Events: {stats_data.get('critical_count', 0)}
        - High Threat Events: {stats_data.get('high_count', 0)}

        Provide 5-7 concise, actionable air quality recommendations. Focus on:
        1. Air quality monitoring improvements
        2. Ventilation system enhancements
        3. Air purification solutions
        4. Environmental health protocols
        5. Indoor air quality management
        6. Outdoor air quality considerations
        7. Student and staff health protection

        Each recommendation should be:
        - Specific and measurable
        - Practical to implement
        - Cost-effective where possible
        - Focused on improving air quality and health outcomes

        Format as a numbered list with brief explanations. Keep responses concise and actionable.
        """
        
        response = gemini_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        app.logger.error(f"Error generating AI recommendations: {e}")
        return f"AI recommendations generation failed: {str(e)}"

def generate_preventative_recommendations(stats_data):
    """Generate AI-powered preventative recommendations"""
    if not gemini_model:
        return "AI recommendations not available - Gemini API key not configured"
    
    try:
        # Prepare data for AI
        prompt = f"""
        As an expert safety and security consultant, analyze the following SCOPE monitoring data from a school facility and provide specific, actionable preventative recommendations.

        KEY STATISTICS:
        - Average Threat Score: {stats_data.get('avg_threat', 0):.1f}/100
        - Average Quality Score: {stats_data.get('avg_quality', 0):.1f}/100
        - Average People Count: {stats_data.get('avg_people', 0):.1f}
        - Average Noise Level: {stats_data.get('avg_noise', 0):.1f} dB
        - Average Air Quality Index: {stats_data.get('avg_aqi', 0):.0f}
        - Total Events: {stats_data.get('total_events', 0)}
        - Critical Events: {stats_data.get('critical_count', 0)}
        - High Threat Events: {stats_data.get('high_count', 0)}

        THREAT LEVEL DISTRIBUTION:
        - Critical: {stats_data.get('critical_count', 0)} events
        - High: {stats_data.get('high_count', 0)} events  
        - Elevated: {stats_data.get('elevated_count', 0)} events
        - Moderate: {stats_data.get('moderate_count', 0)} events
        - Low: {stats_data.get('low_count', 0)} events

        Please provide 5-7 specific, actionable preventative recommendations that the school administration can implement immediately. Focus on:
        1. Security enhancements
        2. Facility improvements
        3. Operational procedures
        4. Staff training
        5. Infrastructure upgrades
        6. Monitoring improvements
        7. Emergency preparedness

        Each recommendation should be:
        - Specific and measurable
        - Practical to implement
        - Cost-effective where possible
        - Focused on prevention rather than reaction

        Format as a numbered list with brief explanations for each recommendation.
        """
        
        response = gemini_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        app.logger.error(f"Error generating AI recommendations: {e}")
        return f"AI recommendations generation failed: {str(e)}"

def create_chart_image(data, chart_type, title):
    """Create a matplotlib chart and return as base64 image"""
    if not PDF_AVAILABLE:
        return None
        
    try:
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == 'timeline':
            timestamps = [datetime.fromisoformat(d['timestamp']) for d in data]
            threat_scores = [d.get('threat_score', 0) for d in data]
            quality_scores = [d.get('quality_score', 0) for d in data]
            
            ax.plot(timestamps, threat_scores, 'r-', label='Threat Score', linewidth=2)
            ax.plot(timestamps, quality_scores, 'g-', label='Quality Score', linewidth=2)
            ax.set_title(title)
            ax.set_ylabel('Score')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        elif chart_type == 'threat_distribution':
            levels = ['Critical', 'High', 'Elevated', 'Moderate', 'Low']
            counts = [
                sum(1 for d in data if d.get('threat_score', 0) >= 80),
                sum(1 for d in data if 60 <= d.get('threat_score', 0) < 80),
                sum(1 for d in data if 40 <= d.get('threat_score', 0) < 60),
                sum(1 for d in data if 20 <= d.get('threat_score', 0) < 40),
                sum(1 for d in data if d.get('threat_score', 0) < 20)
            ]
            colors = ['#8B0000', '#DC143C', '#FF8C00', '#FFD700', '#32CD32']
            
            ax.pie(counts, labels=levels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title(title)
            
        elif chart_type == 'facility_metrics':
            timestamps = [datetime.fromisoformat(d['timestamp']) for d in data]
            noise_levels = [d.get('sound_db', 0) for d in data]
            aqi_levels = [d.get('air_aqi', 0) for d in data]
            
            ax2 = ax.twinx()
            ax.plot(timestamps, noise_levels, 'b-', label='Noise (dB)', linewidth=2)
            ax2.plot(timestamps, aqi_levels, 'orange', label='AQI', linewidth=2)
            
            ax.set_ylabel('Noise (dB)', color='b')
            ax2.set_ylabel('Air Quality Index', color='orange')
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            
            # Combine legends
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        app.logger.error(f"Error creating chart: {e}")
        return None

def generate_weekly_html_report():
    """Generate comprehensive weekly HTML report"""
    if not PDF_AVAILABLE:
        raise ImportError("PDF generation not available. Install weasyprint and matplotlib.")
        
    try:
        # Get weekly data (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get events data
        cursor.execute("""
            SELECT timestamp, threat_overall, quality_score, radar_target_count, 
                   sound_db, air_aqi, threat_level
            FROM events 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (week_ago,))
        
        events_data = [dict(row) for row in cursor.fetchall()]
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                AVG(threat_overall) as avg_threat,
                MAX(threat_overall) as max_threat,
                AVG(quality_score) as avg_quality,
                AVG(radar_target_count) as avg_people,
                AVG(sound_db) as avg_noise,
                AVG(air_aqi) as avg_aqi,
                SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN threat_level = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN threat_level = 'ELEVATED' THEN 1 ELSE 0 END) as elevated_count,
                SUM(CASE WHEN threat_level = 'MODERATE' THEN 1 ELSE 0 END) as moderate_count,
                SUM(CASE WHEN threat_level = 'LOW' THEN 1 ELSE 0 END) as low_count
            FROM events
            WHERE timestamp >= ?
        """, (week_ago,))
        
        stats_data = dict(cursor.fetchone())
        conn.close()
        
        # Generate AI summary
        ai_summary = generate_ai_summary(events_data, stats_data, "weekly")
        
        # Create charts
        timeline_img = create_chart_image(events_data, 'timeline', '7-Day Threat and Quality Timeline')
        threat_img = create_chart_image(events_data, 'threat_distribution', 'Threat Level Distribution')
        facility_img = create_chart_image(events_data, 'facility_metrics', 'Noise and Air Quality Trends')
        
        # Generate preventative recommendations
        preventative_text = generate_preventative_recommendations(stats_data)
        
        # Create HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SCOPE Weekly Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #007bff;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #007bff;
                    margin: 0;
                }}
                .metadata {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .metadata table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .metadata td {{
                    padding: 8px;
                    border-bottom: 1px solid #dee2e6;
                }}
                .metadata td:first-child {{
                    font-weight: bold;
                    width: 30%;
                }}
                .section {{
                    margin: 30px 0;
                    page-break-inside: avoid;
                }}
                .section h2 {{
                    color: #007bff;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 10px;
                }}
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .stats-table th,
                .stats-table td {{
                    border: 1px solid #dee2e6;
                    padding: 12px;
                    text-align: center;
                }}
                .stats-table th {{
                    background: #007bff;
                    color: white;
                    font-weight: bold;
                }}
                .stats-table tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                .chart {{
                    text-align: center;
                    margin: 20px 0;
                    page-break-inside: avoid;
                }}
                .chart img {{
                    max-width: 100%;
                    height: auto;
                }}
                .ai-summary {{
                    background: #e9ecef;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    white-space: pre-wrap;
                    font-family: Arial, sans-serif;
                }}
                .recommendations {{
                    background: #d4edda;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    border-left: 4px solid #28a745;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #dee2e6;
                    color: #6c757d;
                    font-size: 0.9em;
                }}
                @media print {{
                    body {{ margin: 20px; }}
                    .section {{ page-break-inside: avoid; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>SCOPE Weekly Report</h1>
                <p>Professional Analysis for School Administration</p>
            </div>
            
            <div class="metadata">
                <table>
                    <tr>
                        <td>Report Generated:</td>
                        <td>{datetime.now().strftime("%B %d, %Y")}</td>
                    </tr>
                    <tr>
                        <td>Analysis Period:</td>
                        <td>{(datetime.now() - timedelta(days=7)).strftime("%B %d, %Y")} - {datetime.now().strftime("%B %d, %Y")}</td>
                    </tr>
                    <tr>
                        <td>Facility:</td>
                        <td>SCOPE</td>
                    </tr>
                    <tr>
                        <td>Total Monitoring Hours:</td>
                        <td>168 hours</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <div class="ai-summary">{ai_summary}</div>
            </div>
            
            <div class="section">
                <h2>Key Performance Indicators</h2>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Average Threat Score</td>
                            <td>{stats_data.get('avg_threat', 0):.1f}/100</td>
                        </tr>
                        <tr>
                            <td>Average Quality Score</td>
                            <td>{stats_data.get('avg_quality', 0):.1f}/100</td>
                        </tr>
                        <tr>
                            <td>Average Occupancy</td>
                            <td>{stats_data.get('avg_people', 0):.1f} people</td>
                        </tr>
                        <tr>
                            <td>Average Noise Level</td>
                            <td>{stats_data.get('avg_noise', 0):.1f} dB</td>
                        </tr>
                        <tr>
                            <td>Average Air Quality Index</td>
                            <td>{stats_data.get('avg_aqi', 0):.0f}</td>
                        </tr>
                        <tr>
                            <td>Total Events Recorded</td>
                            <td>{stats_data.get('total_events', 0)}</td>
                        </tr>
                        <tr>
                            <td>Critical Threat Events</td>
                            <td>{stats_data.get('critical_count', 0)}</td>
                        </tr>
                        <tr>
                            <td>High Threat Events</td>
                            <td>{stats_data.get('high_count', 0)}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            {f'''<div class="section">
                <h2>Threat & Quality Trends</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{timeline_img}" alt="Threat and Quality Timeline">
                </div>
            </div>''' if timeline_img else ''}
            
            {f'''<div class="section">
                <h2>Threat Level Distribution</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{threat_img}" alt="Threat Level Distribution">
                </div>
            </div>''' if threat_img else ''}
            
            {f'''<div class="section">
                <h2>Environmental Conditions</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{facility_img}" alt="Environmental Metrics">
                </div>
            </div>''' if facility_img else ''}
            
            <div class="section">
                <h2>Preventative Recommendations</h2>
                <div class="recommendations">
                    <pre>{preventative_text}</pre>
                </div>
            </div>
            
            <div class="footer">
                <p>This report was automatically generated by the SCOPE system.</p>
                <p>Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            </div>
        </body>
        </html>
        """
        
        return html_template
        
    except Exception as e:
        app.logger.error(f"Error generating HTML report: {e}")
        raise e

def generate_weekly_pdf_report():
    """Generate comprehensive weekly PDF report using HTML to PDF"""
    html_content = generate_weekly_html_report()
    
    # Convert HTML to PDF using WeasyPrint
    pdf_data = weasyprint.HTML(string=html_content).write_pdf()
    
    return pdf_data

def generate_preventative_recommendations(stats_data):
    """Generate preventative recommendations based on statistics"""
    recommendations = []
    
    avg_threat = stats_data.get('avg_threat', 0)
    critical_count = stats_data.get('critical_count', 0)
    high_count = stats_data.get('high_count', 0)
    avg_noise = stats_data.get('avg_noise', 0)
    avg_aqi = stats_data.get('avg_aqi', 0)
    avg_people = stats_data.get('avg_people', 0)
    
    if avg_threat > 60:
        recommendations.append("• Review and enhance security protocols during high-threat periods")
    
    if critical_count > 0:
        recommendations.append("• Implement immediate response plan for critical threat events")
    
    if high_count > 5:
        recommendations.append("• Conduct staff training on threat de-escalation procedures")
    
    if avg_noise > 70:
        recommendations.append("• Install noise reduction measures in high-traffic areas")
    
    if avg_aqi > 100:
        recommendations.append("• Improve ventilation systems and consider air purification solutions")
    
    if avg_people > 10:
        recommendations.append("• Monitor occupancy levels and implement crowd management strategies")
    
    if not recommendations:
        recommendations.append("• Continue current monitoring protocols - all indicators within acceptable ranges")
    
    return '\n'.join(recommendations)

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
    
    # Use the calculated threat as the primary score with minimal natural variation
    # Add small random walk for natural movement
    import time
    current_time = time.time()
    
    # Create a more natural variation based on time (slower changes)
    time_factor = math.sin(current_time / 30) * 3  # Slow oscillation over ~30 seconds
    small_variation = random.uniform(-1, 1)  # Much smaller variation
    
    threat_score = calculated_threat + time_factor + small_variation
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

def create_user(username, password, email, role='user', name=None, phone=None, dob=None, gender=None):
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
            INSERT INTO users (username, password, emailAddress, role, name, phoneNumber, dateOfBirth, gender, dateJoined, accountStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, password_hash, email, role, name, phone, dob, gender, datetime.now().isoformat(), 'active'))
        
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
    name = request.form.get('name', '').strip() or None
    phone = request.form.get('phone', '').strip() or None
    dob = request.form.get('dob', '').strip() or None
    gender = request.form.get('gender', '').strip() or None
    
    if not username or not email or not password:
        flash('Username, email, and password are required.', 'error')
        return redirect(url_for('users'))
    
    success, message = create_user(username, password, email, role, name, phone, dob, gender)
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

@app.route("/weekly-report")
@login_required
def weekly_report():
    """Comprehensive weekly report page"""
    # Get environment data for consistency
    fake_mode = session.get('fake_mode', True)
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    # Get weekly statistics (7 days = 168 hours)
    stats = get_threat_statistics(168)
    
    # Calculate report metadata
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    uptime = str(end_date - START_TIME).split('.')[0]  # Remove microseconds
    
    # Get critical events for the week
    conn = get_db_connection()
    cursor = conn.cursor()
    week_ago = start_date.isoformat()
    
    try:
        cursor.execute("""
            SELECT timestamp, threat_score, people_count, sound_db, air_aqi, description
            FROM events_log
            WHERE timestamp >= ? AND threat_level = 'CRITICAL'
            ORDER BY timestamp DESC
            LIMIT 20
        """, (week_ago,))
        
        critical_events = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        app.logger.error(f"Error fetching critical events: {e}")
        critical_events = []
    finally:
        conn.close()
    
    return render_template('weekly_report.html',
                         stats=stats,
                         report_date=end_date.strftime('%B %d, %Y at %I:%M %p'),
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         uptime=uptime,
                         critical_events=critical_events,
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
    
    # Check if a scenario is active
    if active_scenario:
        # Return scenario data with real-time variations
        data = generate_scenario_data(active_scenario)
        return jsonify(data)
    
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
        # Get real sensor data
        data = get_realtime_sensor_data()
        # Don't fall back to fake data - return empty data when no real data available
    
    return jsonify(data or {})

@app.route("/api/environments")
def api_environments():
    """Get all environments data"""
    fake_mode = session.get('fake_mode', True)
    return jsonify(live_data.get_all_environments(fake_mode))

@app.route("/api/environment/current", methods=['GET', 'POST'])
@login_required
def update_environment():
    """Update current environment"""
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

@app.route("/api/test-notification", methods=["POST"])
def api_test_notification():
    """Test notification channels (fake data mode only)"""
    # Only allow in fake data mode
    fake_mode = session.get('fake_mode', True)
    if not fake_mode:
        return jsonify({'success': False, 'error': 'Test notifications only available in fake data mode'})
    
    try:
        data = request.get_json()
        channel = data.get('channel', 'all')
        message = data.get('message', 'Test notification from SCOPE')
        use_ai_summary = data.get('use_ai_summary', False)
        
        # Import fake data generator
        from fake_data_generator import FakeDataGenerator
        generator = FakeDataGenerator()
        
        # Generate AI summary if requested
        ai_summary = None
        if use_ai_summary:
            ai_summary = generate_test_ai_summary()
        
        if channel == 'all':
            results = generator.send_test_notifications(message, ai_summary)
        elif channel == 'email':
            results = {'email': generator.send_test_email(message, ai_summary)}
        elif channel == 'teams':
            results = {'teams': generator.send_test_teams(message, ai_summary)}
        elif channel == 'sms':
            results = {'sms': generator.send_test_sms(message, ai_summary)}
        else:
            return jsonify({'success': False, 'error': f'Unknown channel: {channel}'})
        
        return jsonify({'success': True, 'results': results, 'ai_summary': ai_summary})
        
    except Exception as e:
        app.logger.error(f"Error testing notifications: {e}")
        return jsonify({'success': False, 'error': str(e)})

def generate_test_ai_summary():
    """Generate AI-powered summary for test notifications based on current fake data"""
    try:
        # Get current fake data for real-time analysis
        current_data = get_cached_fake_data()

        # Get recent statistics for AI summary
        stats = get_threat_statistics(hours=1)  # Last hour of fake data
        events = get_recent_events(limit=10)  # Last 10 events

        if not stats or not events:
            return "No recent data available for analysis."

        # Extract current threat score from fake data with safe defaults
        current_threat = current_data.get('threat', {}).get('overall_threat', 0) or 0
        people_count = current_data.get('people_count', 0) or 0
        sound_level = current_data.get('sound', {}).get('db', 0) or 0
        air_quality = current_data.get('odor', {}).get('air_quality_index', 0) or 0

        # Generate AI summary similar to the main report but shorter
        avg_threat = stats.get('avg_threat', 0) or 0
        max_threat = stats.get('max_threat', 0) or 0
        total_events = stats.get('total_events', 0) or 0
        critical_count = stats.get('critical_count', 0) or 0
        high_count = stats.get('high_count', 0) or 0

        # Determine threat level and recommendations based on CURRENT threat score
        if current_threat >= 85:
            threat_level = "CRITICAL"
            urgency = "🚨 IMMEDIATE ACTION REQUIRED"
            threat_emoji = "🔴"
            recommendations = "• Evacuate area immediately if safe\n• Contact emergency services now\n• Implement full lockdown procedures\n• Alert all personnel via all channels"
            analysis = "Extreme threat detected with multiple risk factors active"
        elif current_threat >= 65:
            threat_level = "HIGH"
            urgency = "⚡ URGENT ATTENTION NEEDED"
            threat_emoji = "🟠"
            recommendations = "• Increase security patrols immediately\n• Review live surveillance footage\n• Prepare contingency plans\n• Alert management and security team"
            analysis = "High threat situation requiring immediate intervention"
        elif current_threat >= 45:
            threat_level = "ELEVATED"
            urgency = "⚠️ ENHANCED MONITORING"
            threat_emoji = "🟡"
            recommendations = "• Increase monitoring frequency\n• Verify all access points are secured\n• Alert security personnel to stand by\n• Document all activities"
            analysis = "Elevated risk factors detected - close monitoring required"
        elif current_threat >= 25:
            threat_level = "MODERATE"
            urgency = "📊 INCREASED AWARENESS"
            threat_emoji = "🔵"
            recommendations = "• Continue routine monitoring with increased attention\n• Verify sensor calibration\n• Prepare response protocols\n• Maintain standard security posture"
            analysis = "Moderate threat levels - normal monitoring with increased awareness"
        else:
            threat_level = "LOW"
            urgency = "✅ NORMAL OPERATIONS"
            threat_emoji = "🟢"
            recommendations = "• Continue standard monitoring procedures\n• Maintain regular patrols\n• Document any anomalies\n• System operating within normal parameters"
            analysis = "All systems operating within safe parameters"

        # Add environmental context
        environmental_status = []
        if sound_level > 80:
            environmental_status.append(f"🔊 Sound spike: {sound_level}dB")
        if air_quality > 150:
            environmental_status.append(f"💨 Poor air quality: AQI {air_quality}")
        if people_count > 4:
            environmental_status.append(f"👥 High occupancy: {people_count} people")
        
        env_context = "\nEnvironmental Factors:\n" + "\n".join(f"• {status}" for status in environmental_status) if environmental_status else ""
        
        # Get recent event patterns
        recent_events_text = ""
        if events:
            recent_events_text = "\n📋 Recent Activity:\n"
            for i, event in enumerate(events[:3], 1):
                timestamp = event.get('timestamp', 'Unknown')
                threat_score = event.get('threat_score', 0) or 0
                description = event.get('description', 'No description')
                recent_events_text += f"  {i}. {timestamp[-8:]} - Threat: {threat_score}/100 - {description}\n"
        
        summary = f"""
{threat_emoji} SCOPE THREAT ANALYSIS PING {threat_emoji}

🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📡 Current Status: LIVE FAKE DATA MODE
🎯 Analysis: Real-time threat assessment ping

📊 CURRENT THREAT ASSESSMENT:
• Threat Level: {threat_level} ({current_threat:.1f}/100)
• People Detected: {people_count}
• Sound Level: {sound_level} dB
• Air Quality: AQI {air_quality}
• 1-Hour Average: {avg_threat:.1f}/100
• Peak Threat: {max_threat:.1f}/100

⚡ URGENCY: {urgency}

🧠 Analysis: {analysis}

🎯 IMMEDIATE ACTIONS:
{recommendations}
{env_context}
{recent_events_text}

---
🤖 This analysis was generated by SCOPE system based on current threat assessment.
📱 For detailed reports and live monitoring, check the SCOPE dashboard.
                """.strip()

        return summary

    except Exception as e:
        app.logger.error(f"Error generating AI summary: {e}")
        return f"Analysis Error: {str(e)}"

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

@app.route("/api/data/archive", methods=['POST'])
@login_required
def archive_old_data():
    """Archive data older than specified number of days"""
    try:
        data = request.get_json()
        days = data.get('days', 30)  # Default to 30 days
        
        if days < 1:
            return jsonify({'success': False, 'error': 'Days must be greater than 0'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Create archive tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events_archive AS 
            SELECT * FROM events WHERE 1=0
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events_log_archive AS 
            SELECT * FROM events_log WHERE 1=0
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS targets_archive AS 
            SELECT * FROM targets WHERE 1=0
        ''')
        
        # Move old data to archive tables
        # Archive events
        cursor.execute('''
            INSERT INTO events_archive 
            SELECT * FROM events 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        archived_events = cursor.rowcount
        
        # Archive events_log
        cursor.execute('''
            INSERT INTO events_log_archive 
            SELECT * FROM events_log 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        archived_log = cursor.rowcount
        
        # Archive targets (need to join with events to get timestamp)
        cursor.execute('''
            INSERT INTO targets_archive 
            SELECT t.* FROM targets t
            INNER JOIN events e ON t.event_id = e.id
            WHERE e.timestamp < ?
        ''', (cutoff_date,))
        
        archived_targets = cursor.rowcount
        
        # Delete old data from main tables
        cursor.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM events_log WHERE timestamp < ?", (cutoff_date,))
        
        # Delete targets that belong to archived events
        cursor.execute('''
            DELETE FROM targets 
            WHERE event_id IN (
                SELECT id FROM events 
                WHERE timestamp < ?
            )
        ''', (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        app.logger.info(f"Archived {archived_events} events, {archived_log} log entries, {archived_targets} targets older than {days} days")
        
        return jsonify({
            'success': True,
            'message': f'Successfully archived data older than {days} days',
            'archived_events': archived_events,
            'archived_log': archived_log,
            'archived_targets': archived_targets
        })
        
    except Exception as e:
        app.logger.error(f"Error archiving data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/data/clear", methods=['POST'])
@login_required
def clear_history():
    """Clear all historical data from the database"""
    try:
        # Get confirmation from request body
        data = request.get_json()
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({'success': False, 'error': 'Confirmation required to clear all data'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get counts before deletion for logging
        cursor.execute("SELECT COUNT(*) as count FROM events")
        events_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM events_log")
        log_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM targets")
        targets_count = cursor.fetchone()['count']
        
        # Clear all data from main tables
        cursor.execute("DELETE FROM events")
        cursor.execute("DELETE FROM events_log")
        cursor.execute("DELETE FROM targets")
        
        # Also clear archive tables
        cursor.execute("DELETE FROM events_archive")
        cursor.execute("DELETE FROM events_log_archive")
        cursor.execute("DELETE FROM targets_archive")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('events', 'events_log', 'targets')")
        
        conn.commit()
        conn.close()
        
        app.logger.warning(f"Cleared all historical data: {events_count} events, {log_count} log entries, {targets_count} targets")
        
        return jsonify({
            'success': True,
            'message': 'All historical data has been cleared',
            'cleared_events': events_count,
            'cleared_log': log_count,
            'cleared_targets': targets_count
        })
        
    except Exception as e:
        app.logger.error(f"Error clearing data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/data/export", methods=['GET'])
@login_required
def export_data():
    """Export all data as JSON"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all data from main tables
        cursor.execute("SELECT * FROM events ORDER BY timestamp DESC")
        events = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM events_log ORDER BY timestamp DESC")
        events_log = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM targets ORDER BY timestamp DESC")
        targets = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'events': events,
            'events_log': events_log,
            'targets': targets
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        app.logger.error(f"Error exporting data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/reports/summary")
@login_required
def get_weekly_summary():
    """Get AI-powered executive summary for weekly report"""
    try:
        # Get weekly data
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get events data
        cursor.execute("""
            SELECT timestamp, threat_overall, quality_score, radar_target_count, 
                   sound_db, air_aqi, threat_level
            FROM events 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (week_ago,))
        
        events_data = [dict(row) for row in cursor.fetchall()]
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                AVG(threat_overall) as avg_threat,
                MAX(threat_overall) as max_threat,
                AVG(quality_score) as avg_quality,
                AVG(radar_target_count) as avg_people,
                AVG(sound_db) as avg_noise,
                AVG(air_aqi) as avg_aqi,
                SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN threat_level = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN threat_level = 'ELEVATED' THEN 1 ELSE 0 END) as elevated_count,
                SUM(CASE WHEN threat_level = 'MODERATE' THEN 1 ELSE 0 END) as moderate_count,
                SUM(CASE WHEN threat_level = 'LOW' THEN 1 ELSE 0 END) as low_count
            FROM events
            WHERE timestamp >= ?
        """, (week_ago,))
        
        stats_data = dict(cursor.fetchone())
        conn.close()
        
        # Generate AI summary
        summary = generate_ai_summary(events_data, stats_data, "weekly")
        
        return jsonify({'summary': summary})
        
    except Exception as e:
        app.logger.error(f"Error generating weekly summary: {e}")
        return jsonify({'summary': None}), 500

@app.route("/api/reports/recommendations")
@login_required
def get_weekly_recommendations():
    """Get AI-powered preventative recommendations for weekly report"""
    try:
        # Get weekly data for AI analysis
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get events data
        cursor.execute("""
            SELECT timestamp, threat_overall, quality_score, radar_target_count, 
                   sound_db, air_aqi, threat_level
            FROM events 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (week_ago,))
        
        events_data = [dict(row) for row in cursor.fetchall()]
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                AVG(threat_overall) as avg_threat,
                MAX(threat_overall) as max_threat,
                AVG(quality_score) as avg_quality,
                AVG(radar_target_count) as avg_people,
                AVG(sound_db) as avg_noise,
                AVG(air_aqi) as avg_aqi,
                SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN threat_level = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN threat_level = 'ELEVATED' THEN 1 ELSE 0 END) as elevated_count,
                SUM(CASE WHEN threat_level = 'MODERATE' THEN 1 ELSE 0 END) as moderate_count,
                SUM(CASE WHEN threat_level = 'LOW' THEN 1 ELSE 0 END) as low_count
            FROM events
            WHERE timestamp >= ?
        """, (week_ago,))
        
        stats_data = dict(cursor.fetchone())
        conn.close()
        
        # Generate AI recommendations
        recommendations = generate_ai_recommendations(events_data, stats_data, "weekly")
        
        return jsonify({'recommendations': recommendations})
        
    except Exception as e:
        app.logger.error(f"Error generating AI recommendations: {e}")
        return jsonify({'recommendations': None}), 500

@app.route("/api/reports/detailed-stats")
@login_required
def get_detailed_statistics():
    """Get detailed statistical analysis for weekly report"""
    try:
        # Get 7-day timeline data
        timeline_data = get_threat_timeline(168)
        
        if not timeline_data:
            return jsonify({'stats': []})
        
        # Calculate statistics for each metric
        metrics = {
            'Threat Score': {'values': [], 'unit': ''},
            'Quality Score': {'values': [], 'unit': ''},
            'People Count': {'values': [], 'unit': ''},
            'Noise Level': {'values': [], 'unit': 'dB'},
            'Air Quality': {'values': [], 'unit': 'AQI'}
        }
        
        for data_point in timeline_data:
            metrics['Threat Score']['values'].append(data_point.get('threat_score', 0))
            metrics['Quality Score']['values'].append(data_point.get('quality_score', 0))
            metrics['People Count']['values'].append(data_point.get('people_count', 0))
            metrics['Noise Level']['values'].append(data_point.get('sound_db', 0))
            metrics['Air Quality']['values'].append(data_point.get('air_aqi', 0))
        
        # Calculate statistics
        detailed_stats = []
        for metric_name, metric_data in metrics.items():
            values = metric_data['values']
            if not values:
                continue
                
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            
            # Calculate standard deviation
            variance = sum((x - avg_val) ** 2 for x in values) / len(values)
            std_dev = math.sqrt(variance)
            
            # Determine trend
            trend = "Stable"
            if len(values) >= 10:
                recent_avg = sum(values[-5:]) / 5
                older_avg = sum(values[-10:-5]) / 5
                if recent_avg > older_avg * 1.1:
                    trend = "Increasing"
                elif recent_avg < older_avg * 0.9:
                    trend = "Decreasing"
            
            # Determine status
            status = "Normal"
            status_color = "success"
            if metric_name == 'Threat Score' and avg_val > 60:
                status = "Elevated"
                status_color = "warning"
            elif metric_name == 'Noise Level' and avg_val > 70:
                status = "High"
                status_color = "warning"
            elif metric_name == 'Air Quality' and avg_val > 100:
                status = "Poor"
                status_color = "danger"
            
            detailed_stats.append({
                'metric': metric_name,
                'min': f"{min_val:.1f}{metric_data['unit']}",
                'max': f"{max_val:.1f}{metric_data['unit']}",
                'avg': f"{avg_val:.1f}{metric_data['unit']}",
                'std_dev': f"{std_dev:.2f}",
                'trend': trend,
                'status': status,
                'status_color': status_color
            })
        
        return jsonify({'stats': detailed_stats})
        
    except Exception as e:
        app.logger.error(f"Error generating detailed statistics: {e}")
        return jsonify({'stats': []}), 500

@app.route("/api/reports/event-timerange")
@login_required
def get_event_timerange():
    """Get the time range of first to last event for accurate uptime calculation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get first and last event timestamps
        cursor.execute("""
            SELECT MIN(timestamp) as first_event, 
                   MAX(timestamp) as last_event,
                   COUNT(*) as total_events
            FROM events
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result['first_event'] and result['last_event']:
            first_event = datetime.fromisoformat(result['first_event'])
            last_event = datetime.fromisoformat(result['last_event'])
            
            # Calculate duration
            duration = last_event - first_event
            
            return jsonify({
                'first_event': result['first_event'],
                'last_event': result['last_event'],
                'duration_seconds': int(duration.total_seconds()),
                'duration_formatted': str(duration).split('.')[0],  # Remove microseconds
                'total_events': result['total_events']
            })
        else:
            # No events found, return system uptime as fallback
            uptime = datetime.now() - START_TIME
            return jsonify({
                'first_event': None,
                'last_event': None,
                'duration_seconds': int(uptime.total_seconds()),
                'duration_formatted': str(uptime).split('.')[0],
                'total_events': 0
            })
        
    except Exception as e:
        app.logger.error(f"Error getting event time range: {e}")
        # Fallback to system uptime
        uptime = datetime.now() - START_TIME
        return jsonify({
            'first_event': None,
            'last_event': None,
            'duration_seconds': int(uptime.total_seconds()),
            'duration_formatted': str(uptime).split('.')[0],
            'total_events': 0
        })

@app.route("/api/reports/weekly", methods=['GET'])
@login_required
def generate_weekly_report():
    """Generate and download weekly PDF report"""
    try:
        if not PDF_AVAILABLE:
            return jsonify({
                'success': False, 
                'error': 'PDF generation not available. Install weasyprint and matplotlib packages.'
            }), 500
            
        # Generate PDF report
        pdf_data = generate_weekly_pdf_report()
        
        # Create filename with current date
        filename = f"weekly_environmental_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Return PDF as downloadable file
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': len(pdf_data)
            }
        )
        
    except Exception as e:
        app.logger.error(f"Error generating weekly report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SCENARIO SIMULATION ====================

# Global scenario state
active_scenario = None
scenario_data_override = {}

def generate_scenario_data(scenario_config):
    """Generate fake data based on scenario configuration"""
    # Base values from scenario
    threat_base = scenario_config.get('threatScore', 50)
    voc_base = random.uniform(scenario_config.get('voc', {}).get('min', 30), 
                             scenario_config.get('voc', {}).get('max', 50))
    people_base = random.uniform(scenario_config.get('people', {}).get('min', 1), 
                                scenario_config.get('people', {}).get('max', 3))
    noise_base = random.uniform(scenario_config.get('noise', {}).get('min', 40), 
                                scenario_config.get('noise', {}).get('max', 60))
    pm25_base = random.uniform(scenario_config.get('pm25', {}).get('min', 10), 
                               scenario_config.get('pm25', {}).get('max', 25))
    
    # Add realistic variations
    threat = max(0, min(100, threat_base + random.uniform(-5, 5)))
    voc = max(0, voc_base + random.uniform(-10, 10))
    people = max(0, int(people_base + random.uniform(-1, 1)))
    noise = max(0, noise_base + random.uniform(-5, 5))
    pm25 = max(0, pm25_base + random.uniform(-5, 5))
    
    # Generate scenario-specific components
    components = {
        'proximity': {
            'score': threat * 0.8 if scenario_config.get('name') in ['Fighting/Altercation', 'Unauthorized Intrusion'] else threat * 0.3,
            'confidence': 0.9,
            'weight': 0.25
        },
        'count': {
            'score': min(100, people * 20),
            'confidence': 0.95,
            'weight': 0.15
        },
        'behavior': {
            'score': threat * 0.9 if scenario_config.get('name') in ['Fighting/Altercation', 'Bullying Incident'] else threat * 0.4,
            'confidence': 0.85,
            'weight': 0.20
        },
        'vital_signs': {
            'score': threat * 0.7 if scenario_config.get('name') == 'Medical Emergency' else threat * 0.2,
            'confidence': 0.8,
            'weight': 0.15
        },
        'air_quality': {
            'score': min(100, (voc / 200) * 100) if scenario_config.get('name') in ['Vaping Detection', 'Chemical Spill', 'Fire/Smoke Detection'] else threat * 0.3,
            'confidence': 0.9,
            'weight': 0.15
        },
        'noise': {
            'score': min(100, (noise / 100) * 100) if scenario_config.get('name') in ['Fighting/Altercation', 'Crowd Rush/Panic'] else threat * 0.2,
            'confidence': 0.8,
            'weight': 0.10
        }
    }
    
    # Generate targets based on scenario
    targets = []
    for i in range(people):
        target = {
            'id': f"T{i+1:02d}",
            'target_x': random.uniform(-5, 5),
            'target_y': random.uniform(-5, 5),
            'target_distance': random.uniform(0.5, 8),
            'target_angle': random.uniform(-60, 60),
            'target_velocity': random.uniform(0, 2) if scenario_config.get('name') in ['Fighting/Altercation', 'Crowd Rush/Panic'] else random.uniform(0, 0.5),
            'target_direction': random.choice(['incoming', 'outgoing']),
            'target_orientation': random.choice(['toward', 'away', 'stationary']),
            'target_confidence': random.uniform(0.7, 0.95),
            'target_activity': random.choice(['running', 'walking', 'stationary']) if scenario_config.get('name') in ['Fighting/Altercation', 'Crowd Rush/Panic'] else random.choice(['walking', 'stationary']),
            'target_activity_confidence': random.uniform(0.6, 0.9),
            'target_breathing_rate': random.uniform(15, 35) if scenario_config.get('name') == 'Medical Emergency' else random.uniform(10, 20),
            'target_breathing_confidence': random.uniform(0.5, 0.9),
            'target_abnormal_breathing': scenario_config.get('name') in ['Medical Emergency', 'Fighting/Altercation'] or random.random() < 0.1,
            'target_vx': random.uniform(-2, 2),
            'target_vy': random.uniform(-2, 2),
            'target_ax': 0,
            'target_ay': 0,
            'target_speed': random.uniform(0, 2)
        }
        targets.append(target)
    
    # Generate threat data structure
    threat_data = {
        'overall_threat': threat,
        'level': 'CRITICAL' if threat > 70 else 'HIGH' if threat > 50 else 'ELEVATED' if threat > 30 else 'MODERATE' if threat > 15 else 'LOW',
        'components': components,
        'temporal': {
            'trend': 'worsening' if threat > 60 else 'stable',
            'slope': random.uniform(-0.5, 0.5),
            'acceleration': random.uniform(-0.1, 0.1),
            'persistence': random.uniform(1.0, 1.5)
        },
        'trajectory': {
            '5min': min(100, threat + random.uniform(-10, 10)),
            '15min': min(100, threat + random.uniform(-20, 20)),
            '30min': min(100, threat + random.uniform(-30, 30))
        }
    }
    
    return {
        'fake_mode': True,
        'people_count': people,
        'active_targets': sum(1 for t in targets if t['target_velocity'] > 0.1),
        'abnormal_count': sum(1 for t in targets if t['target_abnormal_breathing']),
        'threat': threat_data,
        'components': components,
        'targets': targets,
        'voc': voc,
        'pm25': pm25,
        'aqi': (voc / 200 * 50) + (pm25 / 35 * 50),
        'odor_type': 'strong_chemical' if voc > 120 else 'human_activity' if voc > 50 else 'clean_air',
        'odor_confidence': 0.85,
        'odor_intensity': voc / 25,
        'sound_db': noise,
        'sound_event': 'shouting' if noise > 80 else 'conversation' if noise > 60 else 'quiet',
        'sound_spike': noise > 75,
        'sound_baseline': noise - 10,
        'uptime': (datetime.now() - START_TIME).total_seconds(),
        'data_rate': random.uniform(10, 50),
        'packet_count': random.randint(1000, 9999),
        'last_update': datetime.now().strftime('%H:%M:%S.%f')[:-3],
        'scenario_active': True,
        'scenario_name': scenario_config.get('name', 'Unknown Scenario')
    }

@app.route("/scenarios")
@login_required
def scenarios():
    """Scenario simulator page"""
    fake_mode = session.get('fake_mode', True)
    
    # Get environment data for consistency
    all_environments = live_data.get_all_environments()
    current_env = live_data.get_current_environment()
    highest_threat_env = live_data.get_highest_threat_environment()
    
    # Get current data or scenario data
    if active_scenario:
        data = scenario_data_override
    elif fake_mode:
        data = get_cached_fake_data()
    else:
        data = get_realtime_sensor_data()
        if not data:
            data = {'no_data': True}
    
    # Extract template data
    template_data = {
        'fake_mode': fake_mode,
        'active_scenario': active_scenario,
        'environments': all_environments,
        'current_environment': current_env,
        'highest_threat_environment': highest_threat_env,
        'last_update': data.get('last_update', datetime.now().strftime('%H:%M:%S')),
        'threat_score': data.get('threat', {}).get('overall_threat', 0),
        'threat_level': data.get('threat', {}).get('level', 'UNKNOWN'),
        'components': data.get('components', {}),
        'voc': data.get('voc', 0),
        'pm25': data.get('pm25', 0),
        'aqi': data.get('aqi', 0),
        'people_count': data.get('people_count', 0),
        'sound_db': data.get('sound_db', 0),
        'targets': data.get('targets', []),
        'no_data': data.get('no_data', False)
    }
    
    return render_template('scenarios.html', **template_data)

@app.route("/api/activate-scenario", methods=['POST'])
@login_required
def activate_scenario():
    """API endpoint to activate a scenario"""
    global active_scenario, scenario_data_override
    
    try:
        data = request.get_json()
        scenario_config = data.get('scenario')
        
        if not scenario_config:
            return jsonify({'success': False, 'error': 'No scenario provided'})
        
        active_scenario = scenario_config
        scenario_data_override = generate_scenario_data(scenario_config)
        
        # Update live data store with scenario data
        live_data.update(scenario_data_override)
        
        app.logger.info(f"Activated scenario: {scenario_config.get('name', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'scenario': scenario_config.get('name'),
            'message': f"Scenario '{scenario_config.get('name')}' activated successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error activating scenario: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/stop-scenario", methods=['POST'])
@login_required
def stop_scenario():
    """API endpoint to stop the current scenario"""
    global active_scenario, scenario_data_override
    
    try:
        scenario_name = active_scenario.get('name', 'Unknown') if active_scenario else 'None'
        
        active_scenario = None
        scenario_data_override = {}
        
        app.logger.info(f"Stopped scenario: {scenario_name}")
        
        return jsonify({
            'success': True,
            'message': f"Scenario '{scenario_name}' stopped successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error stopping scenario: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/scenario-status")
@login_required
def scenario_status():
    """API endpoint to get current scenario status"""
    global active_scenario
    
    return jsonify({
        'active_scenario': active_scenario,
        'scenario_active': active_scenario is not None
    })

# ==================== ERROR HANDLERS ====================
# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)