import cv2
import numpy as np
from ultralytics import YOLO
import yt_dlp

model_ppe = YOLO("hasil_training_uas (1)/content/runs/detect/train/weights/best_openvino_model")
model_pose = YOLO("runs/detect/yolo26n-pose_int8_openvino_model")

youtube_url = "https://www.youtube.com/shorts/LnXTqsPb500" 

print("Sedang mendownload video YouTube sementara, harap tunggu...")
ydl_opts = {
    'format': 'best[ext=mp4][height<=720]',
    'outtmpl': 'temp_video.mp4', 
    'overwrite': True, # Otomatis nimpa video lama kalau lu ganti link
    'quiet': True
} 

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([youtube_url])

cap = cv2.VideoCapture('temp_video.mp4')

if not cap.isOpened():
    print("❌ ERROR: OpenCV gagal membuka file video temp_video.mp4!")
    exit()

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
if frame_width == 0: frame_width = 1280
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
if frame_height == 0: frame_height = 720

danger_zone = np.array([
    [int(frame_width * 0.3), int(frame_height * 0.3)],
    [int(frame_width * 0.7), int(frame_height * 0.3)],
    [int(frame_width * 0.7), int(frame_height * 0.8)],
    [int(frame_width * 0.3), int(frame_height * 0.8)]
], np.int32)

class_colors = {
    0: (255, 100, 100), 
    1: (0, 255, 0),     
    2: (255, 0, 0),     
    3: (0, 255, 255),   
    4: (255, 0, 255),   
    5: (0, 165, 255),   
    10: (0, 255, 0),    
    12: (0, 255, 255)   
}

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    overlay = frame.copy()
    cv2.fillPoly(overlay, [danger_zone], (0, 0, 255))
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    cv2.polylines(frame, [danger_zone], isClosed=True, color=(0, 0, 255), thickness=2)

    results_ppe = model_ppe(frame, conf=0.25, verbose=False, device="intel:cpu")
    results_pose = model_pose(frame, conf=0.50, verbose=False, device="intel:cpu")

    persons = []
    helmets = []
    vests = []
    
    if results_ppe[0].boxes is not None:
        boxes = results_ppe[0].boxes.xyxy.int().cpu().tolist()
        class_ids = results_ppe[0].boxes.cls.int().cpu().tolist()
        
        for box, cls_id in zip(boxes, class_ids):
            label_name = results_ppe[0].names[cls_id].lower()
            
            if "person" in label_name:
                persons.append(box)
            elif "helmet" in label_name and "no" not in label_name:
                helmets.append(box)
            elif "vest" in label_name and "no" not in label_name:
                vests.append(box)
            
            color = class_colors.get(cls_id, (200, 200, 200))
            
            x1, y1, x2, y2 = box
            label = results_ppe[0].names[cls_id]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for p_box in persons:
            px1, py1, px2, py2 = p_box
            p_center_x = int((px1 + px2) / 2)
            p_center_y = int((py1 + py2) / 2)
            
            in_danger_zone = cv2.pointPolygonTest(danger_zone, (p_center_x, p_center_y), False) >= 0
            if in_danger_zone:
                cv2.putText(frame, "!!! INTRUSION DETECTED !!!", (px1, py1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)

            has_helmet = False
            for h_box in helmets:
                hx1, hy1, hx2, hy2 = h_box
                if hx1 >= px1 - 20 and hx2 <= px2 + 20 and hy1 >= py1 - 20 and hy2 <= py2:
                    has_helmet = True
                    break
            
            if not has_helmet:
                cv2.putText(frame, "NO HELMET", (px1, py2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    if results_pose[0].keypoints is not None:
        keypoints = results_pose[0].keypoints.xy.cpu().numpy()
        
        for kpts in keypoints:
            if len(kpts) >= 17:
                shoulder_y = (kpts[5][1] + kpts[6][1]) / 2
                ankle_y = (kpts[15][1] + kpts[16][1]) / 2
                
                if shoulder_y > 0 and ankle_y > 0:
                    if shoulder_y >= ankle_y - 30: 
                        head_x, head_y = int(kpts[0][0]), int(kpts[0][1])
                        cv2.putText(frame, "!!! MAN-DOWN / FALL !!!", (head_x - 50, head_y - 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)

    cv2.imshow("Workplace Safety Engine - Phase 2", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()