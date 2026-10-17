import supervision as sv
from ultralytics import YOLO
from configparser import ConfigParser
import cv2
import websocket
import time
import socket

model = YOLO("/mnt/c/Documents and Settings/MANJU/Downloads/yolo_model/yolo_model/combined_best.pt")
arm_id = "J007_L01_01_X"

box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)) 
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

ip_address = get_local_ip()

def is_image(path):
    return path.lower().endswith(IMAGE_EXTENSIONS)

def process_frame(frame, tracker):
    frame = cv2.resize(frame, (640, 640))

    results = model(frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    detections = tracker.update_with_detections(detections)

    for class_id, tracker_id, xyxy in zip(detections.class_id,detections.tracker_id,detections.xyxy):
        cv2.rectangle(frame,(int(xyxy[0]), int(xyxy[1])),(int(xyxy[2]), int(xyxy[3])),(0, 255, 255), 2)
        cv2.putText(frame,f"#{tracker_id} {model.names[class_id]}",(int(xyxy[0]), int(xyxy[1]) - 10),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0, 255, 255),2)

    return frame

def stream(zone_configfile):
    try:
        parser = ConfigParser()
        parser.read(zone_configfile)
        input_source = parser.get(arm_id, 'stream')

        tracker = sv.ByteTrack()

    except Exception as e:
        print(f"Config/Init Error: {e}")
        return

    uri = f"ws://{ip_address}:88/ws/test/upload"

    if is_image(input_source):
        print("Image detected. Processing single frame...")

        frame = cv2.imread(input_source)
        if frame is None:
            print("Failed to read image")
            return

        frame = process_frame(frame, tracker)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])

        try:
            ws = websocket.create_connection(uri)
            ws.send_binary(buffer.tobytes())
            ws.close()
            print("Image sent successfully")
        except Exception as e:
            print(f"Socket Error: {e}")

        return

    cap = cv2.VideoCapture(input_source)

    while True:
        try:
            ws = websocket.create_connection(uri)
            print("Connected to server. Tracking active...")

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame = process_frame(frame, tracker)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])

                try:
                    ws.send_binary(buffer.tobytes())
                except Exception as e:
                    print(f"Connection lost: {e}")
                    break

                time.sleep(0.01)

            ws.close()

        except Exception as e:
            print(f"Socket Error: {e}. Retrying in 2s...")
            time.sleep(2)

if __name__ == "__main__":
    stream("configfile.ini")
