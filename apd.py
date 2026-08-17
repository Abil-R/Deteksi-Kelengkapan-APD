import os
import ctypes
import queue
import time
import threading
from datetime import datetime
import cv2
import numpy as np
import torch
from ultralytics import YOLO
import firebase_admin
from firebase_admin import credentials, db

# ==============================================================================
# [FIX ERROR TLS JETSON]
# ==============================================================================
libgomp_path = "/home/.local/lib/python3.8/site-packages/pygame.libs/libgomp-d22c30c5.so.1.0.0"
try:
    ctypes.CDLL(libgomp_path, mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
pygame.mixer.init()

# =====================================================
# INIT FIREBASE (Jalan sekali saat modul diimport)
# =====================================================
cred_apd = credentials.Certificate("/home/jetson/serviceAccountKey.json")
if not firebase_admin._apps:
    app_apd = firebase_admin.initialize_app(cred_apd, {
        'databaseURL': 'key firebase'
    }, name='app_apd')
history_apd_ref = db.reference("history", app=app_apd)

offline_queue_apd = queue.Queue()

def firebase_worker():
    while True:
        if not offline_queue_apd.empty():
            data = offline_queue_apd.get()
            try:
                history_apd_ref.push(data)
            except Exception:
                offline_queue_apd.put(data)
                time.sleep(5) 
        time.sleep(0.5)

threading.Thread(target=firebase_worker, daemon=True).start()

# =====================================================
# INIT YOLOV8 MODEL (Jalan sekali saat modul diimport)
# =====================================================
print("Memuat Model YOLOv8 APD (Sabar, Jetson sedang memproses)...")
torch.backends.cudnn.benchmark = True
model = YOLO("runs/detect/train10/weights/best.pt") 
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
model.fuse()
if device == "cuda":
    model.half()

# =====================================================
# FUNGSI AUDIO PENDUKUNG
# =====================================================
def putar_audio_thread(file_audio):
    try:
        pygame.mixer.music.load(file_audio)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
    except Exception: 
        pass

def putar_audio(mask, labcoat, glove):
    if mask and labcoat and glove: file_audio = "apdlengkap.mp3"
    elif not mask and not labcoat and not glove: file_audio = "tidaklengkap.mp3"
    elif mask and not labcoat and not glove: file_audio = "glovejaslab.mp3"        
    elif not mask and labcoat and not glove: file_audio = "maskerglove.mp3"        
    elif not mask and not labcoat and glove: file_audio = "maskerjaslab.mp3"       
    elif mask and labcoat and not glove: file_audio = "noglove.mp3"            
    elif mask and not labcoat and glove: file_audio = "nojaslab.mp3"          
    elif not mask and labcoat and glove: file_audio = "nomasker.mp3"          
    else: return
    threading.Thread(target=putar_audio_thread, args=(file_audio,), daemon=True).start()

def tampilkan_tengah_layar(frame, screen_w, screen_h):
    canvas = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    h, w = frame.shape[:2]
    scale = min(screen_w / w, screen_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized_frame = cv2.resize(frame, (new_w, new_h))
    x_offset = (screen_w - new_w) // 2
    y_offset = (screen_h - new_h) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_frame
    return canvas

# =====================================================
# CLASS APDDETECTOR (UNTUK DIPANGGIL OLEH SISTEM GABUNGAN)
# =====================================================
class APDDetector:
    def __init__(self):
        self.kamera_path_1 = "/dev/v4l/by-path/platform-3610000.xhci-usb-0:2.3:1.0-video-index0"
        self.LCD_WIDTH = 900
        self.LCD_HEIGHT = 620
        self.cap_apd = None
        
        self.global_conf = 0.45  
        self.conf_thresh = {"labcoat": 0.80, "no_labcoat": 0.60, "mask": 0.70, "glove": 0.75, "no_glove": 0.60}
        self.daily_violation = 0
        self.current_day = datetime.now().date()

        self.detecting_apd = False
        self.start_time_apd = 0
        self.max_duration_apd = 8  
        self.last_seen_time_apd = 0
        self.idle_timeout_apd = 3
        self.show_result_until_apd = 0       
        self.show_result_duration_apd = 8.0  
        
        self.mask_ok = False
        self.labcoat_ok = False
        self.glove_ok = False

        self.apd_tracker = self.reset_tracker()
        self.prev_time = 0
        self.fps_list = []

    def reset_tracker(self):
        return {
            "mask": {"start": 0.0, "last": 0.0, "ok": False},
            "labcoat": {"start": 0.0, "last": 0.0, "ok": False},
            "no_labcoat": {"start": 0.0, "last": 0.0, "ok": False},
            "glove": {"start": 0.0, "last": 0.0, "ok": False},
            "no_glove": {"start": 0.0, "last": 0.0, "ok": False}
        }

    def start(self):
        while True:
            print("\n[HARDWARE] Mencoba membuka Kamera APD...")
            self.cap_apd = cv2.VideoCapture(self.kamera_path_1, cv2.CAP_V4L2)
            self.cap_apd.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.cap_apd.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap_apd.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap_apd.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if self.cap_apd.isOpened():
                print("[SUCCESS] Kamera APD Berhasil Terhubung!")
                break
            print("[ERROR] Kamera APD Gagal dibuka! Mengulangi dalam 3 detik...")
            time.sleep(3)

    def stop(self):
        if self.cap_apd is not None:
            self.cap_apd.release()

    def process_frame(self):
        # Pengganti "while True" - Dipanggil berkali-kali oleh sistem_gabungan
        current_time = time.time()
        
        if datetime.now().date() != self.current_day:
            self.daily_violation = 0
            self.current_day = datetime.now().date()

        if not self.cap_apd.grab():
            print("[CRITICAL] Kamera APD Terputus! Menghubungkan ulang...")
            self.cap_apd.release()
            self.detecting_apd = False
            self.start()
            return None
            
        ret, frame = self.cap_apd.retrieve()
        if not ret or frame is None: 
            return None

        # Inferensi YOLO
        if device == "cuda":
            results = model(frame, imgsz=640, device=device, conf=self.global_conf, verbose=False, half=True)
        else:
            results = model(frame, imgsz=640, device=device, conf=self.global_conf, verbose=False)
        
        annotated_frame = results[0].plot()
        detected_classes = []
        
        if results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names[cls_id].strip().lower()
                
                if class_name in ["jaslab", "jas_lab", "jas lab"]: class_name = "labcoat"
                if class_name in ["no_jaslab", "no jas_lab", "no jas lab", "no_jas_lab"]: class_name = "no_labcoat"
                
                if class_name in self.conf_thresh and conf >= self.conf_thresh[class_name]:
                    detected_classes.append(class_name)

        # Trigger Aturan Anti-Orang Lewat
        start_trigger = any(x in detected_classes for x in ["glove", "no_glove"])
        keep_alive_trigger = any(x in detected_classes for x in ["glove", "no_glove", "mask", "labcoat", "no_labcoat"])

        if keep_alive_trigger: 
            self.last_seen_time_apd = current_time

        if self.detecting_apd and (current_time - self.last_seen_time_apd > self.idle_timeout_apd):
            self.detecting_apd = False

        if start_trigger and not self.detecting_apd and (current_time > self.show_result_until_apd):
            self.detecting_apd = True
            self.start_time_apd = current_time
            self.mask_ok = self.labcoat_ok = self.glove_ok = False
            self.apd_tracker = self.reset_tracker()

        if self.detecting_apd:
            elapsed = current_time - self.start_time_apd
            for apd in ["mask", "labcoat", "no_labcoat", "glove", "no_glove"]:
                if self.apd_tracker[apd]["ok"]: continue 
                if apd in detected_classes:
                    if self.apd_tracker[apd]["start"] == 0.0: self.apd_tracker[apd]["start"] = current_time
                    self.apd_tracker[apd]["last"] = current_time
                    if (current_time - self.apd_tracker[apd]["start"]) >= 3.0: self.apd_tracker[apd]["ok"] = True
                else:
                    if self.apd_tracker[apd]["start"] != 0.0 and (current_time - self.apd_tracker[apd]["last"]) > 1.2:
                        self.apd_tracker[apd]["start"] = 0.0

            self.mask_ok = self.apd_tracker["mask"]["ok"]
            self.labcoat_ok = self.apd_tracker["labcoat"]["ok"] and not self.apd_tracker["no_labcoat"]["ok"]
            self.glove_ok = self.apd_tracker["glove"]["ok"] and not self.apd_tracker["no_glove"]["ok"]

            if (self.mask_ok and self.labcoat_ok and self.glove_ok) or (elapsed > self.max_duration_apd):
                self.detecting_apd = False
                self.show_result_until_apd = current_time + self.show_result_duration_apd
                
                if not (self.mask_ok and self.labcoat_ok and self.glove_ok): 
                    self.daily_violation += 1
                
                # Push ke Firebase & Audio
                pel_mask = not self.mask_ok
                pel_lab = not self.labcoat_ok
                pel_glove = not self.glove_ok
                total = int(pel_mask + pel_lab + pel_glove)
                if total > 0:
                    data = {
                        "masker": self.mask_ok, "jas_lab": self.labcoat_ok, "sarung_tangan": self.glove_ok,
                        "pelanggaran_masker": pel_mask, "pelanggaran_jas_lab": pel_lab, "pelanggaran_sarung_tangan": pel_glove,
                        "status": "PELANGGARAN", "total_pelanggaran": total,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    offline_queue_apd.put(data)
                
                putar_audio(self.mask_ok, self.labcoat_ok, self.glove_ok)

        # Hitung FPS
        fps = 1 / (current_time - self.prev_time) if self.prev_time != 0 else 0
        self.prev_time = current_time
        self.fps_list.append(fps)
        if len(self.fps_list) > 30: self.fps_list.pop(0)
        avg_fps = sum(self.fps_list) / len(self.fps_list)

        # Visualisasi
        hijau = (0, 255, 0)
        merah = (0, 0, 255)

        if self.detecting_apd:
            status_data = [
                ("MASKER: OK", hijau) if self.apd_tracker["mask"]["ok"] else ("MASKER: ...", hijau),
                ("JAS: OK", hijau) if self.apd_tracker["labcoat"]["ok"] else ("JAS: ...", hijau),
                ("SARUNG TANGAN: OK", hijau) if self.apd_tracker["glove"]["ok"] else ("SARUNG: ...", hijau)
            ]
        elif current_time < self.show_result_until_apd:
            status_data = [
                ("MASKER: OK", hijau) if self.mask_ok else ("MASKER: TIDAK", merah),
                ("JAS: OK", hijau) if self.labcoat_ok else ("JAS: TIDAK", merah),
                ("SARUNG TANGAN: OK", hijau) if self.glove_ok else ("SARUNG: TIDAK", merah)
            ]
        else:
            status_data = [("MASKER: -", hijau), ("JAS: -", hijau), ("SARUNG TANGAN: -", hijau)]

        def put_text_shadow(img, text, pos, color, font_scale=1.2, thickness=2):
            cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 3)
            cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

        put_text_shadow(annotated_frame, status_data[0][0], (20, 50), status_data[0][1], font_scale=1.2)
        put_text_shadow(annotated_frame, status_data[1][0], (20, 95), status_data[1][1], font_scale=1.2)
        put_text_shadow(annotated_frame, status_data[2][0], (20, 140), status_data[2][1], font_scale=1.2)
        put_text_shadow(annotated_frame, f"PELANGGARAN: {self.daily_violation}", (20, 195), (0, 255, 255), font_scale=1.0)
        
        put_text_shadow(annotated_frame, f"SISTEM: {'DETEKSI' if self.detecting_apd else 'IDLE'}", (380, 50), (255, 255, 255), font_scale=1, thickness=2)
        put_text_shadow(annotated_frame, f"FPS: {avg_fps:.1f}", (380, 90), (0, 255, 0), font_scale=1, thickness=2)

        # MENGEMBALIKAN GAMBAR KE SISTEM GABUNGAN (Tanpa imshow & waitKey)
        return tampilkan_tengah_layar(annotated_frame, self.LCD_WIDTH, self.LCD_HEIGHT)
