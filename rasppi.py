#!/usr/bin/env python3
"""
ENHANCED ENVIRONMENTAL MONITORING SYSTEM
Advanced threat detection with temporal dynamics and exponential escalation
"""

import time
import serial
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np
import math
from collections import deque
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import DBSCAN
import warnings
import json
from datetime import datetime, timedelta
from scipy import signal as scipy_signal
from scipy import ndimage
from scipy.stats import pearsonr
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

warnings.filterwarnings('ignore')

# ==================== CONFIGURATION PARAMETERS ====================

# System Configuration
SYSTEM_NAME = "Advanced Environmental Monitor"
VERSION = "2.0.0"
LOG_LEVEL = logging.INFO

# Sound Analysis Parameters
SAMPLE_RATE = 200
WINDOW_TIME = 1
WINDOW_SIZE = SAMPLE_RATE * WINDOW_TIME
REFERENCE_VOLTAGE = 0.05
SPIKE_THRESHOLD_DB = 15
LOUD_THRESHOLD_DB = 65

# Gas Sensor Parameters
RLOAD = 10000
VCC = 5.0
R0 = 20000
MQ135_CLEAN_AIR_RATIO = 3.6

# Odor Classification Thresholds
VOC_CLEAN_THRESHOLD = 50
VOC_ACTIVITY_THRESHOLD = 80
VOC_CHEMICAL_THRESHOLD = 120
PM_CLEAN_THRESHOLD = 10
PM_SMOKE_THRESHOLD = 40

# Radar Configuration
RADAR_CONFIGS = {
    'rd03d': {
        'baudrate': 256000,
        'protocol': 'uart',
        'data_format': 'binary',
        'max_targets': 3,
        'has_velocity': True,
        'has_angle': True,
        'has_distance': True,
        'has_snr': True,
        'frame_size': 22,
        'detection_threshold': 0.6
    },
    'ld2410': {
        'baudrate': 256000,
        'protocol': 'uart',
        'data_format': 'packet',
        'max_targets': 3,
        'has_velocity': False,
        'has_angle': False,
        'has_distance': True,
        'has_energy': True,
        'has_motion': True,
        'detection_threshold': 0.5
    }
}

RADAR_TYPE = 'auto'
RADAR_PORT = "/dev/ttyUSB0"

# Breathing detection parameters
BREATHING_FREQ_RANGE = (0.15, 0.4)  # Hz (9-24 breaths per minute)
BREATHING_HISTORY_SIZE = 150

# ==================== TEMPORAL THREAT SCORING PARAMETERS ====================

@dataclass
class ThreatConfig:
    """Configuration for temporal threat scoring"""
    # Exponential escalation factors
    BASE_ESCALATION_FACTOR: float = 1.5
    TIME_DECAY_HALF_LIFE: float = 300  # 5 minutes
    PERSISTENCE_THRESHOLD: int = 3  # Number of occurrences for persistence
    PERSISTENCE_MULTIPLIER: float = 2.0
    
    # Intensity thresholds (exponential jumps)
    INTENSITY_LEVELS: List[float] = None  # Will be initialized
    
    # Time windows for trend analysis
    TREND_WINDOWS: Dict[str, int] = None  # Will be initialized
    
    # Component weights
    COMPONENT_WEIGHTS: Dict[str, float] = None  # Will be initialized
    
    def __post_init__(self):
        self.INTENSITY_LEVELS = [20, 40, 60, 80, 95]
        self.TREND_WINDOWS = {
            'short': 60,    # 1 minute
            'medium': 300,  # 5 minutes
            'long': 900     # 15 minutes
        }
        self.COMPONENT_WEIGHTS = {
            'proximity': 0.25,
            'count': 0.15,
            'behavior': 0.20,
            'vital_signs': 0.15,
            'air_quality': 0.15,
            'noise': 0.10
        }

# ==================== DATA STORAGE ====================
samples = deque(maxlen=WINDOW_SIZE)
db_history = deque(maxlen=50)
sound_history = deque(maxlen=WINDOW_SIZE)
odor_history = deque(maxlen=60)
radar_history = deque(maxlen=30)
activity_history = deque(maxlen=20)
score_history = deque(maxlen=100)
breathing_history = deque(maxlen=BREATHING_HISTORY_SIZE)
threat_history = deque(maxlen=1000)
event_history = deque(maxlen=500)

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('environmental_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(SYSTEM_NAME)

# ==================== SOUND UTILITIES ====================
def voltage_to_db(v):
    """Convert voltage to decibels with protection against invalid values"""
    if v <= 0 or math.isnan(v) or math.isinf(v):
        return 0
    try:
        return 20 * math.log10(max(v, 1e-10) / REFERENCE_VOLTAGE)
    except (ValueError, OverflowError):
        return 0

def rms(values):
    """Calculate RMS of signal with numerical stability"""
    if not values:
        return 0
    arr = np.array(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return 0
    return np.sqrt(np.mean(np.square(arr)))

# ==================== FFT ANALYSIS ====================
def fft_features(signal):
    """Extract frequency domain features with error handling"""
    if len(signal) < 4:
        return 0, 0, 0, 0, 0
    
    signal = np.array(signal, dtype=np.float64)
    signal = signal - np.mean(signal)
    
    window = np.hanning(len(signal))
    signal_windowed = signal * window
    
    fft = np.fft.rfft(signal_windowed)
    magnitude = np.abs(fft)
    freqs = np.fft.rfftfreq(len(signal), 1/SAMPLE_RATE)
    
    if np.sum(magnitude) == 0:
        return 0, 0, 0, 0, 0
    
    low_freq_mask = freqs < 200
    mid_freq_mask = (freqs >= 200) & (freqs < 2000)
    high_freq_mask = freqs >= 2000
    
    low_energy = np.sum(magnitude[low_freq_mask]) if np.any(low_freq_mask) else 0
    mid_energy = np.sum(magnitude[mid_freq_mask]) if np.any(mid_freq_mask) else 0
    high_energy = np.sum(magnitude[high_freq_mask]) if np.any(high_freq_mask) else 0
    
    dominant_freq = freqs[np.argmax(magnitude)]
    spectral_energy = np.sum(np.square(magnitude))
    spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
    spectral_spread = np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * magnitude) / np.sum(magnitude))
    
    return dominant_freq, spectral_energy, spectral_centroid, spectral_spread, (low_energy, mid_energy, high_energy)

# ==================== FEATURE EXTRACTION ====================
def extract_features(signal):
    """Extract comprehensive features from sound signal"""
    if not signal:
        return [0] * 12
    
    rms_val = rms(signal)
    db = voltage_to_db(rms_val)
    dom_freq, energy, centroid, spread, band_energies = fft_features(signal)
    
    signal_array = np.array(signal)
    peak = np.max(np.abs(signal_array)) if len(signal_array) > 0 else 0
    zero_crossings = np.sum(np.diff(np.sign(signal_array)) != 0) if len(signal_array) > 1 else 0
    
    skewness = float(np.mean(((signal_array - np.mean(signal_array)) / np.std(signal_array)) ** 3)) if len(signal_array) > 0 and np.std(signal_array) > 0 else 0
    kurtosis = float(np.mean(((signal_array - np.mean(signal_array)) / np.std(signal_array)) ** 4)) - 3 if len(signal_array) > 0 and np.std(signal_array) > 0 else 0
    
    return [db, dom_freq, energy, centroid, peak, zero_crossings, spread, skewness, kurtosis] + list(band_energies)

# ==================== MACHINE LEARNING MODEL ====================
def initialize_model():
    """Initialize and train the Random Forest model"""
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=7,
        random_state=42,
        min_samples_split=3,
        min_samples_leaf=2
    )
    
    X_train = [
        [40, 100, 5000, 120, 0.5, 50, 50, 0.1, -0.5, 2000, 2500, 500],
        [45, 120, 6000, 150, 0.8, 80, 60, 0.2, -0.3, 1500, 3500, 1000],
        [70, 500, 20000, 600, 2.5, 200, 200, 0.5, 1.2, 500, 5000, 14500],
        [80, 800, 30000, 900, 3.2, 50, 300, 1.2, 2.5, 1000, 15000, 14000],
        [60, 300, 15000, 400, 1.5, 150, 150, 0.3, 0.8, 2000, 8000, 5000],
        [35, 50, 2000, 80, 0.3, 30, 30, 0.05, -0.8, 1000, 800, 200],
        [90, 1200, 40000, 1200, 4.0, 40, 400, 2.0, 5.0, 500, 5000, 34500],
        [55, 250, 12000, 350, 1.2, 120, 120, 0.4, 0.2, 3000, 7000, 2000],
    ]
    
    y_train = [
        "quiet", "conversation", "crowd", "door_slam",
        "shouting", "background", "impact", "traffic"
    ]
    
    model.fit(X_train, y_train)
    return model

model = initialize_model()

# ==================== SOUND ANALYSIS ====================
def analyze_sound(new_sample):
    """Analyze sound samples and return features"""
    samples.append(new_sample)
    
    if len(samples) < WINDOW_SIZE:
        return None
    
    features = extract_features(list(samples))
    prediction_proba = model.predict_proba([features])[0]
    prediction = model.predict([features])[0]
    confidence = np.max(prediction_proba)
    
    db = features[0]
    db_history.append(db)
    
    if len(db_history) > 10:
        baseline = np.median(db_history)
        std_dev = np.std(db_history)
        spike = db > baseline + (SPIKE_THRESHOLD_DB * (1 + 0.1 * (std_dev / max(baseline, 1))))
        rate_of_change = abs(db - baseline) / max(baseline, 1)
    else:
        baseline = db
        spike = False
        rate_of_change = 0
    
    for _ in range(WINDOW_SIZE // 2):
        samples.popleft()
    
    return {
        'db': db,
        'baseline': baseline,
        'spike': spike,
        'rate_of_change': rate_of_change,
        'event': prediction,
        'confidence': confidence,
        'features': features
    }

# ==================== ENHANCED RADAR PROCESSING ====================
class RadarProcessor:
    """Advanced mmWave radar processor with tracking and vital signs"""
    
    def __init__(self, radar_type='auto', port='/dev/ttyUSB0'):
        self.radar_type = radar_type
        self.port = port
        self.config = None
        self.serial_conn = None
        self.target_history = deque(maxlen=100)
        self.velocity_history = {}
        self.range_history = {}
        self.breathing_buffers = {}
        self.last_positions = {}
        self.tracking_id = 0
        self.detected_radar_type = None
        self._connect_and_detect()
    
    def _connect_and_detect(self):
        """Connect to radar and auto-detect type"""
        test_baudrates = [256000, 115200, 921600, 9600]
        
        for baud in test_baudrates:
            try:
                self.serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=baud,
                    timeout=1,
                    write_timeout=1
                )
                
                time.sleep(0.5)
                if self.serial_conn.in_waiting:
                    test_data = self.serial_conn.read(50)
                    
                    if test_data:
                        if len(test_data) >= 22 and test_data[0] == 0xAA and test_data[1] == 0xFF:
                            self.detected_radar_type = 'rd03d'
                            self.config = RADAR_CONFIGS['rd03d']
                            self.config['baudrate'] = baud
                            logger.info(f"✅ Detected RD-03D radar at {baud} baud")
                            break
                        elif b'F' in test_data or b'T' in test_data:
                            self.detected_radar_type = 'ld2410'
                            self.config = RADAR_CONFIGS['ld2410']
                            self.config['baudrate'] = baud
                            logger.info(f"✅ Detected LD2410 radar at {baud} baud")
                            break
                
                self.serial_conn.close()
            except:
                continue
        
        if not self.detected_radar_type:
            self.detected_radar_type = 'rd03d'
            self.config = RADAR_CONFIGS['rd03d']
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=256000,
                timeout=1,
                write_timeout=1
            )
            logger.warning("⚠ Could not auto-detect radar, assuming RD-03D")
    
    def _parse_rd03d_frame(self, data):
        """Parse RD-03D radar data format"""
        targets = []
        
        if len(data) >= 22 and data[0] == 0xAA and data[1] == 0xFF:
            num_targets = data[4]
            
            for i in range(min(num_targets, self.config['max_targets'])):
                offset = 5 + i * 6
                if offset + 6 <= len(data):
                    target_id = data[offset]
                    x = int.from_bytes(data[offset+1:offset+3], 'little', signed=True) / 100.0
                    y = int.from_bytes(data[offset+3:offset+5], 'little', signed=True) / 100.0
                    velocity = int.from_bytes(data[offset+5:offset+6], 'little', signed=True) / 100.0
                    
                    distance = math.sqrt(x**2 + y**2)
                    angle = math.degrees(math.atan2(y, x)) if distance > 0 else 0
                    
                    orientation = 'toward' if velocity > 0.05 else 'away' if velocity < -0.05 else 'stationary'
                    
                    target = {
                        'id': f"T{target_id:02d}",
                        'x': x,
                        'y': y,
                        'distance': distance,
                        'angle': angle,
                        'velocity': abs(velocity),
                        'direction': 'incoming' if velocity > 0 else 'outgoing',
                        'orientation': orientation,
                        'confidence': 0.7 + (0.3 * min(1.0, abs(velocity) / 2.0)),
                        'timestamp': time.time()
                    }
                    targets.append(target)
            
            return {
                'timestamp': time.time(),
                'targets': targets,
                'target_count': len(targets),
                'format': 'rd03d'
            }
        return None
    
    def parse_radar_frame(self, raw_data):
        """Parse raw radar data based on detected type"""
        if not raw_data:
            return None
        
        try:
            if self.detected_radar_type == 'rd03d':
                return self._parse_rd03d_frame(raw_data)
            return None
        except Exception as e:
            logger.error(f"Radar parse error: {e}")
            return None
    
    def detect_breathing(self, target_id, range_data, sampling_rate=10):
        """Extract breathing rate from radar range data"""
        if len(range_data) < 50:
            return None, None
        
        nyquist = sampling_rate / 2
        low = BREATHING_FREQ_RANGE[0] / nyquist
        high = BREATHING_FREQ_RANGE[1] / nyquist
        
        try:
            b, a = scipy_signal.butter(4, [low, high], btype='band')
            filtered = scipy_signal.filtfilt(b, a, range_data)
            
            freqs = np.fft.fftfreq(len(filtered), 1/sampling_rate)
            fft_vals = np.abs(np.fft.fft(filtered))
            
            mask = (freqs >= BREATHING_FREQ_RANGE[0]) & (freqs <= BREATHING_FREQ_RANGE[1])
            if np.any(mask):
                peak_idx = np.argmax(fft_vals[mask])
                peak_freq = freqs[mask][peak_idx]
                breathing_rate = peak_freq * 60
                
                signal_power = np.max(fft_vals[mask])
                noise_power = np.mean(fft_vals[~mask]) if np.any(~mask) else 0.001
                confidence = min(1.0, signal_power / (noise_power * 5))
                
                return breathing_rate, confidence
        except Exception as e:
            logger.debug(f"Breathing detection error: {e}")
        
        return None, 0
    
    def recognize_activity(self, recent_velocities):
        """Recognize human activity from velocity patterns"""
        if len(recent_velocities) < 5:
            return 'unknown', 0.0
        
        avg_speed = np.mean(recent_velocities)
        max_speed = np.max(recent_velocities)
        speed_variance = np.var(recent_velocities)
        
        if avg_speed < 0.1:
            activity = 'stationary'
            confidence = 0.8
        elif avg_speed < 0.3:
            activity = 'sitting'
            confidence = 0.7
        elif avg_speed < 0.8:
            activity = 'walking'
            confidence = 0.8
        elif max_speed > 1.5:
            activity = 'running'
            confidence = 0.9
        elif speed_variance > 0.3:
            activity = 'transition'
            confidence = 0.7
        else:
            activity = 'unknown'
            confidence = 0.3
        
        return activity, confidence
    
    def track_targets(self, radar_data):
        """Track targets across frames"""
        if not radar_data or 'targets' not in radar_data:
            return radar_data
        
        current_targets = radar_data.get('targets', [])
        tracked_targets = []
        
        for target in current_targets:
            target_id = target.get('id')
            
            # Initialize histories for new targets
            if target_id not in self.range_history:
                self.range_history[target_id] = deque(maxlen=100)
                self.velocity_history[target_id] = deque(maxlen=50)
                self.breathing_buffers[target_id] = deque(maxlen=150)
            
            # Update histories
            if 'distance' in target:
                self.range_history[target_id].append(target['distance'])
            if 'velocity' in target:
                self.velocity_history[target_id].append(target['velocity'])
            
            # Detect breathing
            if len(self.range_history[target_id]) > 50:
                breathing_rate, breath_conf = self.detect_breathing(
                    target_id,
                    list(self.range_history[target_id]),
                    sampling_rate=10
                )
                if breathing_rate:
                    target['breathing_rate'] = round(breathing_rate, 1)
                    target['breathing_confidence'] = round(breath_conf, 2)
                    target['abnormal_breathing'] = breathing_rate < 8 or breathing_rate > 24
            
            # Recognize activity
            if len(self.velocity_history[target_id]) > 5:
                activity, act_conf = self.recognize_activity(
                    list(self.velocity_history[target_id])
                )
                target['activity'] = activity
                target['activity_confidence'] = act_conf
            
            self.last_positions[target_id] = target.copy()
            tracked_targets.append(target)
        
        radar_data['targets'] = tracked_targets
        radar_data['target_count'] = len(tracked_targets)
        
        return radar_data
    
    def analyze_motion_patterns(self):
        """Analyze overall motion patterns"""
        if not self.last_positions:
            return {
                'pattern': 'no_detections',
                'activity_level': 0,
                'crowd_density': 0
            }
        
        active_targets = sum(1 for t in self.last_positions.values() 
                           if t.get('velocity', 0) > 0.1)
        total_targets = len(self.last_positions)
        activity_level = active_targets / max(total_targets, 1)
        
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
            'total_targets': total_targets,
            'active_targets': active_targets
        }
    
    def detect_activity_events(self):
        """Detect specific activity events"""
        events = []
        
        if len(self.target_history) < 3:
            return events
        
        recent = list(self.target_history)[-3:]
        
        if len(recent) >= 2:
            count_change = recent[-1].get('target_count', 0) - recent[-2].get('target_count', 0)
            
            if count_change > 0:
                events.append({
                    'type': 'entry',
                    'magnitude': count_change,
                    'confidence': min(0.9, 0.5 + count_change * 0.2)
                })
            elif count_change < 0:
                events.append({
                    'type': 'exit',
                    'magnitude': abs(count_change),
                    'confidence': min(0.9, 0.5 + abs(count_change) * 0.2)
                })
        
        return events
    
    def read_radar(self):
        """Read and process radar data"""
        if not self.serial_conn:
            return None
        
        try:
            if self.serial_conn.in_waiting:
                if self.detected_radar_type == 'rd03d':
                    raw_data = self.serial_conn.read(22)
                else:
                    raw_data = self.serial_conn.readline()
                
                if raw_data:
                    parsed_data = self.parse_radar_frame(raw_data)
                    
                    if parsed_data and 'targets' in parsed_data:
                        tracked_data = self.track_targets(parsed_data)
                        self.target_history.append({
                            'timestamp': time.time(),
                            'target_count': tracked_data.get('target_count', 0),
                            'data': tracked_data
                        })
                        return tracked_data
        except Exception as e:
            logger.error(f"Radar read error: {e}")
        
        return None

# ==================== TEMPORAL THREAT SCORING ENGINE ====================

class TemporalThreatScorer:
    """
    Advanced threat scoring with exponential time-based escalation
    """
    
    def __init__(self, config: ThreatConfig = None):
        self.config = config or ThreatConfig()
        self.threat_history = deque(maxlen=1000)
        self.event_log = []
        self.component_history = {name: deque(maxlen=100) for name in self.config.COMPONENT_WEIGHTS.keys()}
        self.last_update = time.time()
        
        # Exponential moving averages
        self.ema_short = 0
        self.ema_medium = 0
        self.ema_long = 0
        
        # Decay factors
        self.alpha_short = 0.3
        self.alpha_medium = 0.1
        self.alpha_long = 0.03
    
    def exponential_escalation(self, base_threat: float, time_active: float, 
                               intensity: float, persistence: int) -> float:
        """
        Calculate exponentially escalated threat based on multiple factors
        
        threat = base * (1 + k1 * time)^(k2 * intensity) * (1 + k3 * persistence)
        """
        # Time factor: exponential growth with time
        time_factor = math.pow(1 + 0.1 * time_active / 60, 2)  # Quadratic time factor
        
        # Intensity factor: exponential jumps at thresholds
        intensity_factor = 1.0
        for i, threshold in enumerate(self.config.INTENSITY_LEVELS):
            if intensity > threshold:
                intensity_factor *= self.config.BASE_ESCALATION_FACTOR
        
        # Persistence factor: linear multiplier for recurring threats
        persistence_factor = 1.0 + (persistence / self.config.PERSISTENCE_THRESHOLD) * \
                            (self.config.PERSISTENCE_MULTIPLIER - 1)
        
        # Combined exponential escalation
        escalated = base_threat * time_factor * intensity_factor * persistence_factor
        
        return min(100, escalated)
    
    def exponential_decay(self, threat: float, time_elapsed: float) -> float:
        """
        Apply exponential decay to threat over time
        threat(t) = threat * 2^(-t / half_life)
        """
        return threat * math.pow(2, -time_elapsed / self.config.TIME_DECAY_HALF_LIFE)
    
    def calculate_trend_factor(self, values: List[float]) -> Tuple[float, float, float]:
        """Calculate trend slope, acceleration, and strength"""
        if len(values) < 3:
            return 0, 0, 0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Quadratic fit for acceleration
        coeffs = np.polyfit(x, y, 2)
        slope = coeffs[-2] if len(coeffs) > 1 else 0
        acceleration = coeffs[0] * 2 if len(coeffs) > 2 else 0
        
        # R-squared for trend strength
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        strength = 1 - (ss_res / max(ss_tot, 0.001))
        
        return slope, acceleration, strength
    
    def calculate_persistence(self, component: str, time_window: int = 300) -> int:
        """Calculate persistence count for a component within time window"""
        now = time.time()
        recent = [t for t in self.threat_history 
                 if now - t['timestamp'] < time_window]
        
        if not recent:
            return 0
        
        # Count occurrences where component threat was significant
        count = 0
        for entry in recent:
            comp_data = entry.get('components', {}).get(component, {})
            if comp_data.get('score', 0) > 50:  # Significant threat
                count += 1
        
        return count
    
    def calculate_component_threat(self, name: str, current_score: float, 
                                  confidence: float) -> float:
        """
        Calculate temporally-adjusted component threat with exponential factors
        """
        # Get historical values
        history = list(self.component_history[name])[-20:] if name in self.component_history else []
        self.component_history[name].append(current_score)
        
        # Calculate trend
        slope, acceleration, strength = self.calculate_trend_factor(history)
        
        # Calculate persistence
        persistence = self.calculate_persistence(name)
        
        # Calculate time active (how long this component has been elevated)
        time_active = 0
        if history:
            elevated_count = sum(1 for v in history if v > 40)
            time_active = elevated_count * 5  # Assuming 5-second intervals
        
        # Base intensity from current score
        intensity = current_score
        
        # Apply exponential escalation
        if slope > 0 or acceleration > 0:
            # Worsening trend - escalate exponentially
            escalated = self.exponential_escalation(
                current_score, time_active, intensity, persistence
            )
            # Blend with current based on trend strength
            adjusted = current_score * (1 - strength) + escalated * strength
        else:
            # Improving trend - apply decay
            decay_time = abs(slope) * 60  # Convert slope to time
            adjusted = self.exponential_decay(current_score, decay_time)
        
        # Apply confidence weighting
        adjusted = adjusted * (0.5 + 0.5 * confidence)
        
        return min(100, max(0, adjusted))
    
    def get_temporal_context(self) -> Dict:
        """Get current temporal context"""
        now = time.time()
        recent = [t for t in self.threat_history 
                 if now - t['timestamp'] < self.config.TREND_WINDOWS['long']]
        
        if len(recent) < 3:
            return {
                'trend': 'stable',
                'slope': 0,
                'acceleration': 0,
                'volatility': 0,
                'persistence_factor': 1.0
            }
        
        values = [t['overall_threat'] for t in recent]
        slope, acceleration, strength = self.calculate_trend_factor(values)
        volatility = np.std(values[-10:]) if len(values) >= 10 else 0
        
        # Calculate overall persistence factor
        total_persistence = sum(
            self.calculate_persistence(name) 
            for name in self.config.COMPONENT_WEIGHTS.keys()
        )
        persistence_factor = 1.0 + (total_persistence / 10) * 0.5
        
        # Determine trend direction with exponential consideration
        if slope > 0.5:
            trend = 'rapidly_worsening'
        elif slope > 0.1:
            trend = 'worsening'
        elif slope < -0.5:
            trend = 'rapidly_improving'
        elif slope < -0.1:
            trend = 'improving'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'slope': slope,
            'acceleration': acceleration,
            'volatility': volatility,
            'persistence_factor': persistence_factor,
            'trend_strength': strength
        }
    
    def predict_trajectory(self, minutes: int = 30) -> Dict[str, Optional[float]]:
        """Predict threat trajectory"""
        if len(self.threat_history) < 10:
            return {'5min': None, '15min': None, '30min': None}
        
        recent = list(self.threat_history)[-20:]
        values = [t['overall_threat'] for t in recent]
        
        if len(values) >= 5:
            x = np.arange(len(values))
            coeffs = np.polyfit(x, values, 2)  # Quadratic for acceleration
            current = values[-1]
            
            predictions = {}
            for minutes_ahead, label in [(5, '5min'), (15, '15min'), (30, '30min')]:
                future_x = len(values) + minutes_ahead
                pred = np.polyval(coeffs, future_x)
                # Apply exponential bounds
                if pred > current * 2:
                    pred = current * 2  # Cap at 2x current
                predictions[label] = min(100, max(0, pred))
            
            return predictions
        
        return {'5min': None, '15min': None, '30min': None}

# ==================== ENHANCED THREAT SCORER ====================

class EnhancedThreatScorer:
    """Complete threat scoring system with temporal dynamics"""
    
    def __init__(self):
        self.temporal = TemporalThreatScorer()
        self.config = ThreatConfig()
        
    def calculate_proximity_threat(self, targets: List[Dict]) -> Tuple[float, float]:
        """Calculate threat based on proximity"""
        if not targets:
            return 0, 1.0
        
        threat_score = 0
        closest_distance = float('inf')
        
        for target in targets:
            distance = target.get('distance', 10)
            closest_distance = min(closest_distance, distance)
            
            # Exponential proximity threat
            if distance < 1.0:
                threat_score += 30
            elif distance < 2.0:
                threat_score += 15
            elif distance < 3.0:
                threat_score += 8
            elif distance < 5.0:
                threat_score += 3
            
            # Direction multiplier
            if target.get('direction') == 'incoming':
                threat_score *= 1.5
            
            # Loitering multiplier
            if target.get('activity') == 'stationary' and distance < 3.0:
                threat_score *= 1.3
        
        threat_score = min(100, threat_score)
        confidence = 0.9 if closest_distance < 5 else 0.7
        
        return threat_score, confidence
    
    def calculate_count_threat(self, target_count: int) -> Tuple[float, float]:
        """Calculate threat based on number of people"""
        if target_count == 0:
            return 0, 1.0
        
        # Exponential scaling for crowd size
        if target_count <= 2:
            threat = target_count * 15
        elif target_count <= 4:
            threat = 30 + (target_count - 2) * 20
        else:
            threat = 70 + (target_count - 4) * 10
        
        threat = min(100, threat)
        confidence = 0.9 if target_count <= 5 else 0.7
        
        return threat, confidence
    
    def calculate_behavior_threat(self, targets: List[Dict], motion_patterns: Dict,
                                 activity_events: List[Dict]) -> Tuple[float, float]:
        """Calculate threat based on unusual behavior"""
        threat_score = 0
        confidence = 0.8
        
        for target in targets:
            activity = target.get('activity', 'unknown')
            
            # Activity-based threats
            if activity == 'running':
                threat_score += 25
            elif activity == 'transition' and target.get('activity_confidence', 0) > 0.7:
                threat_score += 20
            
            # Abnormal breathing
            if target.get('abnormal_breathing', False):
                threat_score += 30
                confidence = max(confidence, 0.9)
        
        # Motion pattern threats
        if motion_patterns:
            pattern = motion_patterns.get('pattern', '')
            if pattern == 'chaotic':
                threat_score += 35
            elif pattern == 'high_activity':
                threat_score += 15
        
        # Event-based threats
        for event in activity_events:
            if event['type'] == 'entry' and event.get('magnitude', 0) > 1:
                threat_score += 10
            elif event['type'] == 'possible_fall':
                threat_score += 50
                confidence = 0.95
        
        return min(100, threat_score), confidence
    
    def calculate_vital_signs_threat(self, targets: List[Dict]) -> Tuple[float, float]:
        """Calculate threat based on abnormal vital signs"""
        if not targets:
            return 0, 0.5
        
        threat_score = 0
        total_targets = len(targets)
        abnormal_count = 0
        
        for target in targets:
            if target.get('abnormal_breathing', False):
                abnormal_count += 1
                threat_score += 25
            
            if 'breathing_rate' in target:
                rate = target['breathing_rate']
                if rate < 6:  # Dangerously low
                    threat_score += 50
                elif rate > 30:  # Dangerously high
                    threat_score += 40
        
        threat_score = min(100, threat_score)
        confidence = abnormal_count / max(total_targets, 1)
        
        return threat_score, confidence
    
    def calculate_air_quality_threat(self, odor_data: Optional[Dict]) -> Tuple[float, float]:
        """Calculate threat from air quality sensors"""
        if not odor_data:
            return 0, 0.3
        
        threat_score = 0
        
        # VOC exponential threat
        voc = odor_data.get('voc_ppm', 0)
        if voc > 200:
            threat_score += 50
        elif voc > 100:
            threat_score += 30
        elif voc > 50:
            threat_score += 15
        elif voc > 30:
            threat_score += 5
        
        # PM2.5 exponential threat
        pm25 = odor_data.get('pm25', 0)
        if pm25 > 100:
            threat_score += 45
        elif pm25 > 50:
            threat_score += 25
        elif pm25 > 25:
            threat_score += 10
        
        # Odor type multiplier
        odor_type = odor_data.get('odor_type', '')
        if odor_type == 'strong_chemical':
            threat_score *= 1.5
        elif odor_type == 'dust_or_smoke':
            threat_score *= 1.3
        
        threat_score = min(100, threat_score)
        confidence = odor_data.get('classification_confidence', 0.5)
        
        return threat_score, confidence
    
    def calculate_noise_threat(self, sound_data: Optional[Dict]) -> Tuple[float, float]:
        """Calculate threat from sound levels"""
        if not sound_data:
            return 0, 0.3
        
        db = sound_data.get('db', 40)
        
        # Exponential noise threat
        if db > 100:
            threat_score = 90
        elif db > 90:
            threat_score = 70
        elif db > 80:
            threat_score = 45
        elif db > 70:
            threat_score = 25
        elif db > 60:
            threat_score = 10
        else:
            threat_score = 0
        
        # Spike multiplier
        if sound_data.get('spike', False):
            threat_score *= 1.5
        
        # Event multiplier
        event = sound_data.get('event', '')
        if event in ['impact', 'explosion']:
            threat_score *= 2.0
        elif event in ['door_slam', 'shouting']:
            threat_score *= 1.3
        
        threat_score = min(100, threat_score)
        confidence = sound_data.get('confidence', 0.5)
        
        return threat_score, confidence
    
    def calculate_overall_threat(self, radar_data: Optional[Dict], 
                                odor_data: Optional[Dict],
                                sound_data: Optional[Dict],
                                motion_patterns: Dict,
                                activity_events: List[Dict]) -> Dict:
        """Calculate overall threat with temporal dynamics"""
        
        targets = radar_data.get('targets', []) if radar_data else []
        
        # Calculate base component threats
        components_raw = {
            'proximity': self.calculate_proximity_threat(targets),
            'count': self.calculate_count_threat(len(targets)),
            'behavior': self.calculate_behavior_threat(targets, motion_patterns, activity_events),
            'vital_signs': self.calculate_vital_signs_threat(targets),
            'air_quality': self.calculate_air_quality_threat(odor_data),
            'noise': self.calculate_noise_threat(sound_data)
        }
        
        # Apply temporal adjustments
        components_adjusted = {}
        confidences = {}
        for name, (score, conf) in components_raw.items():
            adj_score = self.temporal.calculate_component_threat(name, score, conf)
            components_adjusted[name] = adj_score
            confidences[name] = conf
        
        # Dynamic weight adjustment
        adjusted_weights = {}
        total_weight = 0
        
        for name, score in components_adjusted.items():
            conf = confidences[name]
            base_weight = self.config.COMPONENT_WEIGHTS[name]
            
            # Reduce weight for low confidence
            if conf < 0.4:
                adj_weight = base_weight * (conf / 0.4)
            else:
                adj_weight = base_weight
            
            adjusted_weights[name] = adj_weight
            total_weight += adj_weight
        
        # Normalize weights
        if total_weight > 0:
            for name in adjusted_weights:
                adjusted_weights[name] /= total_weight
        
        # Calculate base weighted threat
        base_threat = sum(
            components_adjusted[name] * adjusted_weights[name]
            for name in components_adjusted
        )
        
        # Get temporal context
        temporal_context = self.temporal.get_temporal_context()
        
        # Apply temporal escalation to overall threat
        time_active = len(self.temporal.threat_history) * 5  # Approximate seconds
        intensity = base_threat
        persistence = int(temporal_context['persistence_factor'] * 10)
        
        overall_threat = self.temporal.exponential_escalation(
            base_threat, time_active, intensity, persistence
        )
        
        # Apply trend-based adjustments
        if temporal_context['trend'] in ['worsening', 'rapidly_worsening']:
            # Additional exponential for worsening trends
            trend_multiplier = 1.0 + (abs(temporal_context['slope']) * 2)
            overall_threat = min(100, overall_threat * trend_multiplier)
        
        # Update EMAs
        self.temporal.ema_short = self.temporal.alpha_short * overall_threat + \
                                  (1 - self.temporal.alpha_short) * self.temporal.ema_short
        self.temporal.ema_medium = self.temporal.alpha_medium * overall_threat + \
                                   (1 - self.temporal.alpha_medium) * self.temporal.ema_medium
        self.temporal.ema_long = self.temporal.alpha_long * overall_threat + \
                                (1 - self.temporal.alpha_long) * self.temporal.ema_long
        
        # Get threat trajectory
        trajectory = self.temporal.predict_trajectory()
        
        # Determine threat level
        if overall_threat < 20:
            level = "LOW"
            color = "🟢"
            response = "Normal conditions"
        elif overall_threat < 40:
            level = "MODERATE"
            color = "🟡"
            response = "Monitor situation"
        elif overall_threat < 60:
            level = "ELEVATED"
            color = "🟠"
            response = "Increased awareness advised"
        elif overall_threat < 80:
            level = "HIGH"
            color = "🔴"
            response = "Potential threat detected"
        else:
            level = "CRITICAL"
            color = "⚫"
            response = "IMMEDIATE ATTENTION REQUIRED"
        
        # Add temporal warnings
        if temporal_context['trend'] == 'rapidly_worsening':
            response += " - SITUATION DETERIORATING RAPIDLY"
        elif temporal_context['trend'] == 'worsening':
            response += " - Conditions worsening"
        
        if trajectory.get('30min') and trajectory['30min'] > overall_threat * 1.5:
            response += f" - Warning: {trajectory['30min']:.0f} predicted in 30min"
        
        # Create threat entry
        threat_entry = {
            'timestamp': time.time(),
            'overall_threat': round(overall_threat, 1),
            'base_threat': round(base_threat, 1),
            'level': level,
            'color': color,
            'response': response,
            'components': {
                name: {
                    'score': round(components_adjusted[name], 1),
                    'raw_score': round(components_raw[name][0], 1),
                    'confidence': round(confidences[name], 2),
                    'weight': round(adjusted_weights[name], 2)
                }
                for name in components_adjusted
            },
            'temporal': {
                'trend': temporal_context['trend'],
                'slope': round(temporal_context['slope'], 3),
                'acceleration': round(temporal_context['acceleration'], 3),
                'volatility': round(temporal_context['volatility'], 2),
                'persistence_factor': round(temporal_context['persistence_factor'], 2)
            },
            'trajectory': {
                '5min': round(trajectory['5min'], 1) if trajectory['5min'] else None,
                '15min': round(trajectory['15min'], 1) if trajectory['15min'] else None,
                '30min': round(trajectory['30min'], 1) if trajectory['30min'] else None
            },
            'confidence': round(np.mean(list(confidences.values())), 2)
        }
        
        # Store in history
        self.temporal.threat_history.append(threat_entry)
        threat_history.append(threat_entry)
        
        return threat_entry

# ==================== ENVIRONMENTAL QUALITY SCORER ====================

class EnvironmentalQualityScorer:
    """Scores environmental quality (inverse of threat)"""
    
    def __init__(self):
        self.quality_history = deque(maxlen=500)
        self.baseline_quality = 85
    
    def calculate_quality(self, threat_data: Dict, sound_data: Optional[Dict],
                         odor_data: Optional[Dict], radar_data: Optional[Dict]) -> Dict:
        """Calculate environmental quality score"""
        if not threat_data:
            return {'quality_score': 75, 'category': 'GOOD', 'icon': '✅'}
        
        # Base quality is inverse of threat with exponential scaling
        base_quality = 100 - (threat_data['overall_threat'] * 0.8)
        
        # Adjustments
        adjustments = {}
        
        # Sound quality
        if sound_data:
            db = sound_data.get('db', 40)
            if db < 45:
                sound_quality = 95
            elif db < 55:
                sound_quality = 85
            elif db < 65:
                sound_quality = 70
            elif db < 75:
                sound_quality = 50
            else:
                sound_quality = 30
            adjustments['sound'] = sound_quality
            base_quality = (base_quality + sound_quality) / 2
        
        # Air quality
        if odor_data:
            aqi = odor_data.get('air_quality_index', 50)
            if aqi < 50:
                air_quality = 90
            elif aqi < 100:
                air_quality = 75
            elif aqi < 150:
                air_quality = 55
            elif aqi < 200:
                air_quality = 35
            else:
                air_quality = 20
            adjustments['air'] = air_quality
            base_quality = (base_quality + air_quality) / 2
        
        # Occupancy comfort
        if radar_data and 'targets' in radar_data:
            target_count = len(radar_data['targets'])
            if target_count == 0:
                occ_quality = 90
            elif target_count == 1:
                occ_quality = 85
            elif target_count == 2:
                occ_quality = 75
            elif target_count == 3:
                occ_quality = 60
            else:
                occ_quality = 40
            adjustments['occupancy'] = occ_quality
            base_quality = (base_quality + occ_quality) / 2
        
        # Apply temporal smoothing
        self.quality_history.append(base_quality)
        if len(self.quality_history) > 5:
            smoothed = np.mean(list(self.quality_history)[-5:])
        else:
            smoothed = base_quality
        
        # Determine category
        if smoothed >= 90:
            category = "EXCELLENT"
            icon = "🌟"
        elif smoothed >= 80:
            category = "GOOD"
            icon = "✅"
        elif smoothed >= 70:
            category = "FAIR"
            icon = "⚠️"
        elif smoothed >= 60:
            category = "POOR"
            icon = "🔴"
        else:
            category = "CRITICAL"
            icon = "🚨"
        
        # Calculate trend
        if len(self.quality_history) > 10:
            recent = list(self.quality_history)[-5:]
            previous = list(self.quality_history)[-10:-5]
            trend = 'improving' if np.mean(recent) > np.mean(previous) else 'declining'
        else:
            trend = 'stable'
        
        return {
            'quality_score': round(smoothed, 1),
            'base_quality': round(base_quality, 1),
            'category': category,
            'icon': icon,
            'adjustments': {k: round(v, 1) for k, v in adjustments.items()},
            'trend': trend,
            'timestamp': time.time()
        }

# ==================== ODOR ANALYSIS ENGINE ====================
VOC_BASELINE = None
PM_BASELINE = None

def compute_mq135_ppm(voltage):
    """Convert MQ135 voltage to ppm"""
    if voltage <= 0 or math.isnan(voltage):
        return 0
    
    try:
        rs = RLOAD * (VCC / max(voltage, 0.001) - 1)
        ratio = rs / R0
        ratio = np.clip(ratio, 0.1, 10)
        
        a = 116.6020682
        b = -2.769034857
        ppm = a * (ratio ** b)
        
        return max(0, min(ppm, 1000))
    except:
        return 0

def classify_odor(voc_ppm, pm25, people, noise_db):
    """Classify odor type with confidence"""
    confidence = 1.0
    
    if voc_ppm < VOC_CLEAN_THRESHOLD and pm25 < PM_CLEAN_THRESHOLD:
        return "clean_air", confidence
    
    if voc_ppm > VOC_ACTIVITY_THRESHOLD and people >= 1:
        confidence = min(1.0, (voc_ppm - VOC_ACTIVITY_THRESHOLD) / 100 + 0.5)
        return "human_activity", confidence
    
    if pm25 > PM_SMOKE_THRESHOLD:
        confidence = min(1.0, (pm25 - PM_SMOKE_THRESHOLD) / 50 + 0.6)
        return "dust_or_smoke", confidence
    
    if voc_ppm > VOC_CHEMICAL_THRESHOLD:
        confidence = min(1.0, (voc_ppm - VOC_CHEMICAL_THRESHOLD) / 200 + 0.7)
        return "strong_chemical", confidence
    
    if noise_db > LOUD_THRESHOLD_DB and voc_ppm > VOC_CLEAN_THRESHOLD * 1.5:
        return "noise_correlated_activity", 0.8
    
    return "moderate_odor", 0.6

def compute_odor_intensity(voc_ppm, pm25, people, noise_db, trend):
    """Calculate odor intensity"""
    score = 0
    score += min(voc_ppm / 50, 4)
    score += min(pm25 / 25, 3)
    score += min(people / 3, 2)
    
    if noise_db > LOUD_THRESHOLD_DB:
        score += 0.5
    
    if trend > 20:
        score += 0.5
    elif trend > 10:
        score += 0.25
    
    return score

def detect_odor_anomaly(current_score):
    """Detect anomalies in odor"""
    if len(odor_history) < 10:
        odor_history.append(current_score)
        return False, current_score
    
    baseline = np.median(list(odor_history))
    std_dev = np.std(list(odor_history))
    odor_history.append(current_score)
    
    anomaly = current_score > baseline + max(2, std_dev * 2)
    return anomaly, baseline

def analyze_odor(noise_db):
    """Comprehensive odor analysis"""
    global VOC_BASELINE, PM_BASELINE
    
    try:
        voc_voltage = read_mq135()
        pms_data = read_pms5003()
        
        people = 0
        if radar_processor and radar_processor.last_positions:
            people = len(radar_processor.last_positions)
        
        pm1 = pm25 = pm10 = 0
        if pms_data and len(pms_data) == 3:
            pm1, pm25, pm10 = pms_data
        
        voc_ppm = compute_mq135_ppm(voc_voltage)
        
        if VOC_BASELINE is None:
            VOC_BASELINE = voc_ppm
        else:
            VOC_BASELINE = 0.95 * VOC_BASELINE + 0.05 * voc_ppm
        
        if PM_BASELINE is None:
            PM_BASELINE = pm25
        else:
            PM_BASELINE = 0.95 * PM_BASELINE + 0.05 * pm25
        
        trend = voc_ppm - VOC_BASELINE
        intensity = compute_odor_intensity(voc_ppm, pm25, people, noise_db, trend)
        anomaly, baseline = detect_odor_anomaly(intensity)
        odor_type, confidence = classify_odor(voc_ppm, pm25, people, noise_db)
        
        if intensity < 2:
            level = "LOW"
        elif intensity < 3.5:
            level = "MODERATE"
        elif intensity < 5:
            level = "HIGH"
        elif intensity < 6.5:
            level = "SEVERE"
        else:
            level = "CRITICAL"
        
        aqi = (voc_ppm / 100 * 50) + (pm25 / 35 * 50)
        aqi = min(500, max(0, aqi))
        
        return {
            "timestamp": time.time(),
            "voc_voltage": round(voc_voltage, 3),
            "voc_ppm": round(voc_ppm, 1),
            "pm1": pm1,
            "pm25": pm25,
            "pm10": pm10,
            "people": people,
            "odor_type": odor_type,
            "classification_confidence": round(confidence, 2),
            "odor_intensity": round(intensity, 2),
            "odor_level": level,
            "odor_trend": round(trend, 2),
            "baseline_intensity": round(baseline, 2),
            "odor_anomaly": anomaly,
            "air_quality_index": round(aqi, 1)
        }
    except Exception as e:
        logger.error(f"Odor analysis error: {e}")
        return None

# ==================== HARDWARE INITIALIZATION ====================
def init_hardware():
    """Initialize all hardware components"""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 1
        
        mq135_channel = AnalogIn(ads, ADS.P0)
        sound_channel = AnalogIn(ads, ADS.P1)
        
        pms = serial.Serial(
            port="/dev/serial0",
            baudrate=9600,
            timeout=2,
            write_timeout=2
        )
        
        logger.info("✅ Hardware initialized successfully")
        return i2c, ads, mq135_channel, sound_channel, pms
        
    except Exception as e:
        logger.error(f"Hardware initialization error: {e}")
        return None, None, None, None, None

# Initialize hardware
i2c, ads, mq135_channel, sound_channel, pms = init_hardware()

# ==================== SENSOR READING FUNCTIONS ====================
def read_pms5003():
    """Read PMS5003 sensor"""
    if not pms:
        return None
    
    try:
        pms.reset_input_buffer()
        data = pms.read(32)
        
        if len(data) == 32 and data[0] == 0x42 and data[1] == 0x4d:
            checksum = sum(data[:30]) & 0xFF
            if checksum == data[30] or checksum == data[31]:
                pm1 = (data[10] << 8) | data[11]
                pm25 = (data[12] << 8) | data[13]
                pm10 = (data[14] << 8) | data[15]
                
                if 0 <= pm1 <= 1000 and 0 <= pm25 <= 1000 and 0 <= pm10 <= 1000:
                    return pm1, pm25, pm10
    except Exception as e:
        logger.debug(f"PMS5003 read error: {e}")
    
    return None

def read_mq135():
    """Read MQ135 sensor"""
    if not mq135_channel:
        return 0
    
    try:
        samples = []
        for _ in range(5):
            voltage = mq135_channel.voltage
            if not math.isnan(voltage):
                samples.append(voltage)
            time.sleep(0.01)
        
        return np.median(samples) if samples else 0
    except Exception:
        return 0

def read_sound():
    """Read sound sensor"""
    if not sound_channel:
        return 0
    
    try:
        return sound_channel.voltage
    except Exception:
        return 0

# Initialize processors
radar_processor = RadarProcessor(radar_type=RADAR_TYPE, port=RADAR_PORT)
threat_scorer = EnhancedThreatScorer()
quality_scorer = EnvironmentalQualityScorer()

# ==================== MAIN LOOP ====================
def main():
    """Main program loop"""
    print("\n" + "="*100)
    print(f"🚀 {SYSTEM_NAME} v{VERSION}")
    print("="*100)
    print("Features:")
    print("  • Sound Analysis with ML Classification")
    print("  • Air Quality Monitoring (VOC, PM1.0, PM2.5, PM10)")
    print(f"  • mmWave Radar: {radar_processor.detected_radar_type or 'Unknown'}")
    print("    - Multi-target tracking with orientation")
    print("    - Activity recognition & breathing monitoring")
    print("  • EXPONENTIAL TEMPORAL THREAT SCORING:")
    print("    - Time-based escalation: threat ∝ (1 + 0.1*t)^2")
    print("    - Intensity jumps: 1.5x per threshold")
    print("    - Persistence multiplier: up to 2x")
    print("    - Trend acceleration detection")
    print("    - 5/15/30 minute predictions")
    print("  • Environmental Quality Assessment")
    print("="*100)
    print("Press Ctrl+C to exit\n")
    
    last_print_time = time.time()
    print_interval = 5
    
    # Check hardware
    if None in [mq135_channel, sound_channel, pms]:
        logger.warning("⚠ Some sensors failed to initialize - running in simulation mode")
    
    try:
        while True:
            current_time = time.time()
            
            try:
                # Read all sensors
                pms_data = read_pms5003()
                mq135_voltage = read_mq135()
                sound_voltage = read_sound()
                radar_data = read_radar()
                
                # Analyze sound
                sound_analysis = analyze_sound(sound_voltage)
                
                # Analyze odor
                odor_analysis = None
                if sound_analysis:
                    odor_analysis = analyze_odor(sound_analysis['db'])
                
                # Analyze radar
                motion_patterns = radar_processor.analyze_motion_patterns() if radar_processor else {}
                activity_events = radar_processor.detect_activity_events() if radar_processor else []
                
                # Periodic output
                if current_time - last_print_time >= print_interval:
                    print("\n" + "="*100)
                    print(f"📊 COMPREHENSIVE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("="*100)
                    
                    # Sound Analysis
                    if sound_analysis:
                        print("\n🔊 SOUND ANALYSIS:")
                        print(f"   Level: {sound_analysis['db']:.1f} dB (Baseline: {sound_analysis['baseline']:.1f} dB)")
                        print(f"   Event: {sound_analysis['event']} (conf: {sound_analysis['confidence']:.2f})")
                        if sound_analysis['spike']:
                            print(f"   ⚠ Sound spike! (Rate: {sound_analysis['rate_of_change']:.2f})")
                    
                    # Odor Analysis
                    if odor_analysis:
                        print("\n🌬️ AIR QUALITY:")
                        print(f"   VOC: {odor_analysis['voc_ppm']:.1f} ppm")
                        print(f"   PM2.5: {odor_analysis['pm25']} µg/m³")
                        print(f"   AQI: {odor_analysis['air_quality_index']:.1f}")
                        print(f"   Odor: {odor_analysis['odor_type']} (conf: {odor_analysis['classification_confidence']:.2f})")
                        if odor_analysis['odor_anomaly']:
                            print("   ⚠ Odor anomaly!")
                    
                    # Radar Analysis
                    if radar_data and 'targets' in radar_data:
                        targets = radar_data.get('targets', [])
                        print(f"\n📡 RADAR ANALYSIS:")
                        print(f"   Targets detected: {len(targets)}")
                        
                        for i, target in enumerate(targets):
                            print(f"\n   Target {i+1}:")
                            if 'distance' in target:
                                print(f"     Distance: {target['distance']:.2f}m")
                            if 'angle' in target:
                                print(f"     Angle: {target['angle']:.1f}°")
                            if 'velocity' in target:
                                print(f"     Speed: {target['velocity']:.2f} m/s")
                            if 'direction' in target:
                                print(f"     Direction: {target['direction']}")
                            if 'orientation' in target:
                                print(f"     Orientation: {target['orientation']}")
                            if 'activity' in target:
                                print(f"     Activity: {target['activity']} (conf: {target.get('activity_confidence', 0):.2f})")
                            if 'breathing_rate' in target:
                                indicator = "⚠" if target.get('abnormal_breathing') else "✓"
                                print(f"     {indicator} Breathing: {target['breathing_rate']:.1f} bpm")
                        
                        if motion_patterns:
                            print(f"\n   Motion Pattern: {motion_patterns.get('pattern')}")
                            print(f"   Activity Level: {motion_patterns.get('activity_level')}")
                        
                        if activity_events:
                            print(f"\n   Events: {len(activity_events)}")
                            for event in activity_events:
                                print(f"     • {event['type']} (conf: {event.get('confidence', 0):.2f})")
                    
                    # Threat Assessment
                    threat_data = threat_scorer.calculate_overall_threat(
                        radar_data, odor_analysis, sound_analysis, motion_patterns, activity_events
                    )
                    
                    print(f"\n{threat_data['color']} THREAT ASSESSMENT {threat_data['color']}")
                    print(f"   OVERALL THREAT: {threat_data['overall_threat']}/100 - {threat_data['level']}")
                    print(f"   Response: {threat_data['response']}")
                    print(f"   Confidence: {threat_data['confidence']}")
                    
                    # Temporal Context
                    print(f"\n   ⏱️ TEMPORAL DYNAMICS:")
                    print(f"      Trend: {threat_data['temporal']['trend'].upper()}")
                    print(f"      Rate: {threat_data['temporal']['slope']:.2f} points/min")
                    print(f"      Acceleration: {threat_data['temporal']['acceleration']:.3f}")
                    print(f"      Persistence factor: {threat_data['temporal']['persistence_factor']:.2f}x")
                    
                    # Trajectory
                    print(f"\n   🔮 THREAT TRAJECTORY:")
                    if threat_data['trajectory']['5min']:
                        print(f"      5min:  {threat_data['trajectory']['5min']:.0f}/100")
                        print(f"      15min: {threat_data['trajectory']['15min']:.0f}/100")
                        print(f"      30min: {threat_data['trajectory']['30min']:.0f}/100")
                        
                        # Visual indicator
                        current = threat_data['overall_threat']
                        if threat_data['trajectory']['30min'] > current * 1.5:
                            print("      ⬆️⬆️ RAPIDLY ESCALATING")
                        elif threat_data['trajectory']['30min'] > current * 1.2:
                            print("      ⬆️ ESCALATING")
                        elif threat_data['trajectory']['30min'] < current * 0.7:
                            print("      ⬇️ DECAYING")
                    
                    # Component Breakdown
                    print(f"\n   📊 THREAT COMPONENTS:")
                    for name, data in threat_data['components'].items():
                        bar = "█" * int(data['score'] / 5) + "░" * (20 - int(data['score'] / 5))
                        esc_indicator = "⚡" if data['score'] > data['raw_score'] * 1.2 else " "
                        print(f"      {name.replace('_', ' ').title():12} [{bar}] {data['score']:.1f}{esc_indicator} "
                              f"(base:{data['raw_score']:.0f}, conf:{data['confidence']:.2f}, w:{data['weight']:.2f})")
                    
                    # Environmental Quality
                    quality_data = quality_scorer.calculate_quality(
                        threat_data, sound_analysis, odor_analysis, radar_data
                    )
                    print(f"\n   {quality_data['icon']} ENVIRONMENTAL QUALITY: {quality_data['quality_score']}/100 - {quality_data['category']}")
                    print(f"      Trend: {quality_data['trend']}")
                    
                    # Raw Data
                    print("\n📊 RAW SENSOR DATA:")
                    if pms_data:
                        print(f"   PM1.0: {pms_data[0]:3d}  PM2.5: {pms_data[1]:3d}  PM10: {pms_data[2]:3d} µg/m³")
                    print(f"   MQ135: {mq135_voltage:.3f} V")
                    
                    print("\n" + "="*100 + "\n")
                    last_print_time = current_time
                
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n=== Shutting down gracefully... ===")
        
        # Summary statistics
        if threat_history:
            threats = [t['overall_threat'] for t in threat_history]
            print(f"\n📈 THREAT SUMMARY:")
            print(f"   Average: {np.mean(threats):.1f}")
            print(f"   Maximum: {max(threats):.1f}")
            print(f"   Minimum: {min(threats):.1f}")
            print(f"   Volatility: {np.std(threats):.1f}")
            
            # Time in each level
            levels = {'LOW': 0, 'MODERATE': 0, 'ELEVATED': 0, 'HIGH': 0, 'CRITICAL': 0}
            for t in threat_history:
                levels[t['level']] = levels.get(t['level'], 0) + 1
            print("\n   Time Distribution:")
            for level, count in levels.items():
                pct = count / len(threat_history) * 100
                print(f"     {level}: {pct:.1f}%")
        
        if quality_scorer.quality_history:
            qualities = list(quality_scorer.quality_history)
            print(f"\n🌿 ENVIRONMENTAL QUALITY:")
            print(f"   Average: {np.mean(qualities):.1f}")
            print(f"   Best: {max(qualities):.1f}")
            print(f"   Worst: {min(qualities):.1f}")
    
    finally:
        # Cleanup
        if pms:
            pms.close()
        if radar_processor and radar_processor.serial_conn:
            radar_processor.serial_conn.close()
        print("\n✓ Cleanup complete. Exiting.")

if __name__ == "__main__":
    main()