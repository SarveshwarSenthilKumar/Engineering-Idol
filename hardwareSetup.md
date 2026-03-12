# 📋 COMPLETE HARDWARE SETUP GUIDE
## Environmental Monitoring System with mmWave Radar

## 🎯 SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI ZERO W                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   I2C Bus    │  │   UART Bus   │  │   USB Port   │      │
│  │  (GPIO 2/3)  │  │  (GPIO 14/15)│  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
    ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
    │  ADS1115  │      │  PMS5003  │      │  mmWave   │
    │   ADC     │      │ Particle  │      │   Radar   │
    └─────┬─────┘      │  Sensor   │      │ (USB/UART)│
          │            └───────────┘      └───────────┘
     ┌────┴────┐
     │ MQ135   │
     │ Gas     │
     │ Sensor  │
     └─────────┘
```

---

## 🔧 PART 1: RASPBERRY PI ZERO W SETUP

### 1.1 Initial Setup

```bash
# Download Raspberry Pi OS Lite (32-bit) or Desktop
# Flash to microSD card using Raspberry Pi Imager or balenaEtcher

# Enable SSH (create empty file named 'ssh' in boot partition)
touch /boot/ssh

# Configure WiFi (create wpa_supplicant.conf in boot partition)
cat > /boot/wpa_supplicant.conf << EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_WIFI_SSID"
    psk="YOUR_WIFI_PASSWORD"
    key_mgmt=WPA-PSK
}
EOF

# Boot Pi and SSH in
ssh pi@raspberrypi.local  # default password: raspberry
```

### 1.2 System Updates & Configuration

```bash
# Update system
sudo apt update && sudo apt full-upgrade -y

# Install essential tools
sudo apt install -y git curl wget vim htop tmux screen \
  python3-pip python3-venv python3-full \
  libatlas-base-dev libopenblas-dev \
  i2c-tools minicom screen \
  wiringpi raspi-gpio

# Change default password
passwd

# Expand filesystem
sudo raspi-config --expand-rootfs

# Set correct timezone
sudo dpkg-reconfigure tzdata

# Enable interfaces
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 2  # Enable serial but disable console
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_camera 0  # If using camera

# Reboot
sudo reboot
```

### 1.3 Verify Interfaces After Reboot

```bash
# Check I2C
ls /dev/i2c*        # Should show /dev/i2c-1
sudo i2cdetect -y 1 # Scan I2C bus (should find ADS1115 at 0x48)

# Check Serial
ls -la /dev/serial*  # Should show /dev/serial0
ls -la /dev/ttyAMA0 /dev/ttyS0

# Check USB devices
lsusb
ls -la /dev/ttyUSB*  # For USB radar modules
```

---

## 🔌 PART 2: WIRING DIAGRAMS

### 2.1 GPIO Pinout Reference (Raspberry Pi Zero W)

```
                    Raspberry Pi Zero W GPIO Header
    ┌─────────────────────────────────────────────────┐
    │  ○ 3.3V  (1)  (2) 5V     ○                      │
    │  ○ GPIO2  (3)  (4) 5V     ○   SDA1 (I2C)        │
    │  ○ GPIO3  (5)  (6) GND    ○   SCL1 (I2C)        │
    │  ○ GPIO4  (7)  (8) GPIO14 ○   TXD0 (UART)       │
    │  ○ GND    (9) (10) GPIO15 ○   RXD0 (UART)       │
    │  ○ GPIO17 (11) (12) GPIO18○                      │
    │  ○ GPIO27 (13) (14) GND   ○                      │
    │  ○ GPIO22 (15) (16) GPIO23○                      │
    │  ○ 3.3V  (17) (18) GPIO24○                      │
    │  ○ GPIO10 (19) (20) GND   ○                      │
    │  ○ GPIO9  (21) (22) GPIO25○                      │
    │  ○ GPIO11 (23) (24) GPIO8 ○                      │
    │  ○ GND    (25) (26) GPIO7 ○                      │
    │  ○ GPIO0  (27) (28) GPIO1 ○                      │
    │  ○ GPIO5  (29) (30) GND   ○                      │
    │  ○ GPIO6  (31) (32) GPIO12○                      │
    │  ○ GPIO13 (33) (34) GND   ○                      │
    │  ○ GPIO19 (35) (36) GPIO16○                      │
    │  ○ GPIO26 (37) (38) GPIO20○                      │
    │  ○ GND    (39) (40) GPIO21○                      │
    └─────────────────────────────────────────────────┘
    
    Legend:
    ────────
    Pin 1-2:   5V Power
    Pin 3:     SDA (I2C Data)      → ADS1115
    Pin 5:     SCL (I2C Clock)     → ADS1115
    Pin 6:     GND                  → All sensors
    Pin 8:     TXD (UART Transmit) → PMS5003 RX
    Pin 10:    RXD (UART Receive)  → PMS5003 TX
    Pin 17:    3.3V (for logic)    → Some sensors
```

### 2.2 ADS1115 + MQ135 + Sound Sensor Wiring

```
ADS1115 (16-bit ADC) - I2C Address: 0x48 (default)
┌─────────────────┐
│  VDD ──────┬────┼─── 3.3V (Pin 1 or 17)
│  GND ──────┼────┼─── GND (Pin 6)
│  SCL ──────┼────┼─── GPIO3/SCL1 (Pin 5)
│  SDA ──────┼────┼─── GPIO2/SDA1 (Pin 3)
│  ADDR ─────┘    │   (Leave floating for 0x48)
│                 │
│  A0 ────────────┼─── MQ135 Analog Out (AO)
│  A1 ────────────┼─── Sound Sensor Analog Out
│  A2 ────────────┘   (Optional extra sensor)
│  A3                (Optional extra sensor)
└─────────────────┘

MQ135 Gas Sensor Module
┌─────────────────┐
│ VCC ────────────┼─── 5V (Pin 2 or 4)
│ GND ────────────┼─── GND (Pin 6)  
│ AO ─────────────┼─── ADS1115 A0
│ DO ─────────────┘   (Digital out - not used)
└─────────────────┘

Sound Sensor Module (e.g., MAX4466, KY-037)
┌─────────────────┐
│ VCC ────────────┼─── 3.3V or 5V (check module specs)
│ GND ────────────┼─── GND (Pin 9)
│ OUT ────────────┼─── ADS1115 A1
│ EN ─────────────┘   (Enable - usually not connected)
└─────────────────┘
```

### 2.3 PMS5003 Particle Sensor Wiring

```
PMS5003 Sensor (UART)
┌─────────────────┐    Raspberry Pi
│ Pin 1 (VCC) ────┼─── 5V (Pin 2 or 4)
│ Pin 2 (GND) ────┼─── GND (Pin 6)
│ Pin 3 (SET) ────┼─── 3.3V (Pin 1) - Enable
│ Pin 4 (RX) ─────┼─── GPIO14/TXD (Pin 8) - Pi TX → PMS RX
│ Pin 5 (TX) ─────┼─── GPIO15/RXD (Pin 10) - PMS TX → Pi RX
│ Pin 6 (RESET) ──┼─── 3.3V (optional, pull-up)
└─────────────────┘

NOTE: PMS5003 uses 3.3V logic, but 5V power!
      Use level shifter if unsure about 5V tolerance.
```

### 2.4 mmWave Radar Wiring

**Option A: USB Radar Module (e.g., RD-03D USB, IWR6843 USB)**
```
┌─────────────────┐
│ USB Radar       │
│ Module          │
│ ┌───────────┐   │
│ │ USB-A     │   │
│ └───────────┘   │
└────────┬────────┘
         │
    USB Cable
         │
┌────────┴────────┐
│ Raspberry Pi    │
│ USB Port        │
└─────────────────┘
```

**Option B: UART Radar Module (e.g., RD-03D bare module, LD2410)**
```
RD-03D / LD2410 Radar Module
┌─────────────────┐    Raspberry Pi
│ VCC (5V) ───────┼─── 5V (Pin 2 or 4)
│ GND ────────────┼─── GND (Pin 6)
│ TX ─────────────┼─── GPIO15/RXD (Pin 10) - Radar TX → Pi RX
│ RX ─────────────┼─── GPIO14/TXD (Pin 8) - Pi TX → Radar RX
└─────────────────┘

⚠ IMPORTANT: Many radars use 3.3V logic!
             Check your module specs - use level shifter if needed.
```

---

## ⚡ PART 3: POWER REQUIREMENTS

### 3.1 Power Budget Calculation

| Component | Voltage | Current (typical) | Current (peak) |
|-----------|---------|-------------------|----------------|
| Raspberry Pi Zero W | 5V | 120mA | 350mA |
| PMS5003 | 5V | 80mA | 150mA |
| MQ135 | 5V | 150mA (heater!) | 180mA |
| ADS1115 | 3.3V | 0.15mA | 0.5mA |
| Sound Sensor | 3.3V | 5mA | 10mA |
| mmWave Radar | 5V/3.3V | 100-300mA | 500mA |
| **TOTAL** | | **~455-655mA** | **~1.2A** |

### 3.2 Power Supply Recommendations

```
✅ GOOD: 5V 3A USB power supply (Raspberry Pi official)
   └── Powers Pi + all sensors through Pi's 5V rail

✅ BETTER: 5V 5A supply with separate regulator
   ├── Pi Zero W (5V 2A)
   └── Sensors (5V 3A) - isolates sensor noise

✅ BEST: Powered USB Hub + Pi
   ├── Pi Zero W (micro USB)
   └── Sensors through hub's 5V
```

**⚠ CRITICAL WARNINGS:**
- MQ135 has a heater that draws ~150mA continuously - it gets HOT!
- PMS5003 has a fan that can cause voltage spikes
- Use decoupling capacitors (100µF + 0.1µF) near each sensor
- Keep power and signal wires separated

---

## 🛠️ PART 4: HARDWARE ASSEMBLY STEPS

### Step 1: Prepare the Breadboard/PCB

```
Recommended: Use breadboard for prototyping, then transfer to PCB

┌─────────────────────────────────────────────────┐
│  Breadboard Layout                              │
│                                                 │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  │
│  │ Pi  │  │ADS  │  │MQ135│  │Sound│  │PMS  │  │
│  │Zero │  │1115 │  │     │  │     │  │5003 │  │
│  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘  │
│     │I2C     │I2C     │Analog  │Analog  │UART  │
│     └────────┴────────┴────────┴────────┘     │
│                                                 │
│  Power Rails: +5V ──────────────────────────┐  │
│              +3.3V ──────────────────────┐  │  │
│              GND ─────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Step 2: Mounting Considerations

```
Physical Placement Recommendations:

         ┌─────────────────┐
         │    Ceiling      │  ← Best for radar (overhead view)
         │    Mount        │
         └────────┬────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───┴───┐    ┌────┴────┐   ┌────┴────┐
│Radar  │    │  MQ135  │   │ PMS5003 │
│(facing│    │ (away   │   │ (side   │
│down)  │    │  from   │   │  vent)  │
└───────┘    │  vents) │   └─────────┘
             └─────────┘
                 │
            ┌────┴────┐
            │  Sound  │
            │ Sensor  │
            └─────────┘

- Radar: Ceiling mounted, 2-3m height, clear view
- MQ135: Away from air vents, at breathing height
- PMS5003: Side-mounted for airflow, away from walls
- Sound: Central location, away from direct noise sources
```

---

## 🔧 PART 5: CONNECTION VERIFICATION

### 5.1 Test I2C Connection

```bash
# Install i2c-tools if not already
sudo apt install i2c-tools

# Scan I2C bus
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- -- 
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 70: -- -- -- -- -- -- -- --                         

# 0x48 = ADS1115 detected!
```

### 5.2 Test UART Connection (PMS5003)

```bash
# Test serial connection
sudo apt install minicom

# Read raw data from PMS5003
sudo minicom -D /dev/serial0 -b 9600

# You should see binary data (not readable text)
# Press Ctrl+A then X to exit

# Alternative: Use Python test
python3 << EOF
import serial
ser = serial.Serial('/dev/serial0', 9600, timeout=2)
data = ser.read(32)
print(f"Read {len(data)} bytes")
if len(data) == 32:
    print(f"Header: {hex(data[0])} {hex(data[1])}")
    if data[0] == 0x42 and data[1] == 0x4d:
        print("✅ PMS5003 detected!")
ser.close()
EOF
```

### 5.3 Test Radar Connection

```bash
# For USB radar
ls -la /dev/ttyUSB*
# Should show /dev/ttyUSB0

# Test with screen
sudo screen /dev/ttyUSB0 256000

# You should see binary data stream
# Press Ctrl+A then K to kill screen

# For UART radar (direct connection)
sudo screen /dev/serial0 256000
```

### 5.4 Test Analog Sensors (MQ135, Sound)

```python
# Quick test script
python3 << EOF
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1

chan0 = AnalogIn(ads, ADS.P0)  # MQ135
chan1 = AnalogIn(ads, ADS.P1)  # Sound

for _ in range(10):
    print(f"MQ135: {chan0.voltage:.3f}V  Sound: {chan1.voltage:.3f}V")
    time.sleep(1)
EOF
```

---

## 🐍 PART 6: SOFTWARE ENVIRONMENT SETUP

### 6.1 Python Virtual Environment

```bash
# Create virtual environment
cd ~
python3 -m venv env --system-site-packages

# Activate it
source ~/env/bin/activate

# Verify Python
python --version  # Should be 3.9+
```

### 6.2 Install Required Libraries

```bash
# Update pip
pip install --upgrade pip

# Core scientific libraries (pre-compiled for ARM)
pip install numpy==1.24.3
pip install scipy==1.10.1
pip install scikit-learn==1.2.2

# Hardware libraries
pip install adafruit-blinka
pip install adafruit-circuitpython-ads1x15
pip install RPi.GPIO
pip install spidev

# Serial communication
pip install pyserial

# Optional: For better performance
pip install cython
pip install pandas  # For data logging

# Verify installations
python -c "import numpy; import scipy; import sklearn; import serial; import board; print('✅ All libraries installed')"
```

### 6.3 Create Project Structure

```bash
# Create project directory
mkdir ~/environmental_monitor
cd ~/environmental_monitor

# Create subdirectories
mkdir -p {logs,config,data,models,utils}

# Create main script
touch main.py
chmod +x main.py

# Create config file
touch config/settings.json

# Create log file
touch logs/system.log

# Create startup script
cat > start.sh << 'EOF'
#!/bin/bash
cd ~/environmental_monitor
source ~/env/bin/activate
python main.py >> logs/system.log 2>&1
EOF

chmod +x start.sh
```

---

## ⚙️ PART 7: CONFIGURATION FILES

### 7.1 Create config/settings.json

```json
{
  "hardware": {
    "i2c_bus": 1,
    "ads1115_address": 0x48,
    "ads1115_gain": 1,
    "pms5003_port": "/dev/serial0",
    "pms5003_baud": 9600,
    "radar_port": "/dev/ttyUSB0",
    "radar_baud": 256000,
    "radar_type": "auto"
  },
  "sensors": {
    "mq135": {
      "channel": 0,
      "rload": 10000,
      "r0": 20000,
      "vcc": 5.0
    },
    "sound": {
      "channel": 1,
      "reference_voltage": 0.05
    }
  },
  "sampling": {
    "sound_rate": 200,
    "window_time": 1,
    "print_interval": 5
  },
  "thresholds": {
    "spike_db": 15,
    "loud_db": 65,
    "voc_clean": 50,
    "voc_activity": 80,
    "voc_chemical": 120,
    "pm_clean": 10,
    "pm_smoke": 40
  },
  "logging": {
    "enabled": true,
    "file": "logs/system.log",
    "level": "INFO"
  }
}
```

### 7.2 Create Systemd Service (Auto-start on boot)

```bash
sudo nano /etc/systemd/system/environmental-monitor.service
```

```ini
[Unit]
Description=Environmental Monitoring System
After=multi-user.target

[Service]
Type=simple
ExecStart=/home/pi/environmental_monitor/start.sh
Restart=always
RestartSec=10
User=pi
WorkingDirectory=/home/pi/environmental_monitor
StandardOutput=inherit
StandardError=inherit

[Install]
WantedBy=multi-user.target
```

```bash
# Enable service
sudo systemctl daemon-reload
sudo systemctl enable environmental-monitor.service
sudo systemctl start environmental-monitor.service

# Check status
sudo systemctl status environmental-monitor.service

# View logs
sudo journalctl -u environmental-monitor -f
```

---

## 📊 PART 8: CALIBRATION PROCEDURES

### 8.1 MQ135 Gas Sensor Calibration

```python
# calibration/mq135_calibrate.py
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np

print("🔬 MQ135 CALIBRATION")
print("="*50)
print("Place sensor in clean air for 10 minutes")
print("Make sure no VOC sources nearby")

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
mq135 = AnalogIn(ads, ADS.P0)

RLOAD = 10000
VCC = 5.0

# Collect samples
samples = []
print("\nCollecting samples...")
for i in range(60):  # 1 minute at 1Hz
    voltage = mq135.voltage
    samples.append(voltage)
    print(f"  Sample {i+1}/60: {voltage:.3f}V")
    time.sleep(1)

avg_voltage = np.mean(samples)
rs = RLOAD * (VCC / avg_voltage - 1)

print("\n" + "="*50)
print(f"Average voltage: {avg_voltage:.3f}V")
print(f"Rs value: {rs:.2f} Ω")
print("\nTypical R0 for clean air is 20kΩ")
print("Add this to your config:")
print(f'  "r0": {int(rs * 0.9)},  # 90% of clean air value')
print("="*50)
```

### 8.2 Sound Sensor Calibration

```python
# calibration/sound_calibrate.py
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np

print("🔊 SOUND SENSOR CALIBRATION")
print("="*50)
print("This will measure ambient noise floor")
print("Ensure environment is quiet")

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
sound = AnalogIn(ads, ADS.P1)

# Collect samples
samples = []
print("\nMeasuring noise floor (10 seconds)...")
for i in range(100):
    voltage = sound.voltage
    samples.append(voltage)
    time.sleep(0.1)

avg_voltage = np.mean(samples)
print(f"\nAverage voltage (quiet): {avg_voltage:.4f}V")

print("\nNow make a loud noise (clap, shout)")
time.sleep(3)

loud_samples = []
for i in range(20):
    voltage = sound.voltage
    loud_samples.append(voltage)
    time.sleep(0.1)

max_voltage = np.max(loud_samples)
print(f"Peak voltage (loud): {max_voltage:.4f}V")

print("\n" + "="*50)
print(f"Dynamic range: {max_voltage/avg_voltage:.1f}x")
print("Add to config:")
print(f'  "reference_voltage": {avg_voltage:.4f}')
print("="*50)
```

### 8.3 Radar Position Calibration

```python
# calibration/radar_calibrate.py
import time
import serial
import json

print("📡 RADAR POSITION CALIBRATION")
print("="*50)
print("Stand at various positions and note readings")

# Open radar connection
radar = serial.Serial('/dev/ttyUSB0', 256000, timeout=1)

positions = []
try:
    while True:
        if radar.in_waiting:
            data = radar.readline().decode(errors='ignore').strip()
            if data:
                print(f"\rRaw data: {data[:50]}...", end='')
                
                # Parse if possible (simplified)
                if data.startswith('{'):
                    try:
                        parsed = json.loads(data)
                        print(f"\n✅ Parsed: {parsed}")
                    except:
                        pass
except KeyboardInterrupt:
    radar.close()
    print("\n\nCalibration complete")
```

---

## 🚀 PART 9: RUNNING THE SYSTEM

### 9.1 First Run

```bash
# Activate environment
cd ~/environmental_monitor
source ~/env/bin/activate

# Run main program
python main.py
```

### 9.2 Expected Output

```
============================================================
ENHANCED ENVIRONMENTAL MONITORING SYSTEM
============================================================
✅ ADS1115 detected at 0x48
✅ PMS5003 detected on /dev/serial0
✅ RD-03D radar detected on /dev/ttyUSB0

Features:
  • Sound Analysis with ML Classification
  • Air Quality Monitoring (VOC, PM1.0, PM2.5, PM10)
  • mmWave Radar: rd03d
    - Multi-target tracking
    - Human orientation detection
    - Activity recognition
    - Breathing rate monitoring
  • Threat Level Detection

Press Ctrl+C to exit
```

### 9.3 Monitor Logs

```bash
# View real-time logs
tail -f logs/system.log

# Check systemd logs
sudo journalctl -u environmental-monitor -f -n 50
```

---

## 🔍 PART 10: TROUBLESHOOTING

### 10.1 Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **No I2C devices** | `i2cdetect` shows all -- | Check wiring, enable I2C, check voltage levels |
| **PMS5003 not responding** | No data on serial | Check UART enabled, disable console on serial |
| **Radar no data** | `screen` shows nothing | Check baudrate, power, TX/RX crossover |
| **MQ135 readings erratic** | Values jumping | Add capacitor, check ground, warm-up time |
| **Sound sensor 0V** | Always reads 0 | Check VCC, ADC channel, gain setting |
| **High CPU usage** | Pi running slow | Reduce ML complexity, increase sleep time |
| **Memory errors** | Python crashes | Reduce deque sizes, use less RAM |

### 10.2 Quick Diagnostic Script

```bash
#!/bin/bash
# diagnostics.sh

echo "🔍 SYSTEM DIAGNOSTICS"
echo "====================="

echo -n "I2C bus: "
ls /dev/i2c* || echo "❌ Not found"

echo -n "I2C devices: "
sudo i2cdetect -y 1 | grep -q "48" && echo "✅ ADS1115" || echo "❌ No ADS1115"

echo -n "Serial ports: "
ls -la /dev/serial* 2>/dev/null || echo "None"

echo -n "USB devices: "
lsusb | grep -i "serial\|uart\|cp210" || echo "No USB serial"

echo -n "UART test: "
python3 -c "import serial; ser=serial.Serial('/dev/serial0',9600,timeout=1); print('✅')" 2>/dev/null || echo "❌ Failed"

echo -n "RAM free: "
free -h | grep Mem | awk '{print $4}'

echo -n "CPU temp: "
vcgencmd measure_temp

echo -n "Voltage: "
vcgencmd measure_volts core

echo "===================="
```

---

## 📝 PART 11: MAINTENANCE SCHEDULE

### Daily
- Check logs for errors
- Verify data is being recorded
- Ensure all sensors are powered

### Weekly
- Clean PMS5003 air intake
- Check MQ135 for dust accumulation
- Verify radar mounting is secure

### Monthly
- Recalibrate MQ135 in clean air
- Check all wiring connections
- Update software: `pip install --upgrade -r requirements.txt`
- Backup data: `tar -czf backup_$(date +%Y%m%d).tar.gz data/`

### Quarterly
- Full system reboot
- Check power supply voltage
- Replace air filters if used
- Verify all thresholds with known conditions

---

## 🎯 PART 12: PERFORMANCE OPTIMIZATION

### 12.1 For Raspberry Pi Zero W (512MB RAM)

```python
# Optimize in code:
model = RandomForestClassifier(
    n_estimators=50,  # Reduced from 100
    max_depth=5,       # Reduced depth
    min_samples_split=5
)

# Reduce history buffer sizes
samples = deque(maxlen=200)  # Reduced from 400
odor_history = deque(maxlen=30)  # Reduced from 60
```

### 12.2 CPU Frequency Scaling

```bash
# Force maximum performance
echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Monitor frequency
watch -n 1 "vcgencmd measure_clock arm"
```

### 12.3 Disable Unnecessary Services

```bash
sudo systemctl disable bluetooth.service
sudo systemctl disable triggerhappy.service
sudo systemctl disable avahi-daemon.service
```

---

## 🆘 PART 13: EMERGENCY PROCEDURES

### If System Freezes:
```bash
# SSH in and restart service
sudo systemctl restart environmental-monitor

# If SSH unavailable, use hardware watchdog
sudo raspi-config → Performance Options → Watchdog → Enable
```

### If Sensor Fails:
```bash
# Identify which sensor
python3 -c "
import glob
print('I2C:', glob.glob('/dev/i2c*'))
print('Serial:', glob.glob('/dev/serial*'))
print('USB:', glob.glob('/dev/ttyUSB*'))
"

# Restart that sensor's power via GPIO (if controlled)
```

### Data Recovery:
```bash
# Backup logs before restart
cp -r logs/ logs_backup_$(date +%Y%m%d_%H%M%S)
cp -r data/ data_backup_$(date +%Y%m%d_%H%M%S)
```

---

## ✅ FINAL CHECKLIST

Before first power-on, verify:

- [ ] All connections secured
- [ ] Power supply adequate (3A minimum)
- [ ] I2C enabled in raspi-config
- [ ] Serial enabled (but console disabled)
- [ ] Python virtual environment created
- [ ] All libraries installed
- [ ] Calibration performed
- [ ] Systemd service configured
- [ ] Logging directory writable
- [ ] Radar auto-detection working
- [ ] All sensors responding

---

**🎉 Congratulations! Your Environmental Monitoring System is now fully set up and ready to run!**

Remember: The system will auto-start on boot and can be monitored via SSH. Check logs regularly and recalibrate sensors monthly for best accuracy.