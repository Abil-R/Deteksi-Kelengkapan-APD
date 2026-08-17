# Deteksi-Kelengkapan-APD
# Tugas Akhir Sistem Deteksi Kelengkapan APD

Sistem deteksi kelengkapan Alat Pelindung Diri (APD) berbasis **YOLOv8** yang diimplementasikan pada **NVIDIA Jetson Orin NX**. Sistem digunakan untuk mendeteksi penggunaan APD pada lingkungan laboratorium, meliputi **masker, sarung tangan, dan jas laboratorium**.

## Fitur

* Deteksi masker (`mask`)
* Deteksi sarung tangan (`glove`)
* Deteksi jas laboratorium (`labcoat`)
* Deteksi tidak menggunakan sarung tangan (`no_glove`)
* Deteksi tidak menggunakan jaslab (`no_labcoat`)
* Menampilkan hasil deteksi secara real-time
* Menampilkan status kelengkapan APD
* Pencatatan pelanggaran ke Firebase
* Implementasi pada perangkat NVIDIA Jetson Orin NX

## Teknologi

* Python
* YOLOv8
* Ultralytics
* OpenCV
* NVIDIA Jetson Orin NX
* Firebase Realtime Database

## Struktur Repository

```text
deteksi-apd/
├── main.py
├── requirements.txt
├── models/
│   └── best.pt
├── utils/
└── README.md
```
Buat dulu Databasenya di firebase kemudian dapatkan kode key nya

## Model

Model deteksi dikembangkan menggunakan **YOLOv8** dan dilatih untuk mengenali objek APD sesuai kelas yang digunakan pada sistem.

## Perangkat Keras

Sistem diimplementasikan menggunakan:

* Jetson Orin NX
* Webcam USB
* LCD 7 inci
* Speaker

## Catatan

File konfigurasi yang berisi kredensial atau informasi sensitif tidak disertakan dalam repository.

---

**Project Tugas Akhir — Sistem Deteksi Kelengkapan APD**

