# AI-Driven Driver Drowsiness and Distraction Detection System

## 📌 About the Project
This project uses Artificial Intelligence and Computer Vision to detect driver drowsiness and distractions in real time. It aims to improve road safety by identifying signs of sleepiness, yawning, and mobile phone usage.

## ✨ Features
- 😴 Driver drowsiness detection
- 🥱 Yawning detection
- 📱 Mobile phone detection
- ⚠️ Risk score and risk level analysis
- 📍 GPS location tracking
- 📊 Tableau dashboard for data visualization

## 🛠️ Technologies Used
- Python
- OpenCV
- YOLO (Ultralytics)
- Pandas
- Tableau

## 📂 Project Structure
- `backend/` – Detection and processing scripts
- `models/` – Trained AI model files
- `dataset/` – Dataset information and configuration
- `dashboard_data.csv` – Sample detection data for Tableau
- `get_gps.py` – GPS location functionality, if used

## 🚀 How It Works
1. The webcam captures the driver's video.
2. The AI model analyzes the video to detect drowsiness and distractions.
3. Detection events and risk information are stored in a CSV file.
4. Tableau visualizes the recorded data through charts, KPI cards, risk analysis, and a GPS map.

## ⚙️ Requirements
Python and the required libraries must be installed. Refer to `requirements.txt` for dependencies.

## 📊 Dashboard
The Tableau dashboard can be shared using a packaged Tableau workbook (`.twbx`) file exported from Tableau Desktop.

## 🎯 Objective
The main objective is to support safer driving by detecting signs of drowsiness and distraction using AI-based computer vision.

## 👩‍💻 Project Status
Academic project developed for learning and demonstration purposes.

---
**Note:** This system is a driver-safety aid and should not replace attentive driving or certified vehicle safety systems.
