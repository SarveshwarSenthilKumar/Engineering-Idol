import time
import serial
import board
import busio
import math
import numpy as np
from collections import deque
from sklearn.ensemble import RandomForestClassifier

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ============================================================
# SYSTEM PARAMETERS
# ============================================================

SAMPLE_RATE = 200
WINDOW_TIME = 1
WINDOW_SIZE = SAMPLE_RATE * WINDOW_TIME

REFERENCE_VOLTAGE = 0.05

SPIKE_THRESHOLD = 12
LOUD_THRESHOLD = 65

RLOAD = 10000
VCC = 5.0
R0 = 20000

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def safe_log(x):
    if x <= 0:
        return 0
    return math.log10(x)


def voltage_to_db(v):
    if v <= 0:
        return 0
    return 20 * safe_log(v / REFERENCE_VOLTAGE)


def rms(values):
    arr = np.array(values)
    return np.sqrt(np.mean(arr ** 2))


# ============================================================
# FFT ANALYSIS
# ============================================================

def fft_features(signal):

    signal = np.array(signal)

    if len(signal) == 0:
        return 0, 0, 0

    fft = np.fft.fft(signal)
    magnitude = np.abs(fft)

    freqs = np.fft.fftfreq(len(signal), 1 / SAMPLE_RATE)

    dominant_freq = abs(freqs[np.argmax(magnitude)])

    spectral_energy = float(np.sum(magnitude))

    if np.sum(magnitude) == 0:
        spectral_centroid = 0
    else:
        spectral_centroid = float(np.sum(freqs * magnitude) / np.sum(magnitude))

    return dominant_freq, spectral_energy, spectral_centroid


# ============================================================
# SOUND ANALYZER
# ============================================================

class SoundAnalyzer:

    def __init__(self, channel):

        self.channel = channel

        self.samples = []

        self.db_history = deque(maxlen=60)

        self.model = RandomForestClassifier()

        self.train_model()

    def train_model(self):

        X_train = [

            [40, 100, 5000, 120],
            [45, 120, 6000, 150],
            [70, 500, 20000, 600],
            [80, 800, 30000, 900],
            [60, 300, 15000, 400]

        ]

        y_train = [

            "quiet",
            "conversation",
            "crowd",
            "door_slam",
            "shouting"

        ]

        self.model.fit(X_train, y_train)

    def extract_features(self, signal):

        rms_val = rms(signal)

        db = voltage_to_db(rms_val)

        dom_freq, energy, centroid = fft_features(signal)

        return [db, dom_freq, energy, centroid]

    def analyze(self):

        voltage = self.channel.voltage

        self.samples.append(voltage)

        if len(self.samples) < WINDOW_SIZE:
            return None

        features = self.extract_features(self.samples)

        prediction = self.model.predict([features])[0]

        db = features[0]

        self.db_history.append(db)

        baseline = np.mean(self.db_history) if len(self.db_history) else db

        spike = db > baseline + SPIKE_THRESHOLD

        self.samples = []

        return {

            "db": round(db,2),
            "baseline": round(baseline,2),
            "spike": spike,
            "event": prediction
        }


# ============================================================
# MQ135 GAS SENSOR
# ============================================================

def compute_mq135_ppm(voltage):

    if voltage <= 0:
        return 0

    rs = RLOAD * (VCC / voltage - 1)

    ratio = rs / R0

    a = 116.6020682
    b = -2.769034857

    ppm = a * (ratio ** b)

    return max(ppm,0)


# ============================================================
# ODOR ANALYZER
# ============================================================

class OdorAnalyzer:

    def __init__(self):

        self.voc_baseline = None
        self.pm_baseline = None

        self.odor_history = deque(maxlen=60)

    def classify(self, voc, pm25, people):

        if voc < 50 and pm25 < 10:
            return "clean_air"

        if voc > 80 and people >= 1:
            return "human_activity"

        if pm25 > 40:
            return "dust_or_smoke"

        if voc > 120:
            return "chemical"

        return "moderate"

    def compute_intensity(self, voc, pm25, people, noise):

        score = 0

        score += min(voc / 50, 3)
        score += min(pm25 / 25, 2)
        score += min(people / 3, 2)

        if noise > 65:
            score += 1

        return score

    def detect_anomaly(self, score):

        if len(self.odor_history) < 10:
            self.odor_history.append(score)
            return False, score

        baseline = np.mean(self.odor_history)

        self.odor_history.append(score)

        anomaly = score > baseline * 1.8

        return anomaly, baseline

    def analyze(self, voc_ppm, pm25, people, noise):

        if self.voc_baseline is None:
            self.voc_baseline = voc_ppm

        if self.pm_baseline is None:
            self.pm_baseline = pm25

        intensity = self.compute_intensity(voc_ppm, pm25, people, noise)

        anomaly, baseline = self.detect_anomaly(intensity)

        odor_type = self.classify(voc_ppm, pm25, people)

        trend = voc_ppm - self.voc_baseline

        if intensity < 2:
            level = "LOW"
        elif intensity < 4:
            level = "MODERATE"
        elif intensity < 6:
            level = "HIGH"
        else:
            level = "SEVERE"

        return {

            "voc_ppm": round(voc_ppm,1),
            "pm25": pm25,
            "people": people,
            "odor_type": odor_type,
            "intensity": round(intensity,2),
            "level": level,
            "trend": round(trend,2),
            "anomaly": anomaly
        }


# ============================================================
# SENSOR READERS
# ============================================================

def read_pms5003(port):

    if port.in_waiting < 32:
        return None

    data = port.read(32)

    if data[0] == 0x42 and data[1] == 0x4d:

        pm1 = data[10] * 256 + data[11]
        pm25 = data[12] * 256 + data[13]
        pm10 = data[14] * 256 + data[15]

        return pm1, pm25, pm10

    return None


def read_radar(port):

    if port.in_waiting:

        line = port.readline().decode(errors="ignore").strip()

        if not line:
            return 0

        people = line.count("target")

        return people

    return 0


# ============================================================
# HARDWARE INITIALIZATION
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(i2c)

mq135_channel = AnalogIn(ads, ADS.P0)
sound_channel = AnalogIn(ads, ADS.P1)

pms = serial.Serial("/dev/serial0", 9600, timeout=1)

radar = serial.Serial("/dev/ttyUSB0", 256000, timeout=1)

sound_analyzer = SoundAnalyzer(sound_channel)

odor_analyzer = OdorAnalyzer()

# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        sound_data = sound_analyzer.analyze()

        pms_data = read_pms5003(pms)

        radar_people = read_radar(radar)

        voc_voltage = mq135_channel.voltage

        voc_ppm = compute_mq135_ppm(voc_voltage)

        noise_db = sound_data["db"] if sound_data else 0

        pm25 = pms_data[1] if pms_data else 0

        odor_data = odor_analyzer.analyze(voc_ppm, pm25, radar_people, noise_db)

        print("\n===== ENVIRONMENT STATUS =====")

        if sound_data:

            print("Sound:", sound_data["db"], "dB")
            print("Baseline:", sound_data["baseline"], "dB")
            print("Event:", sound_data["event"])

            if sound_data["spike"]:
                print("⚠ SOUND SPIKE DETECTED")

        if pms_data:

            print("PM1:", pms_data[0])
            print("PM2.5:", pms_data[1])
            print("PM10:", pms_data[2])

        print("VOC:", odor_data["voc_ppm"], "ppm")

        print("People:", radar_people)

        print("Odor:", odor_data["odor_type"])
        print("Odor Level:", odor_data["level"])

        if odor_data["anomaly"]:
            print("⚠ ODOR ANOMALY DETECTED")

        print("==============================\n")

        time.sleep(1)

    except Exception as e:

        print("Sensor error:", e)

        time.sleep(2)

        