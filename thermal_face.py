import cv2
import numpy as np

# Load cascades
frontal = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
profile = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_profileface.xml"
)

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h))

# Camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera error")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    detections = []

    # 1️⃣ Frontal detection
    faces = frontal.detectMultiScale(gray, 1.3, 5, minSize=(50, 50))
    detections.extend(faces)

    # 2️⃣ Profile detection (left + right)
    profiles = profile.detectMultiScale(gray, 1.3, 5, minSize=(50, 50))
    detections.extend(profiles)

    flipped = cv2.flip(gray, 1)
    profiles_flipped = profile.detectMultiScale(flipped, 1.3, 5, minSize=(50, 50))
    for (x, y, w, h) in profiles_flipped:
        detections.append((gray.shape[1] - x - w, y, w, h))

    # 3️⃣ Rotated detection (tilted heads)
    for angle in (-15, 15):
        rotated = rotate_image(gray, angle)
        rotated_faces = frontal.detectMultiScale(rotated, 1.3, 5, minSize=(50, 50))
        detections.extend(rotated_faces)

    # 4️⃣ Draw all detections
    for (x, y, w, h) in detections:
        cv2.rectangle(
            thermal,
            (x, y),
            (x + w, y + h),
            (255, 255, 255),
            2
        )

    cv2.imshow("Robust Pseudo Thermal Face Detection", thermal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
