import time
import serial
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

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
    return voltage

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
    sound = read_sound()
    radar_data = read_radar()

    print("----- SENSOR DATA -----")

    """
    PMS5003 DATA TABLE BREAKDOWN
    PM1.0: 9 µg/m³
    PM2.5: 18 µg/m³
    PM10: 24 µg/m³

    | Value | Meaning          |
    | ----- | ---------------- |
    | 0–12  | clean air        |
    | 12–35 | moderate         |
    | 35+   | poor air quality |




    MQ135 DATA TABLE BREAKDOWN
    Voltage: 0.5V - 4.9V

    | Value | Meaning          |
    | ----- | ---------------- |
    | 0.5V - 1.1V  | clean air        |
    | 1.1V - 2.1V | moderate         |
    | 2.1V - 4.9V   | poor air quality |




    Sound is basic, only need the logic to detect spikes in sound compared to a normal decibel level.
    | dB  | Meaning      |
    | --- | ------------ |
    | 30  | quiet        |
    | 50  | conversation |
    | 70  | loud         |
    | 85+ | very loud    |





    mmWave Radar Data
    Occupancy
    People detected: 3
    Movement: low

    """

    if pms_data:
        print("PM1.0:", pms_data[0], "µg/m3")
        print("PM2.5:", pms_data[1], "µg/m3")
        print("PM10:", pms_data[2], "µg/m3")

    print("MQ135 Gas Voltage:", round(mq135,2), "V")
    print("Sound Voltage:", round(sound,2), "V")

    if radar_data:
        print("Radar:", radar_data)

    print("------------------------\n")

    time.sleep(2)