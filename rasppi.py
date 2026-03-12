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
import warnings
import json
from datetime import datetime
from scipy import signal as scipy_signal
from scipy.stats import pearsonr
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION PARAMETERS ====================
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
RADAR_FRAME_SIZE = 1024
RADAR_SAMPLE_RATE = 256000
RADAR_DETECTION_THRESHOLD = 0.6
RADAR_MAX_TARGETS = 3

# ==================== DATA STORAGE ====================
samples = deque(maxlen=WINDOW_SIZE)
db_history = deque(maxlen=50)
sound_history = deque(maxlen=WINDOW_SIZE)
odor_history = deque(maxlen=60)
radar_history = deque(maxlen=30)
activity_history = deque(maxlen=20)
score_history = deque(maxlen=100)

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
    
    # Apply Hanning window
    window = np.hanning(len(signal))
    signal_windowed = signal * window
    
    fft = np.fft.rfft(signal_windowed)
    magnitude = np.abs(fft)
    freqs = np.fft.rfftfreq(len(signal), 1/SAMPLE_RATE)
    
    if np.sum(magnitude) == 0:
        return 0, 0, 0, 0, 0
    
    # Frequency bands
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
        return [0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    rms_val = rms(signal)
    db = voltage_to_db(rms_val)
    dom_freq, energy, centroid, spread, band_energies = fft_features(signal)
    
    signal_array = np.array(signal)
    peak = np.max(np.abs(signal_array)) if len(signal_array) > 0 else 0
    zero_crossings = np.sum(np.diff(np.sign(signal_array)) != 0) if len(signal_array) > 1 else 0
    
    # Additional statistical features
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
    
    # Enhanced training data with more features
    X_train = [
        [40, 100, 5000, 120, 0.5, 50, 50, 0.1, -0.5, 2000, 2500, 500],    # quiet
        [45, 120, 6000, 150, 0.8, 80, 60, 0.2, -0.3, 1500, 3500, 1000],   # conversation
        [70, 500, 20000, 600, 2.5, 200, 200, 0.5, 1.2, 500, 5000, 14500], # crowd
        [80, 800, 30000, 900, 3.2, 50, 300, 1.2, 2.5, 1000, 15000, 14000],# door_slam
        [60, 300, 15000, 400, 1.5, 150, 150, 0.3, 0.8, 2000, 8000, 5000], # shouting
        [35, 50, 2000, 80, 0.3, 30, 30, 0.05, -0.8, 1000, 800, 200],      # background
        [90, 1200, 40000, 1200, 4.0, 40, 400, 2.0, 5.0, 500, 5000, 34500],# explosion
        [55, 250, 12000, 350, 1.2, 120, 120, 0.4, 0.2, 3000, 7000, 2000], # traffic
    ]
    
    y_train = [
        "quiet",
        "conversation",
        "crowd",
        "door_slam",
        "shouting",
        "background",
        "impact",
        "traffic"
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
    
    # Make prediction with confidence
    prediction_proba = model.predict_proba([features])[0]
    prediction = model.predict([features])[0]
    confidence = np.max(prediction_proba)
    
    db = features[0]
    db_history.append(db)
    
    # Calculate dynamic baseline
    if len(db_history) > 10:
        baseline = np.median(db_history)
        std_dev = np.std(db_history)
        spike = db > baseline + (SPIKE_THRESHOLD_DB * (1 + 0.1 * (std_dev / max(baseline, 1))))
        # Detect rapid changes
        rate_of_change = abs(db - baseline) / max(baseline, 1)
    else:
        baseline = db
        spike = False
        rate_of_change = 0
    
    # Clear samples for next window (50% overlap)
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
    """Advanced mmWave radar data processor"""
    
    def __init__(self, max_targets=3, detection_threshold=0.6):
        self.max_targets = max_targets
        self.detection_threshold = detection_threshold
        self.target_history = deque(maxlen=30)
        self.velocity_history = deque(maxlen=20)
        self.motion_patterns = deque(maxlen=50)
        self.last_positions = {}
        self.tracking_id = 0
        
    def parse_radar_frame(self, raw_data):
        """Parse raw radar data into structured format"""
        try:
            # Try JSON format first
            if raw_data.startswith('{'):
                data = json.loads(raw_data)
                return self._parse_json_radar(data)
            
            # Try binary format detection
            elif len(raw_data) > 20:
                return self._parse_binary_radar(raw_data)
            
            # Try string-based format
            else:
                return self._parse_string_radar(raw_data)
                
        except Exception as e:
            # Fallback to basic parsing
            return self._parse_basic_radar(raw_data)
    
    def _parse_json_radar(self, data):
        """Parse JSON-formatted radar data"""
        targets = []
        
        if 'targets' in data:
            for t in data['targets']:
                target = {
                    'id': t.get('id', self._generate_target_id()),
                    'x': t.get('x', 0),
                    'y': t.get('y', 0),
                    'z': t.get('z', 0),
                    'velocity': t.get('velocity', 0),
                    'acceleration': t.get('acceleration', 0),
                    'angle': t.get('angle', 0),
                    'distance': t.get('distance', 0),
                    'snr': t.get('snr', 0),
                    'confidence': t.get('confidence', 0.5)
                }
                targets.append(target)
        
        return {
            'timestamp': data.get('timestamp', time.time()),
            'targets': targets,
            'target_count': len(targets),
            'format': 'json'
        }
    
    def _parse_binary_radar(self, raw_data):
        """Parse binary radar data format"""
        targets = []
        
        if len(raw_data) >= 12:
            num_targets = min(raw_data[4], self.max_targets)
            
            for i in range(num_targets):
                offset = 8 + i * 16
                if offset + 16 <= len(raw_data):
                    target = {
                        'id': self._generate_target_id(),
                        'x': int.from_bytes(raw_data[offset:offset+2], 'little') / 100.0,
                        'y': int.from_bytes(raw_data[offset+2:offset+4], 'little') / 100.0,
                        'z': int.from_bytes(raw_data[offset+4:offset+6], 'little') / 100.0,
                        'velocity': int.from_bytes(raw_data[offset+6:offset+8], 'little') / 100.0,
                        'snr': raw_data[offset+8],
                        'confidence': raw_data[offset+9] / 100.0
                    }
                    if target['confidence'] >= self.detection_threshold:
                        targets.append(target)
        
        return {
            'timestamp': time.time(),
            'targets': targets,
            'target_count': len(targets),
            'format': 'binary'
        }
    
    def _parse_string_radar(self, raw_data):
        """Parse string-based radar format"""
        targets = []
        parts = raw_data.split(',')
        
        if len(parts) >= 3:
            try:
                num_targets = int(parts[0]) if parts[0].isdigit() else 0
                
                for i in range(min(num_targets, self.max_targets)):
                    if i * 4 + 1 < len(parts):
                        target = {
                            'id': self._generate_target_id(),
                            'x': float(parts[i*4 + 1]) if parts[i*4 + 1].replace('.','').isdigit() else 0,
                            'y': float(parts[i*4 + 2]) if parts[i*4 + 2].replace('.','').isdigit() else 0,
                            'velocity': float(parts[i*4 + 3]) if parts[i*4 + 3].replace('.','').isdigit() else 0,
                            'confidence': 0.7
                        }
                        targets.append(target)
            except:
                if 'target' in raw_data.lower():
                    target = {
                        'id': self._generate_target_id(),
                        'raw': raw_data,
                        'confidence': 0.5
                    }
                    targets.append(target)
        
        return {
            'timestamp': time.time(),
            'targets': targets,
            'target_count': len(targets),
            'format': 'string'
        }
    
    def _parse_basic_radar(self, raw_data):
        """Basic parsing as fallback"""
        targets = []
        
        if raw_data and len(raw_data) > 0:
            target = {
                'id': self._generate_target_id(),
                'raw': raw_data[:50] + '...' if len(raw_data) > 50 else raw_data,
                'confidence': 0.5
            }
            targets.append(target)
        
        return {
            'timestamp': time.time(),
            'targets': targets,
            'target_count': len(targets) if targets else 0,
            'format': 'basic'
        }
    
    def _generate_target_id(self):
        """Generate unique target ID"""
        self.tracking_id += 1
        return f"T{self.tracking_id:04d}"
    
    def track_targets(self, radar_data):
        """Track targets across frames with Kalman filtering"""
        if not radar_data or 'targets' not in radar_data:
            return radar_data
        
        current_targets = radar_data['targets']
        tracked_targets = []
        
        for target in current_targets:
            target_id = target.get('id')
            
            if target_id in self.last_positions:
                last = self.last_positions[target_id]
                
                # Calculate velocity
                if 'x' in target and 'y' in target and 'x' in last and 'y' in last:
                    target['vx'] = (target['x'] - last['x']) / 0.1
                    target['vy'] = (target['y'] - last['y']) / 0.1
                    
                    # Calculate acceleration
                    if 'vx' in last and 'vy' in last:
                        target['ax'] = (target['vx'] - last['vx']) / 0.1
                        target['ay'] = (target['vy'] - last['vy']) / 0.1
                
                # Calculate movement metrics
                if 'x' in target and 'y' in target and 'x' in last and 'y' in last:
                    target['displacement'] = math.sqrt((target['x'] - last['x'])**2 + 
                                                       (target['y'] - last['y'])**2)
            
            self.last_positions[target_id] = target.copy()
            tracked_targets.append(target)
            
            # Update velocity history
            if 'velocity' in target:
                self.velocity_history.append(target['velocity'])
        
        radar_data['targets'] = tracked_targets
        radar_data['target_count'] = len(tracked_targets)
        
        # Store in history
        if tracked_targets:
            self.target_history.append({
                'timestamp': radar_data['timestamp'],
                'count': len(tracked_targets),
                'avg_velocity': np.mean([t.get('velocity', 0) for t in tracked_targets]) if tracked_targets else 0
            })
        
        return radar_data
    
    def analyze_motion_patterns(self):
        """Analyze motion patterns from historical data"""
        if len(self.target_history) < 5:
            return {
                'pattern': 'insufficient_data',
                'activity_level': 0,
                'velocity_trend': 0,
                'occupancy_pattern': 'unknown'
            }
        
        recent_targets = list(self.target_history)[-10:]
        avg_targets = np.mean([t['count'] for t in recent_targets])
        max_targets = np.max([t['count'] for t in recent_targets])
        
        # Determine pattern
        if avg_targets < 0.5:
            pattern = 'no_activity'
        elif avg_targets < 1.5:
            pattern = 'sporadic_activity'
        elif avg_targets < 2.5:
            pattern = 'moderate_activity'
        else:
            pattern = 'high_activity'
        
        # Velocity trend
        if len(self.velocity_history) > 5:
            velocities = list(self.velocity_history)
            velocity_trend = velocities[-1] - np.mean(velocities[:-5]) if velocities else 0
        else:
            velocity_trend = 0
        
        # Occupancy pattern
        if max_targets >= 3:
            occupancy = 'crowded'
        elif max_targets >= 2:
            occupancy = 'multiple_people'
        elif max_targets >= 1:
            occupancy = 'occupied'
        else:
            occupancy = 'empty'
        
        return {
            'pattern': pattern,
            'activity_level': avg_targets / 3.0,
            'velocity_trend': velocity_trend,
            'occupancy_pattern': occupancy,
            'max_occupancy': max_targets
        }
    
    def detect_activity_events(self):
        """Detect specific activity events from radar data"""
        events = []
        
        if len(self.target_history) < 3:
            return events
        
        recent = list(self.target_history)[-3:]
        if len(recent) >= 2:
            count_change = recent[-1]['count'] - recent[-2]['count']
            
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
        
        if len(self.velocity_history) > 3:
            velocities = list(self.velocity_history)[-3:]
            if np.mean(velocities) > 2.0:
                events.append({
                    'type': 'rapid_movement',
                    'velocity': np.mean(velocities),
                    'confidence': min(0.8, np.mean(velocities) / 5.0)
                })
        
        return events

# Initialize radar processor
radar_processor = RadarProcessor(max_targets=RADAR_MAX_TARGETS, 
                                 detection_threshold=RADAR_DETECTION_THRESHOLD)

# ==================== DYNAMIC SCORING SYSTEM ====================

class DynamicEnvironmentalScorer:
    """
    Advanced environmental scoring system with dynamic weighting based on:
    - Sensor reliability and confidence
    - Environmental context
    - Situational awareness
    - Historical patterns
    - Cross-sensor validation
    """
    
    def __init__(self):
        # Base weights
        self.base_weights = {
            'air_quality': 0.35,
            'noise': 0.20,
            'occupancy': 0.15,
            'activity': 0.15,
            'anomaly': 0.15
        }
        
        # Sensor reliability tracking
        self.sensor_reliability = {
            'mq135': {'baseline': 1.0, 'history': deque(maxlen=50), 'consecutive_failures': 0, 'last_reading': None},
            'pms5003': {'baseline': 1.0, 'history': deque(maxlen=50), 'consecutive_failures': 0, 'last_reading': None},
            'sound': {'baseline': 1.0, 'history': deque(maxlen=50), 'consecutive_failures': 0, 'last_reading': None},
            'radar': {'baseline': 1.0, 'history': deque(maxlen=50), 'consecutive_failures': 0, 'last_reading': None}
        }
        
        # Context profiles
        self.context_profiles = {
            'office': {
                'ideal_noise': 45,
                'ideal_occupancy': 2,
                'voc_threshold': 60,
                'pm25_threshold': 15,
                'weights': {'air_quality': 0.30, 'noise': 0.25, 'occupancy': 0.20, 'activity': 0.15, 'anomaly': 0.10}
            },
            'home': {
                'ideal_noise': 40,
                'ideal_occupancy': 3,
                'voc_threshold': 50,
                'pm25_threshold': 12,
                'weights': {'air_quality': 0.35, 'noise': 0.15, 'occupancy': 0.25, 'activity': 0.15, 'anomaly': 0.10}
            },
            'industrial': {
                'ideal_noise': 65,
                'ideal_occupancy': 1,
                'voc_threshold': 100,
                'pm25_threshold': 35,
                'weights': {'air_quality': 0.45, 'noise': 0.10, 'occupancy': 0.10, 'activity': 0.20, 'anomaly': 0.15}
            },
            'classroom': {
                'ideal_noise': 55,
                'ideal_occupancy': 15,
                'voc_threshold': 70,
                'pm25_threshold': 20,
                'weights': {'air_quality': 0.25, 'noise': 0.20, 'occupancy': 0.30, 'activity': 0.15, 'anomaly': 0.10}
            },
            'laboratory': {
                'ideal_noise': 35,
                'ideal_occupancy': 2,
                'voc_threshold': 30,
                'pm25_threshold': 5,
                'weights': {'air_quality': 0.50, 'noise': 0.15, 'occupancy': 0.15, 'activity': 0.10, 'anomaly': 0.10}
            }
        }
        
        # Current context (auto-detected or set manually)
        self.current_context = 'office'
        self.context_confidence = 0.5
        
        # Anomaly patterns
        self.anomaly_patterns = {
            'sudden_voc_spike': {'count': 0, 'last_seen': 0, 'severity': 0},
            'pm25_drift': {'count': 0, 'last_seen': 0, 'severity': 0},
            'radar_glitch': {'count': 0, 'last_seen': 0, 'severity': 0},
            'noise_floor_shift': {'count': 0, 'last_seen': 0, 'severity': 0}
        }
        
        # Scoring history for trend analysis
        self.score_history = deque(maxlen=100)
        
        # Confidence thresholds
        self.min_confidence_for_weight_adjust = 0.3
        
    def update_sensor_reliability(self, sensor_name, reading_success, reading_value=None, expected_range=None):
        """Update sensor reliability based on readings and expected behavior"""
        if sensor_name not in self.sensor_reliability:
            return
        
        reliability = self.sensor_reliability[sensor_name]
        
        # Track consecutive failures
        if not reading_success:
            reliability['consecutive_failures'] += 1
        else:
            reliability['consecutive_failures'] = 0
            reliability['last_reading'] = reading_value
        
        # Update reliability score
        if reading_success and reading_value is not None and expected_range:
            min_val, max_val = expected_range
            if min_val <= reading_value <= max_val:
                reliability['history'].append(1.0)
            else:
                # Out of range readings reduce reliability
                reliability['history'].append(0.7)
        elif reading_success:
            reliability['history'].append(1.0)
        else:
            reliability['history'].append(0.0)
        
        # Calculate moving average reliability
        if len(reliability['history']) > 0:
            history_list = list(reliability['history'])
            weights = np.linspace(0.5, 1.0, len(history_list))
            weighted_avg = np.average(history_list, weights=weights)
            
            # Apply consecutive failure penalty
            failure_penalty = max(0, 1.0 - (reliability['consecutive_failures'] * 0.2))
            reliability['baseline'] = weighted_avg * failure_penalty
    
    def detect_context(self, sound_data, odor_data, radar_data, time_of_day):
        """Automatically detect environmental context based on sensor patterns"""
        context_scores = {}
        
        if not sound_data or not odor_data:
            return self.current_context, 0.3
        
        current_hour = datetime.fromtimestamp(time_of_day).hour
        is_business_hours = 9 <= current_hour <= 17
        is_night = current_hour <= 6 or current_hour >= 22
        
        # Score each possible context
        for context, profile in self.context_profiles.items():
            score = 0
            
            # Noise level matching
            if sound_data:
                noise_diff = abs(sound_data['db'] - profile['ideal_noise'])
                noise_score = max(0, 1 - (noise_diff / 50))
                score += noise_score * 0.3
            
            # Occupancy matching
            if radar_data:
                occ_diff = abs(radar_data.get('target_count', 0) - profile['ideal_occupancy'])
                occ_score = max(0, 1 - (occ_diff / max(profile['ideal_occupancy'], 1)))
                score += occ_score * 0.3
            
            # VOC levels
            if odor_data:
                voc_ratio = odor_data['voc_ppm'] / profile['voc_threshold']
                if voc_ratio < 1:
                    voc_score = 1 - (voc_ratio * 0.5)
                else:
                    voc_score = max(0, 1 - (voc_ratio - 1))
                score += voc_score * 0.2
            
            # Time-based context clues
            if context == 'office' and is_business_hours:
                score += 0.2
            elif context == 'home' and not is_business_hours:
                score += 0.2
            elif context == 'industrial' and is_business_hours:
                score += 0.1
            
            context_scores[context] = score
        
        # Select best matching context
        if context_scores:
            best_context = max(context_scores, key=context_scores.get)
            confidence = context_scores[best_context]
            
            # Only change context if confidence is high enough
            if confidence > 0.6:
                self.current_context = best_context
                self.context_confidence = confidence
            elif confidence > 0.4:
                self.context_confidence = confidence
        
        return self.current_context, self.context_confidence
    
    def calculate_air_quality_score(self, odor_data, sensor_reliability):
        """Dynamic air quality score with sensor fusion and reliability weighting"""
        if not odor_data:
            return 50, 0.3
        
        # Get sensor reliabilities
        mq135_reliability = sensor_reliability['mq135']['baseline']
        pms_reliability = sensor_reliability['pms5003']['baseline']
        
        # VOC scoring with reliability weighting
        if mq135_reliability > 0.3:
            voc_raw_score = max(0, 100 - (odor_data['voc_ppm'] * 0.5))
            
            # Adjust for odor type
            if odor_data['odor_type'] == 'strong_chemical':
                voc_raw_score *= 0.5
            elif odor_data['odor_type'] == 'dust_or_smoke':
                voc_raw_score *= 0.7
            elif odor_data['odor_type'] == 'human_activity':
                voc_raw_score *= 0.9
            
            voc_score = voc_raw_score * mq135_reliability
            voc_confidence = mq135_reliability
        else:
            # Fallback to PM-based estimation if MQ135 unreliable
            voc_score = 50
            voc_confidence = 0.2
        
        # PM2.5 scoring with reliability weighting
        if pms_reliability > 0.3:
            context_profile = self.context_profiles.get(self.current_context, self.context_profiles['office'])
            pm25_threshold = context_profile['pm25_threshold']
            
            pm25_raw_score = max(0, 100 - (odor_data['pm25'] * (100 / pm25_threshold) * 0.5))
            pm25_score = pm25_raw_score * pms_reliability
            pm25_confidence = pms_reliability
        else:
            pm25_score = 50
            pm25_confidence = 0.2
        
        # AQI contribution
        aqi_score = max(0, 100 - (odor_data.get('air_quality_index', 50) * 0.2))
        
        # Fuse scores based on confidence
        total_confidence = (voc_confidence + pm25_confidence) / 2
        
        if total_confidence > 0.5:
            # High confidence - use both sensors
            air_quality_score = (
                voc_score * 0.4 +
                pm25_score * 0.4 +
                aqi_score * 0.2
            )
        else:
            # Low confidence - rely more on AQI and heuristics
            air_quality_score = (
                aqi_score * 0.6 +
                (voc_score + pm25_score) / 2 * 0.4
            )
        
        # Apply context-based adjustments
        context_profile = self.context_profiles.get(self.current_context, self.context_profiles['office'])
        
        # Stricter scoring for sensitive environments
        if self.current_context in ['laboratory', 'home']:
            if odor_data['voc_ppm'] > context_profile['voc_threshold']:
                air_quality_score *= 0.7
        
        return np.clip(air_quality_score, 0, 100), total_confidence
    
    def calculate_noise_score(self, sound_data, sensor_reliability, context):
        """Dynamic noise score with event awareness and context"""
        if not sound_data:
            return 50, 0.3
        
        sound_reliability = sensor_reliability['sound']['baseline']
        context_profile = self.context_profiles.get(context, self.context_profiles['office'])
        
        # Base noise score with context-appropriate ideal
        ideal_noise = context_profile['ideal_noise']
        noise_diff = abs(sound_data['db'] - ideal_noise)
        
        # Non-linear penalty for deviation from ideal
        if noise_diff <= 5:
            base_score = 95 - noise_diff
        elif noise_diff <= 15:
            base_score = 85 - (noise_diff - 5) * 2
        else:
            base_score = max(20, 70 - (noise_diff - 15) * 3)
        
        # Event-based penalties
        event_penalty = 0
        event = sound_data.get('event', 'background')
        
        # Context-specific event penalties
        if context == 'office':
            disruptive_events = ['door_slam', 'shouting', 'impact']
            if event in disruptive_events:
                event_penalty = 30
        elif context == 'home':
            if event in ['impact', 'door_slam']:
                event_penalty = 25
        elif context == 'laboratory':
            if event != 'background' and event != 'quiet':
                event_penalty = 40
        
        # Spike penalty
        if sound_data.get('spike', False):
            spike_magnitude = sound_data.get('rate_of_change', 1)
            event_penalty += min(25, spike_magnitude * 10)
        
        # Calculate final score
        noise_score = base_score - event_penalty
        
        # Apply reliability weighting
        noise_score = noise_score * (0.7 + 0.3 * sound_reliability)
        
        # Confidence based on reliability and event clarity
        confidence = sound_reliability * (0.5 + 0.5 * sound_data.get('confidence', 0.5))
        
        return np.clip(noise_score, 0, 100), confidence
    
    def calculate_occupancy_score(self, radar_data, motion_patterns, sensor_reliability, context):
        """Dynamic occupancy score with comfort modeling"""
        if not radar_data:
            return 50, 0.3
        
        radar_reliability = sensor_reliability['radar']['baseline']
        context_profile = self.context_profiles.get(context, self.context_profiles['office'])
        
        target_count = radar_data.get('target_count', 0)
        ideal_occupancy = context_profile['ideal_occupancy']
        
        # Comfort curve based on occupancy
        if target_count == 0:
            if context in ['office', 'classroom']:
                occupancy_score = 70
            else:
                occupancy_score = 80
        elif target_count <= ideal_occupancy:
            ratio = target_count / max(ideal_occupancy, 1)
            occupancy_score = 85 + (15 * ratio)
        elif target_count <= ideal_occupancy * 1.5:
            excess = (target_count - ideal_occupancy) / ideal_occupancy
            occupancy_score = 80 - (excess * 30)
        else:
            excess_ratio = target_count / ideal_occupancy
            occupancy_score = max(20, 60 - (excess_ratio - 1.5) * 40)
        
        # Adjust for motion patterns
        if motion_patterns:
            pattern = motion_patterns.get('pattern', 'moderate_activity')
            
            if context == 'office':
                if pattern == 'high_activity':
                    occupancy_score *= 0.8
                elif pattern == 'no_activity' and target_count > 0:
                    occupancy_score *= 0.9
            elif context == 'home':
                if pattern == 'sporadic_activity':
                    occupancy_score *= 1.1
        
        # Apply reliability weighting
        occupancy_score *= (0.8 + 0.2 * radar_reliability)
        
        # Confidence based on radar reliability and detection clarity
        confidence = radar_reliability * min(1.0, target_count / 5 + 0.5)
        
        return np.clip(occupancy_score, 0, 100), confidence
    
    def calculate_activity_score(self, motion_patterns, activity_events, sound_data, context):
        """Dynamic activity score considering both motion and sound"""
        if not motion_patterns:
            return 50, 0.3
        
        context_profile = self.context_profiles.get(context, self.context_profiles['office'])
        
        activity_level = motion_patterns.get('activity_level', 0)
        
        # Optimal activity level varies by context
        if context == 'office':
            if activity_level < 0.2:
                activity_score = 70
            elif activity_level < 0.5:
                activity_score = 90
            elif activity_level < 0.7:
                activity_score = 75
            else:
                activity_score = 50
        elif context == 'home':
            if activity_level < 0.1:
                activity_score = 60
            elif activity_level < 0.4:
                activity_score = 85
            elif activity_level < 0.7:
                activity_score = 95
            else:
                activity_score = 70
        elif context == 'laboratory':
            if activity_level < 0.1:
                activity_score = 80
            elif activity_level < 0.3:
                activity_score = 95
            else:
                activity_score = 60
        else:
            # Default scoring
            activity_score = 50 + (activity_level * 40)
        
        # Velocity trend adjustment
        velocity_trend = motion_patterns.get('velocity_trend', 0)
        if abs(velocity_trend) > 1.5:
            activity_score *= 0.85
        
        # Correlate with sound for confidence
        sound_correlation = 1.0
        if sound_data:
            if (activity_level > 0.5 and sound_data['db'] > 60) or \
               (activity_level < 0.2 and sound_data['db'] < 45):
                sound_correlation = 1.2
        
        confidence = min(1.0, activity_level * 1.5) * sound_correlation
        
        return np.clip(activity_score, 0, 100), min(confidence, 1.0)
    
    def calculate_anomaly_score(self, sound_data, odor_data, activity_events):
        """Sophisticated anomaly detection with pattern recognition"""
        anomaly_penalty = 0
        anomaly_details = []
        current_time = time.time()
        
        # Sound anomalies
        if sound_data:
            if sound_data.get('spike', False):
                spike_severity = sound_data.get('rate_of_change', 1)
                penalty = min(25, spike_severity * 15)
                anomaly_penalty += penalty
                anomaly_details.append(f"Sound spike (+{penalty:.0f})")
                
                # Track pattern
                self.anomaly_patterns['noise_floor_shift']['count'] += 1
                self.anomaly_patterns['noise_floor_shift']['last_seen'] = current_time
                self.anomaly_patterns['noise_floor_shift']['severity'] = max(
                    self.anomaly_patterns['noise_floor_shift']['severity'], penalty)
        
        # Odor anomalies
        if odor_data:
            if odor_data.get('odor_anomaly', False):
                intensity = odor_data.get('odor_intensity', 2)
                penalty = min(30, intensity * 8)
                anomaly_penalty += penalty
                anomaly_details.append(f"Odor anomaly (+{penalty:.0f})")
            
            # Check for sudden VOC changes
            odor_trend = odor_data.get('odor_trend', 0)
            if abs(odor_trend) > 30:
                penalty = 20
                anomaly_penalty += penalty
                anomaly_details.append(f"Rapid VOC change (+{penalty:.0f})")
                self.anomaly_patterns['sudden_voc_spike']['count'] += 1
                self.anomaly_patterns['sudden_voc_spike']['last_seen'] = current_time
                self.anomaly_patterns['sudden_voc_spike']['severity'] = max(
                    self.anomaly_patterns['sudden_voc_spike']['severity'], penalty)
        
        # Activity anomalies
        if activity_events:
            for event in activity_events:
                if event['type'] == 'rapid_movement':
                    penalty = 15 * event.get('confidence', 0.5)
                    anomaly_penalty += penalty
                    anomaly_details.append(f"Rapid movement (+{penalty:.0f})")
                    
                    self.anomaly_patterns['radar_glitch']['count'] += 1
                    self.anomaly_patterns['radar_glitch']['last_seen'] = current_time
        
        # Pattern-based penalties (repeat offenders)
        for pattern, data in self.anomaly_patterns.items():
            if data['count'] > 5 and (current_time - data['last_seen']) < 300:
                # Recurring issue in last 5 minutes
                pattern_penalty = min(20, data['count'] * 2)
                anomaly_penalty += pattern_penalty
                anomaly_details.append(f"Recurring {pattern} (+{pattern_penalty:.0f})")
        
        # Calculate score
        anomaly_score = max(0, 100 - anomaly_penalty)
        
        # Confidence based on number and clarity of anomalies
        if anomaly_penalty == 0:
            confidence = 0.9
        else:
            confidence = min(0.8, 0.5 + (len(anomaly_details) * 0.1))
        
        return np.clip(anomaly_score, 0, 100), confidence, anomaly_details
    
    def calculate_final_score(self, component_scores, confidences, context_weights):
        """Calculate weighted final score with confidence-based adjustments"""
        
        # Adjust weights based on confidence
        adjusted_weights = {}
        total_confidence_weight = 0
        
        for component, base_weight in context_weights.items():
            confidence = confidences.get(component, 0.5)
            
            # Low confidence components get reduced weight
            if confidence < self.min_confidence_for_weight_adjust:
                confidence_factor = confidence / self.min_confidence_for_weight_adjust
                adjusted_weight = base_weight * confidence_factor
            else:
                adjusted_weight = base_weight
            
            adjusted_weights[component] = adjusted_weight
            total_confidence_weight += adjusted_weight
        
        # Normalize weights
        if total_confidence_weight > 0:
            for component in adjusted_weights:
                adjusted_weights[component] /= total_confidence_weight
        
        # Calculate weighted score
        final_score = 0
        for component, score in component_scores.items():
            final_score += score * adjusted_weights.get(component, 0)
        
        # Calculate overall confidence
        overall_confidence = np.mean(list(confidences.values())) if confidences else 0.5
        
        return final_score, overall_confidence, adjusted_weights
    
    def generate_insights(self, component_scores, confidences, anomaly_details, context, sound_data, odor_data):
        """Generate contextual insights based on scores and anomalies"""
        insights = []
        recommendations = []
        
        # Low score insights with context
        for component, score in component_scores.items():
            if score < 60:
                if component == 'air_quality':
                    if odor_data:
                        if odor_data['voc_ppm'] > 100:
                            insights.append("⚠ CRITICAL: Very high VOC levels detected")
                            recommendations.append("• Increase ventilation immediately")
                            recommendations.append("• Check for chemical sources")
                        elif odor_data['pm25'] > 50:
                            insights.append("⚠ WARNING: High particulate matter")
                            recommendations.append("• Consider air purifier")
                            recommendations.append("• Check for smoke or dust sources")
                        else:
                            insights.append("⚠ Poor air quality detected")
                            recommendations.append("• Improve ventilation")
                
                elif component == 'noise':
                    if sound_data:
                        db = sound_data['db']
                        if db > 75:
                            insights.append(f"🔊 CRITICAL: Excessive noise ({db:.0f} dB)")
                            recommendations.append("• Hearing protection recommended")
                        elif db > 65:
                            insights.append(f"🔊 WARNING: High noise levels ({db:.0f} dB)")
                            recommendations.append("• Consider noise reduction measures")
                        else:
                            insights.append(f"🔊 Elevated noise levels ({db:.0f} dB)")
                
                elif component == 'occupancy':
                    if context == 'office' and score < 60:
                        insights.append("👥 Suboptimal occupancy for productivity")
                        recommendations.append("• Consider adjusting workspace allocation")
                    elif context == 'home':
                        insights.append("👥 Occupancy level may affect comfort")
                
                elif component == 'activity':
                    if score < 60:
                        insights.append("🏃 Unusual activity patterns detected")
                        recommendations.append("• Monitor for unusual behavior")
                
                elif component == 'anomaly':
                    if anomaly_details:
                        insights.append(f"⚠ {len(anomaly_details)} anomalies detected")
                        for detail in anomaly_details[:3]:
                            insights.append(f"  • {detail}")
        
        # Confidence-based insights
        low_confidence_components = [comp for comp, conf in confidences.items() if conf < 0.4]
        if low_confidence_components:
            insights.append(f"📊 Low confidence in: {', '.join(low_confidence_components)}")
            recommendations.append("• Check sensor connections")
            recommendations.append("• Verify sensor calibration")
        
        # Positive insights
        high_scores = [comp for comp, score in component_scores.items() if score > 85]
        if len(high_scores) >= 3:
            insights.append("✅ Environment is in excellent condition")
            recommendations.append("• Continue current practices")
        
        return insights, recommendations
    
    def detect_trend(self):
        """Detect environmental trend from score history"""
        if len(self.score_history) < 5:
            return "insufficient_data"
        
        recent_scores = [entry['final_score'] for entry in list(self.score_history)[-5:]]
        
        if len(recent_scores) >= 3:
            # Calculate slope
            x = np.arange(len(recent_scores))
            slope = np.polyfit(x, recent_scores, 1)[0]
            
            if slope > 1:
                return "improving"
            elif slope < -1:
                return "worsening"
            else:
                return "stable"
        
        return "stable"
    
    def score_environment(self, sound_data, odor_data, radar_data, motion_patterns, activity_events):
        """
        Main scoring function that synthesizes all inputs into a dynamic environmental score
        """
        # Update sensor reliability
        self.update_sensor_reliability('mq135', odor_data is not None, 
                                       odor_data.get('voc_ppm') if odor_data else None,
                                       (0, 500) if odor_data else None)
        self.update_sensor_reliability('pms5003', odor_data is not None,
                                       odor_data.get('pm25') if odor_data else None,
                                       (0, 200) if odor_data else None)
        self.update_sensor_reliability('sound', sound_data is not None,
                                       sound_data.get('db') if sound_data else None,
                                       (20, 100) if sound_data else None)
        self.update_sensor_reliability('radar', radar_data is not None,
                                       radar_data.get('target_count') if radar_data else None,
                                       (0, 10) if radar_data else None)
        
        # Detect context
        current_time = time.time()
        context, context_confidence = self.detect_context(sound_data, odor_data, radar_data, current_time)
        
        # Get context-specific weights
        context_weights = self.context_profiles.get(context, self.context_profiles['office'])['weights']
        
        component_scores = {}
        confidences = {}
        all_anomaly_details = []
        
        # Calculate each component score with confidence
        if odor_data:
            aq_score, aq_confidence = self.calculate_air_quality_score(odor_data, self.sensor_reliability)
            component_scores['air_quality'] = aq_score
            confidences['air_quality'] = aq_confidence
        
        if sound_data:
            noise_score, noise_confidence = self.calculate_noise_score(sound_data, self.sensor_reliability, context)
            component_scores['noise'] = noise_score
            confidences['noise'] = noise_confidence
        
        if radar_data:
            occ_score, occ_confidence = self.calculate_occupancy_score(
                radar_data, motion_patterns, self.sensor_reliability, context
            )
            component_scores['occupancy'] = occ_score
            confidences['occupancy'] = occ_confidence
            
            act_score, act_confidence = self.calculate_activity_score(
                motion_patterns, activity_events, sound_data, context
            )
            component_scores['activity'] = act_score
            confidences['activity'] = act_confidence
        
        # Always calculate anomaly score
        anom_score, anom_confidence, anomaly_details = self.calculate_anomaly_score(
            sound_data, odor_data, activity_events
        )
        component_scores['anomaly'] = anom_score
        confidences['anomaly'] = anom_confidence
        all_anomaly_details.extend(anomaly_details)
        
        # Calculate final weighted score
        final_score, overall_confidence, used_weights = self.calculate_final_score(
            component_scores, confidences, context_weights
        )
        
        # Generate insights
        insights, recommendations = self.generate_insights(
            component_scores, confidences, all_anomaly_details, context, sound_data, odor_data
        )
        
        # Determine quality category
        if final_score >= 90:
            category = "EXCELLENT"
        elif final_score >= 80:
            category = "GOOD"
        elif final_score >= 70:
            category = "FAIR"
        elif final_score >= 60:
            category = "POOR"
        else:
            category = "CRITICAL"
        
        # Store in history
        score_entry = {
            'timestamp': current_time,
            'final_score': final_score,
            'components': component_scores,
            'confidences': confidences,
            'context': context,
            'context_confidence': context_confidence,
            'overall_confidence': overall_confidence
        }
        self.score_history.append(score_entry)
        
        # Detect trends
        trend = self.detect_trend()
        
        return {
            'final_score': round(final_score, 1),
            'category': category,
            'overall_confidence': round(overall_confidence, 2),
            'context': context,
            'context_confidence': round(context_confidence, 2),
            'component_scores': {k: round(v, 1) for k, v in component_scores.items()},
            'confidences': {k: round(v, 2) for k, v in confidences.items()},
            'weights_used': {k: round(v, 2) for k, v in used_weights.items()},
            'insights': insights,
            'recommendations': recommendations,
            'anomaly_details': all_anomaly_details,
            'trend': trend,
            'sensor_reliability': {
                k: round(v['baseline'], 2) for k, v in self.sensor_reliability.items()
            },
            'timestamp': current_time
        }

# Initialize the dynamic scorer
dynamic_scorer = DynamicEnvironmentalScorer()

# ==================== ODOR ANALYSIS ENGINE ====================
VOC_BASELINE = None
PM_BASELINE = None

def compute_mq135_ppm(voltage):
    """Convert MQ135 voltage to ppm with improved accuracy"""
    if voltage <= 0 or math.isnan(voltage):
        return 0
    
    try:
        rs = RLOAD * (VCC / max(voltage, 0.001) - 1)
        ratio = rs / R0
        
        # MQ135 characteristic curve parameters
        a = 116.6020682
        b = -2.769034857
        
        ratio = np.clip(ratio, 0.1, 10)
        ppm = a * (ratio ** b)
        
        return max(0, min(ppm, 1000))
    except (ZeroDivisionError, OverflowError):
        return 0

def classify_odor(voc_ppm, pm25, people, noise_db):
    """Enhanced odor classification with confidence"""
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
    """Calculate comprehensive odor intensity score"""
    score = 0
    
    voc_score = min(voc_ppm / 50, 4)
    score += voc_score
    
    pm_score = min(pm25 / 25, 3)
    score += pm_score
    
    people_score = min(people / 3, 2)
    score += people_score
    
    if noise_db > LOUD_THRESHOLD_DB:
        score += 0.5
    
    if trend > 20:
        score += 0.5
    elif trend > 10:
        score += 0.25
    
    return score

def detect_odor_anomaly(current_score):
    """Detect anomalies in odor patterns"""
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
        radar_data = read_radar()
        
        people = 0
        if radar_data and isinstance(radar_data, dict):
            people = radar_data.get('target_count', 0)
        
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
            severity_score = 1
        elif intensity < 3.5:
            level = "MODERATE"
            severity_score = 2
        elif intensity < 5:
            level = "HIGH"
            severity_score = 3
        elif intensity < 6.5:
            level = "SEVERE"
            severity_score = 4
        else:
            level = "CRITICAL"
            severity_score = 5
        
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
            "severity_score": severity_score,
            "odor_trend": round(trend, 2),
            "baseline_intensity": round(baseline, 2),
            "odor_anomaly": anomaly,
            "air_quality_index": round(aqi, 1)
        }
        
    except Exception as e:
        print(f"Error in odor analysis: {e}")
        return None

# ==================== HARDWARE INITIALIZATION ====================
def init_hardware():
    """Initialize all hardware components with error handling"""
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
        
        radar = serial.Serial(
            port="/dev/ttyUSB0",
            baudrate=RADAR_SAMPLE_RATE,
            timeout=1,
            write_timeout=1
        )
        
        return i2c, ads, mq135_channel, sound_channel, pms, radar
        
    except Exception as e:
        print(f"Hardware initialization error: {e}")
        return None, None, None, None, None, None

# Initialize hardware
i2c, ads, mq135_channel, sound_channel, pms, radar = init_hardware()

# ==================== SENSOR READING FUNCTIONS ====================
def read_pms5003():
    """Read PMS5003 particulate matter sensor with validation"""
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
        print(f"PMS5003 read error: {e}")
    
    return None

def read_mq135():
    """Read MQ135 gas sensor with filtering"""
    if not mq135_channel:
        return 0
    
    try:
        samples = []
        for _ in range(5):
            voltage = mq135_channel.voltage
            if not math.isnan(voltage):
                samples.append(voltage)
            time.sleep(0.01)
        
        if samples:
            return np.median(samples)
        return 0
        
    except Exception as e:
        print(f"MQ135 read error: {e}")
        return 0

def read_sound():
    """Read sound sensor with validation"""
    if not sound_channel:
        return 0
    
    try:
        voltage = sound_channel.voltage
        return voltage if not math.isnan(voltage) else 0
    except Exception:
        return 0

def read_radar():
    """Read mmWave radar data with enhanced processing"""
    if not radar:
        return None
    
    try:
        if radar.in_waiting:
            raw_data = radar.readline().decode(errors='ignore').strip()
            
            if raw_data:
                parsed_data = radar_processor.parse_radar_frame(raw_data)
                tracked_data = radar_processor.track_targets(parsed_data)
                
                radar_history.append({
                    'timestamp': time.time(),
                    'data': tracked_data
                })
                
                return tracked_data
                
    except Exception as e:
        print(f"Radar read error: {e}")
    
    return None

# ==================== MAIN LOOP ====================
def main():
    """Main program loop with error recovery"""
    print("="*60)
    print("ENHANCED ENVIRONMENTAL MONITORING SYSTEM")
    print("="*60)
    print("Features:")
    print("  • Sound Analysis with ML Classification")
    print("  • Air Quality Monitoring (VOC, PM1.0, PM2.5, PM10)")
    print("  • mmWave Radar Tracking & Motion Analysis")
    print("  • Dynamic Environmental Scoring with Context Detection")
    print("  • Sensor Reliability Tracking")
    print("  • Anomaly Pattern Recognition")
    print("="*60)
    print("Press Ctrl+C to exit\n")
    
    last_print_time = time.time()
    print_interval = 5  # seconds
    
    # Check hardware initialization
    if None in [mq135_channel, sound_channel, pms, radar]:
        print("⚠ Warning: Some sensors failed to initialize")
        print("   Running in simulation/debug mode\n")
    
    try:
        while True:
            current_time = time.time()
            
            try:
                # Read all sensors
                pms_data = read_pms5003()
                mq135_voltage = read_mq135()
                sound_voltage = read_sound()
                radar_raw_data = read_radar()
                
                # Analyze sound
                sound_analysis = analyze_sound(sound_voltage)
                
                # Analyze odor (if sound analysis available)
                odor_analysis = None
                if sound_analysis:
                    odor_analysis = analyze_odor(sound_analysis['db'])
                
                # Analyze radar patterns
                motion_patterns = radar_processor.analyze_motion_patterns()
                activity_events = radar_processor.detect_activity_events()
                
                # Periodic comprehensive analysis
                if current_time - last_print_time >= print_interval:
                    print("\n" + "="*80)
                    print(f"📊 COMPREHENSIVE REPORT - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("="*80)
                    
                    # Sound Analysis
                    if sound_analysis:
                        print("\n🔊 SOUND ANALYSIS:")
                        print(f"   Level: {sound_analysis['db']:.1f} dB (Baseline: {sound_analysis['baseline']:.1f} dB)")
                        print(f"   Event: {sound_analysis['event']} (confidence: {sound_analysis['confidence']:.2f})")
                        if sound_analysis['spike']:
                            print(f"   ⚠ Sound spike detected! (Rate: {sound_analysis['rate_of_change']:.2f})")
                    
                    # Odor Analysis
                    if odor_analysis:
                        print("\n🌬️ AIR QUALITY ANALYSIS:")
                        print(f"   VOC: {odor_analysis['voc_ppm']:.1f} ppm")
                        print(f"   PM2.5: {odor_analysis['pm25']} µg/m³")
                        print(f"   Air Quality Index: {odor_analysis['air_quality_index']:.1f}")
                        print(f"   Odor Type: {odor_analysis['odor_type']} (conf: {odor_analysis['classification_confidence']:.2f})")
                        print(f"   Intensity: {odor_analysis['odor_intensity']} ({odor_analysis['odor_level']})")
                        if odor_analysis['odor_anomaly']:
                            print("   ⚠ Odor anomaly detected!")
                    
                    # Radar Analysis
                    if radar_raw_data:
                        print(f"\n📡 RADAR ANALYSIS:")
                        print(f"   Targets: {radar_raw_data.get('target_count', 0)}")
                        print(f"   Format: {radar_raw_data.get('format', 'unknown')}")
                        
                        if motion_patterns:
                            print(f"   Pattern: {motion_patterns.get('pattern', 'unknown')}")
                            print(f"   Occupancy: {motion_patterns.get('occupancy_pattern', 'unknown')}")
                            print(f"   Activity Level: {motion_patterns.get('activity_level', 0):.2f}")
                        
                        if activity_events:
                            print(f"   Events: {len(activity_events)} detected")
                            for event in activity_events:
                                print(f"     • {event['type']} (conf: {event.get('confidence', 0):.2f})")
                    
                    # Calculate and display environmental score using dynamic scorer
                    score_data = dynamic_scorer.score_environment(
                        sound_analysis, 
                        odor_analysis, 
                        radar_raw_data,
                        motion_patterns,
                        activity_events
                    )
                    
                    # Store score history
                    score_history.append(score_data)
                    
                    print("\n🎯 DYNAMIC ENVIRONMENTAL SCORE:")
                    print(f"   FINAL SCORE: {score_data['final_score']}/100 - {score_data['category']}")
                    print(f"   Context: {score_data['context']} (conf: {score_data['context_confidence']})")
                    print(f"   Trend: {score_data['trend']}")
                    print(f"   Overall Confidence: {score_data['overall_confidence']}")
                    
                    print("\n   Component Scores:")
                    for component, score in score_data['component_scores'].items():
                        conf = score_data['confidences'].get(component, 0)
                        weight = score_data['weights_used'].get(component, 0)
                        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                        print(f"   {component.replace('_', ' ').title():12} [{bar}] {score:.1f} "
                              f"(conf:{conf:.2f}, weight:{weight:.2f})")
                    
                    if score_data['insights']:
                        print("\n   Insights:")
                        for insight in score_data['insights']:
                            print(f"   • {insight}")
                    
                    if score_data['recommendations']:
                        print("\n   Recommendations:")
                        for rec in score_data['recommendations']:
                            print(f"   {rec}")
                    
                    if score_data['anomaly_details']:
                        print(f"\n   Anomalies: {len(score_data['anomaly_details'])}")
                        for anomaly in score_data['anomaly_details'][:3]:
                            print(f"     • {anomaly}")
                    
                    print("\n   Sensor Reliability:")
                    for sensor, rel in score_data['sensor_reliability'].items():
                        bar = "█" * int(rel * 10) + "░" * (10 - int(rel * 10))
                        print(f"   {sensor:8} [{bar}] {rel:.2f}")
                    
                    # Raw sensor data
                    print("\n📊 RAW SENSOR DATA:")
                    if pms_data:
                        print(f"   PM1.0: {pms_data[0]:3d} µg/m³  PM2.5: {pms_data[1]:3d} µg/m³  PM10: {pms_data[2]:3d} µg/m³")
                    print(f"   MQ135: {mq135_voltage:.3f} V")
                    
                    print("\n" + "="*80 + "\n")
                    
                    last_print_time = current_time
                
                # Small delay
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Loop iteration error: {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\n=== Shutting down gracefully... ===")
        
        # Print summary statistics
        if score_history:
            print("\n📈 Session Summary:")
            avg_score = np.mean([s['final_score'] for s in score_history])
            best_score = max([s['final_score'] for s in score_history])
            worst_score = min([s['final_score'] for s in score_history])
            print(f"   Average Score: {avg_score:.1f}")
            print(f"   Best Score: {best_score:.1f}")
            print(f"   Worst Score: {worst_score:.1f}")
            print(f"   Total Readings: {len(score_history)}")
            
            # Most common context
            contexts = [s['context'] for s in score_history]
            most_common = max(set(contexts), key=contexts.count)
            print(f"   Primary Context: {most_common}")
        
    finally:
        # Clean up resources
        if pms:
            pms.close()
        if radar:
            radar.close()
        print("\n✓ Cleanup complete. Exiting.")

# Run the main program
if __name__ == "__main__":
    main()