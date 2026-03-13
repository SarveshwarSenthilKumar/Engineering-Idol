# 🎯 SIMPLE SCORING SYSTEM BREAKDOWN

## 📊 **THE BIG PICTURE**

Your system produces **2 main scores**:
- **THREAT SCORE** (0-100): How dangerous/unusual the situation is
- **QUALITY SCORE** (0-100): How comfortable/pleasant the environment is

Think of it like a thermometer:
- **0-20**: Everything is perfect (🟢)
- **20-40**: Minor issues (🟡)
- **40-60**: Getting concerning (🟠)
- **60-80**: Dangerous (🔴)
- **80-100**: CRITICAL EMERGENCY (⚫)

---

## 🔴 **THREAT SCORE = 6 COMPONENTS ADDED TOGETHER**

```
THREAT = (Proximity × 0.25) + (Count × 0.15) + (Behavior × 0.20) + 
         (Vital Signs × 0.15) + (Air Quality × 0.15) + (Noise × 0.10)
```

### **Component 1: PROXIMITY THREAT** (from RADAR)

**How it works**: The closer someone is, the higher the threat

```
Distance from radar:
├── < 1 meter  → +30 points  (🚨 Intruder right next to you!)
├── 1-2 meters → +15 points  (⚠️ Very close)
├── 2-3 meters → +8 points   (😐 Getting closer)
├── 3-5 meters → +3 points   (👤 In the room)
└── > 5 meters → 0 points    (✅ Safe distance)

Multipliers:
├── Moving TOWARD radar → ×1.5 (Coming closer = worse)
├── Standing still near radar (<3m) → ×1.3 (Loitering = suspicious)
└── Moving AWAY → ×1.0 (Leaving = normal)
```

**Example**: Someone at 1.5 meters walking toward you
- Base: 15 points
- ×1.5 (incoming) = **22.5 points**

---

### **Component 2: COUNT THREAT** (from RADAR)

**How it works**: More people = exponentially worse

```
Number of people:
├── 0 people → 0 points     (Empty room)
├── 1 person → 15 points    (👤 One person)
├── 2 people → 30 points    (👥 Two people - normal)
├── 3 people → 50 points    (👥👤 Three - getting crowded)
├── 4 people → 70 points    (👥👥 Four - party!)
├── 5 people → 80 points    (👥👥👤 Five - very crowded)
└── 6+ people → 90+ points  (👥👥👥 Crowd - chaos!)
```

**Example**: 4 people in room = **70 points**

---

### **Component 3: BEHAVIOR THREAT** (from RADAR + ACTIVITY)

**How it works**: Unusual activities = higher threat

```
Activity type:
├── Running         → +25 points  (🏃 Chase/panic)
├── Sudden movement → +20 points  (🔄 Transition)
├── Chaotic motion  → +35 points  (🌀 Multiple people running)
├── High activity   → +15 points  (🏋️ Normal movement)
└── Normal/Still    → 0 points    (🧘 Relaxed)

Special events:
├── Possible fall   → +50 points  (😵 Medical emergency!)
├── Abnormal breathing → +30 points (😮‍💨 Distressed/panicked)
└── Normal breathing → 0 points
```

**Example**: Someone running (25) with abnormal breathing (30) = **55 points**

---

### **Component 4: VITAL SIGNS THREAT** (from RADAR BREATHING)

**How it works**: Breathing too fast/slow = medical emergency

```
Breathing rate (breaths per minute):
├── < 6 bpm  → +50 points  (😴 Unconscious/overdose!)
├── 6-8 bpm  → +30 points  (😰 Dangerously slow)
├── 8-12 bpm → +15 points  (😐 Slower than normal)
├── 12-24 bpm → 0 points   (✅ Normal range)
├── 24-30 bpm → +20 points (😤 Rapid breathing)
└── > 30 bpm  → +40 points (😱 Hyperventilating/panic)

Abnormal flag:
├── Yes → +25 points  (Any abnormal pattern)
└── No  → 0 points
```

**Example**: Person breathing 8 bpm (30) + abnormal flag (25) = **55 points**

---

### **Component 5: AIR QUALITY THREAT** (from MQ135 + PMS5003)

**How it works**: Bad air = health hazard

```
VOC (Volatile Organic Compounds) in ppm:
├── > 200 ppm → +50 points  (☠️ Toxic! Gas leak/chemical spill)
├── 100-200 ppm → +30 points (⚠️ Dangerous fumes)
├── 50-100 ppm → +15 points  (😷 Poor air quality)
├── 30-50 ppm  → +5 points   (😐 Slightly stuffy)
└── < 30 ppm   → 0 points    (✅ Fresh air)

PM2.5 (Particulate Matter) in µg/m³:
├── > 100 → +45 points  (🔥 Smoke/fire!)
├── 50-100 → +25 points (🚬 Heavy pollution)
├── 25-50  → +10 points (😮‍💨 Moderate pollution)
└── < 25   → 0 points   (✅ Clean air)

Odor type multipliers:
├── Strong chemical → ×1.5 (🧪 Gas leak)
├── Dust/smoke      → ×1.3 (🔥 Fire)
└── Normal          → ×1.0
```

**Example**: VOC 150ppm (30) + PM2.5 60 (25) + Chemical odor (×1.5)
- Base = 30 + 25 = 55
- ×1.5 = **82.5 points** (🚨 EMERGENCY!)

---

### **Component 6: NOISE THREAT** (from SOUND SENSOR)

**How it works**: Loud noises = potential danger

```
Sound level in decibels:
├── > 100 dB → 90 points  (💥 Explosion/gunshot!)
├── 90-100 dB → 70 points (🔊 Screaming/alarm)
├── 80-90 dB  → 45 points (📢 Shouting/loud music)
├── 70-80 dB  → 25 points (🗣️ Loud conversation)
├── 60-70 dB  → 10 points (💬 Normal conversation)
└── < 60 dB   → 0 points  (🤫 Quiet)

Multipliers:
├── Sudden spike → ×1.5 (💥 Bang/crash)
├── Impact sound → ×2.0 (💢 Breaking glass)
├── Door slam    → ×1.3 (🚪)
└── Normal       → ×1.0
```

**Example**: 95dB scream (70) × spike (1.5) = **105 → capped at 100 points**

---

## ⏰ **TIME MAKES IT WORSE (Exponential Escalation)**

```
FINAL THREAT = Base Threat × Time Factor × Intensity Factor × Persistence Factor
```

### **Time Factor**: The longer it lasts, the worse it gets
```
After 1 minute  → ×1.1
After 5 minutes → ×1.5
After 15 minutes → ×2.3
After 30 minutes → ×3.6
After 1 hour     → ×6.3
```

### **Intensity Factor**: Each threshold crossed = 1.5x multiplier
```
Thresholds: 20, 40, 60, 80 points
├── Cross 1 threshold → ×1.5
├── Cross 2 thresholds → ×2.25
├── Cross 3 thresholds → ×3.38
└── Cross 4 thresholds → ×5.06
```

### **Persistence Factor**: Repeated events = worse
```
Events in last 5 minutes:
├── 1 event  → ×1.1
├── 2 events → ×1.3
├── 3 events → ×1.5
├── 4 events → ×1.7
└── 5+ events → ×2.0
```

---

## 🌿 **QUALITY SCORE = The Opposite of Threat**

```
QUALITY = 100 - (THREAT × 0.8) + Adjustments
```

### **Quality Adjustments** (from sensors)

**Sound comfort**:
```
< 45 dB → +95 points (Library quiet)
45-55 dB → +85 points (Normal office)
55-65 dB → +70 points (Slightly loud)
65-75 dB → +50 points (Annoying)
> 75 dB → +30 points (Uncomfortable)
```

**Air comfort**:
```
AQI < 50   → +90 points (Excellent)
AQI 50-100 → +75 points (Good)
AQI 100-150 → +55 points (Moderate)
AQI 150-200 → +35 points (Poor)
AQI > 200   → +20 points (Hazardous)
```

**Occupancy comfort**:
```
0 people  → +90 points (Empty - peaceful)
1 person  → +85 points (Ideal)
2 people  → +75 points (Comfortable)
3 people  → +60 points (Crowded)
4+ people → +40 points (Too many)
```

---

## 📋 **QUICK REFERENCE CARD**

### **THREAT THRESHOLDS**

| Component | Low (0) | Medium (+10-30) | High (+30-60) | Critical (+60-100) |
|-----------|---------|-----------------|---------------|-------------------|
| **Proximity** | >5m | 3-5m | 1-3m | <1m |
| **Count** | 0 | 1-2 | 3-4 | 5+ |
| **Behavior** | Still | Walking | Running | Fall/Fight |
| **Vital Signs** | 12-24 bpm | 8-12 or 24-30 | 6-8 or >30 | <6 bpm |
| **VOC (ppm)** | <30 | 30-100 | 100-200 | >200 |
| **PM2.5** | <25 | 25-50 | 50-100 | >100 |
| **Noise (dB)** | <60 | 60-80 | 80-100 | >100 |

### **MULTIPLIERS**

| Factor | Normal | Warning | Danger | Critical |
|--------|--------|---------|--------|----------|
| **Time (minutes)** | <1 | 1-5 | 5-15 | >15 |
| **Intensity (thresholds)** | 0 | 1 | 2 | 3+ |
| **Persistence (events)** | 0 | 1-2 | 3-4 | 5+ |

### **FINAL LEVELS**

| Score | Level | Color | What It Means |
|-------|-------|-------|---------------|
| 0-20 | LOW | 🟢 | Everything is fine |
| 20-40 | MODERATE | 🟡 | Something's off, monitor |
| 40-60 | ELEVATED | 🟠 | Getting concerning |
| 60-80 | HIGH | 🔴 | Dangerous, take action |
| 80-100 | CRITICAL | ⚫ | EMERGENCY! |

---

## 🎮 **REAL-WORLD EXAMPLES**

### **Example 1: Normal Day at Office**
```
Sensor readings:
├── 2 people at 4m → Count 30 + Proximity 3 = 33
├── Walking normally → Behavior 0
├── Breathing 16 bpm → Vital Signs 0
├── VOC 40ppm, PM2.5 15 → Air Quality 5
├── Noise 55dB → Noise 0
└── Duration: 5 minutes → Time ×1.5

Base Threat = (33×0.25)+(0×0.15)+(0×0.20)+(0×0.15)+(5×0.15)+(0×0.10)
            = 8.25 + 0 + 0 + 0 + 0.75 + 0 = 9 points

Final = 9 × 1.5 = 13.5 → 🟢 LOW (13)
Quality = 100 - (13×0.8) + adjustments = ~88 → 🌟 EXCELLENT
```

### **Example 2: Someone Running + Shouting**
```
Sensor readings:
├── 1 person at 2m, incoming → Proximity 15×1.5 = 22.5
├── Running → Behavior 25
├── Breathing 28 bpm → Vital Signs 20
├── Shouting 85dB → Noise 45
├── Duration: 2 minutes → Time ×1.2
└── Crossed thresholds: 20,40 → Intensity ×2.25

Base = (22.5×0.25)+(0×0.15)+(25×0.20)+(20×0.15)+(0×0.15)+(45×0.10)
     = 5.6 + 0 + 5 + 3 + 0 + 4.5 = 18.1

Final = 18.1 × 1.2 × 2.25 = 48.9 → 🟠 ELEVATED (49)
```

### **Example 3: Gas Leak + Multiple People**
```
Sensor readings:
├── 3 people at 2m → Proximity 8 + Count 50 = 58
├── Chaotic movement → Behavior 35
├── VOC 250ppm, PM2.5 30 → Air Quality 50×1.5 = 75
├── Duration: 10 minutes → Time ×1.8
├── Crossed thresholds: 20,40,60 → Intensity ×3.38
└── Persistence: 4 events → ×1.7

Base = (8×0.25)+(50×0.15)+(35×0.20)+(0×0.15)+(75×0.15)+(0×0.10)
     = 2 + 7.5 + 7 + 0 + 11.25 + 0 = 27.75

Final = 27.75 × 1.8 × 3.38 × 1.7 = 287 → capped at 100 → ⚫ CRITICAL (100)
```

---

## 🔧 **SIMPLE WAYS TO ADJUST**

### **Make it MORE sensitive** (earlier warnings)
```python
# Lower these thresholds:
PROXIMITY_DANGER_ZONES = {
    'critical': 2.0,  # Was 1.0
    'high': 3.0,      # Was 2.0
    'medium': 5.0,    # Was 3.0
}

INTENSITY_LEVELS = [10, 20, 30, 40, 50]  # Was [20,40,60,80,95]
BASE_ESCALATION_FACTOR = 2.0  # Was 1.5
```

### **Make it LESS sensitive** (ignore small issues)
```python
# Raise these thresholds:
PROXIMITY_DANGER_ZONES = {
    'critical': 0.5,  # Only 0.5m is critical
    'high': 1.0,      # Only 1.0m is high
}

INTENSITY_LEVELS = [30, 50, 70, 85, 95]  # Higher thresholds
BASE_ESCALATION_FACTOR = 1.2  # Gentler escalation
```

### **Focus on SPECIFIC threats**
```python
# Security focus (people threats)
WEIGHTS = {
    'proximity': 0.35,  # Up from 0.25
    'count': 0.20,      # Up from 0.15
    'behavior': 0.25,   # Up from 0.20
    'vital_signs': 0.05, # Down from 0.15
    'air_quality': 0.05, # Down from 0.15
    'noise': 0.10       # Same
}

# Health focus (air quality)
WEIGHTS = {
    'proximity': 0.10,
    'count': 0.10,
    'behavior': 0.15,
    'vital_signs': 0.20,
    'air_quality': 0.35,  # Up from 0.15
    'noise': 0.10
}
```

---
