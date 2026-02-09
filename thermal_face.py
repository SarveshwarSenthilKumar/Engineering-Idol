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

def non_max_suppression(boxes, overlapThresh=0.4):
    if len(boxes) == 0:
        return []

    boxes = np.array(boxes)
    x1 = boxes[:,0]
    y1 = boxes[:,1]
    x2 = boxes[:,0] + boxes[:,2]
    y2 = boxes[:,1] + boxes[:,3]

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
            np.concatenate(([len(idxs)-1], np.where(overlap > overlapThresh)[0]))
        )

    return boxes[pick].astype("int")

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

    # Frontal faces
    detections.extend(frontal.detectMultiScale(gray, 1.3, 5, minSize=(50, 50)))

    # Profile faces (left)
    detections.extend(profile.detectMultiScale(gray, 1.3, 5, minSize=(50, 50)))

    # Profile faces (right via flip)
    flipped = cv2.flip(gray, 1)
    profiles_flipped = profile.detectMultiScale(flipped, 1.3, 5, minSize=(50, 50))
    for (x, y, w, h) in profiles_flipped:
        detections.append((gray.shape[1] - x - w, y, w, h))

    # Tilted faces
    for angle in (-15, 15):
        rotated = rotate_image(gray, angle)
        rotated_faces = frontal.detectMultiScale(rotated, 1.3, 5, minSize=(50, 50))
        detections.extend(rotated_faces)

    # 🔥 Merge overlapping boxes
    final_faces = non_max_suppression(detections)

    # Draw ONE box per face
    for (x, y, w, h) in final_faces:
        cv2.rectangle(thermal, (x, y), (x + w, y + h), (255, 255, 255), 2)

    cv2.imshow("Robust Thermal Face Detection", thermal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
