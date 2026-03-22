#!/usr/bin/env python3
"""
Simple Sensor GIF Generator - Fixed Version
Creates animated GIFs for all SCOPE sensors without animation errors
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import os

# Set style
plt.style.use('dark_background')

class SimpleRadarViz:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        self.time_step = 0
        self.setup_plot()
        
    def setup_plot(self):
        # Dark black background for contrast
        self.fig.patch.set_facecolor('#000000')
        self.ax.set_facecolor('#000000')
        
        # Set up proper radar display (polar coordinates)
        self.ax.set_ylim(0, 5.5)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)
        
        self.ax.set_title('mmWave Radar - 60GHz ULTRA-WIDEBAND', fontsize=16, color='#FF0000', fontweight='bold')
        
        # Draw radar range circles (like real radar)
        range_radii = [1, 2, 3, 4, 5]
        for radius in range_radii:
            self.ax.plot([0, 2*np.pi], [radius, radius], color='#FF0000', alpha=0.8, linewidth=2)
            # Add range labels
            self.ax.text(0, radius, f'{radius}m', fontsize=8, color='#FF0000', 
                        ha='center', va='center', fontweight='bold')
        
        # Draw radar sweep lines (like real radar)
        sweep_angles = np.linspace(0, 2*np.pi, 36, endpoint=False)
        for angle in sweep_angles:
            self.ax.plot([angle, angle], [0, 5.5], color='#FF0000', alpha=0.4, linewidth=1)
        
        # Add compass directions
        self.ax.text(0, 5.8, 'N', fontsize=12, color='#FF0000', ha='center', va='center', fontweight='bold')
        self.ax.text(np.pi/2, 5.8, 'E', fontsize=12, color='#FF0000', ha='center', va='center', fontweight='bold')
        self.ax.text(np.pi, 5.8, 'S', fontsize=12, color='#FF0000', ha='center', va='center', fontweight='bold')
        self.ax.text(3*np.pi/2, 5.8, 'W', fontsize=12, color='#FF0000', ha='center', va='center', fontweight='bold')
        
        # Draw square washroom walls in polar coordinates
        wall_color = '#FF0000'
        wall_width = 3
        
        # Convert square walls to polar coordinates
        # Top wall (y = 4)
        x_top = np.linspace(-4, 4, 50)
        y_top = np.full_like(x_top, 4)
        angles_top = np.arctan2(y_top, x_top)
        radii_top = np.sqrt(x_top**2 + y_top**2)
        self.ax.plot(angles_top, radii_top, color=wall_color, linewidth=wall_width)
        
        # Bottom wall (y = -4) with door opening
        x_bottom_left = np.linspace(-4, -0.75, 25)
        y_bottom_left = np.full_like(x_bottom_left, -4)
        angles_bottom_left = np.arctan2(y_bottom_left, x_bottom_left)
        radii_bottom_left = np.sqrt(x_bottom_left**2 + y_bottom_left**2)
        self.ax.plot(angles_bottom_left, radii_bottom_left, color=wall_color, linewidth=wall_width)
        
        x_bottom_right = np.linspace(0.75, 4, 25)
        y_bottom_right = np.full_like(x_bottom_right, -4)
        angles_bottom_right = np.arctan2(y_bottom_right, x_bottom_right)
        radii_bottom_right = np.sqrt(x_bottom_right**2 + y_bottom_right**2)
        self.ax.plot(angles_bottom_right, radii_bottom_right, color=wall_color, linewidth=wall_width)
        
        # Left wall (x = -4)
        y_left = np.linspace(-4, 4, 50)
        x_left = np.full_like(y_left, -4)
        angles_left = np.arctan2(y_left, x_left)
        radii_left = np.sqrt(x_left**2 + y_left**2)
        self.ax.plot(angles_left, radii_left, color=wall_color, linewidth=wall_width)
        
        # Right wall (x = 4)
        y_right = np.linspace(-4, 4, 50)
        x_right = np.full_like(y_right, 4)
        angles_right = np.arctan2(y_right, x_right)
        radii_right = np.sqrt(x_right**2 + y_right**2)
        self.ax.plot(angles_right, radii_right, color=wall_color, linewidth=wall_width)
        
        # Door markers in polar coordinates
        door_left_angle = np.arctan2(-4, -0.75)
        door_right_angle = np.arctan2(-4, 0.75)
        self.ax.plot([door_left_angle, door_left_angle], [4.0, 4.5], color='#00FF00', linewidth=4)
        self.ax.plot([door_right_angle, door_right_angle], [4.0, 4.5], color='#00FF00', linewidth=4)
        self.ax.text((door_left_angle + door_right_angle)/2, 4.8, 'DOOR', 
                    fontsize=10, color='#00FF00', ha='center', fontweight='bold')
        
        # Draw fixtures in polar coordinates
        # Sinks (left wall)
        sink_positions = [(-3.6, -2), (-3.6, 0), (-3.6, 2)]
        for x, y in sink_positions:
            angle = np.arctan2(y, x)
            radius = np.sqrt(x**2 + y**2)
            self.ax.scatter([angle], [radius], c='#FFFF00', s=50, marker='s')
        
        # Stalls (right wall)
        stall_positions = [(3.6, -3), (3.6, -1), (3.6, 1), (3.6, 3)]
        for x, y in stall_positions:
            angle = np.arctan2(y, x)
            radius = np.sqrt(x**2 + y**2)
            self.ax.scatter([angle], [radius], c='#FFFF00', s=50, marker='s')
        
        # Single target type with uniform color
        self.all_targets = self.ax.scatter([], [], c='#FF0000', s=200, alpha=0.8, 
                                          edgecolors='#FFFFFF', linewidth=2, marker='o')
        
        # Alert flags
        self.alert_texts = []
        
        # Bright red info text
        self.info_text = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes,
                                    fontsize=11, fontweight='bold', color='#FF0000',
                                    verticalalignment='top',
                                    bbox=dict(boxstyle='round', facecolor='#000000', 
                                             edgecolor='#FF0000', linewidth=2, alpha=0.9))
        
    def update(self, frame):
        self.time_step += 1
        t = self.time_step * 0.05
        
        # Clear previous alert texts
        for alert_text in self.alert_texts:
            alert_text.remove()
        self.alert_texts = []
        
        # Generate 10 targets with realistic linear movement in polar coordinates
        target_angles = []
        target_radii = []
        
        # Energy levels for different activities
        energy_levels = {
            'stationary': 0.1,    # Very low energy
            'normal': 0.3,        # Low energy
            'vaping': 0.5,        # Medium energy
            'fighting': 0.9       # High energy
        }
        
        for i in range(10):
            if i < 2:  # 2 stationary targets (at sinks)
                # Different sink positions
                sink_positions = [(-3.6, -2), (-3.6, 2)]
                x, y = sink_positions[i]
                # Minimal movement with very low energy
                x += 0.1 * np.sin(t * energy_levels['stationary'])
                y += 0.05 * np.cos(t * energy_levels['stationary'])
                
                angle = np.arctan2(y, x)
                radius = np.sqrt(x**2 + y**2)
                target_angles.append(angle)
                target_radii.append(radius)
                
                # Add alert flag
                alert_text = self.ax.text(angle, radius + 0.3, 'STATIONARY', 
                                         fontsize=7, color='#FFFF00', fontweight='bold',
                                         ha='center', va='bottom')
                self.alert_texts.append(alert_text)
                
            elif i < 6:  # 4 normal moving targets (linear movement)
                # Linear movement patterns, not circular
                base_x = -2.0 + i * 1.0  # Spread across room
                base_y = -1.0 + (i % 2) * 2.0  # Alternating y positions
                
                # Linear oscillation, not circular
                x = base_x + 0.8 * np.sin(t * 0.2 * energy_levels['normal'] + i)
                y = base_y + 0.6 * np.cos(t * 0.3 * energy_levels['normal'] + i * 0.5)
                
                # Keep within walls with margin
                x = np.clip(x, -3.5, 3.5)
                y = np.clip(y, -3.5, 3.5)
                
                angle = np.arctan2(y, x)
                radius = np.sqrt(x**2 + y**2)
                target_angles.append(angle)
                target_radii.append(radius)
                
            elif i < 8:  # 2 vaping targets (linear huddled movement)
                # Linear huddled movement
                vape_base_x = 2.0 + 0.4 * np.sin(t * 0.1 * energy_levels['vaping'])
                vape_base_y = 1.0 + 0.3 * np.cos(t * 0.1 * energy_levels['vaping'])
                
                if i == 6:
                    x = vape_base_x - 0.2
                    y = vape_base_y
                else:
                    x = vape_base_x + 0.2
                    y = vape_base_y
                
                # Keep within walls
                x = np.clip(x, -3.5, 3.5)
                y = np.clip(y, -3.5, 3.5)
                
                angle = np.arctan2(y, x)
                radius = np.sqrt(x**2 + y**2)
                target_angles.append(angle)
                target_radii.append(radius)
                
                # Add alert flag
                alert_text = self.ax.text(angle, radius + 0.3, 'VAPING!', 
                                         fontsize=7, color='#00FF00', fontweight='bold',
                                         ha='center', va='bottom')
                self.alert_texts.append(alert_text)
                
            else:  # 2 fighting targets (linear erratic movement)
                # Erratic linear movement with high energy
                fight_base_x = -2.0 + 0.6 * np.sin(t * 0.8 * energy_levels['fighting'])
                fight_base_y = -1.0 + 0.6 * np.cos(t * 0.8 * energy_levels['fighting'])
                
                if i == 8:
                    # Erratic linear movement
                    x = fight_base_x + 0.4 * np.sin(t * 3.0 * energy_levels['fighting'])
                    y = fight_base_y + 0.4 * np.cos(t * 2.5 * energy_levels['fighting'])
                else:
                    # Opposite erratic linear movement
                    x = fight_base_x - 0.4 * np.sin(t * 2.8 * energy_levels['fighting'])
                    y = fight_base_y - 0.4 * np.cos(t * 3.2 * energy_levels['fighting'])
                
                # Keep within walls
                x = np.clip(x, -3.5, 3.5)
                y = np.clip(y, -3.5, 3.5)
                
                angle = np.arctan2(y, x)
                radius = np.sqrt(x**2 + y**2)
                target_angles.append(angle)
                target_radii.append(radius)
                
                # Add alert flag
                alert_text = self.ax.text(angle, radius + 0.3, 'FIGHTING!', 
                                         fontsize=7, color='#FF00FF', fontweight='bold',
                                         ha='center', va='bottom')
                self.alert_texts.append(alert_text)
        
        # Update single scatter plot with polar coordinates
        if target_angles:
            self.all_targets.set_offsets(np.c_[target_angles, target_radii])
        else:
            self.all_targets.set_offsets(np.empty((0, 2)))
        
        # Update info text with real-time alerts
        info = f"🚨 RADAR MONITORING ACTIVE\n"
        info += f"👥 TOTAL TARGETS: {len(target_angles)}\n"
        info += f"⚡ LINEAR MOVEMENT\n"
        info += f"🔥 POLAR RADAR DISPLAY\n"
        info += f"📡 RANGE: 5.5m"
        
        self.info_text.set_text(info)
        
        return [self.all_targets, self.info_text] + self.alert_texts
    
    def create_gif(self, filename='mmwave_radar_polar.gif', frames=50):
        print(f"Creating {filename}...")
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=100, blit=True)
        anim.save(filename, writer='pillow', fps=10)
        print(f"Saved: {filename}")
        plt.close()

class SimpleSoundViz:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.time_step = 0
        self.setup_plot()
        
    def setup_plot(self):
        self.ax.set_title('Sound Sensor - Acoustic Analysis', fontsize=14, color='lime')
        self.ax.set_ylabel('Sound Level (dB)')
        self.ax.set_ylim(20, 120)
        self.ax.grid(True, alpha=0.3)
        
        self.line, = self.ax.plot([], [], 'lime', linewidth=2)
        
    def update(self, frame):
        self.time_step += 1
        t = self.time_step * 0.1
        
        # Generate sound data
        base_db = 50 + 20 * np.sin(t * 0.1)
        spike = random.random() < 0.1
        if spike:
            db = base_db + random.uniform(15, 40)
        else:
            db = base_db + random.uniform(-5, 5)
        
        # Update history
        if not hasattr(self, 'db_history'):
            self.db_history = []
            self.time_history = []
        
        self.db_history.append(db)
        self.time_history.append(t)
        
        # Keep only recent history
        if len(self.db_history) > 30:
            self.db_history.pop(0)
            self.time_history.pop(0)
        
        self.line.set_data(self.time_history, self.db_history)
        
        if self.time_history:
            self.ax.set_xlim(max(0, self.time_history[-1] - 3), self.time_history[-1] + 0.5)
        
        return [self.line]
    
    def create_gif(self, filename='sound_sensor.gif', frames=50):
        print(f"Creating {filename}...")
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=200, blit=True)
        anim.save(filename, writer='pillow', fps=5)
        print(f"Saved: {filename}")
        plt.close()

class SimpleAirViz:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        self.time_step = 0
        self.setup_plot()
        
    def setup_plot(self):
        # Dark black background for contrast
        self.fig.patch.set_facecolor('#000000')
        self.ax.set_facecolor('#000000')
        
        # Set up radar-style polar coordinates
        self.ax.set_ylim(0, 5.5)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)
        
        self.ax.set_title('Air Quality Radar - Pollutant Detection', fontsize=16, color='#00FF00', fontweight='bold')
        
        # Draw radar range circles
        range_radii = [1, 2, 3, 4, 5]
        for radius in range_radii:
            self.ax.plot([0, 2*np.pi], [radius, radius], color='#00FF00', alpha=0.8, linewidth=2)
            # Add range labels
            self.ax.text(0, radius, f'{radius}m', fontsize=8, color='#00FF00', 
                        ha='center', va='center', fontweight='bold')
        
        # Draw radar sweep lines
        sweep_angles = np.linspace(0, 2*np.pi, 36, endpoint=False)
        for angle in sweep_angles:
            self.ax.plot([angle, angle], [0, 5.5], color='#00FF00', alpha=0.4, linewidth=1)
        
        # Add compass directions
        self.ax.text(0, 5.8, 'N', fontsize=12, color='#00FF00', ha='center', va='center', fontweight='bold')
        self.ax.text(np.pi/2, 5.8, 'E', fontsize=12, color='#00FF00', ha='center', va='center', fontweight='bold')
        self.ax.text(np.pi, 5.8, 'S', fontsize=12, color='#00FF00', ha='center', va='center', fontweight='bold')
        self.ax.text(3*np.pi/2, 5.8, 'W', fontsize=12, color='#00FF00', ha='center', va='center', fontweight='bold')
        
        # Add room boundaries in polar coordinates
        wall_color = '#00FF00'
        wall_width = 3
        
        # Top wall (y = 4)
        x_top = np.linspace(-4, 4, 50)
        y_top = np.full_like(x_top, 4)
        angles_top = np.arctan2(y_top, x_top)
        radii_top = np.sqrt(x_top**2 + y_top**2)
        self.ax.plot(angles_top, radii_top, color=wall_color, linewidth=wall_width)
        
        # Bottom wall (y = -4) with door opening
        x_bottom_left = np.linspace(-4, -0.75, 25)
        y_bottom_left = np.full_like(x_bottom_left, -4)
        angles_bottom_left = np.arctan2(y_bottom_left, x_bottom_left)
        radii_bottom_left = np.sqrt(x_bottom_left**2 + y_bottom_left**2)
        self.ax.plot(angles_bottom_left, radii_bottom_left, color=wall_color, linewidth=wall_width)
        
        x_bottom_right = np.linspace(0.75, 4, 25)
        y_bottom_right = np.full_like(x_bottom_right, -4)
        angles_bottom_right = np.arctan2(y_bottom_right, x_bottom_right)
        radii_bottom_right = np.sqrt(x_bottom_right**2 + y_bottom_right**2)
        self.ax.plot(angles_bottom_right, radii_bottom_right, color=wall_color, linewidth=wall_width)
        
        # Left wall (x = -4)
        y_left = np.linspace(-4, 4, 50)
        x_left = np.full_like(y_left, -4)
        angles_left = np.arctan2(y_left, x_left)
        radii_left = np.sqrt(x_left**2 + y_left**2)
        self.ax.plot(angles_left, radii_left, color=wall_color, linewidth=wall_width)
        
        # Right wall (x = 4)
        y_right = np.linspace(-4, 4, 50)
        x_right = np.full_like(y_right, 4)
        angles_right = np.arctan2(y_right, x_right)
        radii_right = np.sqrt(x_right**2 + y_right**2)
        self.ax.plot(angles_right, radii_right, color=wall_color, linewidth=wall_width)
        
        # Door markers
        door_left_angle = np.arctan2(-4, -0.75)
        door_right_angle = np.arctan2(-4, 0.75)
        self.ax.plot([door_left_angle, door_left_angle], [4.0, 4.5], color='#FFFF00', linewidth=4)
        self.ax.plot([door_right_angle, door_right_angle], [4.0, 4.5], color='#FFFF00', linewidth=4)
        self.ax.text((door_left_angle + door_right_angle)/2, 4.8, 'DOOR', 
                    fontsize=10, color='#FFFF00', ha='center', fontweight='bold')
        
        # Add pollution sources (fixtures) in polar coordinates
        # Source positions (like HVAC vents, pollution sources)
        sources = [
            (-3.6, -2), (-3.6, 0), (-3.6, 2),  # Left wall sources
            (3.6, -3), (3.6, -1), (3.6, 1), (3.6, 3)   # Right wall sources
        ]
        for x, y in sources:
            angle = np.arctan2(y, x)
            radius = np.sqrt(x**2 + y**2)
            self.ax.scatter([angle], [radius], c='#FF0000', s=100, marker='^', alpha=0.8)
        
        # Initialize pollutant cloud points
        self.cloud_scatter = self.ax.scatter([], [], c=[], s=[], cmap='hot', 
                                            vmin=0, vmax=100, alpha=0.8, edgecolors='white', linewidth=1)
        
        # Add colorbar for air quality
        cbar = plt.colorbar(self.cloud_scatter, ax=self.ax, label='Pollutant Concentration')
        cbar.set_label('AQI (0-100)', color='#00FF00', fontweight='bold')
        cbar.ax.yaxis.label.set_color('#00FF00')
        cbar.ax.tick_params(colors='#00FF00')
        
        # Info text
        self.info_text = self.fig.text(0.02, 0.98, '', transform=self.fig.transFigure,
                                    fontsize=11, fontweight='bold', color='#00FF00',
                                    verticalalignment='top',
                                    bbox=dict(boxstyle='round', facecolor='#000000', 
                                             edgecolor='#00FF00', linewidth=2, alpha=0.9))
        
        # Sweep line (rotating radar)
        self.sweep_line, = self.ax.plot([], [], color='#00FF00', linewidth=3, alpha=0.6)
        
    def update(self, frame):
        self.time_step += 1
        t = self.time_step * 0.05
        
        # Update rotating sweep line
        sweep_angle = (t * 2) % (2 * np.pi)
        self.sweep_line.set_data([sweep_angle, sweep_angle], [0, 5.5])
        
        # Generate air quality data with slow, gradual changes
        base_voc = 30 + 15 * np.sin(t * 0.05)  # Slow sine wave variation
        base_pm25 = 15 + 10 * np.sin(t * 0.08)  # Different slow sine wave
        
        # Slow pollution events (less frequent, more gradual)
        if random.random() < 0.05:  # 5% chance of pollution spike
            voc_ppm = base_voc + random.uniform(10, 20)
            pm25 = base_pm25 + random.uniform(5, 15)
            event_type = 'POLLUTION RISING'
        elif random.random() < 0.15:  # 15% chance of moderate increase
            voc_ppm = base_voc + random.uniform(5, 10)
            pm25 = base_pm25 + random.uniform(2, 8)
            event_type = 'QUALITY DEGRADING'
        else:
            voc_ppm = base_voc + random.uniform(-3, 3)
            pm25 = base_pm25 + random.uniform(-2, 2)
            event_type = 'STABLE'
        
        # Calculate AQI
        aqi = (voc_ppm / 100 * 50) + (pm25 / 35 * 50)
        aqi = min(100, max(0, aqi))
        
        # Generate pollutant cloud points with radar-style distribution
        base_points = 80  # Fixed base number of points
        num_points = int(base_points * (1 + aqi / 100))  # Slowly vary with AQI
        
        cloud_angles = []
        cloud_radii = []
        cloud_colors = []
        
        for i in range(num_points):
            # Random position in room (polar coordinates)
            angle = random.uniform(0, 2*np.pi)
            radius = random.uniform(0.5, 4.5)
            
            # Avoid walls in polar coordinates
            if radius > 4.0:
                radius = 4.0
            
            cloud_angles.append(angle)
            cloud_radii.append(radius)
            
            # Color based on air quality with slow variations
            local_variation = random.uniform(-5, 5)  # Smaller local variations
            local_aqi = aqi + local_variation
            local_aqi = min(100, max(0, local_aqi))
            cloud_colors.append(local_aqi)
        
        # Update cloud visualization
        if cloud_angles:
            self.cloud_scatter.set_offsets(np.c_[cloud_angles, cloud_radii])
            self.cloud_scatter.set_array(np.array(cloud_colors))
            # Size based on air quality (radar blips)
            sizes = [50 + aqi/2 for _ in range(len(cloud_angles))]
            self.cloud_scatter.set_sizes(sizes)
        else:
            self.cloud_scatter.set_offsets(np.empty((0, 2)))
        
        # Determine air quality status
        if aqi < 25:
            status = 'GOOD'
            status_color = '#00FF00'
        elif aqi < 50:
            status = 'MODERATE'
            status_color = '#FFFF00'
        elif aqi < 75:
            status = 'UNHEALTHY'
            status_color = '#FF8C00'
        else:
            status = 'HAZARDOUS'
            status_color = '#FF0000'
        
        # Update info text
        info = f"🌫️ AIR QUALITY RADAR\n"
        info += f"📊 Status: {status}\n"
        info += f"📈 VOC: {voc_ppm:.1f} ppm\n"
        info += f"💨 PM2.5: {pm25:.1f} μg/m³\n"
        info += f"🔥 AQI: {aqi:.0f}\n"
        info += f"⚠️ Event: {event_type}\n"
        info += f"🔍 Pollutant Points: {num_points}"
        
        self.info_text.set_text(info)
        
        return [self.cloud_scatter, self.sweep_line, self.info_text]
    
    def create_gif(self, filename='air_quality_radar.gif', frames=50):
        print(f"Creating {filename}...")
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                     interval=100, blit=True)
        anim.save(filename, writer='pillow', fps=10)
        print(f"Saved: {filename}")
        plt.close()

def create_simple_gifs():
    """Create all sensor GIFs with simple version"""
    print("🎬 Creating Simple SCOPE Sensor GIFs...")
    
    # Create mmWave radar GIF
    radar = SimpleRadarViz()
    radar.create_gif('mmwave_radar_simple.gif', frames=50)
    
    # Create sound sensor GIF
    sound = SimpleSoundViz()
    sound.create_gif('sound_sensor_simple.gif', frames=50)
    
    # Create air quality GIF
    air = SimpleAirViz()
    air.create_gif('air_quality_simple.gif', frames=50)
    
    print("✅ All simple sensor GIFs created successfully!")
    print("📁 Files saved:")
    print("   - mmwave_radar_simple.gif")
    print("   - sound_sensor_simple.gif") 
    print("   - air_quality_simple.gif")

if __name__ == "__main__":
    create_simple_gifs()
