import sqlite3
import os
from datetime import datetime

# Clear existing database
database_path = '../users.db'
if os.path.exists(database_path):
    os.remove(database_path)

# Create new database connection
connection = sqlite3.connect(database_path)
crsr = connection.cursor()

# ==================== USERS TABLE ====================
users_fields = [
    # Personal Information for Account Setup and Maintenance
    "username TEXT NOT NULL",
    "password TEXT NOT NULL",
    "dateJoined TEXT",
    "salt TEXT",
    "accountStatus TEXT",
    "role TEXT",  # hierarchy for possible admins
    "twoFactorAuth INTEGER",  # 0/1 boolean
    "lastLogin TEXT",
    "emailAddress TEXT",
    "phoneNumber TEXT",
    "name TEXT",  # Full Name
    "dateOfBirth TEXT",
    "gender TEXT",  # Prefer Not to Say or Other
]

users_create = "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(users_fields) + ")"
crsr.execute(users_create)

# ==================== EVENTS TABLE (Complete Environmental Data) ====================
events_fields = [
    # ===== Timestamp =====
    "timestamp TEXT NOT NULL",  # ISO format timestamp
    
    # ===== THREAT ASSESSMENT METRICS =====
    "threat_overall REAL",  # 0-100 Final threat score
    "threat_base REAL",  # 0-100 Raw threat before temporal adjustments
    "threat_level TEXT",  # LOW/MODERATE/ELEVATED/HIGH/CRITICAL
    "threat_color TEXT",  # 🟢/🟡/🟠/🔴/⚫
    "threat_response TEXT",  # Recommended action
    "threat_confidence REAL",  # 0-1 Overall confidence
    
    # ===== TEMPORAL DYNAMICS =====
    "temporal_trend TEXT",  # stable/worsening/rapidly_worsening/improving/rapidly_improving
    "temporal_slope REAL",  # Rate of change (points/minute)
    "temporal_acceleration REAL",  # Change in slope (points/minute²)
    "temporal_volatility REAL",  # 0-100 Standard deviation
    "temporal_persistence_factor REAL",  # 1.0-2.0 Multiplier
    
    # ===== THREAT TRAJECTORY =====
    "trajectory_5min REAL",  # 0-100 Predicted in 5 min
    "trajectory_15min REAL",  # 0-100 Predicted in 15 min
    "trajectory_30min REAL",  # 0-100 Predicted in 30 min
    
    # ===== PROXIMITY THREAT =====
    "proximity_score REAL",  # 0-100 Adjusted score
    "proximity_raw REAL",  # 0-100 Raw score
    "proximity_confidence REAL",  # 0-1 Confidence
    "proximity_weight REAL",  # 0-1 Dynamic weight
    
    # ===== COUNT THREAT =====
    "count_score REAL",  # 0-100 Adjusted score
    "count_raw REAL",  # 0-100 Raw score
    "count_confidence REAL",  # 0-1 Confidence
    "count_weight REAL",  # 0-1 Dynamic weight
    
    # ===== BEHAVIOR THREAT =====
    "behavior_score REAL",  # 0-100 Adjusted score
    "behavior_raw REAL",  # 0-100 Raw score
    "behavior_confidence REAL",  # 0-1 Confidence
    "behavior_weight REAL",  # 0-1 Dynamic weight
    
    # ===== VITAL SIGNS THREAT =====
    "vital_signs_score REAL",  # 0-100 Adjusted score
    "vital_signs_raw REAL",  # 0-100 Raw score
    "vital_signs_confidence REAL",  # 0-1 Confidence
    "vital_signs_weight REAL",  # 0-1 Dynamic weight
    
    # ===== AIR QUALITY THREAT =====
    "air_quality_score REAL",  # 0-100 Adjusted score
    "air_quality_raw REAL",  # 0-100 Raw score
    "air_quality_confidence REAL",  # 0-1 Confidence
    "air_quality_weight REAL",  # 0-1 Dynamic weight
    
    # ===== NOISE THREAT =====
    "noise_score REAL",  # 0-100 Adjusted score
    "noise_raw REAL",  # 0-100 Raw score
    "noise_confidence REAL",  # 0-1 Confidence
    "noise_weight REAL",  # 0-1 Dynamic weight
    
    # ===== ENVIRONMENTAL QUALITY METRICS =====
    "quality_score REAL",  # 0-100 Overall quality
    "quality_base REAL",  # 0-100 Raw quality
    "quality_category TEXT",  # EXCELLENT/GOOD/FAIR/POOR/CRITICAL
    "quality_icon TEXT",  # 🌟/✅/⚠️/🔴/🚨
    "quality_trend TEXT",  # improving/stable/declining
    "quality_sound_adjust REAL",  # 0-100 Sound-specific quality
    "quality_air_adjust REAL",  # 0-100 Air-specific quality
    "quality_occupancy_adjust REAL",  # 0-100 Occupancy-specific quality
    
    # ===== SOUND ANALYSIS METRICS =====
    "sound_db REAL",  # 0-120 Current sound level
    "sound_baseline REAL",  # 0-120 Median noise floor
    "sound_spike INTEGER",  # 0/1 Boolean
    "sound_rate_of_change REAL",  # How fast sound changed
    "sound_event TEXT",  # quiet/conversation/crowd/door_slam/shouting/background/impact/traffic
    "sound_confidence REAL",  # 0-1 ML confidence
    
    # ===== SOUND FFT FEATURES =====
    "sound_dominant_freq REAL",  # Hz
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
    
    # ===== AIR QUALITY METRICS =====
    "air_voc_ppm REAL",  # 0-1000 Volatile Organic Compounds
    "air_voc_voltage REAL",  # 0-5 Raw MQ135 voltage
    "air_pm1 INTEGER",  # 0-1000 PM1.0 concentration
    "air_pm25 INTEGER",  # 0-1000 PM2.5 concentration
    "air_pm10 INTEGER",  # 0-1000 PM10 concentration
    "air_aqi REAL",  # 0-500 Air Quality Index
    "air_odor_type TEXT",  # Classification
    "air_odor_confidence REAL",  # 0-1 Confidence
    "air_odor_intensity REAL",  # 0-10 Intensity score
    "air_odor_level TEXT",  # LOW/MODERATE/HIGH/SEVERE/CRITICAL
    "air_odor_trend REAL",  # Change from baseline
    "air_baseline_intensity REAL",  # 0-10 Historical baseline
    "air_odor_anomaly INTEGER",  # 0/1 Boolean
    
    # ===== RADAR AGGREGATE METRICS =====
    "radar_target_count INTEGER",  # 0-20 Total people
    "radar_format TEXT",  # rd03d/ld2410/unknown
    
    # ===== MOTION PATTERNS =====
    "motion_pattern TEXT",  # no_detections/low_activity/normal_activity/high_activity/chaotic
    "motion_activity_level REAL",  # 0-1 Proportion moving
    "motion_total_targets INTEGER",  # Total people
    "motion_active_targets INTEGER",  # Moving people
    
    # ===== ACTIVITY EVENTS (JSON for multiple events) =====
    "activity_events TEXT",  # JSON array of events
    
    # ===== PER-TARGET DATA (JSON for multiple targets) =====
    "radar_targets TEXT",  # JSON array of all targets with full details
    
    # ===== DERIVED METRICS =====
    "physical_risk REAL",  # (proximity + count + behavior)/3
    "health_risk REAL",  # (vital_signs + air_quality)/2
    "environmental_risk REAL",  # (noise + air_quality)/2
    "danger_index REAL",  # threat_overall * persistence_factor
    "comfort_index REAL",  # 100 - (threat_overall * 0.5)
    "urgency_score REAL",  # threat_overall * (1 + |slope|/10)
    
    # ===== SENSOR RELIABILITY =====
    "sensor_radar_connected INTEGER",  # 0/1
    "sensor_pms_connected INTEGER",  # 0/1
    "sensor_mq135_connected INTEGER",  # 0/1
    "sensor_sound_connected INTEGER",  # 0/1
    
    # ===== ALERTS =====
    "alert_critical_threat INTEGER",  # 0/1 threat > 80
    "alert_high_threat INTEGER",  # 0/1 threat > 60
    "alert_rapid_escalation INTEGER",  # 0/1 trend rapidly_worsening
    "alert_abnormal_vitals INTEGER",  # 0/1 any abnormal breathing
    "alert_air_quality INTEGER",  # 0/1 AQI > 150
    
    # ===== METADATA =====
    "notes TEXT",  # Any additional notes
]

events_create = "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(events_fields) + ")"
crsr.execute(events_create)

# ==================== TARGETS TABLE (Normalized per-person data) ====================
targets_fields = [
    "event_id INTEGER",  # Foreign key to events table
    "timestamp TEXT NOT NULL",
    "target_id TEXT",  # T00-T99
    "target_x REAL",  # meters
    "target_y REAL",  # meters
    "target_distance REAL",  # meters
    "target_angle REAL",  # -180 to 180 degrees
    "target_velocity REAL",  # m/s
    "target_direction TEXT",  # incoming/outgoing
    "target_orientation TEXT",  # toward/away/stationary
    "target_confidence REAL",  # 0-1
    "target_activity TEXT",  # stationary/sitting/walking/running/transition/unknown
    "target_activity_confidence REAL",  # 0-1
    "target_breathing_rate REAL",  # 0-40 bpm
    "target_breathing_confidence REAL",  # 0-1
    "target_abnormal_breathing INTEGER",  # 0/1
    "target_vx REAL",  # Velocity X
    "target_vy REAL",  # Velocity Y
    "target_ax REAL",  # Acceleration X
    "target_ay REAL",  # Acceleration Y
    "target_speed REAL",  # Magnitude
]

targets_create = "CREATE TABLE targets (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(targets_fields) + ")"
crsr.execute(targets_create)

# ==================== EVENTS_LOG TABLE (Simplified for quick lookup) ====================
events_log_fields = [
    "timestamp TEXT NOT NULL",
    "threat_level TEXT",
    "threat_score REAL",
    "quality_score REAL",
    "people_count INTEGER",
    "sound_db REAL",
    "air_aqi REAL",
    "event_type TEXT",  # Type of significant event
    "description TEXT",
]

events_log_create = "CREATE TABLE events_log (id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(events_log_fields) + ")"
crsr.execute(events_log_create)

# ==================== CREATE INDEXES for faster queries ====================
crsr.execute("CREATE INDEX idx_events_timestamp ON events(timestamp)")
crsr.execute("CREATE INDEX idx_events_threat_level ON events(threat_level)")
crsr.execute("CREATE INDEX idx_events_quality_score ON events(quality_score)")
crsr.execute("CREATE INDEX idx_targets_event_id ON targets(event_id)")
crsr.execute("CREATE INDEX idx_targets_target_id ON targets(target_id)")
crsr.execute("CREATE INDEX idx_events_log_timestamp ON events_log(timestamp)")

# Commit changes and close
connection.commit()
crsr.close()
connection.close()

print("✅ Database created successfully!")
print(f"📁 Location: {os.path.abspath(database_path)}")
print("\n📊 Tables created:")
print("  • users - User accounts and profiles")
print("  • events - Complete environmental data snapshots")
print("  • targets - Per-person radar tracking data")
print("  • events_log - Simplified event log for quick lookup")