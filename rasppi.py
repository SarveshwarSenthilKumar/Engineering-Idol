import time
import serial
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import math
from collections import deque

import math
import time
from collections import deque

# SOUND ANALYSIS PARAMETERS
SAMPLE_RATE = 120        # samples per second
WINDOW_DURATION = 1      # seconds
SAMPLES_PER_WINDOW = SAMPLE_RATE * WINDOW_DURATION

REFERENCE_VOLTAGE = 0.05

SPIKE_DB_THRESHOLD = 15
LOUD_DB_THRESHOLD = 65
SUSTAINED_DURATION = 5

# DATA STORAGE
samples = []
db_history = deque(maxlen=50)

event_timer = 0

# Voltage → Decibel Conversion
def voltage_to_db(v):

    if v <= 0:
        return 0

    return 20 * math.log10(v / REFERENCE_VOLTAGE)

# RMS Calculation
def rms(values):

    square_sum = sum(v*v for v in values)
    mean = square_sum / len(values)

    return math.sqrt(mean)

# SOUND ANALYSIS FUNCTION
def analyze_sound():

    global samples
    global event_timer

    voltage = sound_channel.voltage

    samples.append(voltage)

    if len(samples) < SAMPLES_PER_WINDOW:
        return None

    rms_voltage = rms(samples)

    db = voltage_to_db(rms_voltage)

    samples = []

    db_history.append(db)

    baseline = sum(db_history)/len(db_history)

    spike = db > baseline + SPIKE_DB_THRESHOLD

    event = None

    if spike and db > LOUD_DB_THRESHOLD:
        event = "IMPACT EVENT (possible door slam)"

    if db > LOUD_DB_THRESHOLD:
        event_timer += 1
    else:
        event_timer = 0

    if event_timer >= SUSTAINED_DURATION:
        event = "SUSTAINED LOUD ACTIVITY"

    return db, baseline, spike, event

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