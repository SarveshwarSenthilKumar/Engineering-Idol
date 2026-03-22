#!/usr/bin/env python3
"""
Complete SCOPE Teams Notification System
Creates professional Teams notifications with comprehensive SCOPE system information
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import json

class CompleteSCOPENotification:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.patch.set_facecolor('#f0f2f5')  # Teams notification background
        
        # Animation state
        self.frame_count = 0
        self.notification_opacity = 0
        self.slide_offset = -3.0
        self.pulse_phase = 0
        
        # Complete SCOPE system data
        self.scope_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'system_status': 'ACTIVE',
            'threat_level': 'ELEVATED',
            'threat_score': 68.4,
            'location': 'Washroom Area B - Stall 3',
            'event_type': 'VAPING DETECTED',
            'confidence': 94.2,
            'people_count': 2,
            'duration': '00:03:47',
            'air_quality': {
                'aqi': 277.1,
                'voc_ppm': 186.3,
                'pm25': 62.8,
                'status': 'HAZARDOUS'
            },
            'sound_level': {
                'db': 73.2,
                'peak': 89.1,
                'baseline': 45.3,
                'status': 'LOUD'
            },
            'radar_data': {
                'targets': 2,
                'activity': 'IRREGULAR_MOVEMENT',
                'proximity': 'CLOSE',
                'breathing_abnormal': True
            },
            'response_actions': [
                '🚨 Immediate security response required',
                '📍 Location: Washroom Area B - Stall 3',
                '⏰ Duration: 3 minutes 47 seconds',
                '👥 Personnel count: 2 individuals',
                '💨 Air quality: HAZARDOUS (AQI 277)',
                '🔊 Sound level: ELEVATED (73.2 dB peak)',
                '📡 Confidence: 94.2%'
            ],
            'system_info': {
                'version': 'SCOPE v2.0.0',
                'sensors_online': 12,
                'last_calibration': '2026-03-22 13:15:00',
                'data_retention': '30 days',
                'alert_level': 'HIGH_PRIORITY'
            }
        }
        
        self.setup_complete_notification()
        
    def setup_complete_notification(self):
        """Setup comprehensive Teams notification"""
        self.ax.set_xlim(0, 12)
        self.ax.set_ylim(0, 8)
        self.ax.axis('off')
        
        # Create expanded notification container
        self.create_expanded_container()
        
        # Notification elements (initially hidden)
        self.notification_elements = []
        
    def create_expanded_container(self):
        """Create expanded Teams notification container"""
        # Main notification card (larger for comprehensive info)
        self.notification_card = FancyBboxPatch(
            (0.5, 1.0), 11, 6.5,
            boxstyle="round,pad=0.03",
            facecolor='white',
            edgecolor='#e1e5e9',
            linewidth=1.5,
            alpha=0
        )
        self.ax.add_patch(self.notification_card)
        
        # Header bar with SCOPE branding
        self.header_bar = Rectangle((0.5, 6.8), 11, 0.7,
                                  facecolor='#464775', alpha=0)
        self.ax.add_patch(self.header_bar)
        
        # Close button
        self.close_button = Rectangle((11.2, 7.2), 0.2, 0.2, 
                                   facecolor='#f0f2f5', edgecolor='#8a8a8a', 
                                   linewidth=1, alpha=0)
        self.ax.add_patch(self.close_button)
        self.ax.text(11.3, 7.3, '×', fontsize=14, color='#8a8a8a', 
                   ha='center', va='center', alpha=0)
        
        # SCOPE logo in header
        self.scope_logo_bg = Circle((1.0, 7.15), 0.25, 
                                  facecolor='#ff4444', alpha=0)
        self.ax.add_patch(self.scope_logo_bg)
        self.scope_logo_text = self.ax.text(1.0, 7.15, 'S', fontsize=12, 
                                           color='white', fontweight='bold', 
                                           ha='center', va='center', alpha=0)
        
        # Status indicator
        self.status_indicator = Circle((1.5, 7.15), 0.08, 
                                     facecolor='#ff4444', alpha=0)
        self.ax.add_patch(self.status_indicator)
        
        # Teams logo area
        self.teams_logo_bg = Rectangle((10.5, 6.9), 0.6, 0.5, 
                                     facecolor='#464775', alpha=0)
        self.ax.add_patch(self.teams_logo_bg)
        self.teams_logo = self.ax.text(10.8, 7.15, 'Teams', fontsize=10, 
                                     color='white', fontweight='bold', 
                                     ha='center', va='center', alpha=0)
        
    def create_comprehensive_content(self):
        """Create complete notification content"""
        elements = []
        alpha = min(1.0, self.notification_opacity)
        
        # Header section
        header_y = 7.0
        elements.append(self.ax.text(1.8, header_y, '🚨 SCOPE SECURITY ALERT', 
                                         fontsize=14, color='#ff4444', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.8, header_y - 0.4, f'📡 {self.scope_data["timestamp"]}', 
                                         fontsize=9, color='#605e5c', 
                                         va='top', alpha=alpha))
        
        # Event details section
        details_y = 6.3
        elements.append(self.ax.text(1.0, details_y, 'EVENT DETAILS:', 
                                         fontsize=10, color='#323130', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, details_y - 0.35, f'🎯 Event: {self.scope_data["event_type"]}', 
                                         fontsize=9, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, details_y - 0.7, f'📍 Location: {self.scope_data["location"]}', 
                                         fontsize=9, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, details_y - 1.05, f'⏰ Duration: {self.scope_data["duration"]}', 
                                         fontsize=9, color='#605e5c', va='top', alpha=alpha))
        
        # Threat assessment section
        threat_y = 5.0
        elements.append(self.ax.text(1.0, threat_y, 'THREAT ASSESSMENT:', 
                                         fontsize=10, color='#323130', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        # Create threat level with color coding
        threat_color = '#ff4444' if self.scope_data['threat_score'] > 60 else '#ffa500'
        elements.append(self.ax.text(1.0, threat_y - 0.35, 
                                         f'🔴 Level: {self.scope_data["threat_level"]} ({self.scope_data["threat_score"]}/100)', 
                                         fontsize=9, color=threat_color, 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, threat_y - 0.7, 
                                         f'🎯 Confidence: {self.scope_data["confidence"]}%', 
                                         fontsize=9, color='#605e5c', va='top', alpha=alpha))
        
        # Sensor readings section (2 columns)
        sensor_y = 3.8
        elements.append(self.ax.text(1.0, sensor_y, 'SENSOR READINGS:', 
                                         fontsize=10, color='#323130', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        # Left column - Air Quality
        air_y = sensor_y - 0.35
        elements.append(self.ax.text(1.0, air_y, '💨 Air Quality:', 
                                         fontsize=9, color='#0078d4', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, air_y - 0.3, f'   AQI: {self.scope_data["air_quality"]["aqi"]}', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, air_y - 0.6, f'   VOC: {self.scope_data["air_quality"]["voc_ppm"]} ppm', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(1.0, air_y - 0.9, f'   PM2.5: {self.scope_data["air_quality"]["pm25"]} μg/m³', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        # Right column - Sound & Radar
        radar_y = sensor_y - 0.35
        elements.append(self.ax.text(6.0, radar_y, '📡 Radar:', 
                                         fontsize=9, color='#0078d4', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(6.0, radar_y - 0.3, f'   Targets: {self.scope_data["radar_data"]["targets"]}', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(6.0, radar_y - 0.6, f'   Activity: {self.scope_data["radar_data"]["activity"]}', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(6.0, radar_y - 0.9, f'   Abnormal Breathing: {self.scope_data["radar_data"]["breathing_abnormal"]}', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        # Sound readings
        sound_y = radar_y - 1.2
        elements.append(self.ax.text(6.0, sound_y, '🔊 Sound:', 
                                         fontsize=9, color='#0078d4', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        elements.append(self.ax.text(6.0, sound_y - 0.3, f'   Current: {self.scope_data["sound_level"]["db"]} dB', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        elements.append(self.ax.text(6.0, sound_y - 0.6, f'   Peak: {self.scope_data["sound_level"]["peak"]} dB', 
                                         fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        # Response actions section
        response_y = 2.0
        elements.append(self.ax.text(1.0, response_y, '🚨 IMMEDIATE RESPONSE ACTIONS:', 
                                         fontsize=10, color='#ff4444', 
                                         fontweight='bold', va='top', alpha=alpha))
        
        for i, action in enumerate(self.scope_data['response_actions'][:3]):  # Show first 3 actions
            elements.append(self.ax.text(1.0, response_y - 0.35 - (i * 0.3), action, 
                                             fontsize=8, color='#605e5c', va='top', alpha=alpha))
        
        # System info section
        system_y = 0.8
        elements.append(self.ax.text(1.0, system_y, f'🔧 System: {self.scope_data["system_info"]["version"]} | Sensors: {self.scope_data["system_info"]["sensors_online"]}/12 online', 
                                         fontsize=8, color='#8a8a8a', 
                                         fontstyle='italic', va='top', alpha=alpha))
        
        # Action buttons
        button_alpha = min(1.0, self.notification_opacity * 0.9)
        
        # View Details button
        view_button = FancyBboxPatch((8.5, 1.5), 1.5, 0.4,
                                    boxstyle="round,pad=0.02",
                                    facecolor='#0078d4', 
                                    edgecolor='none', alpha=button_alpha)
        elements.append(view_button)
        elements.append(self.ax.text(9.25, 1.7, 'View Details', 
                               fontsize=9, color='white', 
                               ha='center', va='center', alpha=button_alpha))
        
        # Acknowledge button
        ack_button = FancyBboxPatch((10.1, 1.5), 1.2, 0.4,
                                   boxstyle="round,pad=0.02",
                                   facecolor='#28a745', 
                                   edgecolor='none', alpha=button_alpha)
        elements.append(ack_button)
        elements.append(self.ax.text(10.7, 1.7, 'Acknowledge', 
                               fontsize=9, color='white', 
                               ha='center', va='center', alpha=button_alpha))
        
        # Dismiss button
        dismiss_button = FancyBboxPatch((8.5, 1.0), 2.8, 0.4,
                                     boxstyle="round,pad=0.02",
                                     facecolor='#f0f2f5', 
                                     edgecolor='#8a8a8a', 
                                     linewidth=1, alpha=button_alpha)
        elements.append(dismiss_button)
        elements.append(self.ax.text(9.9, 1.2, 'Dismiss Notification', 
                               fontsize=9, color='#605e5c', 
                               ha='center', va='center', alpha=button_alpha))
        
        return elements
    
    def update(self, frame):
        """Update animation frame"""
        self.frame_count = frame
        self.pulse_phase = frame * 0.15
        
        # Clear and redraw
        self.ax.clear()
        self.ax.set_xlim(0, 12)
        self.ax.set_ylim(0, 8)
        self.ax.axis('off')
        
        # Recreate base elements
        self.create_expanded_container()
        
        # Animation phases
        if frame < 15:
            # Phase 1: Slide in from right
            self.animate_slide_in()
        elif frame < 25:
            # Phase 2: Fade in
            self.animate_fade_in()
        elif frame < 100:
            # Phase 3: Display with pulse
            self.animate_display()
        elif frame < 115:
            # Phase 4: Fade out
            self.animate_fade_out()
        else:
            # Phase 5: Slide out
            self.animate_slide_out()
        
        return []
    
    def animate_slide_in(self):
        """Animate notification sliding in from right"""
        progress = self.frame_count / 15
        self.slide_offset = -3.0 + (3.5 * progress)
        self.notification_opacity = progress
        
        # Update card position
        self.notification_card.set_x(0.5 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        
        # Update other elements
        self.update_static_elements()
        
        # Add comprehensive content
        self.notification_elements.extend(self.create_comprehensive_content())
    
    def animate_fade_in(self):
        """Animate notification fading in"""
        progress = (self.frame_count - 15) / 10
        self.notification_opacity = progress
        self.slide_offset = 0.5
        
        # Update card
        self.notification_card.set_x(0.5 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        
        # Update other elements
        self.update_static_elements()
        
        # Add comprehensive content
        self.notification_elements.extend(self.create_comprehensive_content())
    
    def animate_display(self):
        """Display notification with pulse effect"""
        self.notification_opacity = 1.0
        self.slide_offset = 0.5
        
        # Update card with subtle pulse
        pulse_alpha = 0.95 + 0.05 * np.sin(self.pulse_phase)
        self.notification_card.set_x(0.5 + self.slide_offset)
        self.notification_card.set_alpha(pulse_alpha)
        self.notification_card.set_linewidth(2)
        
        # Update other elements
        self.update_static_elements()
        
        # Add comprehensive content
        self.notification_elements.extend(self.create_comprehensive_content())
        
        # Add subtle shadow
        shadow = FancyBboxPatch((0.55, 0.95), 11, 6.5,
                                boxstyle="round,pad=0.03",
                                facecolor='#000000', alpha=0.1,
                                edgecolor='none')
        self.notification_elements.append(shadow)
    
    def animate_fade_out(self):
        """Animate notification fading out"""
        progress = (self.frame_count - 100) / 15
        self.notification_opacity = 1.0 - progress
        self.slide_offset = 0.5
        
        # Update card
        self.notification_card.set_x(0.5 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        self.notification_card.set_linewidth(1)
        
        # Update other elements
        self.update_static_elements()
        
        # Add comprehensive content
        self.notification_elements.extend(self.create_comprehensive_content())
    
    def animate_slide_out(self):
        """Animate notification sliding out to right"""
        progress = (self.frame_count - 115) / 20
        self.slide_offset = 0.5 + (3.5 * progress)
        self.notification_opacity = 0
        
        # Update card
        self.notification_card.set_x(0.5 + self.slide_offset)
        self.notification_card.set_alpha(0)
        
        # Update other elements
        self.update_static_elements()
    
    def update_static_elements(self):
        """Update static notification elements"""
        alpha = min(1.0, self.notification_opacity)
        
        # Close button
        self.close_button.set_alpha(alpha)
        
        # Header elements
        self.header_bar.set_alpha(alpha)
        self.scope_logo_bg.set_alpha(alpha)
        self.scope_logo_text.set_alpha(alpha)
        self.status_indicator.set_alpha(alpha)
        self.teams_logo_bg.set_alpha(alpha)
        self.teams_logo.set_alpha(alpha)
        
        # Add to elements list
        self.notification_elements.extend([
            self.close_button, self.header_bar, self.scope_logo_bg, 
            self.scope_logo_text, self.status_indicator, 
            self.teams_logo_bg, self.teams_logo
        ])
    
    def create_gif(self, filename='scope_complete_notification.gif', frames=135):
        """Create the comprehensive notification GIF"""
        print(f"🔵 Creating Complete SCOPE Notification: {filename}")
        
        anim = animation.FuncAnimation(
            self.fig, self.update, frames=frames,
            interval=50, blit=False, repeat=True
        )
        
        # Save as GIF
        print("📽️ Rendering comprehensive notification...")
        anim.save(filename, writer='pillow', fps=20, dpi=100)
        print(f"✅ Saved: {filename}")
        
        plt.close()
    
    def save_data_json(self):
        """Save complete SCOPE data as JSON"""
        filename = 'scope_notification_data.json'
        with open(filename, 'w') as f:
            json.dump(self.scope_data, f, indent=2)
        print(f"📄 Saved SCOPE data to: {filename}")

def main():
    """Main function"""
    print("=" * 70)
    print("🔵 COMPLETE SCOPE TEAMS NOTIFICATION SYSTEM")
    print("=" * 70)
    print("📱 Creating comprehensive Teams notification with:")
    print("   • Complete SCOPE system information")
    print("   • Real-time sensor readings")
    print("   • Threat assessment details")
    print("   • Response action recommendations")
    print("   • System status and metadata")
    print("   • Professional Teams styling")
    print("   • Multi-section layout")
    print()
    
    # Create comprehensive notification
    scope_notifier = CompleteSCOPENotification()
    
    # Save data
    scope_notifier.save_data_json()
    
    # Create GIF
    scope_notifier.create_gif('scope_complete_notification.gif', frames=135)
    
    print()
    print("🎯 Animation phases:")
    print("   1. Slide in from right (frames 0-15)")
    print("   2. Fade in effect (frames 15-25)")
    print("   3. Display with pulse (frames 25-100)")
    print("   4. Fade out effect (frames 100-115)")
    print("   5. Slide out to right (frames 115-135)")
    print()
    print("📊 Complete SCOPE data included:")
    print("   • Event details and timestamps")
    print("   • Threat assessment with confidence scores")
    print("   • Air quality readings (AQI, VOC, PM2.5)")
    print("   • Sound level measurements")
    print("   • Radar target analysis")
    print("   • Response action recommendations")
    print("   • System information and status")
    print()
    print("✅ Complete SCOPE Teams notification system ready!")

if __name__ == "__main__":
    main()
