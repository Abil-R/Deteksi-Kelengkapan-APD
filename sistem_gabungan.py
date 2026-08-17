# ==============================================================================
# 1. BLOK AUDIO & MEMORI (HARUS DI PALING ATAS)
# ==============================================================================
import os
import ctypes

# Fix TLS Memory dari teman Anda
libgomp_path = "/home/jetsonpakyoan/.local/lib/python3.8/site-packages/pygame.libs/libgomp-d22c30c5.so.1.0.0"
try:
    ctypes.CDLL(libgomp_path, mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

# Trik Rahasia: Paksa Pygame menjadi 'dummy' untuk urusan video/input 
# sehingga dia TIDAK AKAN BISA membajak keyboard dari OpenCV atau Pynput.
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame
pygame.mixer.init()

# ==============================================================================
# 2. BLOK VISUAL & SISTEM UTAMA
# ==============================================================================
import cv2
from pynput import keyboard
from apd import APDDetector
from dimensiobat import DimensionDetector

# Variabel global untuk mengontrol mode dari latar belakang
requested_mode = "APD"
is_running = True

def on_press(key):
    global requested_mode, is_running
    
    try:
        # Cek jika tombol berupa karakter string (- atau +)
        if hasattr(key, 'char') and key.char is not None:
            if key.char == '4':
                requested_mode = "APD"
            elif key.char == '6':
                requested_mode = "DIMENSI"
                
        # Cek jika tombol adalah Enter
        elif key == keyboard.Key.enter:
            is_running = False
            
    except Exception as e:
        pass

def main():
    global requested_mode, is_running
    
    print("=== INISIALISASI SISTEM GABUNGAN ===")
    
    apd_system = APDDetector()
    dimensi_system = DimensionDetector()
    
    current_mode = "APD"
    
    print("\n[INFO] Memulai Mode Default: APD")
    apd_system.start()
    
    print("\n=== KONTROL SISTEM ===")
    print("[4] (Minus)  -> Mode APD")
    print("[6] (Tambah) -> Mode Dimensi Obat")
    print("[Enter]      -> Keluar Program\n")

    cv2.namedWindow("SISTEM MONITORING TA", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("SISTEM MONITORING TA", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Mulai pynput listener di latar belakang
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    while is_running:
        # OpenCV tetap butuh ini agar frame video berjalan, 
        # tapi dia tidak bertugas membaca input numpad lagi.
        cv2.waitKey(1) 
        
        # Pindah mode jika ada perintah dari tombol
        if requested_mode != current_mode:
            if requested_mode == "APD":
                print("\n[SWITCH] Mematikan Dimensi, Menyalakan APD...")
                dimensi_system.stop()
                apd_system.start()
                current_mode = "APD"
            elif requested_mode == "DIMENSI":
                print("\n[SWITCH] Mematikan APD, Menyalakan Dimensi...")
                apd_system.stop()
                dimensi_system.start()
                current_mode = "DIMENSI"
                
        # Proses tampilan berdasarkan mode
        if current_mode == "APD":
            frame_final = apd_system.process_frame()
            if frame_final is not None:
                cv2.imshow("SISTEM MONITORING TA", frame_final)
                
        elif current_mode == "DIMENSI":
            frame_final = dimensi_system.process_frame()
            if frame_final is not None:
                cv2.imshow("SISTEM MONITORING TA", frame_final)

    # Cleanup saat keluar
    print("\n[INFO] Keluar dari program. Membersihkan memori...")
    listener.stop()
    apd_system.stop()
    dimensi_system.stop()
    cv2.destroyAllWindows()
    print("[SUCCESS] Port USB Bersih. Sistem berhasil ditutup.")

if __name__ == "__main__":
    main()
