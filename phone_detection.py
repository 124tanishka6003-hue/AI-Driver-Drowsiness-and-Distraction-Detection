import cv2
import subprocess
from ultralytics import YOLO  
import time

# Load YOLO model
model = YOLO("yolov8n.pt")

PERSON = 0
CELL_PHONE = 67

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera could not be opened")
    exit()

# Prevent the voice from repeating continuously
last_alert_time = 0
alert_cooldown = 5

print("✅ Driver monitoring started")
print("Press Q to stop")

while True:
    success, frame = cap.read()

    if not success:
        break

    results = model(frame, verbose=False)

    phone_detected = False
    person_detected = False

    for box in results[0].boxes:

        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        if confidence < 0.5:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        if class_id == PERSON:
            person_detected = True
            label = f"Person {confidence:.0%}"

        elif class_id == CELL_PHONE:
            phone_detected = True
            label = f"Phone {confidence:.0%}"

        else:
            continue

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

    # Driver status
    if phone_detected:

        status = "WARNING: PHONE DETECTED"

        # Voice alert every 5 seconds
        current_time = time.time()

        if current_time - last_alert_time > alert_cooldown:

            subprocess.Popen([
                "say",
                "Warning. Please do not use your phone while driving."
            ])

            last_alert_time = current_time

    elif person_detected:
        status = "DRIVER ALERT"

    else:
        status = "NO DRIVER DETECTED"

    # Display status
    cv2.putText(
        frame,
        status,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255) if phone_detected else (0, 255, 0),
        3
    )

    cv2.imshow("AI Driver Monitoring System", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()