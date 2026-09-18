import cv2
from pathlib import Path
from ultralytics import YOLO

video_path = Path("sample.mp4")
if not video_path.exists():
    print("sample.mp4 not found")
    exit(1)

cap = cv2.VideoCapture(str(video_path))
fps = cap.get(cv2.CAP_PROP_FPS)
count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
duration = count / max(1, fps)
print(f"Sample Video: {w}x{h}, {fps:.1f} FPS, {count} frames, {duration:.1f}s")

# Grab middle frame
cap.set(cv2.CAP_PROP_POS_FRAMES, count // 2)
ret, frame = cap.read()
cap.release()

if ret:
    frame_save_path = Path("backend/data/demos/user_sample_preview.jpg")
    cv2.imwrite(str(frame_save_path), frame)
    print(f"Saved preview frame to {frame_save_path}")

    model = YOLO("yolov8n.pt")
    results = model(frame, verbose=False)
    boxes = results[0].boxes
    detected_classes = [results[0].names[int(b.cls[0].item())] for b in boxes]
    print(f"Detected targets in sample: {detected_classes}")
else:
    print("Failed to decode frame from sample.mp4")
