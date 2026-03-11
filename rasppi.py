import time
import serial
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np
import math
import time
from collections import deque
from sklearn.ensemble import RandomForestClassifier

# Parameters
SAMPLE_RATE = 200
WINDOW_TIME = 1
WINDOW_SIZE = SAMPLE_RATE * WINDOW_TIME

REFERENCE_VOLTAGE = 0.05

SPIKE_THRESHOLD = 15
LOUD_THRESHOLD = 65

# Data Storage
samples = []
db_history = deque(maxlen=50)

# Sound Utilities
def voltage_to_db(v):

    if v <= 0:
        return 0

    return 20 * math.log10(v / REFERENCE_VOLTAGE)


def rms(values):

    arr = np.array(values)

    return np.sqrt(np.mean(arr**2))

# FFT Analysis
def fft_features(signal):

    signal = np.array(signal)

    fft = np.fft.fft(signal)

    magnitude = np.abs(fft)

    freqs = np.fft.fftfreq(len(signal), 1/SAMPLE_RATE)

    dominant_freq = freqs[np.argmax(magnitude)]

    spectral_energy = np.sum(magnitude)

    spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)

    return dominant_freq, spectral_energy, spectral_centroid

# Feature Extraction
def extract_features(signal):

    rms_val = rms(signal)

    db = voltage_to_db(rms_val)

    dom_freq, energy, centroid = fft_features(signal)

    return [db, dom_freq, energy, centroid]


# Machine Learning Model
model = RandomForestClassifier()

# Example training data
X_train = [

    [40,100,5000,120],
    [45,120,6000,150],
    [70,500,20000,600],
    [80,800,30000,900],
    [60,300,15000,400]

]

y_train = [

    "quiet",
    "conversation",
    "crowd",
    "door_slam",
    "shouting"

]

model.fit(X_train, y_train)

# Sound Analysis
def analyze_sound():
    global samples
    voltage = sound_channel.voltage
    samples.append(voltage)

    if len(samples) < WINDOW_SIZE:
        return None

    features = extract_features(samples)
    prediction = model.predict([features])[0]

    db = features[0]
    db_history.append(db)

    baseline = sum(db_history) / len(db_history)
    spike = db > baseline + SPIKE_THRESHOLD

    samples = []

    return db, baseline, spike, prediction

# Initialize ADC (ADS1115)
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

mq135_channel = AnalogIn(ads, ADS.P0)
sound_channel = AnalogIn(ads, ADS.P1)

# Serial connections

# PMS5003
pms = serial.Serial("/dev/serial0", baudrate=9600, timeout=2)

# mmWave radar (example port)
radar = serial.Serial("/dev/ttyUSB0", baudrate=256000, timeout=1)

# PMS5003 Reading Function
def read_pms5003():
    data = pms.read(32)

    if len(data) == 32 and data[0] == 0x42 and data[1] == 0x4d:
        pm1 = data[10] * 256 + data[11]
        pm25 = data[12] * 256 + data[13]
        pm10 = data[14] * 256 + data[15]

        return pm1, pm25, pm10

    return None

# MQ135 Gas Reading
def read_mq135():
    voltage = mq135_channel.voltage
    return voltage

# Sound Sensor
def read_sound():
    voltage = sound_channel.voltage
    db = voltage_to_db(voltage)

    sound_history.append(db)

    if len(sound_history) < WINDOW_SIZE:
        return db, None, False

    baseline = sum(sound_history) / len(sound_history)

    spike = db > baseline + SPIKE_THRESHOLD_DB

    return db, baseline, spike

# mmWave Radar Data
def read_radar():
    if radar.in_waiting:
        data = radar.readline().decode(errors="ignore").strip()
        return data
    return None

# Main Loop
while True:

    pms_data = read_pms5003()
    mq135 = read_mq135()
    sound_data = analyze_sound()
    if sound_data:
        db, baseline, spike, event = sound_data

        print("Sound Level:", round(db,2),"dB")
        print("Baseline:", round(baseline,2),"dB")

        if spike:
            print("⚠ Spike detected")

        if event:
            print("EVENT:", event)

    radar_data = read_radar()

    print("----- SENSOR DATA -----")

    if pms_data:
        print("PM1.0:", pms_data[0], "µg/m3")
        print("PM2.5:", pms_data[1], "µg/m3")
        print("PM10:", pms_data[2], "µg/m3")

    print("MQ135 Gas Voltage:", round(mq135,2), "V")
    print("Sound Level:", round(db,2), "dB")

    if baseline:
        print("Noise Baseline:", round(baseline,2), "dB")

    if spike:
        print("⚠ SOUND SPIKE DETECTED")

    if radar_data:
        print("Radar:", radar_data)

    print("------------------------\n")

    time.sleep(2)