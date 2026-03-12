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
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION PARAMETERS ====================
# Sound Analysis Parameters
SAMPLE_RATE = 200
WINDOW_TIME = 1
WINDOW_SIZE = SAMPLE_RATE * WINDOW_TIME
REFERENCE_VOLTAGE = 0.05
SPIKE_THRESHOLD_DB = 15  # Fixed variable name
LOUD_THRESHOLD_DB = 65    # Fixed variable name

# Gas Sensor Parameters
RLOAD = 10000
VCC = 5.0
R0 = 20000
MQ135_CLEAN_AIR_RATIO = 3.6  # Typical clean air ratio for MQ135

# Odor Classification Thresholds
VOC_CLEAN_THRESHOLD = 50
VOC_ACTIVITY_THRESHOLD = 80
VOC_CHEMICAL_THRESHOLD = 120
PM_CLEAN_THRESHOLD = 10
PM_SMOKE_THRESHOLD = 40

# ==================== DATA STORAGE ====================
samples = deque(maxlen=WINDOW_SIZE)  # Use deque for efficiency
db_history = deque(maxlen=50)
sound_history = deque(maxlen=WINDOW_SIZE)
odor_history = deque(maxlen=60)

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
    # Remove any NaN or inf values
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return 0
    return np.sqrt(np.mean(np.square(arr)))

# ==================== FFT ANALYSIS ====================
def fft_features(signal):
    """Extract frequency domain features with error handling"""
    if len(signal) < 4:  # Need at least a few samples
        return 0, 0, 0
    
    signal = np.array(signal, dtype=np.float64)
    # Remove DC offset
    signal = signal - np.mean(signal)
    
    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(len(signal))
    signal_windowed = signal * window
    
    fft = np.fft.rfft(signal_windowed)  # Use rfft for real signals
    magnitude = np.abs(fft)
    freqs = np.fft.rfftfreq(len(signal), 1/SAMPLE_RATE)
    
    # Handle edge cases
    if np.sum(magnitude) == 0:
        return 0, 0, 0
    
    dominant_freq = freqs[np.argmax(magnitude)]
    spectral_energy = np.sum(np.square(magnitude))
    spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
    
    return dominant_freq, spectral_energy, spectral_centroid

# ==================== FEATURE EXTRACTION ====================
def extract_features(signal):
    """Extract comprehensive features from sound signal"""
    if not signal:
        return [0, 0, 0, 0]
    
    rms_val = rms(signal)
    db = voltage_to_db(rms_val)
    dom_freq, energy, centroid = fft_features(signal)
    
    # Add signal statistics for better classification
    signal_array = np.array(signal)
    peak = np.max(np.abs(signal_array)) if len(signal_array) > 0 else 0
    zero_crossings = np.sum(np.diff(np.sign(signal_array)) != 0) if len(signal_array) > 1 else 0
    
    return [db, dom_freq, energy, centroid, peak, zero_crossings]

# ==================== MACHINE LEARNING MODEL ====================
def initialize_model():
    """Initialize and train the Random Forest model"""
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        min_samples_split=3
    )
    
    # Enhanced training data with more features
    X_train = [
        [40, 100, 5000, 120, 0.5, 50],    # quiet
        [45, 120, 6000, 150, 0.8, 80],    # conversation
        [70, 500, 20000, 600, 2.5, 200],  # crowd
        [80, 800, 30000, 900, 3.2, 50],   # door_slam
        [60, 300, 15000, 400, 1.5, 150],  # shouting
        [35, 50, 2000, 80, 0.3, 30],      # background
        [90, 1200, 40000, 1200, 4.0, 40], # explosion/impact
        [55, 250, 12000, 350, 1.2, 120],  # traffic
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
        baseline = np.median(db_history)  # Use median for robustness
        std_dev = np.std(db_history)
        spike = db > baseline + (SPIKE_THRESHOLD_DB * (1 + 0.1 * (std_dev / baseline)))
    else:
        baseline = db
        spike = False
    
    # Clear samples for next window (overlap of 50% for smoother analysis)
    for _ in range(WINDOW_SIZE // 2):
        samples.popleft()
    
    return {
        'db': db,
        'baseline': baseline,
        'spike': spike,
        'event': prediction,
        'confidence': confidence,
        'features': features
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
        
        # MQ135 characteristic curve parameters (adjusted for better accuracy)
        a = 116.6020682
        b = -2.769034857
        
        # Apply limits to avoid extreme values
        ratio = np.clip(ratio, 0.1, 10)
        ppm = a * (ratio ** b)
        
        return max(0, min(ppm, 1000))  # Clip to reasonable range
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
    
    # VOC contribution
    voc_score = min(voc_ppm / 50, 4)
    score += voc_score
    
    # Particulate matter contribution
    pm_score = min(pm25 / 25, 3)
    score += pm_score
    
    # Occupancy contribution
    people_score = min(people / 3, 2)
    score += people_score
    
    # Noise correlation
    if noise_db > LOUD_THRESHOLD_DB:
        score += 0.5
    
    # Trend factor (increasing trend increases intensity)
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
    
    # Use robust statistics
    baseline = np.median(list(odor_history))
    std_dev = np.std(list(odor_history))
    
    odor_history.append(current_score)
    
    # Anomaly detection with adaptive threshold
    anomaly = current_score > baseline + max(2, std_dev * 2)
    
    return anomaly, baseline

def analyze_odor(noise_db):
    """Comprehensive odor analysis"""
    global VOC_BASELINE, PM_BASELINE
    
    try:
        # Read Sensors with error handling
        voc_voltage = read_mq135()
        pms_data = read_pms5003()
        radar_data = read_radar()
        
        # Occupancy estimation with fallback
        people = 0
        if radar_data and isinstance(radar_data, dict):
            people = radar_data.get('target_count', 0)
        
        # Particle data with defaults
        pm1 = pm25 = pm10 = 0
        if pms_data and len(pms_data) == 3:
            pm1, pm25, pm10 = pms_data
        
        # Convert MQ135 to VOC ppm
        voc_ppm = compute_mq135_ppm(voc_voltage)
        
        # Baseline learning (with gradual update)
        if VOC_BASELINE is None:
            VOC_BASELINE = voc_ppm
        else:
            # Slowly adapt baseline
            VOC_BASELINE = 0.95 * VOC_BASELINE + 0.05 * voc_ppm
        
        if PM_BASELINE is None:
            PM_BASELINE = pm25
        else:
            PM_BASELINE = 0.95 * PM_BASELINE + 0.05 * pm25
        
        # Trend detection
        trend = voc_ppm - VOC_BASELINE
        
        # Odor intensity calculation
        intensity = compute_odor_intensity(voc_ppm, pm25, people, noise_db, trend)
        
        # Odor anomaly detection
        anomaly, baseline = detect_odor_anomaly(intensity)
        
        # Odor classification with confidence
        odor_type, confidence = classify_odor(voc_ppm, pm25, people, noise_db)
        
        # Severity level with more granularity
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
        
        # Air quality index calculation
        aqi = (voc_ppm / 100 * 50) + (pm25 / 35 * 50)
        aqi = min(500, max(0, aqi))
        
        # Return comprehensive analysis
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
        # Initialize I2C and ADC
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        
        # Set ADC gain for appropriate voltage range
        ads.gain = 1  # +/- 4.096V
        
        mq135_channel = AnalogIn(ads, ADS.P0)
        sound_channel = AnalogIn(ads, ADS.P1)
        
        # Initialize serial connections with timeouts
        pms = serial.Serial(
            port="/dev/serial0",
            baudrate=9600,
            timeout=2,
            write_timeout=2
        )
        
        radar = serial.Serial(
            port="/dev/ttyUSB0",
            baudrate=256000,
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
        # Clear buffer
        pms.reset_input_buffer()
        
        # Read data frame
        data = pms.read(32)
        
        if len(data) == 32 and data[0] == 0x42 and data[1] == 0x4d:
            # Verify checksum
            checksum = sum(data[:30]) & 0xFF
            if checksum == data[30] or checksum == data[31]:  # Some sensors use 2-byte checksum
                pm1 = (data[10] << 8) | data[11]
                pm25 = (data[12] << 8) | data[13]
                pm10 = (data[14] << 8) | data[15]
                
                # Validate values
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
        # Read multiple samples and average for stability
        samples = []
        for _ in range(5):
            voltage = mq135_channel.voltage
            if not math.isnan(voltage):
                samples.append(voltage)
            time.sleep(0.01)
        
        if samples:
            return np.median(samples)  # Use median for robustness
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
    """Read mmWave radar data with parsing"""
    if not radar:
        return None
    
    try:
        if radar.in_waiting:
            data = radar.readline().decode(errors='ignore').strip()
            if data:
                # Parse radar data (example format - adjust based on actual radar)
                parsed = {}
                if 'target' in data.lower():
                    parsed['raw'] = data
                    # Count targets (simplified - adjust based on actual protocol)
                    parsed['target_count'] = data.lower().count('target')
                return parsed
    except Exception as e:
        print(f"Radar read error: {e}")
    
    return None

# ==================== MAIN LOOP ====================
def main():
    """Main program loop with error recovery"""
    print("=== Environmental Monitoring System Started ===")
    print("Press Ctrl+C to exit\n")
    
    last_print_time = time.time()
    print_interval = 2  # seconds
    
    # Check hardware initialization
    if None in [mq135_channel, sound_channel, pms, radar]:
        print("Warning: Some sensors failed to initialize")
    
    try:
        while True:
            current_time = time.time()
            
            try:
                # Read all sensors
                pms_data = read_pms5003()
                mq135_voltage = read_mq135()
                sound_voltage = read_sound()
                
                # Analyze sound
                sound_analysis = analyze_sound(sound_voltage)
                
                # Periodic printing
                if current_time - last_print_time >= print_interval:
                    print("\n" + "="*50)
                    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Sound Analysis
                    if sound_analysis:
                        print("\n--- SOUND ANALYSIS ---")
                        print(f"Level: {sound_analysis['db']:.1f} dB")
                        print(f"Baseline: {sound_analysis['baseline']:.1f} dB")
                        print(f"Event: {sound_analysis['event']} (conf: {sound_analysis['confidence']:.2f})")
                        if sound_analysis['spike']:
                            print("⚠ SOUND SPIKE DETECTED!")
                    
                    # Odor Analysis
                    if sound_analysis:
                        odor_analysis = analyze_odor(sound_analysis['db'])
                        
                        if odor_analysis:
                            print("\n--- AIR QUALITY ANALYSIS ---")
                            print(f"VOC: {odor_analysis['voc_ppm']:.1f} ppm")
                            print(f"PM2.5: {odor_analysis['pm25']} µg/m³")
                            print(f"Air Quality Index: {odor_analysis['air_quality_index']:.1f}")
                            print(f"Odor Type: {odor_analysis['odor_type']}")
                            print(f"Intensity: {odor_analysis['odor_intensity']} ({odor_analysis['odor_level']})")
                            print(f"People Count: {odor_analysis['people']}")
                            if odor_analysis['odor_anomaly']:
                                print("⚠ ODOR ANOMALY DETECTED!")
                    
                    # Raw sensor data
                    print("\n--- RAW SENSOR DATA ---")
                    if pms_data:
                        print(f"PM1.0: {pms_data[0]} µg/m³")
                        print(f"PM2.5: {pms_data[1]} µg/m³")
                        print(f"PM10: {pms_data[2]} µg/m³")
                    print(f"MQ135: {mq135_voltage:.3f} V")
                    
                    print("="*50 + "\n")
                    
                    last_print_time = current_time
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Loop iteration error: {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\n=== Shutting down... ===")
    finally:
        # Clean up resources
        if pms:
            pms.close()
        if radar:
            radar.close()
        print("Cleanup complete. Exiting.")

# Run the main program
if __name__ == "__main__":
    main()