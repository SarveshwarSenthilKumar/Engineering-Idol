#!/usr/bin/env python3
"""
Fake Data Generator for Environmental Monitoring System
Generates realistic sensor data and events for testing/demo purposes
"""

import sqlite3
import random
import time
from datetime import datetime, timedelta
import numpy as np
import json
import os
import sys
import smtplib
import ssl
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = 'events.db'
DAYS_OF_HISTORY = 7  # Generate 7 days of history to support all time intervals (6h, 12h, 24h, 48h, 168h)
EVENTS_PER_DAY = 50   # Average events per day
TARGETS_PER_EVENT = 2 # Average targets per event

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
    'PERSON_EXIT': 0.20
}

# Activity types
ACTIVITIES = ['stationary', 'sitting', 'walking', 'running', 'transition']

class FakeDataGenerator:
    """Generates realistic fake environmental data"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def clear_existing_data(self):
        """Clear existing data from tables"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM targets")
        cursor.execute("DELETE FROM events_log")
        cursor.execute("DELETE FROM events")
        self.conn.commit()
        print("✅ Cleared existing data")
        
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
            # Random with realistic distribution
            r = random.random()
            if r < 0.4:
                return random.uniform(5, 25)  # Low
            elif r < 0.65:
                return random.uniform(25, 45) # Moderate
            elif r < 0.8:
                return random.uniform(45, 65) # Elevated
            elif r < 0.95:
                return random.uniform(65, 85) # High
            else:
                return random.uniform(85, 100) # Critical
                
    def generate_quality_score(self, threat_score):
        """Generate quality score (inverse of threat)"""
        base_quality = 100 - (threat_score * 0.8)
        # Add some random variation
        variation = random.uniform(-5, 5)
        return max(0, min(100, base_quality + variation))
        
    def generate_sound_data(self, timestamp, is_night=False):
        """Generate realistic sound data"""
        hour = datetime.fromisoformat(timestamp).hour
        
        # Different sound patterns based on time of day
        if hour < 6 or hour > 22:  # Night
            base_db = random.uniform(30, 45)
            spike_prob = 0.05
        elif 6 <= hour < 9:  # Morning
            base_db = random.uniform(45, 65)
            spike_prob = 0.15
        elif 9 <= hour < 17:  # Day
            base_db = random.uniform(50, 70)
            spike_prob = 0.20
        else:  # Evening
            base_db = random.uniform(45, 60)
            spike_prob = 0.10
            
        # Add random spikes
        spike = random.random() < spike_prob
        if spike:
            db = base_db + random.uniform(10, 30)
        else:
            db = base_db + random.uniform(-5, 5)
            
        # Determine event type based on dB
        if db > 80:
            event = 'impact' if random.random() < 0.3 else 'door_slam'
        elif db > 70:
            event = 'shouting' if random.random() < 0.4 else 'crowd'
        elif db > 60:
            event = 'conversation' if random.random() < 0.7 else 'traffic'
        elif db > 50:
            event = 'background'
        else:
            event = 'quiet'
            
        # Generate FFT features
        features = [
            db,  # dB
            random.uniform(100, 1000),  # dominant_freq
            random.uniform(1000, 50000),  # spectral_energy
            random.uniform(200, 800),  # spectral_centroid
            random.uniform(0.1, 4.0),  # peak
            random.randint(20, 200),  # zero_crossings
            random.uniform(30, 300),  # spectral_spread
            random.uniform(-2, 2),  # skewness
            random.uniform(-2, 3),  # kurtosis
            random.uniform(100, 5000),  # low_energy
            random.uniform(500, 10000),  # mid_energy
            random.uniform(100, 5000),  # high_energy
        ]
        
        return {
            'db': db,
            'baseline': base_db,
            'spike': spike,
            'rate_of_change': random.uniform(0, 5) if spike else random.uniform(0, 1),
            'event': event,
            'confidence': random.uniform(0.7, 0.98),
            'features': features
        }
        
    def generate_odor_data(self, timestamp, people_count):
        """Generate realistic air quality data"""
        hour = datetime.fromisoformat(timestamp).hour
        
        # VOC levels (ppm)
        if people_count > 2:
            voc_base = random.uniform(80, 150)
        elif people_count > 0:
            voc_base = random.uniform(40, 90)
        else:
            voc_base = random.uniform(20, 50)
            
        # Add time-of-day variation
        if 8 <= hour <= 10 or 17 <= hour <= 19:  # Rush hours
            voc_base *= random.uniform(1.2, 1.5)
            
        voc_ppm = voc_base + random.uniform(-10, 10)
        
        # PM2.5 levels
        if voc_ppm > 100:
            pm25 = random.uniform(30, 80)
        elif voc_ppm > 50:
            pm25 = random.uniform(15, 40)
        else:
            pm25 = random.uniform(5, 20)
            
        # Determine odor type
        if voc_ppm > 120:
            odor_type = 'strong_chemical' if random.random() < 0.7 else 'human_activity'
        elif pm25 > 40:
            odor_type = 'dust_or_smoke'
        elif voc_ppm > 80 and people_count > 0:
            odor_type = 'human_activity'
        elif voc_ppm > 50:
            odor_type = 'moderate_odor'
        else:
            odor_type = 'clean_air'
            
        # Calculate AQI
        aqi = (voc_ppm / 100 * 50) + (pm25 / 35 * 50)
        aqi = min(500, max(0, aqi))
        
        return {
            'voc_ppm': round(voc_ppm, 1),
            'voc_voltage': round(voc_ppm / 200, 3),
            'pm1': int(pm25 * random.uniform(0.3, 0.7)),
            'pm25': int(pm25),
            'pm10': int(pm25 * random.uniform(1.2, 1.8)),
            'air_quality_index': round(aqi, 1),
            'odor_type': odor_type,
            'classification_confidence': random.uniform(0.6, 0.95),
            'odor_intensity': round(voc_ppm / 25, 1),
            'odor_level': 'CRITICAL' if voc_ppm > 120 else 'HIGH' if voc_ppm > 80 else 'MODERATE' if voc_ppm > 50 else 'LOW',
            'odor_trend': random.uniform(-15, 15),
            'baseline_intensity': round(voc_ppm / 30, 1),
            'odor_anomaly': random.random() < 0.1
        }
        
    def generate_radar_targets(self, count):
        """Generate realistic radar targets"""
        targets = []
        for i in range(count):
            # Random position
            distance = random.uniform(0.5, 8.0)
            angle = random.uniform(-60, 60)
            x = distance * math.cos(math.radians(angle))
            y = distance * math.sin(math.radians(angle))
            
            # Velocity based on activity
            activity = random.choice(ACTIVITIES)
            if activity == 'running':
                velocity = random.uniform(1.5, 3.0)
            elif activity == 'walking':
                velocity = random.uniform(0.5, 1.5)
            elif activity == 'transition':
                velocity = random.uniform(0.3, 0.8)
            else:
                velocity = random.uniform(0, 0.2)
                
            # Breathing rate
            if activity == 'running':
                breathing_rate = random.uniform(20, 35)
            elif activity == 'walking':
                breathing_rate = random.uniform(15, 25)
            else:
                breathing_rate = random.uniform(10, 18)
                
            abnormal_breathing = breathing_rate < 8 or breathing_rate > 24 or random.random() < 0.05
            
            target = {
                'id': f"T{random.randint(1, 99):02d}",
                'x': round(x, 2),
                'y': round(y, 2),
                'distance': round(distance, 2),
                'angle': round(angle, 1),
                'velocity': round(velocity, 2),
                'direction': 'incoming' if random.random() < 0.5 else 'outgoing',
                'orientation': random.choice(['toward', 'away', 'stationary']),
                'confidence': round(random.uniform(0.6, 0.98), 2),
                'activity': activity,
                'activity_confidence': round(random.uniform(0.6, 0.95), 2),
                'breathing_rate': round(breathing_rate, 1),
                'breathing_confidence': round(random.uniform(0.5, 0.9), 2),
                'abnormal_breathing': abnormal_breathing,
                'vx': round(velocity * math.cos(math.radians(angle)), 2),
                'vy': round(velocity * math.sin(math.radians(angle)), 2),
                'speed': round(velocity, 2)
            }
            targets.append(target)
        return targets
        
    def generate_motion_patterns(self, targets):
        """Generate motion patterns from targets"""
        if not targets:
            return {
                'pattern': 'no_detections',
                'activity_level': 0,
                'total_targets': 0,
                'active_targets': 0
            }
            
        active = sum(1 for t in targets if t['velocity'] > 0.1)
        total = len(targets)
        activity_level = active / total if total > 0 else 0
        
        if activity_level < 0.2:
            pattern = 'low_activity'
        elif activity_level < 0.5:
            pattern = 'normal_activity'
        elif activity_level < 0.8:
            pattern = 'high_activity'
        else:
            pattern = 'chaotic'
            
        return {
            'pattern': pattern,
            'activity_level': round(activity_level, 2),
            'total_targets': total,
            'active_targets': active
        }
        
    def generate_activity_events(self, targets, prev_count):
        """Generate activity events"""
        events = []
        current_count = len(targets)
        
        # Entry/exit events
        if current_count > prev_count:
            events.append({
                'type': 'entry',
                'magnitude': current_count - prev_count,
                'confidence': round(random.uniform(0.7, 0.95), 2)
            })
        elif current_count < prev_count:
            events.append({
                'type': 'exit',
                'magnitude': prev_count - current_count,
                'confidence': round(random.uniform(0.7, 0.95), 2)
            })
            
        # Possible fall events (rare)
        if random.random() < 0.02:
            events.append({
                'type': 'possible_fall',
                'target_id': random.choice(targets)['id'] if targets else 'T01',
                'confidence': round(random.uniform(0.5, 0.8), 2)
            })
            
        return events
        
    def generate_temporal_context(self, threat_score, history_length):
        """Generate temporal context"""
        slopes = [-0.8, -0.3, 0, 0.3, 0.8]
        trends = ['rapidly_improving', 'improving', 'stable', 'worsening', 'rapidly_worsening']
        idx = random.randint(0, 4)
        
        return {
            'trend': trends[idx],
            'slope': slopes[idx],
            'acceleration': random.uniform(-0.1, 0.1),
            'volatility': random.uniform(1, 15),
            'persistence_factor': round(random.uniform(1.0, 1.8), 2),
            'trend_strength': round(random.uniform(0.3, 0.95), 2)
        }
        
    def generate_component_threats(self, targets, sound_data, odor_data):
        """Generate component threat scores"""
        # Proximity threat
        proximity_score = 0
        for t in targets:
            dist = t['distance']
            if dist < 1.0:
                proximity_score += 30
            elif dist < 2.0:
                proximity_score += 15
            elif dist < 3.0:
                proximity_score += 8
            elif dist < 5.0:
                proximity_score += 3
        proximity_score = min(100, proximity_score)
        
        # Count threat
        count = len(targets)
        if count <= 2:
            count_score = count * 15
        elif count <= 4:
            count_score = 30 + (count - 2) * 20
        else:
            count_score = 70 + (count - 4) * 10
        count_score = min(100, count_score)
        
        # Behavior threat
        behavior_score = 0
        for t in targets:
            if t['activity'] == 'running':
                behavior_score += 25
            elif t['activity'] == 'transition':
                behavior_score += 20
            if t['abnormal_breathing']:
                behavior_score += 30
        behavior_score = min(100, behavior_score)
        
        # Vital signs threat
        vital_score = 0
        abnormal_count = sum(1 for t in targets if t['abnormal_breathing'])
        vital_score += abnormal_count * 25
        for t in targets:
            if t['breathing_rate'] < 6:
                vital_score += 50
            elif t['breathing_rate'] > 30:
                vital_score += 40
        vital_score = min(100, vital_score)
        
        # Air quality threat
        air_score = 0
        voc = odor_data['voc_ppm']
        pm25 = odor_data['pm25']
        if voc > 200:
            air_score += 50
        elif voc > 100:
            air_score += 30
        elif voc > 50:
            air_score += 15
        elif voc > 30:
            air_score += 5
            
        if pm25 > 100:
            air_score += 45
        elif pm25 > 50:
            air_score += 25
        elif pm25 > 25:
            air_score += 10
            
        if odor_data['odor_type'] == 'strong_chemical':
            air_score *= 1.5
        elif odor_data['odor_type'] == 'dust_or_smoke':
            air_score *= 1.3
        air_score = min(100, air_score)
        
        # Noise threat
        db = sound_data['db']
        if db > 100:
            noise_score = 90
        elif db > 90:
            noise_score = 70
        elif db > 80:
            noise_score = 45
        elif db > 70:
            noise_score = 25
        elif db > 60:
            noise_score = 10
        else:
            noise_score = 0
            
        if sound_data['spike']:
            noise_score *= 1.5
        if sound_data['event'] in ['impact', 'explosion']:
            noise_score *= 2.0
        elif sound_data['event'] in ['door_slam', 'shouting']:
            noise_score *= 1.3
        noise_score = min(100, noise_score)
        
        return {
            'proximity': {'score': proximity_score, 'raw_score': proximity_score, 'confidence': 0.9, 'weight': 0.25},
            'count': {'score': count_score, 'raw_score': count_score, 'confidence': 0.9, 'weight': 0.15},
            'behavior': {'score': behavior_score, 'raw_score': behavior_score, 'confidence': 0.8, 'weight': 0.20},
            'vital_signs': {'score': vital_score, 'raw_score': vital_score, 'confidence': 0.7, 'weight': 0.15},
            'air_quality': {'score': air_score, 'raw_score': air_score, 'confidence': 0.8, 'weight': 0.15},
            'noise': {'score': noise_score, 'raw_score': noise_score, 'confidence': 0.8, 'weight': 0.10}
        }
        
    def generate_trajectory(self, current_score):
        """Generate threat trajectory predictions"""
        return {
            '5min': min(100, current_score + random.uniform(-10, 20)),
            '15min': min(100, current_score + random.uniform(-20, 35)),
            '30min': min(100, current_score + random.uniform(-30, 50))
        }
        
    def generate_events(self, count=1000, hours=24):
        """Generate multiple events across specified time span"""
        print(f"📊 Generating {count} events across {hours} hours...")
        
        cursor = self.conn.cursor()
        start_time = datetime.now() - timedelta(hours=hours)  # Start from specified hours ago
        
        prev_target_count = 0
        for i in range(count):
            # Calculate timestamp with realistic spacing across the time span
            time_offset = timedelta(
                seconds=random.uniform(0, hours * 3600)  # Distribute across the entire time span
            )
            timestamp = (start_time + time_offset).isoformat()
            
            # Determine threat level
            threat_level = random.choices(
                list(THREAT_LEVELS.keys()),
                weights=list(THREAT_LEVELS.values())
            )[0]
            
            # Generate threat score
            threat_score = self.generate_threat_score(threat_level)
            
            # Generate people count
            if threat_level == 'CRITICAL':
                people_count = random.randint(3, 8)
            elif threat_level == 'HIGH':
                people_count = random.randint(2, 5)
            elif threat_level == 'ELEVATED':
                people_count = random.randint(1, 4)
            else:
                people_count = random.randint(0, 2)
                
            # Generate sound data
            sound_data = self.generate_sound_data(timestamp)
            
            # Generate odor data
            odor_data = self.generate_odor_data(timestamp, people_count)
            
            # Generate radar targets
            targets = self.generate_radar_targets(people_count)
            
            # Generate motion patterns
            motion_patterns = self.generate_motion_patterns(targets)
            
            # Generate activity events
            activity_events = self.generate_activity_events(targets, prev_target_count)
            prev_target_count = people_count
            
            # Generate component threats
            components = self.generate_component_threats(targets, sound_data, odor_data)
            
            # Calculate base threat
            base_threat = sum(
                components[c]['score'] * components[c]['weight']
                for c in components
            )
            
            # Generate temporal context
            temporal = self.generate_temporal_context(threat_score, i)
            
            # Generate trajectory
            trajectory = self.generate_trajectory(threat_score)
            
            # Calculate derived metrics
            physical_risk = (components['proximity']['score'] + components['count']['score'] + components['behavior']['score']) / 3
            health_risk = (components['vital_signs']['score'] + components['air_quality']['score']) / 2
            environmental_risk = (components['noise']['score'] + components['air_quality']['score']) / 2
            danger_index = threat_score * temporal['persistence_factor']
            comfort_index = 100 - (threat_score * 0.5)
            urgency_score = threat_score * (1 + abs(temporal['slope']) / 10)
            
            # Quality score
            quality_score = self.generate_quality_score(threat_score)
            
            # Determine quality category
            if quality_score >= 90:
                quality_category = "EXCELLENT"
                quality_icon = "🌟"
            elif quality_score >= 80:
                quality_category = "GOOD"
                quality_icon = "✅"
            elif quality_score >= 70:
                quality_category = "FAIR"
                quality_icon = "⚠️"
            elif quality_score >= 60:
                quality_category = "POOR"
                quality_icon = "🔴"
            else:
                quality_category = "CRITICAL"
                quality_icon = "🚨"
                
            # Quality adjustments
            quality_adjustments = {
                'sound': 100 - sound_data['db'] * 0.8 if sound_data['db'] < 100 else 20,
                'air': 100 - odor_data['air_quality_index'] * 0.15,
                'occupancy': 90 if people_count == 0 else 85 if people_count == 1 else 75 if people_count == 2 else 60 if people_count == 3 else 40
            }
            
            # Insert into events table
            cursor.execute("""
                INSERT INTO events (
                    timestamp, threat_overall, threat_base, threat_level, threat_color, threat_response, threat_confidence,
                    temporal_trend, temporal_slope, temporal_acceleration, temporal_volatility, temporal_persistence_factor,
                    trajectory_5min, trajectory_15min, trajectory_30min,
                    proximity_score, proximity_raw, proximity_confidence, proximity_weight,
                    count_score, count_raw, count_confidence, count_weight,
                    behavior_score, behavior_raw, behavior_confidence, behavior_weight,
                    vital_signs_score, vital_signs_raw, vital_signs_confidence, vital_signs_weight,
                    air_quality_score, air_quality_raw, air_quality_confidence, air_quality_weight,
                    noise_score, noise_raw, noise_confidence, noise_weight,
                    quality_score, quality_base, quality_category, quality_icon, quality_trend,
                    quality_sound_adjust, quality_air_adjust, quality_occupancy_adjust,
                    sound_db, sound_baseline, sound_spike, sound_rate_of_change, sound_event, sound_confidence,
                    sound_dominant_freq, sound_spectral_energy, sound_spectral_centroid, sound_peak,
                    sound_zero_crossings, sound_spectral_spread, sound_skewness, sound_kurtosis,
                    sound_low_energy, sound_mid_energy, sound_high_energy,
                    air_voc_ppm, air_voc_voltage, air_pm1, air_pm25, air_pm10, air_aqi,
                    air_odor_type, air_odor_confidence, air_odor_intensity, air_odor_level,
                    air_odor_trend, air_baseline_intensity, air_odor_anomaly,
                    radar_target_count, radar_format,
                    motion_pattern, motion_activity_level, motion_total_targets, motion_active_targets,
                    activity_events, radar_targets,
                    physical_risk, health_risk, environmental_risk, danger_index, comfort_index, urgency_score,
                    sensor_radar_connected, sensor_pms_connected, sensor_mq135_connected, sensor_sound_connected,
                    alert_critical_threat, alert_high_threat, alert_rapid_escalation, alert_abnormal_vitals, alert_air_quality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                threat_score, base_threat, threat_level, 
                '🔴' if threat_level == 'HIGH' else '🟠' if threat_level == 'ELEVATED' else '🟡' if threat_level == 'MODERATE' else '🟢',
                f"{threat_level} conditions detected", 0.85,
                temporal['trend'], temporal['slope'], temporal['acceleration'], temporal['volatility'], temporal['persistence_factor'],
                trajectory['5min'], trajectory['15min'], trajectory['30min'],
                components['proximity']['score'], components['proximity']['raw_score'], components['proximity']['confidence'], components['proximity']['weight'],
                components['count']['score'], components['count']['raw_score'], components['count']['confidence'], components['count']['weight'],
                components['behavior']['score'], components['behavior']['raw_score'], components['behavior']['confidence'], components['behavior']['weight'],
                components['vital_signs']['score'], components['vital_signs']['raw_score'], components['vital_signs']['confidence'], components['vital_signs']['weight'],
                components['air_quality']['score'], components['air_quality']['raw_score'], components['air_quality']['confidence'], components['air_quality']['weight'],
                components['noise']['score'], components['noise']['raw_score'], components['noise']['confidence'], components['noise']['weight'],
                quality_score, quality_score * 1.1, quality_category, quality_icon, 'stable',
                quality_adjustments['sound'], quality_adjustments['air'], quality_adjustments['occupancy'],
                sound_data['db'], sound_data['baseline'], 1 if sound_data['spike'] else 0, sound_data['rate_of_change'], sound_data['event'], sound_data['confidence'],
                sound_data['features'][1], sound_data['features'][2], sound_data['features'][3], sound_data['features'][4],
                sound_data['features'][5], sound_data['features'][6], sound_data['features'][7], sound_data['features'][8],
                sound_data['features'][9], sound_data['features'][10], sound_data['features'][11],
                odor_data['voc_ppm'], odor_data['voc_voltage'], odor_data['pm1'], odor_data['pm25'], odor_data['pm10'], odor_data['air_quality_index'],
                odor_data['odor_type'], odor_data['classification_confidence'], odor_data['odor_intensity'], odor_data['odor_level'],
                odor_data['odor_trend'], odor_data['baseline_intensity'], 1 if odor_data['odor_anomaly'] else 0,
                len(targets), 'rd03d',
                motion_patterns['pattern'], motion_patterns['activity_level'], motion_patterns['total_targets'], motion_patterns['active_targets'],
                json.dumps(activity_events), json.dumps(targets),
                physical_risk, health_risk, environmental_risk, danger_index, comfort_index, urgency_score,
                1, 1, 1, 1,
                1 if threat_score > 80 else 0,
                1 if threat_score > 60 else 0,
                1 if temporal['trend'] == 'rapidly_worsening' else 0,
                1 if any(t['abnormal_breathing'] for t in targets) else 0,
                1 if odor_data['air_quality_index'] > 150 else 0
            ))
            
            event_id = cursor.lastrowid
            
            # Insert targets
            for target in targets:
                cursor.execute("""
                    INSERT INTO targets (
                        event_id, timestamp, target_id, target_x, target_y, target_distance,
                        target_angle, target_velocity, target_direction, target_orientation,
                        target_confidence, target_activity, target_activity_confidence,
                        target_breathing_rate, target_breathing_confidence, target_abnormal_breathing,
                        target_vx, target_vy, target_ax, target_ay, target_speed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    timestamp,
                    target['id'],
                    target['x'],
                    target['y'],
                    target['distance'],
                    target['angle'],
                    target['velocity'],
                    target['direction'],
                    target['orientation'],
                    target['confidence'],
                    target['activity'],
                    target['activity_confidence'],
                    target['breathing_rate'],
                    target['breathing_confidence'],
                    1 if target['abnormal_breathing'] else 0,
                    target['vx'],
                    target['vy'],
                    0,  # ax
                    0,  # ay
                    target['speed']
                ))
                
            # Insert into events_log for quick lookup
            cursor.execute("""
                INSERT INTO events_log (
                    timestamp, threat_level, threat_score, quality_score,
                    people_count, sound_db, air_aqi, event_type, description, temperature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                threat_level,
                threat_score,
                quality_score,
                people_count,
                sound_data['db'],
                odor_data['air_quality_index'],
                random.choices(list(EVENT_TYPES.keys()), weights=list(EVENT_TYPES.values()))[0],
                f"{threat_level} threat detected with {people_count} people",
                odor_data.get('temperature', 20)  # Add temperature
            ))
            
            if i % 100 == 0:
                print(f"   Generated {i}/{count} events...")
                self.conn.commit()
                
        self.conn.commit()
        print(f"✅ Generated {count} events successfully!")
        
    def send_test_email(self, message="Test notification from fake data generator"):
        """Send test email notification"""
        try:
            smtp_server = os.getenv('GMAIL_SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('GMAIL_SMTP_PORT', 587))
            sender_email = os.getenv('GMAIL_SENDER_EMAIL')
            sender_password = os.getenv('GMAIL_SENDER_PASSWORD')
            recipient_email = os.getenv('GMAIL_RECIPIENT_EMAIL')
            
            if not all([sender_email, sender_password, recipient_email]):
                print("⚠️ Gmail credentials not configured")
                return False
            
            msg = MimeMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = '🧪 TEST: Fake Data Generator Notification'
            
            body = f"""
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 System: Fake Data Generator

{message}

---
This is a test message from the Environmental Monitoring System Fake Data Generator.
            """
            msg.attach(MimeText(body, 'plain'))
            
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(sender_email, sender_password)
                server.send_message(msg)
                
            print("✅ Test email sent successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send test email: {e}")
            return False
    
    def send_test_teams(self, message="Test notification from fake data generator"):
        """Send test Teams notification"""
        try:
            webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
            if not webhook_url or webhook_url == 'https://your-tenant.webhook.office.com/webhookb3/...':
                print("⚠️ Teams webhook not configured")
                return False
            
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0078D4",
                "summary": "🧪 TEST: Fake Data Generator",
                "sections": [{
                    "activityTitle": "🧪 TEST NOTIFICATION",
                    "activitySubtitle": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "facts": [{
                        "name": "System",
                        "value": "Fake Data Generator"
                    }, {
                        "name": "Purpose",
                        "value": "Test Notification"
                    }],
                    "text": message
                }]
            }
            
            response = requests.post(webhook_url, 
                                    json=payload, 
                                    headers={'Content-Type': 'application/json'},
                                    timeout=10)
            
            if response.status_code == 200:
                print("✅ Test Teams message sent successfully")
                return True
            else:
                print(f"❌ Teams notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send test Teams message: {e}")
            return False
    
    def send_test_sms(self, message="Test notification from fake data generator"):
        """Send test SMS notification"""
        try:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_PHONE_NUMBER')
            to_number = os.getenv('RECIPIENT_PHONE_NUMBER')
            
            if not all([account_sid, auth_token, from_number, to_number]):
                print("⚠️ Twilio credentials not configured")
                return False
            
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                
                # Add test prefix and truncate if needed
                message = "🧪 TEST: " + message
                if len(message) > 160:
                    message = message[:157] + "..."
                
                message_obj = client.messages.create(
                    body=message,
                    from_=from_number,
                    to=to_number
                )
                
                print(f"✅ Test SMS sent successfully: SID {message_obj.sid}")
                return True
                
            except ImportError:
                print("⚠️ Twilio library not installed")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send test SMS: {e}")
            return False
    
    def send_test_notifications(self, message="Test notification from fake data generator"):
        """Send test notifications to all configured channels"""
        print("🧪 Sending test notifications...")
        
        results = {
            'email': self.send_test_email(message),
            'teams': self.send_test_teams(message),
            'sms': self.send_test_sms(message)
        }
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len([r for r in results.values() if r is not False])
        
        print(f"\n📊 Test Results: {success_count}/{total_count} notifications sent successfully")
        
        for channel, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {channel.capitalize()}: {'Sent' if success else 'Failed'}")
        
        return results

    def run(self):
        """Main execution"""
        try:
            print("="*60)
            print("🚀 FAKE DATA GENERATOR FOR ENVIRONMENTAL MONITORING")
            print("="*60)
            
            self.connect()
            self.clear_existing_data()
            self.generate_events(DAYS_OF_HISTORY * EVENTS_PER_DAY, DAYS_OF_HISTORY * 24)
            
            # Verify data
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            events_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM targets")
            targets_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM events_log")
            log_count = cursor.fetchone()[0]
            
            print("\n" + "="*60)
            print("📊 DATA GENERATION SUMMARY")
            print("="*60)
            print(f"📁 Database: {self.db_path}")
            print(f"📅 Days of history: {DAYS_OF_HISTORY}")
            print(f"📊 Events generated: {events_count}")
            print(f"👥 Targets generated: {targets_count}")
            print(f"📋 Log entries: {log_count}")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == "__main__":
    # Add math import for trig functions
    import math
    generator = FakeDataGenerator()
    generator.run()