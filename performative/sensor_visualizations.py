#!/usr/bin/env python3
"""
Sensor Visualization GIF Generator
Creates animated GIFs for all SCOPE sensors: mmWave Radar, Sound, Air Quality
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from matplotlib.collections import LineCollection
import random
from datetime import datetime, timedelta
import os

# Set style for professional look
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.facecolor'] = '#1a1a1a'
plt.rcParams['axes.facecolor'] = '#2a2a2a'
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'

class mmWaveRadarVisualizer:
    """mmWave Radar Sensor Visualization"""
    
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        self.time_step = 0
        self.targets = []
        self.max_range = 8.0
        self.setup_plot()
        
    def setup_plot(self):
        """Setup radar plot with professional styling"""
        self.ax.set_ylim(0, self.max_range)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)
        self.ax.set_title('mmWave Radar - 60GHz Ultra-Wideband', 
                         fontsize=16, fontweight='bold', pad=20, color='cyan')
        
        # Range circles
        for r in np.arange(1, self.max_range + 1, 1):
            circle = plt.Circle((0, 0), r, fill=False, color='gray', alpha=0.3, linewidth=0.5)
            self.ax.add_patch(circle)
            
        # Angle lines
        for angle in np.arange(0, 360, 30):
            self.ax.plot([angle * np.pi / 180, angle * np.pi / 180], 
                        [0, self.max_range], 'gray', alpha=0.3, linewidth=0.5)
        
        # Initialize target scatter plot
        self.target_scatter = self.ax.scatter([], [], c=[], s=[], cmap='plasma', 
                                             vmin=0, vmax=1, alpha=0.8, edgecolors='white', linewidth=2)
        
        # Initialize trajectory lines
        self.trajectory_lines = []
        for i in range(3):  # Max 3 targets
            line, = self.ax.plot([], [], 'cyan', alpha=0.5, linewidth=2)
            self.trajectory_lines.append(line)
        
        # Info text
        self.info_text = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes,
                                    fontsize=10, verticalalignment='top',
                                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
    def generate_targets(self):
        """Generate realistic targets with smooth movement"""
        self.time_step += 1
        t = self.time_step * 0.1
        targets = []
        
        for i in range(3):  # 3 targets
            # Smooth circular movement
            base_distance = 3.0 + 1.5 * np.sin(t + i * 2.09)
            angle = (t * 0.2 + i * 2.09) % (2 * np.pi)
            
            x = base_distance * np.cos(angle)
            y = base_distance * np.sin(angle)
            distance = np.sqrt(x**2 + y**2)
            
            # Velocity based on movement
            velocity = abs(1.5 * np.sin(t * 0.15 + i))
            
            # Activity determination
            if velocity > 1.2:
                activity = 'running'
            elif velocity > 0.6:
                activity = 'walking'
            elif velocity > 0.2:
                activity = 'transition'
            else:
                activity = 'stationary'
            
            # Breathing rate
            base_breathing = 12 + 4 * np.sin(t * 0.05 + i)
            if activity == 'running':
                breathing_rate = base_breathing + random.uniform(4, 8)
            elif activity == 'walking':
                breathing_rate = base_breathing + random.uniform(2, 5)
            else:
                breathing_rate = base_breathing + random.uniform(-2, 3)
            
            # Confidence
            confidence = 0.92 + 0.05 * np.sin(t * 0.1 + i)
            
            targets.append({
                'angle': angle,
                'distance': distance,
                'velocity': velocity,
                'activity': activity,
                'breathing_rate': breathing_rate,
                'confidence': confidence,
                'x': x,
                'y': y
            })
        
        return targets
    
    def update(self, frame):
        """Update animation frame"""
        self.targets = self.generate_targets()
        
        if self.targets:
            angles = [t['angle'] for t in self.targets]
            distances = [t['distance'] for t in self.targets]
            confidences = [t['confidence'] for t in self.targets]
            sizes = [200 * t['confidence'] for t in self.targets]
            
            # Update scatter plot
            self.target_scatter.set_offsets(np.c_[angles, distances])
            self.target_scatter.set_array(np.array(confidences))
            self.target_scatter.set_sizes(sizes)
            
            # Update trajectories
            for i, (target, line) in enumerate(zip(self.targets, self.trajectory_lines)):
                if i < len(self.targets):
                    # Create trajectory trail
                    trail_angles = []
                    trail_distances = []
                    for j in range(20):  # 20 frame trail
                        trail_t = (self.time_step - j) * 0.1
                        trail_distance = 3.0 + 1.5 * np.sin(trail_t + i * 2.09)
                        trail_angle = (trail_t * 0.2 + i * 2.09) % (2 * np.pi)
                        trail_angles.append(trail_angle)
                        trail_distances.append(trail_distance)
                    
                    line.set_data(trail_angles, trail_distances)
        
        # Update info text
        info = f"Targets: {len(self.targets)}\n"
        info += f"Max Range: {self.max_range}m\n"
        info += f"Resolution: 3.75cm\n"
        info += f"Update: 10Hz"
        for i, target in enumerate(self.targets):
            info += f"\nT{i+1}: {target['activity']} | {target['velocity']:.1f}m/s | {target['breathing_rate']:.0f}bpm"
        
        self.info_text.set_text(info)
        
        return [self.target_scatter, self.info_text] + self.trajectory_lines
    
    def create_gif(self, filename='mmwave_radar.gif', frames=100):
        """Create animated GIF"""
        print(f"Creating mmWave Radar GIF: {filename}")
        
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=100, blit=True, repeat=True)
        
        # Save GIF
        writer = animation.PillowWriter(fps=10, metadata=dict(artist='SCOPE System'))
        anim.save(filename, writer=writer)
        print(f"Saved: {filename}")
        
        plt.close()
        return anim

class SoundSensorVisualizer:
    """Sound Sensor Visualization"""
    
    def __init__(self):
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(12, 10))
        self.time_step = 0
        self.history_length = 50
        self.setup_plot()
        
    def setup_plot(self):
        """Setup sound sensor plots"""
        self.fig.suptitle('Sound Sensor - High-Fidelity Acoustic Analysis', 
                         fontsize=16, fontweight='bold', color='lime')
        
        # Time series plot
        self.ax1.set_title('Sound Pressure Level (dB)', fontsize=12, color='lime')
        self.ax1.set_ylabel('dB', fontsize=10)
        self.ax1.set_ylim(20, 120)
        self.ax1.grid(True, alpha=0.3)
        
        self.db_line, = self.ax1.plot([], [], 'lime', linewidth=2, label='SPL')
        self.spike_scatter = self.ax1.scatter([], [], c='red', s=50, alpha=0.8, label='Spikes')
        self.ax1.legend(loc='upper right')
        
        # Frequency spectrum
        self.ax2.set_title('Frequency Spectrum', fontsize=12, color='lime')
        self.ax2.set_ylabel('Magnitude', fontsize=10)
        self.ax2.set_xlabel('Frequency (Hz)', fontsize=10)
        self.ax2.set_xlim(0, 5000)
        self.ax2.set_ylim(0, 1)
        self.ax2.grid(True, alpha=0.3)
        
        self.spectrum_line, = self.ax2.plot([], [], 'cyan', linewidth=2)
        
        # Spectrogram
        self.ax3.set_title('Spectrogram', fontsize=12, color='lime')
        self.ax3.set_ylabel('Frequency (Hz)', fontsize=10)
        self.ax3.set_xlabel('Time (s)', fontsize=10)
        self.ax3.set_ylim(0, 5000)
        
        # Initialize spectrogram data
        self.spectrogram_data = np.zeros((50, 100))
        self.spectrogram_img = self.ax3.imshow(self.spectrogram_data, aspect='auto', 
                                              cmap='hot', vmin=0, vmax=1,
                                              extent=[0, 10, 0, 5000])
        
        # Info text
        self.info_text = self.fig.text(0.02, 0.95, '', fontsize=10, 
                                     transform=self.fig.transFigure,
                                     bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        plt.tight_layout()
        
    def generate_sound_data(self):
        """Generate realistic sound data"""
        self.time_step += 1
        t = self.time_step * 0.1
        
        # Base sound level with variations
        base_db = 50 + 20 * np.sin(t * 0.1)
        
        # Random spikes
        spike_prob = 0.1
        spike = random.random() < spike_prob
        if spike:
            db = base_db + random.uniform(15, 40)
        else:
            db = base_db + random.uniform(-5, 5)
        
        # Generate frequency spectrum
        frequencies = np.linspace(0, 5000, 100)
        spectrum = np.random.rand(100) * 0.5
        
        # Add dominant frequency
        dominant_freq = random.uniform(100, 2000)
        dominant_idx = int(dominant_freq / 50)
        spectrum[dominant_idx] = 1.0
        
        # Smooth spectrum
        from scipy.ndimage import gaussian_filter1d
        spectrum = gaussian_filter1d(spectrum, sigma=2)
        
        # Determine event type
        if db > 80:
            event = 'impact' if random.random() < 0.3 else 'door_slam'
        elif db > 70:
            event = 'shouting' if random.random() < 0.4 else 'crowd'
        elif db > 60:
            event = 'conversation'
        else:
            event = 'background'
        
        return {
            'db': db,
            'spike': spike,
            'frequencies': frequencies,
            'spectrum': spectrum,
            'event': event,
            'dominant_freq': dominant_freq
        }
    
    def update(self, frame):
        """Update animation frame"""
        sound_data = self.generate_sound_data()
        
        # Update time series
        if not hasattr(self, 'db_history'):
            self.db_history = []
            self.time_history = []
            self.spike_times = []
            self.spike_values = []
        
        self.db_history.append(sound_data['db'])
        self.time_history.append(self.time_step * 0.1)
        
        if sound_data['spike']:
            self.spike_times.append(self.time_step * 0.1)
            self.spike_values.append(sound_data['db'])
        
        # Keep only recent history
        if len(self.db_history) > self.history_length:
            self.db_history.pop(0)
            self.time_history.pop(0)
            if self.spike_times and self.spike_times[0] < self.time_history[0]:
                self.spike_times.pop(0)
                self.spike_values.pop(0)
        
        # Update plots
        self.db_line.set_data(self.time_history, self.db_history)
        self.spike_scatter.set_offsets(np.c_[self.spike_times, self.spike_values])
        
        # Update spectrum
        self.spectrum_line.set_data(sound_data['frequencies'], sound_data['spectrum'])
        
        # Update spectrogram
        self.spectrogram_data = np.roll(self.spectrogram_data, -1, axis=1)
        self.spectrogram_data[:, -1] = sound_data['spectrum']
        self.spectrogram_img.set_data(self.spectrogram_data)
        
        # Update info text
        info = f"Event: {sound_data['event']}\n"
        info += f"SPL: {sound_data['db']:.1f} dB\n"
        info += f"Dominant: {sound_data['dominant_freq']:.0f} Hz\n"
        info += f"Sample Rate: 44.1 kHz\n"
        info += f"Dynamic Range: 30-120 dB"
        
        self.info_text.set_text(info)
        
        # Adjust x-axis limits
        if self.time_history:
            self.ax1.set_xlim(max(0, self.time_history[-1] - 5), self.time_history[-1] + 0.5)
        
        return [self.db_line, self.spike_scatter, self.spectrum_line, 
                self.spectrogram_img, self.info_text]
    
    def create_gif(self, filename='sound_sensor.gif', frames=100):
        """Create animated GIF"""
        print(f"Creating Sound Sensor GIF: {filename}")
        
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=100, blit=True, repeat=True)
        
        # Save GIF
        writer = animation.PillowWriter(fps=10, metadata=dict(artist='SCOPE System'))
        anim.save(filename, writer=writer)
        print(f"Saved: {filename}")
        
        plt.close()
        return anim

class AirQualityVisualizer:
    """Air Quality Sensor Visualization"""
    
    def __init__(self):
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        self.time_step = 0
        self.history_length = 50
        self.setup_plot()
        
    def setup_plot(self):
        """Setup air quality plots"""
        self.fig.suptitle('Air Quality Sensor - Multi-Gas Analysis', 
                         fontsize=16, fontweight='bold', color='orange')
        
        # VOC levels
        self.ax1.set_title('VOC Levels (ppm)', fontsize=12, color='orange')
        self.ax1.set_ylabel('VOC (ppm)', fontsize=10)
        self.ax1.set_ylim(0, 200)
        self.ax1.grid(True, alpha=0.3)
        
        self.voc_line, = self.ax1.plot([], [], 'orange', linewidth=2, label='VOC')
        self.voc_baseline, = self.ax1.plot([], [], 'yellow', linewidth=1, alpha=0.7, label='Baseline')
        self.ax1.legend(loc='upper right')
        
        # PM2.5 levels
        self.ax2.set_title('Particulate Matter (PM2.5)', fontsize=12, color='orange')
        self.ax2.set_ylabel('PM2.5 (μg/m³)', fontsize=10)
        self.ax2.set_ylim(0, 100)
        self.ax2.grid(True, alpha=0.3)
        
        self.pm25_line, = self.ax2.plot([], [], 'brown', linewidth=2, label='PM2.5')
        self.ax2.legend(loc='upper right')
        
        # AQI gauge
        self.ax3.set_title('Air Quality Index', fontsize=12, color='orange')
        self.ax3.set_xlim(0, 500)
        self.ax3.set_ylim(0, 1)
        self.ax3.set_xlabel('AQI', fontsize=10)
        self.ax3.set_yticks([])
        
        # AQI color zones
        self.ax3.axvspan(0, 50, alpha=0.3, color='green', label='Good')
        self.ax3.axvspan(50, 100, alpha=0.3, color='yellow', label='Moderate')
        self.ax3.axvspan(100, 150, alpha=0.3, color='orange', label='Unhealthy for Sensitive')
        self.ax3.axvspan(150, 200, alpha=0.3, color='red', label='Unhealthy')
        self.ax3.axvspan(200, 300, alpha=0.3, color='purple', label='Very Unhealthy')
        self.ax3.axvspan(300, 500, alpha=0.3, color='maroon', label='Hazardous')
        
        self.aqi_indicator = self.ax3.scatter([], [], c='white', s=200, marker='o', 
                                              edgecolors='black', linewidth=2, zorder=5)
        
        # Odor classification
        self.ax4.set_title('Odor Classification', fontsize=12, color='orange')
        self.ax4.set_xlim(0, 10)
        self.ax4.set_ylim(0, 10)
        self.ax4.set_xticks([])
        self.ax4.set_yticks([])
        
        # Odor type display
        self.odor_text = self.ax4.text(5, 5, '', fontsize=20, fontweight='bold',
                                      ha='center', va='center',
                                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
        
        # Info text
        self.info_text = self.fig.text(0.02, 0.95, '', fontsize=10,
                                     transform=self.fig.transFigure,
                                     bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        plt.tight_layout()
        
    def generate_air_quality_data(self):
        """Generate realistic air quality data"""
        self.time_step += 1
        t = self.time_step * 0.1
        
        # VOC levels with realistic variations
        base_voc = 40 + 30 * np.sin(t * 0.05)  # 10-70 ppm base
        voc_ppm = base_voc + random.uniform(-10, 10)
        
        # PM2.5 correlated with VOC
        if voc_ppm > 100:
            pm25 = random.uniform(30, 80)
        elif voc_ppm > 50:
            pm25 = random.uniform(15, 40)
        else:
            pm25 = random.uniform(5, 20)
        
        # Calculate AQI
        aqi = (voc_ppm / 100 * 50) + (pm25 / 35 * 50)
        aqi = min(500, max(0, aqi))
        
        # Determine odor type
        if voc_ppm > 120:
            odor_type = 'STRONG CHEMICAL'
            odor_color = 'red'
        elif pm25 > 40:
            odor_type = 'DUST/SMOKE'
            odor_color = 'brown'
        elif voc_ppm > 80:
            odor_type = 'HUMAN ACTIVITY'
            odor_color = 'orange'
        elif voc_ppm > 50:
            odor_type = 'MODERATE ODOR'
            odor_color = 'yellow'
        else:
            odor_type = 'CLEAN AIR'
            odor_color = 'green'
        
        return {
            'voc_ppm': voc_ppm,
            'voc_baseline': base_voc,
            'pm25': pm25,
            'aqi': aqi,
            'odor_type': odor_type,
            'odor_color': odor_color
        }
    
    def update(self, frame):
        """Update animation frame"""
        air_data = self.generate_air_quality_data()
        
        # Update history
        if not hasattr(self, 'voc_history'):
            self.voc_history = []
            self.pm25_history = []
            self.time_history = []
        
        self.voc_history.append(air_data['voc_ppm'])
        self.pm25_history.append(air_data['pm25'])
        self.time_history.append(self.time_step * 0.1)
        
        # Keep only recent history
        if len(self.voc_history) > self.history_length:
            self.voc_history.pop(0)
            self.pm25_history.pop(0)
            self.time_history.pop(0)
        
        # Update plots
        self.voc_line.set_data(self.time_history, self.voc_history)
        self.voc_baseline.set_data(self.time_history, 
                                  [air_data['voc_baseline']] * len(self.time_history))
        self.pm25_line.set_data(self.time_history, self.pm25_history)
        
        # Update AQI indicator
        self.aqi_indicator.set_offsets([[air_data['aqi'], 0.5]])
        
        # Update odor display
        self.odor_text.set_text(air_data['odor_type'])
        self.odor_text.set_color(air_data['odor_color'])
        
        # Update info text
        info = f"VOC: {air_data['voc_ppm']:.1f} ppm\n"
        info += f"PM2.5: {air_data['pm25']} μg/m³\n"
        info += f"AQI: {air_data['aqi']:.0f}\n"
        info += f"Classification: {air_data['odor_type']}\n"
        info += f"Sensors: MQ135, PMS5003"
        
        self.info_text.set_text(info)
        
        # Adjust x-axis limits
        if self.time_history:
            self.ax1.set_xlim(max(0, self.time_history[-1] - 5), self.time_history[-1] + 0.5)
            self.ax2.set_xlim(max(0, self.time_history[-1] - 5), self.time_history[-1] + 0.5)
        
        return [self.voc_line, self.voc_baseline, self.pm25_line, 
                self.aqi_indicator, self.odor_text, self.info_text]
    
    def create_gif(self, filename='air_quality.gif', frames=100):
        """Create animated GIF"""
        print(f"Creating Air Quality GIF: {filename}")
        
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=100, blit=True, repeat=True)
        
        # Save GIF
        writer = animation.PillowWriter(fps=10, metadata=dict(artist='SCOPE System'))
        anim.save(filename, writer=writer)
        print(f"Saved: {filename}")
        
        plt.close()
        return anim

def create_all_sensor_gifs():
    """Create GIFs for all sensors"""
    print("🎬 Creating SCOPE Sensor Visualization GIFs...")
    
    # Already in performative directory, no need to change
    # os.chdir('performative')  # Removed this line
    
    # Create mmWave radar GIF
    radar_viz = mmWaveRadarVisualizer()
    radar_viz.create_gif('mmwave_radar.gif', frames=100)
    
    # Create sound sensor GIF
    sound_viz = SoundSensorVisualizer()
    sound_viz.create_gif('sound_sensor.gif', frames=100)
    
    # Create air quality GIF
    air_viz = AirQualityVisualizer()
    air_viz.create_gif('air_quality.gif', frames=100)
    
    print("✅ All sensor GIFs created successfully!")
    print("📁 Files saved in performative/ directory:")
    print("   - mmwave_radar.gif")
    print("   - sound_sensor.gif") 
    print("   - air_quality.gif")

if __name__ == "__main__":
    create_all_sensor_gifs()
