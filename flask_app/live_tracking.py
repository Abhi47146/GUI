import supervision as sv
from ultralytics import YOLO
from configparser import ConfigParser
from line_count import LineVehicleCounter
import cv2
import websocket
import socket
import time

model = YOLO("/mnt/c/Documents and Settings/MANJU/Downloads/yolo_model/yolo_model/combined_best.pt") 
arm_id = "J007_L01_01_X"

box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)) 
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

ip_address = get_local_ip()

def stream(zone_configfile):
    try:
        parser = ConfigParser()
        parser.read(zone_configfile)
        video_stream = parser.get(arm_id, 'stream')
        cap = cv2.VideoCapture(video_stream)
        line_coords = parser.get(f"{arm_id}_SPEED", 'line_segment_coordinates_1')
        coords = [int(float(c)) for c in line_coords.split(',')]
        x1, y1, x2, y2 = coords
        
        tracker = sv.ByteTrack() 
        counter = LineVehicleCounter(arm_id, line_coords)
        live_counter = 0
    except Exception as e:
        print(f"Config/Init Error: {e}")
        return

    uri = f"ws://{ip_address}:88/ws/live/upload"
    while True:
        try:
            ws = websocket.create_connection(uri)
            print("Connected to server. Tracking active...")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
            
                frame = cv2.resize(frame, (640, 640))

                results = model(frame, verbose=False)[0]
                detections = sv.Detections.from_ultralytics(results)
                
                detections = tracker.update_with_detections(detections)
              
                for class_id, tracker_id, xyxy in zip(detections.class_id, detections.tracker_id, detections.xyxy):
                    cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 255, 255), 2)
                    cv2.putText(frame, f"#{tracker_id} {model.names[class_id]}", (int(xyxy[0]), int(xyxy[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                    bottom_x = int((xyxy[0] + xyxy[2]) / 2)
                    bottom_y = int(xyxy[3])
                    crossed = counter.update(tracker_id, (bottom_x, bottom_y), y1)
                    cv2.line(frame, (x1, y1), (x2, y2), color=(0, 0, 0), thickness=2)
                    cv2.putText(frame, f"Total Vehicles: {live_counter}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    if crossed == 1:
                        cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 0, 255), 2)
                        cv2.putText(frame, f"#{tracker_id} {model.names[class_id]}", (int(xyxy[0]), int(xyxy[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        live_counter+=1

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
