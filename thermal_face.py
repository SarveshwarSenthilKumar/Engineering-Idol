import cv2
import numpy as np

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

# Preprocessing
def enhance_image(gray):
    """Quick contrast enhancement"""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

# Camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera error")
    exit()

# Reduce resolution for faster processing
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Optimized Robust Face Detection Active")
print("Press 'q' to quit")

frame_count = 0
prev_faces = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply thermal colormap
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    
    # Process every frame, but use smart detection
    if frame_count % 1 == 0:  # Process every frame
        # Enhance contrast
        enhanced = enhance_image(gray)
        
        # Smart detection
        detections = detect_faces_smart(enhanced)
        
        # Apply NMS
        final_faces = non_max_suppression(detections, overlapThresh=0.35)
        
        # Store for next frame
        if len(final_faces) > 0:
            prev_faces = final_faces
    else:
        # Use previous detections
        final_faces = prev_faces
    
    # Draw detection boxes
    for (x, y, w, h) in final_faces:
        # Ensure coordinates are valid
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        
        cv2.rectangle(thermal, (x, y), (x + w, y + h), (255, 255, 255), 2)
        cv2.putText(
            thermal, 
            "FACE", 
            (x, y - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (255, 255, 255), 
            2
        )
    
    # Display count
    cv2.putText(
        thermal,
        f"Faces: {len(final_faces)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.imshow("Optimized Thermal Face Detection", thermal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()