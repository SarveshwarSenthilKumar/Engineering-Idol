#Creating a pseudo thermal camera for Engineering Idol testing

import cv2

# Open default camera (0)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not access the camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply a thermal-style colormap
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    # Show the thermal view
    cv2.imshow("Pseudo Thermal Camera", thermal)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
