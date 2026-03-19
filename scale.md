# 🎯 SIMPLE SCORING SYSTEM BREAKDOWN

## 📊 **THE BIG PICTURE**

Your system produces **2 main scores**:
- **THREAT SCORE** (0-100): How dangerous/unusual the situation is
- **QUALITY SCORE** (0-100): How comfortable/pleasant the environment is

Think of it like a thermometer:
- **0-20**: Everything is perfect (🟢)
- **20-40**: Minor issues (🟡)

---

## THREAT SCORE = 5 COMPONENTS ADDED TOGETHER

```
THREAT = (Count × 0.15) + (Behavior(w Proximity) × 0.45) + 
         (Vital Signs × 0.15) + (Air Quality × 0.15) + (Noise × 0.10)
```

### Key Improvements Made:
- Combined proximity with behavior - now Behavior(w Proximity) × 0.45
- Removed separate proximity component - integrated into behavior scoring
- Vital signs dependency - only matter if behavior score > 70
- Air quality auto-alarm - triggers when AQI > 200 or extreme values
- Noise auto-alarm - triggers when > 110dB or spike > 100dB
- Extreme value protection - high air quality or noise can set off alarm regardless

---

### **Component 2: BEHAVIOR THREAT** (from RADAR + ACTIVITY - includes proximity)

**How it works**: Unusual activities + proximity = higher threat

```
Activity type:
├── Running         → +25 points  (🏃 Chase/panic)
├── Sudden movement → +20 points  (🔄 Transition)
├── Chaotic motion  → +35 points  (🌀 Multiple people running)
├── High activity   → +15 points  (🏋️ Normal movement)
└── Normal/Still    → 0 points    (🧘 Relaxed)

Proximity factors (integrated):
├── < 1 meter  → +15 points  (🚨 Very close)
├── 1-2 meters → +8 points   (⚠️ Close)
├── 2-3 meters → +3 points   (😐 Nearby)
└── > 3 meters → 0 points    (✅ Safe distance)

Special events:
├── Possible fall   → +50 points  (😵 Medical emergency!)
├── Abnormal breathing → +30 points (😮‍💨 Distressed/panicked)
└── Normal breathing → 0 points
```

**Weight: 0.45** (includes proximity factor)

**Example**: Someone running 1.5m away (25 + 8) with abnormal breathing (30) = **63 points**

---

### **Component 3: COUNT THREAT** (from RADAR)

**How it works**: More people = exponentially worse

```
Number of people:
├── 0 people → 0 points     (Empty room)
├── 1 person → 15 points    (👤 One person)
├── 2 people → 30 points    (👥 Two people - normal)
├── 3 people → 50 points    (👥👤 Three - getting crowded)
├── 4 people → 70 points    (�👥 Four - party!)
├── 5 people → 80 points    (👥👥👤 Five - very crowded)
└── 6+ people → 90+ points  (��👥 Crowd - chaos!)
```

**Weight: 0.15**

**Example**: 4 people in room = **70 points**

---

### **Component 4: VITAL SIGNS THREAT** (from HEALTH MONITORING)

**How it works**: Only matters if behavior is setting off errors

```
Behavior Score > 70:
├── Vital signs = behavior score  (⚠️ Behavior drives vital signs)
└── Weight: 0.15

Behavior Score ≤ 70:
├── Vital signs = random 0-30 points  (✅ Normal vitals)
└── Weight: 0.15
```

**Logic**: Vital signs only contribute significantly if behavior already indicates problems
- Normal behavior → vital signs mostly ignored (0-30 points)
- Abnormal behavior → vital signs mirror behavior severity

---

### **Component 5: AIR QUALITY THREAT** (from FACILITY SENSORS)

**How it works**: Poor air quality = health risk + auto-alarm + smoking/vaping detection

```
Air Quality Index (AQI):
├── AQI < 50   → 0-20 points   (✅ Excellent air)
├── AQI 50-100 → 20-40 points  (🌤️ Good air)
├── AQI 100-150 → 40-60 points  (😐 Moderate air)
├── AQI 150-200 → 60-80 points  (⚠️ Poor air)
└── AQI > 200   → 80-100 points  (🚨 Hazardous + ALARM)

**Smoking/Vaping Detection**:
├── VOC > 150ppm + PM2.5 > 40  → Smoking detected (🚬)
├── VOC > 180ppm + PM2.5 > 60  → Vaping detected (💨)
├── VOC > 300ppm OR PM2.5 > 150 → Extreme vaping/chemical (☠️)
└── Combined VOC+PM2.5 thresholds → Enhanced detection

**Odor Type Classification**:
├── Cigarette smoke → ×1.3 multiplier (🚬)
├── Vaping aerosol → ×1.4 multiplier (💨)
├── Strong chemical → ×1.5 multiplier (🧪)
├── Dust/smoke → ×1.3 multiplier (🔥)
└── Normal → ×1.0
```

**Auto-Alarm Feature**:
- Triggers when AQI > 200 OR VOC > 300 OR PM2.5 > 150
- Triggers when smoking/vaping detected at high levels
- Sets minimum threat level to 85 regardless of other factors
- Immediate notification to front office
- Weight: 0.15

**Example**: Vaping detected (VOC 200ppm + PM2.5 80) = 70 × 1.4 = **98 points + alarm**

---

### **Component 6: NOISE THREAT** (from SOUND SENSOR)

**How it works**: Loud noises = potential danger

```
Sound level in decibels:
├── > 110 dB → 90 points  (💥 Explosion/gunshot! + ALARM)
├── 90-110 dB → 70 points (🔊 Screaming/alarm)
├── 80-90 dB  → 45 points (📢 Shouting/loud music)
├── 70-80 dB  → 25 points (🗣️ Loud conversation)
├── 60-70 dB  → 10 points (💬 Normal conversation)
└── < 60 dB   → 0 points  (🤫 Quiet)
```

**Auto-Alarm Feature**:
- Triggers when > 110dB OR spike > 100dB
- Sets minimum threat level to 90 regardless of other factors
- Immediate notification to front office
- Weight: 0.10

**Multipliers**:
- Sudden spike → ×1.5 (💥 Bang/crash)
- Impact sound → ×2.0 (💢 Breaking glass)
- Door slam → ×1.3 (🚪)
- Normal → ×1.0

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
