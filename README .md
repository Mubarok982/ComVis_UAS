# 👷‍♂️ Workplace Safety (K3) Engine - Computer Vision

Proyek ini merupakan sistem deteksi otomatis untuk Keselamatan dan Kesehatan Kerja (K3) berbasis Computer Vision. Dibangun menggunakan **YOLO** dan dioptimasi dengan **OpenVINO** untuk inferensi *real-time* secara mulus di CPU.

## ✨ Fitur Utama
1. **Deteksi APD (Alat Pelindung Diri):** Mendeteksi kepatuhan penggunaan Helm (Helmet) dan Rompi (Vest) pada pekerja.
2. **Intrusion Detection (Zona Bahaya):** Memberikan peringatan otomatis (warna merah) jika pekerja memasuki area terlarang (area mesin/forklift).
3. **Man-Down / Fall Detection:** Mendeteksi indikasi kecelakaan (pekerja terjatuh) menggunakan analisis *keypoints* dari YOLO Pose.

## 🚀 Teknologi yang Digunakan
- **Python 3**
- **OpenCV** (Manipulasi frame & visualisasi)
- **Ultralytics YOLO** (Model deteksi objek & pose)
- **Intel OpenVINO** (Akselerasi AI pada CPU)
- **yt-dlp** (Penarikan data video secara dinamis)

## 📂 Struktur Repository & Catatan
> **⚠️ Note:** File *weights* model AI (`.pt`, `.bin`, `.xml`), dataset gambar (ribuan file), dan video *testing* **TIDAK** disertakan dalam repository ini untuk mengikuti standar *best practice* Git (menghindari penumpukan *blob* raksasa). 

Jika ingin menjalankan kode ini secara lokal, pastikan Anda telah meletakkan file model OpenVINO di dalam folder proyek.

## 🛠️ Cara Penggunaan
1. Clone repository ini:
   ```bash
   git clone https://github.com/Mubarok982/ComVis_UAS.git
   cd ComVis_UAS
   ```
2. Install *dependencies* yang dibutuhkan:
   ```bash
   pip install opencv-python numpy ultralytics yt-dlp
   ```
3. Jalankan *engine* utama:
   ```bash
   python3 safety_engine.py
   ```

---
*Proyek ini dikembangkan untuk keperluan Ujian Akhir Semester (UAS) Mata Kuliah Computer Vision.*
