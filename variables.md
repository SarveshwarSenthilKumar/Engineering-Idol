# 📊 COMPLETE VARIABLES & METRICS REFERENCE

Based on your comprehensive SCOPE system, here's every variable, metric, and data point you have access to:

## 🔴 **THREAT ASSESSMENT METRICS**

### Overall Threat Score
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `threat_data['overall_threat']` | float | 0-100 | Final threat score with temporal dynamics |
| `threat_data['base_threat']` | float | 0-100 | Raw threat before temporal adjustments |
| `threat_data['level']` | string | LOW/MODERATE/ELEVATED/HIGH/CRITICAL | Threat level classification |
| `threat_data['color']` | string | 🟢/🟡/🟠/🔴/⚫ | Visual indicator |
| `threat_data['response']` | string | - | Recommended action |
| `threat_data['confidence']` | float | 0-1 | Overall confidence in threat assessment |

### Temporal Dynamics
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `threat_data['temporal']['trend']` | string | stable/worsening/rapidly_worsening/improving/rapidly_improving | Direction of change |
| `threat_data['temporal']['slope']` | float | -∞ to +∞ | Rate of change (points/minute) |
| `threat_data['temporal']['acceleration']` | float | -∞ to +∞ | Change in slope (points/minute²) |
| `threat_data['temporal']['volatility']` | float | 0-100 | Standard deviation of recent threats |
| `threat_data['temporal']['persistence_factor']` | float | 1.0-2.0 | Multiplier for recurring threats |

### Threat Trajectory Predictions
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `threat_data['trajectory']['5min']` | float | 0-100 | Predicted threat in 5 minutes |
| `threat_data['trajectory']['15min']` | float | 0-100 | Predicted threat in 15 minutes |
| `threat_data['trajectory']['30min']` | float | 0-100 | Predicted threat in 30 minutes |

### Component-Level Threats (6 Components)

#### 1. **Proximity Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['proximity']['score']` | float | 0-100 | Temporally-adjusted proximity threat |
| `components['proximity']['raw_score']` | float | 0-100 | Raw proximity threat |
| `components['proximity']['confidence']` | float | 0-1 | Confidence in proximity reading |
| `components['proximity']['weight']` | float | 0-1 | Dynamic weight in final score |

#### 2. **Count Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['count']['score']` | float | 0-100 | Adjusted crowd size threat |
| `components['count']['raw_score']` | float | 0-100 | Raw count-based threat |
| `components['count']['confidence']` | float | 0-1 | Confidence in target count |
| `components['count']['weight']` | float | 0-1 | Dynamic weight |

#### 3. **Behavior Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['behavior']['score']` | float | 0-100 | Adjusted behavioral threat |
| `components['behavior']['raw_score']` | float | 0-100 | Raw behavioral threat |
| `components['behavior']['confidence']` | float | 0-1 | Confidence in behavior detection |
| `components['behavior']['weight']` | float | 0-1 | Dynamic weight |

#### 4. **Vital Signs Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['vital_signs']['score']` | float | 0-100 | Adjusted vital signs threat |
| `components['vital_signs']['raw_score']` | float | 0-100 | Raw vital signs threat |
| `components['vital_signs']['confidence']` | float | 0-1 | Confidence in vital signs |
| `components['vital_signs']['weight']` | float | 0-1 | Dynamic weight |

#### 5. **Air Quality Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['air_quality']['score']` | float | 0-100 | Adjusted air quality threat |
| `components['air_quality']['raw_score']` | float | 0-100 | Raw air quality threat |
| `components['air_quality']['confidence']` | float | 0-1 | Confidence in air quality |
| `components['air_quality']['weight']` | float | 0-1 | Dynamic weight |

#### 6. **Noise Threat**
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `components['noise']['score']` | float | 0-100 | Adjusted noise threat |
| `components['noise']['raw_score']` | float | 0-100 | Raw noise threat |
| `components['noise']['confidence']` | float | 0-1 | Confidence in noise detection |
| `components['noise']['weight']` | float | 0-1 | Dynamic weight |

---

## 🟢 **FACILITY QUALITY METRICS"

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `quality_data['quality_score']` | float | 0-100 | Overall facility quality |
| `quality_data['base_quality']` | float | 0-100 | Raw quality before smoothing |
| `quality_data['category']` | string | EXCELLENT/GOOD/FAIR/POOR/CRITICAL | Quality classification |
| `quality_data['icon']` | string | 🌟/✅/⚠️/🔴/🚨 | Visual indicator |
| `quality_data['trend']` | string | improving/stable/declining | Quality trend |
| `quality_data['adjustments']['sound']` | float | 0-100 | Sound-specific quality |
| `quality_data['adjustments']['air']` | float | 0-100 | Air-specific quality |
| `quality_data['adjustments']['occupancy']` | float | 0-100 | Occupancy-specific quality |

---

## 🔊 **SOUND ANALYSIS METRICS**

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `sound_analysis['db']` | float | 0-120 | Current sound level in decibels |
| `sound_analysis['baseline']` | float | 0-120 | Median noise floor |
| `sound_analysis['spike']` | boolean | True/False | Whether sound spike detected |
| `sound_analysis['rate_of_change']` | float | 0-∞ | How fast sound changed |
| `sound_analysis['event']` | string | quiet/conversation/crowd/door_slam/shouting/background/impact/traffic | Classified sound event |
| `sound_analysis['confidence']` | float | 0-1 | ML model confidence |

### Sound FFT Features (in `features` array)
| Index | Variable | Description |
|-------|----------|-------------|
| 0 | `db` | Decibel level |
| 1 | `dominant_freq` | Primary frequency (Hz) |
| 2 | `spectral_energy` | Total energy in spectrum |
| 3 | `spectral_centroid` | Center of mass of spectrum |
| 4 | `peak` | Peak amplitude |
| 5 | `zero_crossings` | Rate of zero crossings |
| 6 | `spectral_spread` | Spread around centroid |
| 7 | `skewness` | Asymmetry of distribution |
| 8 | `kurtosis` | "Peakedness" of distribution |
| 9 | `low_energy` | Energy in <200Hz band |
| 10 | `mid_energy` | Energy in 200-2000Hz band |
| 11 | `high_energy` | Energy in >2000Hz band |

---

## 🌬️ **AIR QUALITY METRICS**

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `odor_analysis['voc_ppm']` | float | 0-1000 | Volatile Organic Compounds (ppm) |
| `odor_analysis['voc_voltage']` | float | 0-5 | Raw MQ135 voltage |
| `odor_analysis['pm1']` | int | 0-1000 | PM1.0 concentration (µg/m³) |
| `odor_analysis['pm25']` | int | 0-1000 | PM2.5 concentration (µg/m³) |
| `odor_analysis['pm10']` | int | 0-1000 | PM10 concentration (µg/m³) |
| `odor_analysis['air_quality_index']` | float | 0-500 | Combined AQI |
| `odor_analysis['odor_type']` | string | clean_air/human_activity/dust_or_smoke/strong_chemical/noise_correlated_activity/moderate_odor | Classification |
| `odor_analysis['classification_confidence']` | float | 0-1 | Confidence in odor type |
| `odor_analysis['odor_intensity']` | float | 0-10 | Intensity score |
| `odor_analysis['odor_level']` | string | LOW/MODERATE/HIGH/SEVERE/CRITICAL | Intensity level |
| `odor_analysis['odor_trend']` | float | -∞ to +∞ | Change from baseline |
| `odor_analysis['baseline_intensity']` | float | 0-10 | Historical baseline |
| `odor_analysis['odor_anomaly']` | boolean | True/False | Anomaly detected |
| `odor_analysis['people']` | int | 0-∞ | People count from radar |

---

## 📡 **RADAR TARGET METRICS** (Per Person)

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `target['id']` | string | T00-T99 | Unique target identifier |
| `target['x']` | float | -∞ to +∞ | X-coordinate (meters) |
| `target['y']` | float | -∞ to +∞ | Y-coordinate (meters) |
| `target['distance']` | float | 0-∞ | Distance from radar (meters) |
| `target['angle']` | float | -180 to 180 | Angle from radar (degrees) |
| `target['velocity']` | float | 0-∞ | Speed (m/s) |
| `target['direction']` | string | incoming/outgoing | Movement direction |
| `target['orientation']` | string | toward/away/stationary | Facing direction |
| `target['confidence']` | float | 0-1 | Detection confidence |

### Activity & Vital Signs (Per Person)
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `target['activity']` | string | stationary/sitting/walking/running/transition/unknown | Current activity |
| `target['activity_confidence']` | float | 0-1 | Activity recognition confidence |
| `target['breathing_rate']` | float | 0-40 | Breaths per minute |
| `target['breathing_confidence']` | float | 0-1 | Breathing detection confidence |
| `target['abnormal_breathing']` | boolean | True/False | Flag for abnormal rate (<8 or >24) |

### Motion Tracking (Per Person)
| Variable | Type | Description |
|----------|------|-------------|
| `target['vx']` | float | Velocity in X direction |
| `target['vy']` | float | Velocity in Y direction |
| `target['ax']` | float | Acceleration in X |
| `target['ay']` | float | Acceleration in Y |
| `target['speed']` | float | Magnitude of velocity |
| `target['timestamp']` | float | Last update time |

---

## 📊 **RADAR AGGREGATE METRICS**

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `radar_data['target_count']` | int | 0-20 | Total people detected |
| `radar_data['format']` | string | rd03d/ld2410/unknown | Radar data format |

### Motion Patterns
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `motion_patterns['pattern']` | string | no_detections/low_activity/normal_activity/high_activity/chaotic | Overall activity pattern |
| `motion_patterns['activity_level']` | float | 0-1 | Proportion of moving targets |
| `motion_patterns['total_targets']` | int | 0-20 | Total people |
| `motion_patterns['active_targets']` | int | 0-20 | Moving people |

### Activity Events
| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `event['type']` | string | entry/exit/possible_fall | Event type |
| `event['magnitude']` | int | 0-∞ | Number of people in event |
| `event['confidence']` | float | 0-1 | Event detection confidence |
| `event['target_id']` | string | - | Target involved (for falls) |

---

## 📈 **HISTORICAL METRICS** (Deques)

### Threat History (last 1000 entries)
```python
threat_history = deque(maxlen=1000)  # Each entry contains full threat_data
```

### Score History (last 100 entries)
```python
score_history = deque(maxlen=100)  # Facility scores
```

### Radar History (last 30 entries)
```python
radar_history = deque(maxlen=30)  # Raw radar frames
```

### Odor History (last 60 entries)
```python
odor_history = deque(maxlen=60)  # Odor intensity scores
```

### Sound History (last WINDOW_SIZE entries)
```python
sound_history = deque(maxlen=WINDOW_SIZE)  # Raw sound samples
db_history = deque(maxlen=50)  # Recent dB levels
```

### Breathing History (per target)
```python
breathing_buffers[target_id] = deque(maxlen=150)  # Phase data for breathing detection
```

---

## 🎯 **DERIVED METRICS YOU CAN CALCULATE**

### 1. **Rate of Change**
```python
# How fast things are changing
threat_acceleration = threat_data['temporal']['acceleration']
sound_trend = sound_analysis['rate_of_change']
odor_momentum = odor_analysis['odor_trend']
```

### 2. **Risk Scores**
```python
# Composite risk by category
physical_risk = (proximity_score + count_score + behavior_score) / 3
health_risk = (vital_signs_score + air_quality_score) / 2
facility_risk = (noise_score + air_quality_score) / 2
```

### 3. **Occupancy Metrics**
```python
# Space utilization
occupancy_rate = target_count / max_expected_capacity
crowding_index = motion_patterns['crowd_density']  # people/m²
turnover_rate = activity_events.count('entry') + activity_events.count('exit')
```

### 4. **Temporal Patterns**
```python
# Time-based patterns
hour_of_day = datetime.now().hour
day_of_week = datetime.now().weekday()
time_since_last_event = threat_data['temporal']['time_since_last_event']
```

### 5. **Sensor Reliability**
```python
# Can track these manually
sensor_reliability = {
    'radar': radar_processor.serial_conn is not None,
    'pms5003': pms is not None,
    'mq135': mq135_channel is not None,
    'sound': sound_channel is not None
}
```

### 6. **Alert Thresholds**
```python
# Pre-defined alert levels
CRITICAL_THREAT = threat_data['overall_threat'] > 80
HIGH_THREAT = threat_data['overall_threat'] > 60
RAPID_ESCALATION = threat_data['temporal']['trend'] == 'rapidly_worsening'
ABNORMAL_VITALS = any(t.get('abnormal_breathing') for t in targets)
AIR_QUALITY_ALERT = odor_analysis and odor_analysis['air_quality_index'] > 150
```

### 7. **Composite Indices**
```python
# Combined metrics
danger_index = (threat_data['overall_threat'] * 
                threat_data['temporal']['persistence_factor'])

comfort_index = 100 - threat_data['overall_threat'] * 0.5

urgency_score = (threat_data['overall_threat'] * 
                 (1 + abs(threat_data['temporal']['slope']) / 10))
```

---

## 📝 **COMPLETE DATA STRUCTURE EXAMPLE**

```python
full_system_state = {
    'timestamp': datetime.now().isoformat(),
    'threat': {
        'overall': 67.5,
        'level': 'ELEVATED',
        'confidence': 0.82,
        'temporal': {
            'trend': 'worsening',
            'slope': 2.3,
            'acceleration': 0.15,
            'persistence': 1.8
        },
        'trajectory': {
            '5min': 72,
            '15min': 81,
            '30min': 89
        }
    },
    'quality': {
        'score': 72.4,
        'category': 'FAIR',
        'trend': 'stable'
    },
    'environment': {
        'sound': {
            'db': 58.2,
            'event': 'conversation',
            'spike': False
        },
        'air': {
            'voc': 85.3,
            'pm25': 32,
            'aqi': 118,
            'odor': 'human_activity'
        },
        'radar': {
            'people': 2,
            'targets': [
                {
                    'id': 'T01',
                    'distance': 2.3,
                    'activity': 'walking',
                    'breathing': 16.2
                },
                {
                    'id': 'T02',
                    'distance': 1.8,
                    'activity': 'sitting',
                    'breathing': 14.7
                }
            ],
            'pattern': 'normal_activity'
        }
    },
    'alerts': [
        'RAPID_ESCALATION',
        'AIR_QUALITY_ALERT'
    ],
    'recommendations': [
        'Monitor situation',
        'Consider ventilation'
    ]
}
```

## 🎨 **VISUALIZATION METRICS**

For dashboards, you have these visualization-ready metrics:

### Bar Chart Data
```python
threat_components = {
    'Proximity': 45,
    'Count': 30,
    'Behavior': 25,
    'Vital Signs': 40,
    'Air Quality': 35,
    'Noise': 20
}
```

### Time Series Data
```python
threat_history_values = [t['overall_threat'] for t in threat_history]
quality_history_values = [q for q in quality_scorer.quality_history]
```

### Gauges/Meters
```python
gauges = {
    'threat_meter': threat_data['overall_threat'],
    'quality_meter': quality_data['quality_score'],
    'occupancy_meter': len(targets) / 5 * 100,  # Scaled to 5 people max
    'noise_meter': sound_analysis['db'] / 100 * 100  # Scaled to 100dB
}
```

### Heat Map Data
```python
# For radar positions
target_positions = [(t['x'], t['y']) for t in targets]

# For threat over time
time_threat_matrix = [
    [t['overall_threat'] for t in threat_history[-60:]]  # Last hour
]
```
