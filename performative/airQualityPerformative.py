#!/usr/bin/env python3
"""
Air Quality Detection Performative Visualization
Demonstrates the intelligent air quality detection system from rasppi.py
Shows multi-sensor fusion, classification, and threat assessment in real-time
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import time
from datetime import datetime
from collections import deque
import math

# Configuration from rasppi.py
VOC_CLEAN_THRESHOLD = 50
VOC_ACTIVITY_THRESHOLD = 80
VOC_CHEMICAL_THRESHOLD = 120
VOC_SMOKING_THRESHOLD = 150
VOC_VAPING_THRESHOLD = 180

PM_CLEAN_THRESHOLD = 10
PM_SMOKE_THRESHOLD = 40
PM_VAPING_THRESHOLD = 60

LOUD_THRESHOLD_DB = 65

class AirQualityPerformative:
    def __init__(self):
        self.fig, self.axes = plt.subplots(2, 3, figsize=(15, 10))
        self.fig.patch.set_facecolor('#1a1a1a')
        
        # Data storage
        self.time_history = deque(maxlen=100)
        self.voc_history = deque(maxlen=100)
        self.pm25_history = deque(maxlen=100)
        self.aqi_history = deque(maxlen=100)
        self.threat_history = deque(maxlen=100)
        self.odor_history = deque(maxlen=60)
        
        # Baselines (like rasppi.py)
        self.voc_baseline = None
        self.pm_baseline = None
        
        # Current state
        self.current_time = 0
        self.current_voc = 30
        self.current_pm25 = 15
        self.current_people = 2
        self.current_noise = 45
        self.current_odor_type = "clean_air"
        self.current_threat = 0
        
        self.setup_plots()
        
    def setup_plots(self):
        """Setup all visualization panels"""
        titles = [
            'VOC Concentration (PPM)',
            'PM2.5 Particulate Matter',
            'Air Quality Index (AQI)',
            'Odor Classification',
            'Sensor Fusion & Threat',
            'Detection Timeline'
        ]
        
        for i, ax in enumerate(self.axes.flat):
            ax.set_facecolor('#2a2a2a')
            ax.set_title(titles[i], color='#00ff00', fontweight='bold', fontsize=12)
            ax.grid(True, alpha=0.2, color='#444444')
            
            # Style axes
            ax.tick_params(colors='#00ff00')
            for spine in ax.spines.values():
                spine.set_color('#00ff00')
        
        # Setup specific plots
        self.setup_voc_plot()
        self.setup_pm25_plot()
        self.setup_aqi_plot()
        self.setup_classification_plot()
        self.setup_fusion_plot()
        self.setup_timeline_plot()
        
    def setup_voc_plot(self):
        """Setup VOC concentration plot"""
        self.voc_line, = self.axes[0, 0].plot([], [], 'cyan', linewidth=2, label='VOC')
        self.voc_baseline_line, = self.axes[0, 0].plot([], [], 'yellow', linestyle='--', alpha=0.7, label='Baseline')
        self.axes[0, 0].axhline(y=VOC_CLEAN_THRESHOLD, color='green', linestyle=':', alpha=0.5, label='Clean')
        self.axes[0, 0].axhline(y=VOC_ACTIVITY_THRESHOLD, color='yellow', linestyle=':', alpha=0.5, label='Activity')
        self.axes[0, 0].axhline(y=VOC_CHEMICAL_THRESHOLD, color='orange', linestyle=':', alpha=0.5, label='Chemical')
        self.axes[0, 0].axhline(y=VOC_SMOKING_THRESHOLD, color='red', linestyle=':', alpha=0.5, label='Smoking')
        self.axes[0, 0].set_ylabel('VOC (PPM)', color='#00ff00')
        self.axes[0, 0].set_ylim(0, 200)
        self.axes[0, 0].legend(loc='upper right', fontsize=8)
        
    def setup_pm25_plot(self):
        """Setup PM2.5 particulate plot"""
        self.pm25_line, = self.axes[0, 1].plot([], [], 'orange', linewidth=2, label='PM2.5')
        self.pm_baseline_line, = self.axes[0, 1].plot([], [], 'yellow', linestyle='--', alpha=0.7, label='Baseline')
        self.axes[0, 1].axhline(y=PM_CLEAN_THRESHOLD, color='green', linestyle=':', alpha=0.5, label='Clean')
        self.axes[0, 1].axhline(y=PM_SMOKE_THRESHOLD, color='orange', linestyle=':', alpha=0.5, label='Smoke')
        self.axes[0, 1].axhline(y=PM_VAPING_THRESHOLD, color='red', linestyle=':', alpha=0.5, label='Vaping')
        self.axes[0, 1].set_ylabel('PM2.5 (μg/m³)', color='#00ff00')
        self.axes[0, 1].set_ylim(0, 100)
        self.axes[0, 1].legend(loc='upper right', fontsize=8)
        
    def setup_aqi_plot(self):
        """Setup AQI plot"""
        self.aqi_line, = self.axes[0, 2].plot([], [], 'lime', linewidth=2, label='AQI')
        self.axes[0, 2].axhline(y=50, color='yellow', linestyle=':', alpha=0.5, label='Moderate')
        self.axes[0, 2].axhline(y=100, color='orange', linestyle=':', alpha=0.5, label='Unhealthy')
        self.axes[0, 2].axhline(y=150, color='red', linestyle=':', alpha=0.5, label='Very Unhealthy')
        self.axes[0, 2].set_ylabel('AQI (0-500)', color='#00ff00')
        self.axes[0, 2].set_ylim(0, 200)
        self.axes[0, 2].legend(loc='upper right', fontsize=8)
        
    def setup_classification_plot(self):
        """Setup odor classification visualization"""
        self.classification_ax = self.axes[1, 0]
        self.classification_ax.set_xlim(0, 10)
        self.classification_ax.set_ylim(0, 10)
        self.classification_ax.set_xticks([])
        self.classification_ax.set_yticks([])
        
        # Create classification zones
        self.create_classification_zones()
        
        # Current detection point
        self.detection_point, = self.classification_ax.plot([], [], 'ro', markersize=15, label='Current Detection')
        self.classification_text = self.classification_ax.text(5, 9, '', fontsize=12, color='white', 
                                                               ha='center', fontweight='bold')
        
    def create_classification_zones(self):
        """Create visual classification zones"""
        zones = [
            (0, 5, 0, 5, 'Clean Air', '#00ff00'),
            (5, 10, 0, 5, 'Activity', '#ffff00'),
            (0, 5, 5, 10, 'Smoke/Dust', '#ff8800'),
            (5, 10, 5, 10, 'Chemical', '#ff0000')
        ]
        
        for x1, x2, y1, y2, label, color in zones:
            rect = plt.Rectangle((x1, y1), x2-x1, y2-y1, alpha=0.3, facecolor=color, edgecolor='white')
            self.classification_ax.add_patch(rect)
            self.classification_ax.text((x1+x2)/2, (y1+y2)/2, label, fontsize=10, 
                                        color='white', ha='center', va='center', fontweight='bold')
        
        self.classification_ax.set_xlabel('VOC Level', color='#00ff00')
        self.classification_ax.set_ylabel('PM2.5 Level', color='#00ff00')
        
    def setup_fusion_plot(self):
        """Setup sensor fusion and threat assessment"""
        self.fusion_ax = self.axes[1, 1]
        self.fusion_ax.set_xlim(0, 5)
        self.fusion_ax.set_ylim(0, 5)
        self.fusion_ax.set_xticks([0.5, 1.5, 2.5, 3.5, 4.5])
        self.fusion_ax.set_xticklabels(['VOC', 'PM2.5', 'People', 'Noise', 'Trend'])
        self.fusion_ax.set_yticks([1, 2, 3, 4])
        self.fusion_ax.set_yticklabels(['Low', 'Med', 'High', 'Critical'])
        
        # Sensor bars
        self.sensor_bars = self.fusion_ax.bar([0.5, 1.5, 2.5, 3.5, 4.5], [0, 0, 0, 0, 0], 
                                             color=['cyan', 'orange', 'lime', 'yellow', 'red'])
        
        # Threat indicator
        self.threat_bar = self.fusion_ax.bar([2.5], [0], color='red', alpha=0.5, width=3)
        
        self.fusion_ax.set_ylabel('Intensity', color='#00ff00')
        self.fusion_ax.set_title('Multi-Sensor Fusion & Threat', color='#00ff00', fontweight='bold')
        
    def setup_timeline_plot(self):
        """Setup detection timeline"""
        self.timeline_ax = self.axes[1, 2]
        self.timeline_ax.set_xlim(0, 100)
        self.timeline_ax.set_ylim(0, 5)
        
        # Timeline lines for different metrics
        self.threat_timeline, = self.timeline_ax.plot([], [], 'red', linewidth=2, label='Threat')
        self.aqi_timeline, = self.timeline_ax.plot([], [], 'lime', linewidth=2, alpha=0.7, label='AQI/10')
        
        self.timeline_ax.set_xlabel('Time (seconds)', color='#00ff00')
        self.timeline_ax.set_ylabel('Level', color='#00ff00')
        self.timeline_ax.legend(loc='upper right', fontsize=8)
        
    def compute_mq135_ppm(self, voltage):
        """Convert MQ135 voltage to ppm (from rasppi.py)"""
        if voltage <= 0 or math.isnan(voltage):
            return 0
        
        try:
            RLOAD = 10000
            VCC = 5.0
            R0 = 20000
            
            rs = RLOAD * (VCC / max(voltage, 0.001) - 1)
            ratio = rs / R0
            ratio = np.clip(ratio, 0.1, 10)
            
            a = 116.6020682
            b = -2.769034857
            ppm = a * (ratio ** b)
            
            return max(0, min(ppm, 1000))
        except:
            return 0
    
    def classify_odor(self, voc_ppm, pm25, people, noise_db):
        """Classify odor type with confidence (from rasppi.py)"""
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
    
    def compute_odor_intensity(self, voc_ppm, pm25, people, noise_db, trend):
        """Calculate odor intensity (from rasppi.py)"""
        score = 0
        score += min(voc_ppm / 50, 4)
        score += min(pm25 / 25, 3)
        score += min(people / 3, 2)
        
        if noise_db > LOUD_THRESHOLD_DB:
            score += 0.5
        
        if trend > 20:
            score += 0.5
        elif trend > 10:
            score += 0.25
        
        return score
    
    def calculate_air_quality_threat(self, odor_data):
        """Calculate threat from air quality sensors (from rasppi.py)"""
        if not odor_data:
            return 0, 0.3
        
        threat_score = 0
        confidence = odor_data.get('classification_confidence', 0.5)
        
        odor_type = odor_data.get('odor_type', 'clean_air')
        odor_level = odor_data.get('odor_level', 'LOW')
        aqi = odor_data.get('air_quality_index', 0)
        
        if odor_type == 'dust_or_smoke':
            threat_score = min(80, aqi / 2)
        elif odor_type == 'strong_chemical':
            threat_score = min(90, aqi / 1.5)
        elif odor_type == 'human_activity':
            threat_score = min(40, aqi / 3)
        
        return threat_score, confidence
    
    def simulate_sensor_data(self):
        """Simulate realistic sensor data changes"""
        self.current_time += 0.1
        
        # Simulate different scenarios
        scenario = int(self.current_time / 10) % 6
        
        if scenario == 0:  # Clean air
            voc_target = 25 + 10 * np.sin(self.current_time * 0.5)
            pm25_target = 8 + 3 * np.sin(self.current_time * 0.3)
            people_target = 1
            noise_target = 40
            
        elif scenario == 1:  # Human activity
            voc_target = 85 + 15 * np.sin(self.current_time * 0.4)
            pm25_target = 12 + 5 * np.sin(self.current_time * 0.6)
            people_target = 3
            noise_target = 55
            
        elif scenario == 2:  # Smoking/vaping
            voc_target = 160 + 25 * np.sin(self.current_time * 0.3)
            pm25_target = 65 + 15 * np.sin(self.current_time * 0.4)
            people_target = 2
            noise_target = 45
            
        elif scenario == 3:  # Chemical spill
            voc_target = 140 + 30 * np.sin(self.current_time * 0.2)
            pm25_target = 18 + 8 * np.sin(self.current_time * 0.5)
            people_target = 1
            noise_target = 50
            
        elif scenario == 4:  # Dust/particulate
            voc_target = 45 + 12 * np.sin(self.current_time * 0.4)
            pm25_target = 55 + 20 * np.sin(self.current_time * 0.3)
            people_target = 2
            noise_target = 60
            
        else:  # Mixed activity
            voc_target = 95 + 20 * np.sin(self.current_time * 0.3)
            pm25_target = 35 + 10 * np.sin(self.current_time * 0.4)
            people_target = 4
            noise_target = 70
        
        # Smooth transitions
        self.current_voc = 0.9 * self.current_voc + 0.1 * voc_target
        self.current_pm25 = 0.9 * self.current_pm25 + 0.1 * pm25_target
        self.current_people = people_target
        self.current_noise = noise_target
        
        # Add noise
        self.current_voc += random.uniform(-2, 2)
        self.current_pm25 += random.uniform(-1, 1)
        
        # Update baselines
        if self.voc_baseline is None:
            self.voc_baseline = self.current_voc
        else:
            self.voc_baseline = 0.95 * self.voc_baseline + 0.05 * self.current_voc
            
        if self.pm_baseline is None:
            self.pm_baseline = self.current_pm25
        else:
            self.pm_baseline = 0.95 * self.pm_baseline + 0.05 * self.current_pm25
    
    def analyze_air_quality(self):
        """Perform complete air quality analysis (from rasppi.py)"""
        # Simulate sensor readings
        self.simulate_sensor_data()
        
        # Calculate AQI
        aqi = (self.current_voc / 100 * 50) + (self.current_pm25 / 35 * 50)
        aqi = min(500, max(0, aqi))
        
        # Calculate trend
        trend = self.current_voc - self.voc_baseline
        
        # Classify odor
        odor_type, confidence = self.classify_odor(
            self.current_voc, self.current_pm25, 
            self.current_people, self.current_noise
        )
        
        # Calculate intensity
        intensity = self.compute_odor_intensity(
            self.current_voc, self.current_pm25, 
            self.current_people, self.current_noise, trend
        )
        
        # Determine level
        if intensity < 2:
            level = "LOW"
        elif intensity < 3.5:
            level = "MODERATE"
        elif intensity < 5:
            level = "HIGH"
        elif intensity < 6.5:
            level = "SEVERE"
        else:
            level = "CRITICAL"
        
        # Calculate threat
        odor_data = {
            'odor_type': odor_type,
            'classification_confidence': confidence,
            'odor_level': level,
            'air_quality_index': aqi
        }
        
        threat_score, threat_confidence = self.calculate_air_quality_threat(odor_data)
        
        # Store results
        self.current_odor_type = odor_type
        self.current_threat = threat_score
        
        return {
            'voc_ppm': self.current_voc,
            'pm25': self.current_pm25,
            'aqi': aqi,
            'odor_type': odor_type,
            'confidence': confidence,
            'intensity': intensity,
            'level': level,
            'trend': trend,
            'threat': threat_score,
            'people': self.current_people,
            'noise': self.current_noise
        }
    
    def update(self, frame):
        """Update visualization"""
        # Analyze air quality
        analysis = self.analyze_air_quality()
        
        # Update history
        self.time_history.append(self.current_time)
        self.voc_history.append(analysis['voc_ppm'])
        self.pm25_history.append(analysis['pm25'])
        self.aqi_history.append(analysis['aqi'])
        self.threat_history.append(analysis['threat'])
        
        # Update VOC plot
        if len(self.time_history) > 1:
            self.voc_line.set_data(list(self.time_history), list(self.voc_history))
            self.voc_baseline_line.set_data([min(self.time_history), max(self.time_history)], 
                                           [self.voc_baseline, self.voc_baseline])
            self.axes[0, 0].set_xlim(max(0, self.current_time - 10), self.current_time + 0.5)
        
        # Update PM2.5 plot
        if len(self.time_history) > 1:
            self.pm25_line.set_data(list(self.time_history), list(self.pm25_history))
            self.pm_baseline_line.set_data([min(self.time_history), max(self.time_history)], 
                                          [self.pm_baseline, self.pm_baseline])
            self.axes[0, 1].set_xlim(max(0, self.current_time - 10), self.current_time + 0.5)
        
        # Update AQI plot
        if len(self.time_history) > 1:
            self.aqi_line.set_data(list(self.time_history), list(self.aqi_history))
            self.axes[0, 2].set_xlim(max(0, self.current_time - 10), self.current_time + 0.5)
        
        # Update classification plot
        voc_norm = min(10, analysis['voc_ppm'] / 20)
        pm25_norm = min(10, analysis['pm25'] / 10)
        self.detection_point.set_data([voc_norm], [pm25_norm])
        self.classification_text.set_text(f"{analysis['odor_type'].replace('_', ' ').title()}\n"
                                         f"Confidence: {analysis['confidence']:.2f}\n"
                                         f"Level: {analysis['level']}")
        
        # Update fusion plot
        sensor_values = [
            min(4, analysis['voc_ppm'] / 50),
            min(4, analysis['pm25'] / 25),
            min(4, analysis['people'] / 2),
            min(4, analysis['noise'] / 50),
            min(4, abs(analysis['trend']) / 10)
        ]
        
        for bar, value in zip(self.sensor_bars, sensor_values):
            bar.set_height(value)
        
        # Update threat bar
        self.threat_bar[0].set_height(min(4, analysis['threat'] / 25))
        
        # Update timeline
        if len(self.time_history) > 1:
            time_array = list(self.time_history)
            self.threat_timeline.set_data(time_array, list(self.threat_history))
            self.aqi_timeline.set_data(time_array, [a/10 for a in self.aqi_history])
            self.timeline_ax.set_xlim(max(0, self.current_time - 100), self.current_time + 0.5)
        
        # Update title with current status
        self.fig.suptitle(
            f'Air Quality Detection System - {analysis["odor_type"].replace("_", " ").title()} - '
            f'Threat: {analysis["threat"]:.1f} - AQI: {analysis["aqi"]:.0f}',
            fontsize=14, color='#00ff00', fontweight='bold'
        )
        
        return (self.voc_line, self.voc_baseline_line, self.pm25_line, self.pm_baseline_line, 
                self.aqi_line, self.detection_point, self.classification_text, 
                self.threat_timeline, self.aqi_timeline)
    
    def animate(self):
        """Create animation"""
        print("🌫️ Starting Air Quality Detection Visualization...")
        print("📊 Demonstrating multi-sensor fusion and intelligent classification")
        print("⚠️ Real-time threat assessment based on VOC, PM2.5, and contextual data")
        
        anim = animation.FuncAnimation(
            self.fig, self.update, frames=1000,
            interval=100, blit=False, repeat=True
        )
        
        plt.tight_layout()
        plt.show()
        
        return anim

def main():
    """Main function"""
    print("=" * 60)
    print("🔍 AIR QUALITY DETECTION PERFORMATIVE VISUALIZATION")
    print("=" * 60)
    print("📡 Multi-Sensor Fusion System:")
    print("   • MQ135 VOC Sensor")
    print("   • PMS5003 Particulate Matter Sensor")
    print("   • Microphone (Noise Correlation)")
    print("   • Radar (People Count)")
    print()
    print("🧠 Intelligent Classification:")
    print("   • Clean Air Detection")
    print("   • Human Activity Recognition")
    print("   • Smoking/Vaping Detection")
    print("   • Chemical Spill Detection")
    print("   • Dust/Particulate Monitoring")
    print()
    print("⚡ Real-time Analysis:")
    print("   • Baseline Learning")
    print("   • Trend Analysis")
    print("   • Anomaly Detection")
    print("   • Threat Assessment")
    print("   • EPA AQI Calculation")
    print("=" * 60)
    print()
    
    # Create and run visualization
    air_viz = AirQualityPerformative()
    anim = air_viz.animate()
    
    print("✅ Air quality detection visualization complete!")

if __name__ == "__main__":
    main()
