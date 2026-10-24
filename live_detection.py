import cv2
from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolov8n.pt")

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Could not open webcam")
    exit()

while True:
    success, frame = cap.read()

    if not success:
        break

    # Run YOLO on the current frame
    results = model(frame)

    # Draw detections on the frame
    annotated_frame = results[0].plot()

    cv2.imshow("YOLO Live Detection", annotated_frame)

    # Press q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()