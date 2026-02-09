import cv2
import numpy as np
from collections import deque

# Load cascades
frontal = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
profile = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_profileface.xml"
)
alt_frontal = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
)

def rotate_image(image, angle):
    """Rotate image around center"""
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h))

def non_max_suppression(boxes, overlapThresh=0.35):
    """Remove overlapping detections"""
    if len(boxes) == 0:
        return []

    boxes = np.array(boxes, dtype=np.float32)
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]

    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(area)

    pick = []

    while len(idxs) > 0:
        last = idxs[-1]
        pick.append(last)

        xx1 = np.maximum(x1[last], x1[idxs[:-1]])
        yy1 = np.maximum(y1[last], y1[idxs[:-1]])
        xx2 = np.minimum(x2[last], x2[idxs[:-1]])
        yy2 = np.minimum(y2[last], y2[idxs[:-1]])

        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        overlap = (w * h) / area[idxs[:-1]]

        idxs = np.delete(
            idxs,
            np.concatenate(([len(idxs) - 1], np.where(overlap > overlapThresh)[0]))
        )

    return boxes[pick].astype("int")

def detect_faces_smart(gray):
    """Efficient multi-angle detection"""
    detections = []
    
    # 1. Standard frontal detection (most common)
    faces = frontal.detectMultiScale(gray, 1.2, 4, minSize=(40, 40))
    detections.extend(faces)
    
    # 2. Alternative frontal (catches different angles)
    faces_alt = alt_frontal.detectMultiScale(gray, 1.2, 3, minSize=(40, 40))
    detections.extend(faces_alt)
    
    # 3. Profile detection (left side)
    profiles = profile.detectMultiScale(gray, 1.2, 4, minSize=(40, 40))
    detections.extend(profiles)
    
    # 4. Profile detection (right side via flip)
    flipped = cv2.flip(gray, 1)
    profiles_flipped = profile.detectMultiScale(flipped, 1.2, 4, minSize=(40, 40))
    for (x, y, w, h) in profiles_flipped:
        detections.append((gray.shape[1] - x - w, y, w, h))
    
    # 5. ONLY check tilted angles if no faces found yet
    if len(detections) < 2:
        # Check moderate tilts
        for angle in [-20, 20, -40, 40]:
            rotated = rotate_image(gray, angle)
            tilted_faces = frontal.detectMultiScale(rotated, 1.2, 3, minSize=(40, 40))
            detections.extend(tilted_faces)
            
            if len(detections) >= 2:  # Found something, stop searching
                break
    
    return detections

def enhance_image(gray):
    """Quick contrast enhancement"""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def detect_motion(prev_frame, curr_frame, threshold=25):
    """Detect motion between frames"""
    if prev_frame is None:
        return None, 0
    
    # Calculate frame difference
    frame_diff = cv2.absdiff(prev_frame, curr_frame)
    
    # Threshold the difference
    _, thresh = cv2.threshold(frame_diff, threshold, 255, cv2.THRESH_BINARY)
    
    # Dilate to fill gaps
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Calculate total motion area
    motion_area = sum(cv2.contourArea(c) for c in contours)
    
    return contours, motion_area

def analyze_motion_patterns(motion_history, velocity_history, acceleration_history):
    """Analyze motion for violent/physical activity patterns"""
    if len(motion_history) < 5:
        return "NORMAL", 0
    
    recent_motion = list(motion_history)[-10:]
    recent_velocity = list(velocity_history)[-10:]
    recent_accel = list(acceleration_history)[-10:]
    
    avg_motion = np.mean(recent_motion)
    max_motion = np.max(recent_motion)
    avg_velocity = np.mean([abs(v) for v in recent_velocity])
    max_accel = np.max([abs(a) for a in recent_accel])
    
    # Motion intensity score (0-100)
    intensity = 0
    threat_level = "NORMAL"
    
    # High sustained motion
    if avg_motion > 15000:
        intensity += 20
    
    # Sudden large movements (potential strikes)
    if max_motion > 50000:
        intensity += 25
        threat_level = "HIGH MOTION"
    
    # Rapid velocity changes (punches, kicks)
    if avg_velocity > 20000:
        intensity += 25
        threat_level = "RAPID MOVEMENT"
    
    # High acceleration (violent actions)
    if max_accel > 30000:
        intensity += 30
        threat_level = "VIOLENT MOTION"
    
    # Erratic motion pattern (fighting, struggling)
    motion_variance = np.std(recent_motion)
    if motion_variance > 15000:
        intensity += 20
        threat_level = "ERRATIC MOTION"
    
    # Determine threat level
    if intensity >= 60:
        threat_level = "⚠️ PHYSICAL CONTACT DETECTED"
    elif intensity >= 40:
        threat_level = "⚠️ AGGRESSIVE MOVEMENT"
    elif intensity >= 25:
        threat_level = "ELEVATED ACTIVITY"
    else:
        threat_level = "NORMAL"
    
    return threat_level, intensity

def detect_proximity_violations(faces):
    """Detect if faces are too close (potential contact)"""
    if len(faces) < 2:
        return False, []
    
    violations = []
    
    for i, (x1, y1, w1, h1) in enumerate(faces):
        for j, (x2, y2, w2, h2) in enumerate(faces):
            if i >= j:
                continue
            
            # Calculate center points
            center1 = (x1 + w1//2, y1 + h1//2)
            center2 = (x2 + w2//2, y2 + h2//2)
            
            # Calculate distance
            distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
            
            # Average face size
            avg_size = (w1 + w2 + h1 + h2) / 4
            
            # If faces are closer than 0.8x average face size, flag as potential contact
            if distance < avg_size * 0.8:
                violations.append((center1, center2, distance))
    
    return len(violations) > 0, violations

# Camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera error")
    exit()

# Reduce resolution for faster processing
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Enhanced Thermal Detection with Violence Detection")
print("Press 'q' to quit")

frame_count = 0
prev_faces = []
prev_gray = None

# Motion tracking
motion_history = deque(maxlen=30)
velocity_history = deque(maxlen=30)
acceleration_history = deque(maxlen=30)
prev_motion_area = 0

# Alert system
alert_active = False
alert_frames = 0
ALERT_DURATION = 30  # frames

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur for motion detection
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    
    # Detect motion
    motion_contours, motion_area = detect_motion(prev_gray, blurred, threshold=25)
    
    # Calculate velocity and acceleration
    velocity = motion_area - prev_motion_area
    if len(velocity_history) > 0:
        acceleration = velocity - velocity_history[-1]
    else:
        acceleration = 0
    
    # Update histories
    motion_history.append(motion_area)
    velocity_history.append(velocity)
    acceleration_history.append(acceleration)
    
    # Analyze motion patterns
    threat_level, intensity = analyze_motion_patterns(motion_history, velocity_history, acceleration_history)
    
    # Apply thermal colormap
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    thermal = cv2.GaussianBlur(thermal, (81, 81), 0)
    
    # Face detection
    if frame_count % 1 == 0:
        enhanced = enhance_image(gray)
        detections = detect_faces_smart(enhanced)
        final_faces = non_max_suppression(detections, overlapThresh=0.35)
        
        if len(final_faces) > 0:
            prev_faces = final_faces
    else:
        final_faces = prev_faces
    
    # Check for proximity violations (physical contact)
    proximity_alert, violations = detect_proximity_violations(final_faces)
    
    # Determine if alert should be active
    if threat_level in ["⚠️ PHYSICAL CONTACT DETECTED", "⚠️ AGGRESSIVE MOVEMENT"] or proximity_alert:
        alert_active = True
        alert_frames = ALERT_DURATION
    
    # Countdown alert
    if alert_frames > 0:
        alert_frames -= 1
    else:
        alert_active = False
    
    # Draw motion contours (optional visualization)
    if motion_contours is not None:
        for contour in motion_contours:
            if cv2.contourArea(contour) > 500:  # Filter small movements
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(thermal, (x, y), (x + w, y + h), (0, 255, 255), 1)
    
    # Draw face detection boxes
    for (x, y, w, h) in final_faces:
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        
        # Color based on alert status
        box_color = (0, 0, 255) if alert_active else (255, 255, 255)
        
        cv2.rectangle(thermal, (x, y), (x + w, y + h), box_color, 2)
        cv2.putText(
            thermal, 
            "FACE", 
            (x, y - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            box_color, 
            2
        )

    # Draw proximity violations
    for center1, center2, distance in violations:
        cv2.line(thermal, center1, center2, (0, 0, 255), 2)
        cv2.circle(thermal, center1, 5, (0, 0, 255), -1)
        cv2.circle(thermal, center2, 5, (0, 0, 255), -1)
    
    # Display info panel
    info_y = 30
    cv2.putText(thermal, f"Faces: {len(final_faces)}", (10, info_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    info_y += 25
    cv2.putText(thermal, f"Motion: {int(motion_area)}", (10, info_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    info_y += 25
    cv2.putText(thermal, f"Intensity: {int(intensity)}%", (10, info_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Display threat level
    info_y += 35
    threat_color = (0, 0, 255) if alert_active else (255, 255, 255)
    cv2.putText(thermal, threat_level, (10, info_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, threat_color, 2)
    
    # Display proximity warning
    if proximity_alert:
        info_y += 30
        cv2.putText(thermal, "⚠️ CLOSE CONTACT!", (10, info_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Big alert banner
    if alert_active:
        overlay = thermal.copy()
        cv2.rectangle(overlay, (0, 0), (thermal.shape[1], 60), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.4, thermal, 0.6, 0, thermal)
        
        cv2.putText(thermal, "⚠️ ALERT: PHYSICAL ACTIVITY DETECTED ⚠️", 
                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    cv2.imshow("Thermal Detection + Violence Monitor", thermal)

    # Update previous frame
    prev_gray = blurred.copy()
    prev_motion_area = motion_area

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()