#!/usr/bin/env python3
"""
SCOPE Sensor GIF Generator
Creates animated GIFs for all SCOPE sensors:
  - mmwave_radar_simple.gif    — polar radar with person tracking
  - sound_sensor_simple.gif    — acoustic dB waveform
  - air_quality_circles.gif    — overlapping circle grid, color = AQI
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as mcolors
import random
import io
from PIL import Image

plt.style.use('dark_background')


# ══════════════════════════════════════════════════════════════════════════════
#  1.  mmWave Radar
# ══════════════════════════════════════════════════════════════════════════════

class SimpleRadarViz:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        self.time_step = 0
        self.setup_plot()

    def setup_plot(self):
        self.fig.patch.set_facecolor('#000000')
        self.ax.set_facecolor('#000000')

        self.ax.set_ylim(0, 5.5)
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)

        self.ax.set_title('mmWave Radar - 60GHz ULTRA-WIDEBAND',
                          fontsize=16, color='#FF0000', fontweight='bold')

        # Range circles
        for radius in [1, 2, 3, 4, 5]:
            self.ax.plot([0, 2 * np.pi], [radius, radius],
                         color='#FF0000', alpha=0.8, linewidth=2)
            self.ax.text(0, radius, f'{radius}m', fontsize=8, color='#FF0000',
                         ha='center', va='center', fontweight='bold')

        # Sweep lines
        for angle in np.linspace(0, 2 * np.pi, 36, endpoint=False):
            self.ax.plot([angle, angle], [0, 5.5],
                         color='#FF0000', alpha=0.4, linewidth=1)

        # Compass
        for label, angle in [('N', 0), ('E', np.pi / 2),
                              ('S', np.pi), ('W', 3 * np.pi / 2)]:
            self.ax.text(angle, 5.8, label, fontsize=12, color='#FF0000',
                         ha='center', va='center', fontweight='bold')

        # Walls
        wc, ww = '#FF0000', 3

        def wall(xs, ys):
            a = np.arctan2(ys, xs)
            r = np.sqrt(xs ** 2 + ys ** 2)
            self.ax.plot(a, r, color=wc, linewidth=ww)

        x = np.linspace(-4, 4, 50)
        wall(x, np.full_like(x, 4))
        wall(np.linspace(-4, -0.75, 25), np.full(25, -4))
        wall(np.linspace(0.75, 4, 25), np.full(25, -4))
        y = np.linspace(-4, 4, 50)
        wall(np.full_like(y, -4), y)
        wall(np.full_like(y, 4), y)

        # Door markers
        dla = np.arctan2(-4, -0.75)
        dra = np.arctan2(-4, 0.75)
        self.ax.plot([dla, dla], [4.0, 4.5], color='#00FF00', linewidth=4)
        self.ax.plot([dra, dra], [4.0, 4.5], color='#00FF00', linewidth=4)
        self.ax.text((dla + dra) / 2, 4.8, 'DOOR',
                     fontsize=10, color='#00FF00', ha='center', fontweight='bold')

        # Fixtures
        for x, y in [(-3.6, -2), (-3.6, 0), (-3.6, 2)]:
            self.ax.scatter([np.arctan2(y, x)], [np.hypot(x, y)],
                            c='#FFFF00', s=50, marker='s')
        for x, y in [(3.6, -3), (3.6, -1), (3.6, 1), (3.6, 3)]:
            self.ax.scatter([np.arctan2(y, x)], [np.hypot(x, y)],
                            c='#FFFF00', s=50, marker='s')

        self.all_targets = self.ax.scatter([], [], c='#FF0000', s=200, alpha=0.8,
                                           edgecolors='#FFFFFF', linewidth=2, marker='o')
        self.alert_texts = []
        self.info_text = self.ax.text(
            0.02, 0.98, '', transform=self.ax.transAxes,
            fontsize=11, fontweight='bold', color='#FF0000',
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='#000000',
                      edgecolor='#FF0000', linewidth=2, alpha=0.9))

    def update(self, frame):
        self.time_step += 1
        t = self.time_step * 0.05

        for txt in self.alert_texts:
            txt.remove()
        self.alert_texts = []

        energy = {'stationary': 0.1, 'normal': 0.3, 'vaping': 0.5, 'fighting': 0.9}
        target_angles, target_radii = [], []

        for i in range(10):
            if i < 2:
                x, y = [(-3.6, -2), (-3.6, 2)][i]
                x += 0.1 * np.sin(t * energy['stationary'])
                y += 0.05 * np.cos(t * energy['stationary'])
                a, r = np.arctan2(y, x), np.hypot(x, y)
                target_angles.append(a); target_radii.append(r)
                self.alert_texts.append(
                    self.ax.text(a, r + 0.3, 'STATIONARY',
                                 fontsize=7, color='#FFFF00', fontweight='bold',
                                 ha='center', va='bottom'))

            elif i < 6:
                bx = -2.0 + i * 1.0
                by = -1.0 + (i % 2) * 2.0
                x = np.clip(bx + 0.8 * np.sin(t * 0.2 * energy['normal'] + i), -3.5, 3.5)
                y = np.clip(by + 0.6 * np.cos(t * 0.3 * energy['normal'] + i * 0.5), -3.5, 3.5)
                target_angles.append(np.arctan2(y, x))
                target_radii.append(np.hypot(x, y))

            elif i < 8:
                vx = 2.0 + 0.4 * np.sin(t * 0.1 * energy['vaping'])
                vy = 1.0 + 0.3 * np.cos(t * 0.1 * energy['vaping'])
                x = np.clip(vx + (-0.2 if i == 6 else 0.2), -3.5, 3.5)
                y = np.clip(vy, -3.5, 3.5)
                a, r = np.arctan2(y, x), np.hypot(x, y)
                target_angles.append(a); target_radii.append(r)
                self.alert_texts.append(
                    self.ax.text(a, r + 0.3, 'VAPING!',
                                 fontsize=7, color='#00FF00', fontweight='bold',
                                 ha='center', va='bottom'))

            else:
                fbx = -2.0 + 0.6 * np.sin(t * 0.8 * energy['fighting'])
                fby = -1.0 + 0.6 * np.cos(t * 0.8 * energy['fighting'])
                if i == 8:
                    x = fbx + 0.4 * np.sin(t * 3.0 * energy['fighting'])
                    y = fby + 0.4 * np.cos(t * 2.5 * energy['fighting'])
                else:
                    x = fbx - 0.4 * np.sin(t * 2.8 * energy['fighting'])
                    y = fby - 0.4 * np.cos(t * 3.2 * energy['fighting'])
                x, y = np.clip(x, -3.5, 3.5), np.clip(y, -3.5, 3.5)
                a, r = np.arctan2(y, x), np.hypot(x, y)
                target_angles.append(a); target_radii.append(r)
                self.alert_texts.append(
                    self.ax.text(a, r + 0.3, 'FIGHTING!',
                                 fontsize=7, color='#FF00FF', fontweight='bold',
                                 ha='center', va='bottom'))

        if target_angles:
            self.all_targets.set_offsets(np.c_[target_angles, target_radii])
        else:
            self.all_targets.set_offsets(np.empty((0, 2)))

        self.info_text.set_text(
            f"RADAR MONITORING ACTIVE\n"
            f"TOTAL TARGETS: {len(target_angles)}\n"
            f"LINEAR MOVEMENT\n"
            f"POLAR RADAR DISPLAY\n"
            f"RANGE: 5.5m")

        return [self.all_targets, self.info_text] + self.alert_texts

    def create_gif(self, filename='mmwave_radar_simple.gif', frames=50):
        print(f"Creating {filename}...")
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                       interval=100, blit=True)
        anim.save(filename, writer='pillow', fps=10)
        print(f"Saved: {filename}")
        plt.close()


# ══════════════════════════════════════════════════════════════════════════════
#  2.  Sound Sensor
# ══════════════════════════════════════════════════════════════════════════════

class SimpleSoundViz:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.time_step = 0
        self.db_history = []
        self.time_history = []
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
        base_db = 50 + 20 * np.sin(t * 0.1)
        if random.random() < 0.1:
            db = base_db + random.uniform(15, 40)
        else:
            db = base_db + random.uniform(-5, 5)

        self.db_history.append(db)
        self.time_history.append(t)
        if len(self.db_history) > 30:
            self.db_history.pop(0)
            self.time_history.pop(0)

        self.line.set_data(self.time_history, self.db_history)
        if self.time_history:
            self.ax.set_xlim(max(0, self.time_history[-1] - 3),
                             self.time_history[-1] + 0.5)
        return [self.line]

    def create_gif(self, filename='sound_sensor_simple.gif', frames=50):
        print(f"Creating {filename}...")
        anim = animation.FuncAnimation(self.fig, self.update, frames=frames,
                                       interval=200, blit=True)
        anim.save(filename, writer='pillow', fps=5)
        print(f"Saved: {filename}")
        plt.close()


# ══════════════════════════════════════════════════════════════════════════════
#  3.  Air Quality — Overlapping Circle Grid
# ══════════════════════════════════════════════════════════════════════════════

# Color ramp: good (green) -> moderate (yellow) -> unhealthy (orange) -> hazardous (red)
_AQI_STOPS = [
    (0,   '#1a7a3c'),
    (25,  '#4caf50'),
    (50,  '#cddc39'),
    (75,  '#ff9800'),
    (100, '#e53935'),
]


def _aqi_to_rgb(aqi, alpha=None):
    """Interpolate an RGBA (or RGB) color from an AQI value using _AQI_STOPS."""
    aqi = max(0.0, min(100.0, float(aqi)))
    for i in range(len(_AQI_STOPS) - 1):
        a_val, a_hex = _AQI_STOPS[i]
        b_val, b_hex = _AQI_STOPS[i + 1]
        if a_val <= aqi <= b_val:
            t = (aqi - a_val) / (b_val - a_val)
            ac = np.array(mcolors.to_rgb(a_hex))
            bc = np.array(mcolors.to_rgb(b_hex))
            rgb = tuple(ac + t * (bc - ac))
            return (*rgb, alpha) if alpha is not None else rgb
    rgb = mcolors.to_rgb(_AQI_STOPS[-1][1])
    return (*rgb, alpha) if alpha is not None else rgb


def _make_air_frame(aqi: float, frame_idx: int) -> Image.Image:
    """Render one air-quality frame as a PIL Image."""
    fig, ax = plt.subplots(figsize=(7, 7), dpi=110)
    fig.patch.set_facecolor('#f5f4ef')
    ax.set_facecolor('#f5f4ef')
    ax.set_aspect('equal')
    ax.axis('off')

    # Grid layout — hexagonal packing (offset every other row)
    cols, rows = 7, 7
    radius   = 0.72
    spacing  = 1.15
    hex_off  = spacing * 0.5

    total_w = (cols - 1) * spacing + hex_off + radius * 2
    total_h = (rows - 1) * spacing * 0.87 + radius * 2
    margin  = 0.3

    ax.set_xlim(-margin, total_w + margin)
    ax.set_ylim(-margin, total_h + margin)

    # Fixed random phases/amplitudes per sensor (seed for consistency)
    np.random.seed(42)
    phases = np.random.uniform(0, 2 * np.pi, (rows, cols))
    amps   = np.random.uniform(2, 8, (rows, cols))

    circles_drawn = []

    for row in range(rows):
        for col in range(cols):
            cx = col * spacing + (hex_off if row % 2 == 1 else 0) + radius
            cy = row * spacing * 0.87 + radius

            # Each sensor breathes slightly independently
            local_aqi = aqi + amps[row, col] * np.sin(
                frame_idx * 0.08 + phases[row, col])
            local_aqi = max(0.0, min(100.0, local_aqi))

            # Large semi-transparent filled circle
            ax.add_patch(plt.Circle(
                (cx, cy), radius,
                color=_aqi_to_rgb(local_aqi, alpha=0.32),
                linewidth=0, zorder=2))

            # Dashed outline ring
            ring_rgb = _aqi_to_rgb(local_aqi)
            ax.add_patch(plt.Circle(
                (cx, cy), radius,
                fill=False,
                edgecolor=(*ring_rgb, 0.55),
                linewidth=0.8,
                linestyle=(0, (4, 3)),
                zorder=3))

            circles_drawn.append((cx, cy, local_aqi))

    # Small center dots
    for (cx, cy, local_aqi) in circles_drawn:
        dot_rgb = _aqi_to_rgb(local_aqi)
        ax.add_patch(plt.Circle((cx, cy), 0.065, color=dot_rgb, zorder=5))
        ax.add_patch(plt.Circle((cx, cy), 0.025, color='white', zorder=6))

    # Status label
    if aqi < 25:
        status, s_col = 'GOOD',      '#1a7a3c'
    elif aqi < 50:
        status, s_col = 'MODERATE',  '#7a7a00'
    elif aqi < 75:
        status, s_col = 'UNHEALTHY', '#c45c00'
    else:
        status, s_col = 'HAZARDOUS', '#b71c1c'

    label_x = (total_w + margin * 2) / 2 - margin

    ax.text(label_x, total_h + margin * 0.6 + 0.55,
            f'AQI {aqi:.0f}',
            ha='center', va='center',
            fontsize=22, fontweight='bold',
            color=s_col, fontfamily='DejaVu Sans')

    ax.text(label_x, total_h + margin * 0.6,
            status,
            ha='center', va='center',
            fontsize=12, fontweight='bold',
            color=s_col, alpha=0.85,
            fontfamily='DejaVu Sans')

    ax.text(label_x, -margin * 0.7,
            'Air Quality - Sensor Coverage Grid',
            ha='center', va='center',
            fontsize=8, color='#888',
            fontfamily='DejaVu Sans')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight',
                facecolor=fig.get_facecolor(), dpi=110)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).copy()


def create_air_quality_gif(filename='air_quality_circles.gif', n_frames=72):
    """
    Animate the air-quality circle grid through a full AQI cycle
    (good -> hazardous -> good) and save as an animated GIF.
    """
    print(f"Creating {filename}...")
    frames = []
    for i in range(n_frames):
        # Smooth sine cycle: AQI 6 -> 94 -> 6
        aqi = 50 + 44 * np.sin(2 * np.pi * i / n_frames - np.pi / 2)
        frames.append(_make_air_frame(aqi, i))
        if (i + 1) % 12 == 0:
            print(f"  Frame {i + 1}/{n_frames} -- AQI {aqi:.0f}")

    frames[0].save(
        filename,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=80,        # ms per frame (~12 fps)
        optimize=False,
    )
    print(f"Saved: {filename}")


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def create_all_gifs():
    print("Creating SCOPE Sensor GIFs...\n")

    radar = SimpleRadarViz()
    radar.create_gif('mmwave_radar_simple.gif', frames=50)

    sound = SimpleSoundViz()
    sound.create_gif('sound_sensor_simple.gif', frames=50)

    create_air_quality_gif('air_quality_circles.gif', n_frames=72)

    print("\nAll sensor GIFs created successfully!")
    print("Files saved:")
    print("   - mmwave_radar_simple.gif")
    print("   - sound_sensor_simple.gif")
    print("   - air_quality_circles.gif")


if __name__ == '__main__':
    create_all_gifs()