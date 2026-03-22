#!/usr/bin/env python3
"""
Professional Teams Notification Generator
Creates realistic Teams notification with proper styling and animation
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import io
from PIL import Image, ImageDraw, ImageFont
import random

class ProfessionalTeamsNotification:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.patch.set_facecolor('#f0f2f5')  # Teams notification background
        
        # Animation state
        self.frame_count = 0
        self.notification_opacity = 0
        self.slide_offset = -2.0
        self.pulse_phase = 0
        
        # Notification content
        self.notification_title = "SCOPE Security Alert"
        self.notification_message = "ELEVATED threat level detected in Washroom Area B - Immediate response recommended"
        self.notification_time = "Just now"
        self.notification_icon = "🔴"
        
        self.setup_teams_notification()
        
    def setup_teams_notification(self):
        """Setup professional Teams notification"""
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 6)
        self.ax.axis('off')
        
        # Create Windows-style notification container
        self.create_notification_container()
        
        # Notification elements (initially hidden)
        self.notification_elements = []
        
    def create_notification_container(self):
        """Create Windows/Teams style notification container"""
        # Main notification card
        self.notification_card = FancyBboxPatch(
            (1, 1.5), 8, 3,
            boxstyle="round,pad=0.02",
            facecolor='white',
            edgecolor='#e1e5e9',
            linewidth=1,
            alpha=0
        )
        self.ax.add_patch(self.notification_card)
        
        # Windows close button
        self.close_button = Rectangle((8.7, 4.3), 0.2, 0.2, 
                                   facecolor='#f0f2f5', edgecolor='#8a8a8a', 
                                   linewidth=1, alpha=0)
        self.ax.add_patch(self.close_button)
        self.ax.text(8.8, 4.4, '×', fontsize=12, color='#8a8a8a', 
                   ha='center', va='center', alpha=0)
        
        # Teams logo area
        self.teams_logo_bg = Rectangle((1.1, 4.1), 0.4, 0.4, 
                                     facecolor='#464775', alpha=0)
        self.ax.add_patch(self.teams_logo_bg)
        self.teams_logo = self.ax.text(1.3, 4.3, 'T', fontsize=10, 
                                     color='white', fontweight='bold', 
                                     ha='center', va='center', alpha=0)
        
    def create_notification_content(self):
        """Create notification content elements"""
        elements = []
        
        # Icon with pulse effect
        icon_size = 0.3 + 0.05 * np.sin(self.pulse_phase)
        icon_alpha = min(1.0, self.notification_opacity)
        icon_circle = Circle((1.8, 3.5), icon_size, 
                           facecolor='#ff4444', alpha=icon_alpha)
        elements.append(icon_circle)
        
        # Alert icon text
        icon_text = self.ax.text(1.8, 3.5, '🚨', fontsize=16, 
                               ha='center', va='center', alpha=icon_alpha)
        elements.append(icon_text)
        
        # Notification title
        title_alpha = min(1.0, self.notification_opacity)
        title_text = self.ax.text(2.5, 4.0, self.notification_title, 
                                fontsize=12, color='#323130', 
                                fontweight='bold', va='top', alpha=title_alpha)
        elements.append(title_text)
        
        # Notification message
        message_alpha = min(1.0, self.notification_opacity * 0.9)
        message_text = self.ax.text(2.5, 3.6, self.notification_message, 
                                  fontsize=10, color='#605e5c', 
                                  va='top', wrap=True, alpha=message_alpha)
        elements.append(message_text)
        
        # Timestamp
        time_alpha = min(1.0, self.notification_opacity * 0.7)
        time_text = self.ax.text(2.5, 2.0, self.notification_time, 
                              fontsize=8, color='#8a8a8a', 
                              va='top', alpha=time_alpha)
        elements.append(time_text)
        
        # Action buttons
        button_alpha = min(1.0, self.notification_opacity * 0.8)
        
        # View Details button
        view_button = FancyBboxPatch((6.5, 2.2), 1.3, 0.4,
                                    boxstyle="round,pad=0.02",
                                    facecolor='#0078d4', 
                                    edgecolor='none', alpha=button_alpha)
        elements.append(view_button)
        view_text = self.ax.text(7.15, 2.4, 'View Details', 
                               fontsize=8, color='white', 
                               ha='center', va='center', alpha=button_alpha)
        elements.append(view_text)
        
        # Dismiss button
        dismiss_button = FancyBboxPatch((7.9, 2.2), 0.8, 0.4,
                                     boxstyle="round,pad=0.02",
                                     facecolor='#f0f2f5', 
                                     edgecolor='#8a8a8a', 
                                     linewidth=1, alpha=button_alpha)
        elements.append(dismiss_button)
        dismiss_text = self.ax.text(8.3, 2.4, 'Dismiss', 
                                 fontsize=8, color='#605e5c', 
                                 ha='center', va='center', alpha=button_alpha)
        elements.append(dismiss_text)
        
        return elements
    
    def create_windows_taskbar(self):
        """Create Windows taskbar element"""
        taskbar_alpha = min(0.3, self.notification_opacity)
        
        # Taskbar
        taskbar = Rectangle((0, 0), 10, 0.3, 
                          facecolor='#323130', alpha=taskbar_alpha)
        
        # Start button
        start_button = Rectangle((0, 0), 0.8, 0.3, 
                              facecolor='#0078d4', alpha=taskbar_alpha)
        
        # Teams icon in taskbar
        teams_icon = Rectangle((8.5, 0), 0.5, 0.3, 
                             facecolor='#464775', alpha=taskbar_alpha)
        
        return [taskbar, start_button, teams_icon]
    
    def update(self, frame):
        """Update animation frame"""
        self.frame_count = frame
        self.pulse_phase = frame * 0.15
        
        # Clear previous elements by clearing and redrawing
        self.ax.clear()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 6)
        self.ax.axis('off')
        
        # Recreate base elements
        self.create_notification_container()
        
        # Animation phases
        if frame < 10:
            # Phase 1: Slide in from right
            self.animate_slide_in()
        elif frame < 20:
            # Phase 2: Fade in
            self.animate_fade_in()
        elif frame < 80:
            # Phase 3: Display with pulse
            self.animate_display()
        elif frame < 100:
            # Phase 4: Fade out
            self.animate_fade_out()
        else:
            # Phase 5: Slide out
            self.animate_slide_out()
        
        return []  # Return empty list since we're redrawing everything
    
    def animate_slide_in(self):
        """Animate notification sliding in from right"""
        progress = self.frame_count / 10
        self.slide_offset = -2.0 + (3.0 * progress)
        self.notification_opacity = progress
        
        # Update card position
        self.notification_card.set_x(1 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        
        # Update other elements
        self.update_static_elements()
        
        # Add notification content
        self.notification_elements.extend(self.create_notification_content())
    
    def animate_fade_in(self):
        """Animate notification fading in"""
        progress = (self.frame_count - 10) / 10
        self.notification_opacity = progress
        self.slide_offset = 1.0
        
        # Update card
        self.notification_card.set_x(1 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        
        # Update other elements
        self.update_static_elements()
        
        # Add notification content
        self.notification_elements.extend(self.create_notification_content())
    
    def animate_display(self):
        """Display notification with pulse effect"""
        self.notification_opacity = 1.0
        self.slide_offset = 1.0
        
        # Update card with subtle pulse
        pulse_alpha = 0.95 + 0.05 * np.sin(self.pulse_phase)
        self.notification_card.set_x(1 + self.slide_offset)
        self.notification_card.set_alpha(pulse_alpha)
        self.notification_card.set_linewidth(1.5)
        
        # Update other elements
        self.update_static_elements()
        
        # Add notification content
        self.notification_elements.extend(self.create_notification_content())
        
        # Add subtle shadow
        shadow = FancyBboxPatch((1.05, 1.45), 8, 3,
                                boxstyle="round,pad=0.02",
                                facecolor='#000000', alpha=0.1,
                                edgecolor='none')
        self.notification_elements.append(shadow)
    
    def animate_fade_out(self):
        """Animate notification fading out"""
        progress = (self.frame_count - 80) / 20
        self.notification_opacity = 1.0 - progress
        self.slide_offset = 1.0
        
        # Update card
        self.notification_card.set_x(1 + self.slide_offset)
        self.notification_card.set_alpha(self.notification_opacity)
        self.notification_card.set_linewidth(1)
        
        # Update other elements
        self.update_static_elements()
        
        # Add notification content
        self.notification_elements.extend(self.create_notification_content())
    
    def animate_slide_out(self):
        """Animate notification sliding out to right"""
        progress = (self.frame_count - 100) / 20
        self.slide_offset = 1.0 + (2.0 * progress)
        self.notification_opacity = 0
        
        # Update card
        self.notification_card.set_x(1 + self.slide_offset)
        self.notification_card.set_alpha(0)
        
        # Update other elements
        self.update_static_elements()
    
    def update_static_elements(self):
        """Update static notification elements"""
        alpha = min(1.0, self.notification_opacity)
        
        # Close button
        self.close_button.set_alpha(alpha)
        
        # Teams logo
        self.teams_logo_bg.set_alpha(alpha)
        self.teams_logo.set_alpha(alpha)
        
        # Add to elements list
        self.notification_elements.extend([
            self.close_button, self.teams_logo_bg, self.teams_logo
        ])
        
        # Add taskbar
        self.notification_elements.extend(self.create_windows_taskbar())
    
    def create_gif(self, filename='teams_notification.gif', frames=120):
        """Create the animated GIF"""
        print(f"🔵 Creating Professional Teams Notification: {filename}")
        
        anim = animation.FuncAnimation(
            self.fig, self.update, frames=frames,
            interval=50, blit=False, repeat=True
        )
        
        # Save as GIF
        print("📽️ Rendering frames...")
        anim.save(filename, writer='pillow', fps=20, dpi=100)
        print(f"✅ Saved: {filename}")
        
        plt.close()
    
    def create_multiple_notifications(self):
        """Create different notification scenarios"""
        notifications = [
            {
                'title': 'SCOPE Security Alert',
                'message': 'ELEVATED threat level detected in Washroom Area B - Immediate response recommended',
                'time': 'Just now',
                'icon': '🚨',
                'filename': 'teams_security_alert.gif'
            },
            {
                'title': 'Air Quality Warning',
                'message': 'HAZARDOUS air quality detected - AQI 277 - Ventilation required',
                'time': '2 min ago',
                'icon': '💨',
                'filename': 'teams_air_quality.gif'
            },
            {
                'title': 'Vaping Detection',
                'message': 'VAPING activity detected in Stall 3 - Security response needed',
                'time': '5 min ago',
                'icon': '💨',
                'filename': 'teams_vaping_alert.gif'
            },
            {
                'title': 'System Update',
                'message': 'SCOPE sensors calibrated successfully - All systems operational',
                'time': '10 min ago',
                'icon': '✅',
                'filename': 'teams_system_update.gif'
            }
        ]
        
        for i, notification in enumerate(notifications):
            print(f"\n📱 Creating notification {i+1}/{len(notifications)}: {notification['filename']}")
            
            self.notification_title = notification['title']
            self.notification_message = notification['message']
            self.notification_time = notification['time']
            self.notification_icon = notification['icon']
            
            # Reset animation state
            self.frame_count = 0
            self.notification_opacity = 0
            self.slide_offset = -2.0
            self.pulse_phase = 0
            
            # Clear and recreate
            self.ax.clear()
            self.setup_teams_notification()
            
            # Create GIF
            self.create_gif(notification['filename'], frames=120)
            print(f"✅ Created: {notification['filename']}")

def main():
    """Main function"""
    print("=" * 60)
    print("🔵 PROFESSIONAL TEAMS NOTIFICATION GENERATOR")
    print("=" * 60)
    print("📱 Creating realistic Teams notifications:")
    print("   • Windows-style notification cards")
    print("   • Professional slide-in/out animations")
    print("   • Proper Teams branding and colors")
    print("   • Action buttons and timestamps")
    print("   • Multiple alert scenarios")
    print()
    
    # Create notifications
    teams_notifier = ProfessionalTeamsNotification()
    teams_notifier.create_multiple_notifications()
    
    print()
    print("🎯 Animation phases:")
    print("   1. Slide in from right (frames 0-10)")
    print("   2. Fade in effect (frames 10-20)")
    print("   3. Display with pulse (frames 20-80)")
    print("   4. Fade out effect (frames 80-100)")
    print("   5. Slide out to right (frames 100-120)")
    print()
    print("✅ Professional Teams notifications complete!")

if __name__ == "__main__":
    main()
