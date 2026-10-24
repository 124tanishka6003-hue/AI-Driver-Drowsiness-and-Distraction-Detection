import cv2
import time
import subprocess
import csv
import os
import json
import threading
from datetime import datetime
from urllib.request import Request, urlopen
from ultralytics import YOLO

# ================== SETTINGS ==================

CSV_FILE = "dashboard_data.csv"
GOOGLE_SHEET_TOKEN = "DriveSafe2026"

GOOGLE_SHEET_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwaLttGh2PVhFi9ub3bGi-gh-6rhb3bayXAgzab-W8mckxRT1UtmtGDI-zBEfNb1snNPQ/"
    "exec"
)

CONFIDENCE = 0.30
PHONE_CONFIDENCE = 0.45
IMAGE_SIZE = 416
PHONE_CHECK_INTERVAL = 3
LOG_COOLDOWN = 5
ALERT_COOLDOWN = 5

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
stop_event = threading.Event()
state_lock = threading.Lock()

latest_frame = None
frame_id = 0
latest_boxes = []
eye_closed = False
yawn_detected = False
phone_detected = False
risk_score = 0
risk_level = "LOW"

last_logged = {}
last_alert_time = 0

# ================== LOAD MODELS ==================

print("Loading models...")
drowsiness_model = YOLO("models/best.pt")
phone_model = YOLO("yolov8n.pt")
print("Models loaded.")

# ================== CSV ==================

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "session_id", "event_type",
            "drowsiness", "yawn", "phone",
            "risk_score", "risk_level"
        ])

# ================== GOOGLE SHEETS ==================

def send_to_google_sheet(
    timestamp, event_type, drowsy, yawn, phone, score, level
):
    data = {
        "token": GOOGLE_SHEET_TOKEN,
        "timestamp": timestamp,
        "session_id": session_id,
        "event_type": event_type,
        "drowsiness": int(drowsy),
        "yawn": int(yawn),
        "phone": int(phone),
        "risk_score": int(score),
        "risk_level": level
    }

    request = Request(
        GOOGLE_SHEET_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(request, timeout=2) as response:
            response.read()
    except Exception as error:
        print("[SHEET ERROR]", error)


def log_event(event_type, drowsy, yawn, phone, score, level):
    now = time.time()

    if now - last_logged.get(event_type, 0) < LOG_COOLDOWN:
        return

    last_logged[event_type] = now
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(CSV_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                timestamp, session_id, event_type,
                int(drowsy), int(yawn), int(phone),
                score, level
            ])
    except OSError as error:
        print("[CSV ERROR]", error)

    threading.Thread(
        target=send_to_google_sheet,
        args=(
            timestamp, event_type, drowsy, yawn,
            phone, score, level
        ),
        daemon=True
    ).start()

    print(f"[LOG] {event_type} | Risk: {level}")


# ================== VOICE ALERT ==================

def voice_alert(message):
    global last_alert_time

    now = time.time()

    if now - last_alert_time >= ALERT_COOLDOWN:
        try:
            subprocess.Popen(["say", message])
            last_alert_time = now
        except Exception as error:
            print("[VOICE ERROR]", error)


# ================== DETECTION THREAD ==================

def detection_worker():
    global latest_boxes
    global eye_closed, yawn_detected, phone_detected
    global risk_score, risk_level

    processed_id = -1
    inference_count = 0
    phone_boxes = []

    while not stop_event.is_set():

        with state_lock:
            current_id = frame_id
            current_frame = (
                latest_frame.copy()
                if latest_frame is not None else None
            )

        if current_frame is None or current_id == processed_id:
            time.sleep(0.005)
            continue

        processed_id = current_id
        inference_count += 1

        new_eye_closed = False
        new_yawn = False
        boxes = []

        try:
            # Eye and yawning detection
            results = drowsiness_model(
                current_frame,
                conf=CONFIDENCE,
                imgsz=IMAGE_SIZE,
                verbose=False
            )

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(
                        int, box.xyxy[0].tolist()
                    )

                    if cls == 0:
                        new_eye_closed = True
                        label = f"Eye Closed {conf:.2f}"
                        color = (0, 0, 255)

                    elif cls == 1:
                        label = f"Eye Open {conf:.2f}"
                        color = (0, 200, 0)

                    elif cls == 2:
                        new_yawn = True
                        label = f"Yawn {conf:.2f}"
                        color = (0, 165, 255)

                    else:
                        continue

                    boxes.append(
                        (x1, y1, x2, y2, label, color)
                    )

            # Phone model runs less often to reduce lag
            if inference_count % PHONE_CHECK_INTERVAL == 0:
                phone_detected = False
                phone_boxes = []

                phone_results = phone_model(
                    current_frame,
                    conf=PHONE_CONFIDENCE,
                    imgsz=IMAGE_SIZE,
                    verbose=False
                )

                for result in phone_results:
                    for box in result.boxes:
                        if int(box.cls[0]) != 67:
                            continue

                        phone_detected = True
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(
                            int, box.xyxy[0].tolist()
                        )

                        phone_boxes.append((
                            x1, y1, x2, y2,
                            f"Phone {conf:.2f}",
                            (255, 0, 0)
                        ))

            boxes.extend(phone_boxes)

            # Demo risk score, not a medically validated score
            score = (
                (40 if new_eye_closed else 0)
                + (20 if new_yawn else 0)
                + (40 if phone_detected else 0)
            )
            score = min(score, 100)

            if score >= 60:
                level = "HIGH"
            elif score >= 30:
                level = "MEDIUM"
            else:
                level = "LOW"

            with state_lock:
                eye_closed = new_eye_closed
                yawn_detected = new_yawn
                risk_score = score
                risk_level = level
                latest_boxes = boxes

            if new_eye_closed:
                log_event(
                    "Drowsiness", new_eye_closed, new_yawn,
                    phone_detected, score, level
                )

            if new_yawn:
                log_event(
                    "Yawn", new_eye_closed, new_yawn,
                    phone_detected, score, level
                )

            if phone_detected:
                log_event(
                    "Phone", new_eye_closed, new_yawn,
                    phone_detected, score, level
                )

            if level == "HIGH":
                log_event(
                    "High Risk", new_eye_closed, new_yawn,
                    phone_detected, score, level
                )

            if new_eye_closed and phone_detected:
                voice_alert(
                    "Warning. You are drowsy and using your phone."
                )
            elif new_eye_closed:
                voice_alert(
                    "Warning. You appear drowsy. Please stay alert."
                )
            elif new_yawn:
                voice_alert(
                    "You appear tired. Please take a break."
                )
            elif phone_detected:
                voice_alert(
                    "Please do not use your phone while driving."
                )

        except Exception as error:
            print("[DETECTION ERROR]", error)
            time.sleep(0.1)


# ================== CAMERA ==================

camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

if not camera.isOpened():
    camera.release()
    camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not camera.isOpened():
    print("ERROR: Camera could not be opened.")
    raise SystemExit(1)

worker = threading.Thread(
    target=detection_worker,
    daemon=True
)
worker.start()

print("Camera started. Press Q on the camera window to quit.")
print("You can also press Ctrl+C in Terminal.")

try:
    while True:
        success, frame = camera.read()

        if not success:
            print("Camera frame could not be read.")
            break

        # Share the newest frame with the detection thread
        with state_lock:
            latest_frame = frame.copy()
            frame_id += 1
            boxes = list(latest_boxes)
            score = risk_score
            level = risk_level

        # Draw detections on the live camera
        for x1, y1, x2, y2, label, color in boxes:
            cv2.rectangle(
                frame, (x1, y1), (x2, y2), color, 2
            )
            cv2.putText(
                frame, label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, color, 2
            )

        cv2.putText(
            frame, f"Risk: {level}", (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2
        )

        cv2.putText(
            frame, f"Score: {score}", (15, 68),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2
        )

        cv2.putText(
            frame, "Press Q to quit", (15, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2
        )

        cv2.imshow("Driver Monitoring System", frame)

        # Check Q on every display iteration
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), ord("Q")):
            print("Stopping camera...")
            break

except KeyboardInterrupt:
    print("Stopping camera from Terminal...")

finally:
    stop_event.set()
    camera.release()
    cv2.destroyAllWindows()

    try:
        subprocess.run(
            ["killall", "say"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1
        )
    except Exception:
        pass

    print("Monitoring stopped.")
    print(f"Dashboard data saved to: {CSV_FILE}")