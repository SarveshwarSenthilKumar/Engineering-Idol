import cv2

# Load face detection model
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# Open default camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not access the camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply thermal colormap
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(50, 50)
    )

    # Draw bounding boxes on thermal image
    for (x, y, w, h) in faces:
        cv2.rectangle(
            thermal,
            (x, y),
            (x + w, y + h),
            (255, 255, 255),  # white box for contrast
            2
        )

    # Show result
    cv2.imshow("Pseudo Thermal Camera + Face Detection", thermal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
