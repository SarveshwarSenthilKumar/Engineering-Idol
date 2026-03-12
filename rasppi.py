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
RADAR_FRAME_SIZE = 1024  # Typical frame size for mmWave radar
RADAR_SAMPLE_RATE = 256000
RADAR_DETECTION_THRESHOLD = 0.6
RADAR_MAX_TARGETS = 3

# Scoring Weights
WEIGHTS = {
    'air_quality': 0.35,
    'noise': 0.20,
    'occupancy': 0.15,
    'activity': 0.15,
    'anomaly': 0.15
}

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
            # Example parsing for common mmWave radar formats
            # Adjust based on your specific radar model
            
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
        # Example for TI IWR6843 or similar
        targets = []
        
        if len(raw_data) >= 12:  # Minimum frame size
            # Parse header (example format)
            num_targets = min(raw_data[4], self.max_targets)
            
            for i in range(num_targets):
                offset = 8 + i * 16  # 16 bytes per target
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
            # Try to extract numeric values
            try:
                num_targets = int(parts[0]) if parts[0].isdigit() else 0
                
                for i in range(min(num_targets, self.max_targets)):
                    if i * 4 + 1 < len(parts):
                        target = {
                            'id': self._generate_target_id(),
                            'x': float(parts[i*4 + 1]) if parts[i*4 + 1].replace('.','').isdigit() else 0,
                            'y': float(parts[i*4 + 2]) if parts[i*4 + 2].replace('.','').isdigit() else 0,
                            'velocity': float(parts[i*4 + 3]) if parts[i*4 + 3].replace('.','').isdigit() else 0,
                            'confidence': 0.7  # Default confidence
                        }
                        targets.append(target)
            except:
                # Fallback to basic detection
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
            # Simple target detection based on presence
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
                # Apply simple Kalman-like prediction
                last = self.last_positions[target_id]
                predicted_x = last['x'] + last.get('vx', 0) * 0.1
                predicted_y = last['y'] + last.get('vy', 0) * 0.1
                
                # Calculate velocity
                if 'x' in target and 'y' in target:
                    target['vx'] = (target['x'] - last['x']) / 0.1
                    target['vy'] = (target['y'] - last['y']) / 0.1
                    
                    # Calculate acceleration
                    if 'vx' in last and 'vy' in last:
                        target['ax'] = (target['vx'] - last['vx']) / 0.1
                        target['ay'] = (target['vy'] - last['vy']) / 0.1
                
                # Calculate movement metrics
                if 'x' in target and 'y' in target:
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
        
        # Calculate activity level
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
            'activity_level': avg_targets / 3.0,  # Normalized to 0-1
            'velocity_trend': velocity_trend,
            'occupancy_pattern': occupancy,
            'max_occupancy': max_targets
        }
    
    def detect_activity_events(self):
        """Detect specific activity events from radar data"""
        events = []
        
        if len(self.target_history) < 3:
            return events
        
        # Check for sudden entries/exits
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
        
        # Check for rapid movement
        if len(self.velocity_history) > 3:
            velocities = list(self.velocity_history)[-3:]
            if np.mean(velocities) > 2.0:  # Fast movement threshold
                events.append({
                    'type': 'rapid_movement',
                    'velocity': np.mean(velocities),
                    'confidence': min(0.8, np.mean(velocities) / 5.0)
                })
        
        return events

# Initialize radar processor
radar_processor = RadarProcessor(max_targets=RADAR_MAX_TARGETS, 
                                 detection_threshold=RADAR_DETECTION_THRESHOLD)

# ==================== ENHANCED SCORING SYSTEM ====================
def calculate_environmental_score(sound_data, odor_data, radar_data, radar_analysis, motion_patterns, activity_events):
    """
    Calculate comprehensive environmental quality score from all inputs
    
    Returns:
        dict: Comprehensive scoring with components and final score
    """
    score_components = {}
    
    # 1. Air Quality Score (0-100)
    if odor_data:
        # VOC contribution (inverse relationship - lower is better)
        voc_score = max(0, 100 - (odor_data['voc_ppm'] * 0.5))
        
        # PM2.5 contribution
        pm25_score = max(0, 100 - (odor_data['pm25'] * 1.5))
        
        # AQI contribution
        aqi_score = max(0, 100 - (odor_data['air_quality_index'] * 0.2))
        
        # Combined air quality score
        air_quality_score = (
            voc_score * 0.3 +
            pm25_score * 0.4 +
            aqi_score * 0.3
        )
        
        # Apply odor type modifiers
        if odor_data['odor_type'] == 'strong_chemical':
            air_quality_score *= 0.5
        elif odor_data['odor_type'] == 'dust_or_smoke':
            air_quality_score *= 0.6
        elif odor_data['odor_type'] == 'human_activity':
            air_quality_score *= 0.8
    else:
        air_quality_score = 50  # Default mid-range
    
    score_components['air_quality'] = np.clip(air_quality_score, 0, 100)
    
    # 2. Noise Score (0-100)
    if sound_data:
        # Base noise score (inverse relationship)
        base_noise_score = max(0, 100 - (sound_data['db'] * 1.2))
        
        # Spike penalty
        spike_penalty = 20 if sound_data.get('spike', False) else 0
        
        # Event-based modifier
        event_modifiers = {
            'impact': 0.3,
            'door_slam': 0.5,
            'shouting': 0.6,
            'crowd': 0.7,
            'traffic': 0.7,
            'conversation': 0.8,
            'background': 0.9,
            'quiet': 1.0
        }
        
        event = sound_data.get('event', 'background')
        event_modifier = event_modifiers.get(event, 0.8)
        
        # Confidence weighting
        confidence = sound_data.get('confidence', 0.5)
        
        noise_score = (base_noise_score - spike_penalty) * event_modifier
        noise_score = noise_score * (0.7 + 0.3 * confidence)
    else:
        noise_score = 50
    
    score_components['noise'] = np.clip(noise_score, 0, 100)
    
    # 3. Occupancy Comfort Score (0-100)
    if radar_data and radar_analysis:
        target_count = radar_data.get('target_count', 0)
        
        # Optimal occupancy is 1-2 people
        if target_count == 0:
            occupancy_score = 70  # Empty but available
        elif target_count == 1:
            occupancy_score = 90  # Ideal for focused work
        elif target_count == 2:
            occupancy_score = 85  # Good for collaboration
        elif target_count == 3:
            occupancy_score = 70  # Getting crowded
        else:
            occupancy_score = max(40, 100 - (target_count * 10))  # Decreasing comfort
        
        # Adjust based on motion pattern
        pattern = motion_patterns.get('pattern', 'moderate_activity')
        pattern_modifiers = {
            'no_activity': 1.1,  # Too still might indicate absence
            'sporadic_activity': 1.0,
            'moderate_activity': 0.95,
            'high_activity': 0.8
        }
        
        occupancy_score *= pattern_modifiers.get(pattern, 1.0)
    else:
        occupancy_score = 50
    
    score_components['occupancy'] = np.clip(occupancy_score, 0, 100)
    
    # 4. Activity Level Score (0-100) - Different from occupancy, measures movement
    if radar_analysis and motion_patterns:
        activity_level = motion_patterns.get('activity_level', 0)
        velocity_trend = motion_patterns.get('velocity_trend', 0)
        
        # Moderate activity is good, too much or too little is bad
        if activity_level < 0.1:
            activity_score = 60  # Too still
        elif activity_level < 0.3:
            activity_score = 85  # Good low activity
        elif activity_level < 0.6:
            activity_score = 95  # Optimal activity
        elif activity_level < 0.8:
            activity_score = 75  # High activity
        else:
            activity_score = 50  # Very high activity
        
        # Velocity trend adjustment
        if abs(velocity_trend) > 1.0:
            activity_score *= 0.9  # Penalty for rapid changes
    else:
        activity_score = 50
    
    score_components['activity'] = np.clip(activity_score, 0, 100)
    
    # 5. Anomaly Score (0-100) - Lower is better (fewer anomalies)
    anomaly_count = 0
    anomaly_penalty = 0
    
    # Sound anomalies
    if sound_data and sound_data.get('spike', False):
        anomaly_count += 1
        anomaly_penalty += 15
    
    # Odor anomalies
    if odor_data and odor_data.get('odor_anomaly', False):
        anomaly_count += 1
        anomaly_penalty += 20
    
    # Activity anomalies
    if activity_events:
        for event in activity_events:
            if event['type'] in ['rapid_movement']:
                anomaly_count += 1
                anomaly_penalty += 10 * event.get('confidence', 0.5)
    
    anomaly_score = max(0, 100 - anomaly_penalty)
    score_components['anomaly'] = np.clip(anomaly_score, 0, 100)
    
    # 6. Calculate weighted final score
    final_score = (
        score_components['air_quality'] * WEIGHTS['air_quality'] +
        score_components['noise'] * WEIGHTS['noise'] +
        score_components['occupancy'] * WEIGHTS['occupancy'] +
        score_components['activity'] * WEIGHTS['activity'] +
        score_components['anomaly'] * WEIGHTS['anomaly']
    )
    
    # 7. Determine quality category
    if final_score >= 90:
        category = "EXCELLENT"
        recommendation = "Environment is ideal"
    elif final_score >= 80:
        category = "GOOD"
        recommendation = "Minor improvements possible"
    elif final_score >= 70:
        category = "FAIR"
        recommendation = "Some environmental factors need attention"
    elif final_score >= 60:
        category = "POOR"
        recommendation = "Multiple factors require improvement"
    else:
        category = "CRITICAL"
        recommendation = "Immediate action recommended"
    
    # 8. Generate insights
    insights = []
    
    if score_components['air_quality'] < 60:
        insights.append("Poor air quality detected")
    if score_components['noise'] < 60:
        insights.append(f"High noise levels ({sound_data.get('db', 0):.1f} dB)")
    if score_components['occupancy'] < 60:
        insights.append("Occupancy levels are suboptimal")
    if score_components['anomaly'] < 70:
        insights.append("Multiple anomalies detected")
    
    if odor_data and odor_data['odor_type'] != 'clean_air':
        insights.append(f"Odor detected: {odor_data['odor_type']}")
    
    return {
        'final_score': round(final_score, 1),
        'category': category,
        'recommendation': recommendation,
        'components': {k: round(v, 1) for k, v in score_components.items()},
        'insights': insights,
        'anomaly_count': anomaly_count,
        'timestamp': time.time()
    }

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
            # Read available data
            raw_data = radar.readline().decode(errors='ignore').strip()
            
            if raw_data:
                # Parse radar data
                parsed_data = radar_processor.parse_radar_frame(raw_data)
                
                # Track targets
                tracked_data = radar_processor.track_targets(parsed_data)
                
                # Store in history
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
    print("  • Comprehensive Environmental Scoring")
    print("  • Anomaly Detection")
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
                
                # Analyze radar patterns
                motion_patterns = radar_processor.analyze_motion_patterns()
                activity_events = radar_processor.detect_activity_events()
                
                # Periodic comprehensive analysis
                if current_time - last_print_time >= print_interval:
                    print("\n" + "="*70)
                    print(f"📊 COMPREHENSIVE REPORT - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("="*70)
                    
                    # Sound Analysis
                    if sound_analysis:
                        print("\n🔊 SOUND ANALYSIS:")
                        print(f"   Level: {sound_analysis['db']:.1f} dB (Baseline: {sound_analysis['baseline']:.1f} dB)")
                        print(f"   Event: {sound_analysis['event']} (confidence: {sound_analysis['confidence']:.2f})")
                        if sound_analysis['spike']:
                            print("   ⚠ Sound spike detected!")
                    
                    # Odor Analysis
                    if sound_analysis:
                        odor_analysis = analyze_odor(sound_analysis['db'])
                        
                        if odor_analysis:
                            print("\n🌬️ AIR QUALITY ANALYSIS:")
                            print(f"   VOC: {odor_analysis['voc_ppm']:.1f} ppm")
                            print(f"   PM2.5: {odor_analysis['pm25']} µg/m³")
                            print(f"   Air Quality Index: {odor_analysis['air_quality_index']:.1f}")
                            print(f"   Odor Type: {odor_analysis['odor_type']}")
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
                    
                    # Calculate and display environmental score
                    if sound_analysis and odor_analysis and radar_raw_data:
                        score_data = calculate_environmental_score(
                            sound_analysis, 
                            odor_analysis, 
                            radar_raw_data,
                            radar_processor,
                            motion_patterns,
                            activity_events
                        )
                        
                        # Store score history
                        score_history.append(score_data)
                        
                        print("\n🎯 ENVIRONMENTAL SCORE:")
                        print(f"   FINAL SCORE: {score_data['final_score']}/100 - {score_data['category']}")
                        print(f"   Recommendation: {score_data['recommendation']}")
                        
                        print("\n   Component Scores:")
                        for component, score in score_data['components'].items():
                            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                            print(f"   {component.replace('_', ' ').title():12} [{bar}] {score:.1f}")
                        
                        if score_data['insights']:
                            print("\n   Insights:")
                            for insight in score_data['insights']:
                                print(f"   • {insight}")
                    
                    # Raw sensor data
                    print("\n📊 RAW SENSOR DATA:")
                    if pms_data:
                        print(f"   PM1.0: {pms_data[0]:3d} µg/m³  PM2.5: {pms_data[1]:3d} µg/m³  PM10: {pms_data[2]:3d} µg/m³")
                    print(f"   MQ135: {mq135_voltage:.3f} V")
                    
                    print("\n" + "="*70 + "\n")
                    
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
            print(f"   Average Score: {avg_score:.1f}")
            print(f"   Best Score: {max([s['final_score'] for s in score_history]):.1f}")
            print(f"   Worst Score: {min([s['final_score'] for s in score_history]):.1f}")
            print(f"   Total Readings: {len(score_history)}")
        
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