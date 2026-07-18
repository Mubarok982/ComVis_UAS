import streamlit as st
import cv2
import pandas as pd
import plotly.express as px
import yt_dlp
from ultralytics import YOLO
import mysql.connector
from datetime import datetime
import warnings
import os
import math
import numpy as np
import time
import requests
import threading

warnings.filterwarnings("ignore")

# ==========================================
# KONFIGURASI HALAMAN (HARUS PALING ATAS)
# ==========================================
st.set_page_config(page_title="Smart Factory Safety", layout="wide", page_icon="🛡️")

# INJEKSI CSS UNTUK MEMANGKAS PADDING ATAS & BAWAH BIAR FIT 1 LAYAR
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            margin-top: 0rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNGSI TELEGRAM BOT
# ==========================================
def send_telegram_photo(token, chat_id, frame, caption):
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        _, buffer = cv2.imencode('.jpg', frame)
        files = {'photo': ('alert.jpg', buffer.tobytes(), 'image/jpeg')}
        data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
        try: requests.post(url, data=data, files=files, timeout=10)
        except Exception: pass

def trigger_photo_alert_background(token, chat_id, frame, caption):
    thread = threading.Thread(target=send_telegram_photo, args=(token, chat_id, frame.copy(), caption))
    thread.start()

# ==========================================
# FUNGSI DATABASE MYSQL
# ==========================================
def get_db_connection():
    try: return mysql.connector.connect(host="127.0.0.1", user="root", password="root", port=3306)
    except: return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS uas_k3")
            cursor.execute("USE uas_k3")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_safety (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    waktu DATETIME, total_pekerja INT, pekerja_aman INT,
                    pelanggaran_apd INT, kecelakaan INT
                )
            """)
            for col in ["pelanggaran_ganda", "intrusi_zona"]:
                try: cursor.execute(f"ALTER TABLE log_safety ADD COLUMN {col} INT DEFAULT 0")
                except: pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detail_pelanggaran (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    waktu DATETIME, jenis_pelanggaran VARCHAR(50), jumlah INT
                )
            """)
            conn.commit()
        finally: conn.close()

def save_to_db(total, aman, pelanggaran, laka, ganda, intrusi, dict_pelanggaran):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("USE uas_k3")
            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO log_safety (waktu, total_pekerja, pekerja_aman, pelanggaran_apd, kecelakaan, pelanggaran_ganda, intrusi_zona) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                           (waktu_sekarang, total, aman, pelanggaran, laka, ganda, intrusi))
            for jenis, jumlah in dict_pelanggaran.items():
                cursor.execute("INSERT INTO detail_pelanggaran (waktu, jenis_pelanggaran, jumlah) VALUES (%s, %s, %s)", 
                               (waktu_sekarang, jenis, jumlah))
            conn.commit()
        finally: conn.close()

def get_statistik_harian():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("USE uas_k3")
            cursor.execute("SELECT SUM(total_pekerja) as total_pekerja, SUM(pekerja_aman) as total_aman, SUM(pelanggaran_apd) as total_pelanggaran, SUM(kecelakaan) as total_kecelakaan, SUM(pelanggaran_ganda) as total_ganda, SUM(intrusi_zona) as total_intrusi FROM log_safety")
            result = cursor.fetchone()
            if result and result['total_pekerja'] is not None:
                total_ganda = int(result['total_ganda']) if result['total_ganda'] is not None else 0
                total_intrusi = int(result['total_intrusi']) if result['total_intrusi'] is not None else 0
                return int(result['total_pekerja']), int(result['total_aman']), int(result['total_pelanggaran']), int(result['total_kecelakaan']), total_ganda, total_intrusi
        finally: conn.close()
    return 0, 0, 0, 0, 0, 0

def get_statistik_pelanggaran():
    df = pd.DataFrame(columns=["jenis_pelanggaran", "total"])
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("USE uas_k3")
            cursor.execute("SELECT jenis_pelanggaran, SUM(jumlah) as total FROM detail_pelanggaran GROUP BY jenis_pelanggaran")
            rows = cursor.fetchall()
            if rows: df = pd.DataFrame(rows)
        finally: conn.close()
    return df

# ==========================================
# FUNGSI BANTUAN
# ==========================================
@st.cache_data
def get_youtube_stream_url(youtube_url):
    ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(youtube_url, download=False)['url']

def is_inside(box_dalam, box_luar):
    x1_d, y1_d, x2_d, y2_d = box_dalam
    x1_l, y1_l, x2_l, y2_l = box_luar
    cx, cy = (x1_d + x2_d) / 2, (y1_d + y2_d) / 2
    return (x1_l <= cx <= x2_l) and (y1_l <= cy <= y2_l)

def hitung_jarak(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# ==========================================
# LAYOUT UTAMA (HEADER & PLACEHOLDERS)
# ==========================================
# Header dipadatkan agar tidak makan tempat
st.markdown("<h2 style='text-align: center; margin-bottom: 0px;'>🛡️ Smart Factory Safety Monitor</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray; font-size:14px; margin-top: 5px; margin-bottom: 10px;'>Dashboard K3 Real-Time (YOLOv8 & MySQL)</p>", unsafe_allow_html=True)

# 1. METRIK BARIS ATAS
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
metric_pekerja = col_m1.empty()
metric_aman = col_m2.empty()
metric_pelanggaran = col_m3.empty()
metric_laka = col_m4.empty()
metric_score = col_m5.empty()

# 2. GRAFIK (DI TENGAH, BAWAH METRIK, ATAS VIDEO)
col_c1, col_c2, col_c3 = st.columns(3)
with col_c1: chart_apd_placeholder = st.empty()
with col_c2: chart_laka_placeholder = st.empty()
with col_c3: bar_chart_placeholder = st.empty()

# 3. VIDEO (DI BAWAH GRAFIK)
# Diapit kolom kosong (rasio 1:4:1) supaya ukurannya nggak raksasa melebar ke seluruh layar
v_col1, v_col_center, v_col3 = st.columns([1, 4, 1])
with v_col_center:
    video_placeholder = st.empty()

# ==========================================
# SIDEBAR: Kontrol Panel
# ==========================================
TELE_TOKEN = "8777237327:AAEfDcpcRu6wjW_6gH9AGZBXDiqtNGc9Ips"
TELE_CHAT_ID = "7879584619"

st.sidebar.header("🛠️ Kontrol Panel")
sumber_video = st.sidebar.text_input("🔗 Link/Path Video", "https://www.youtube.com/watch?v=YOUR_VIDEO_ID")
st.sidebar.success("✅ Telegram Terkonfigurasi")
start_button = st.sidebar.button("▶️ Mulai Deteksi", use_container_width=True)
stop_button = st.sidebar.button("⏹️ Hentikan", use_container_width=True)

# ==========================================
# ENGINE DETEKSI
# ==========================================
if start_button and sumber_video:
    init_db() 
        
    try:
        if "youtube.com" in sumber_video or "youtu.be" in sumber_video:
            stream_url = get_youtube_stream_url(sumber_video)
        else:
            if not os.path.exists(sumber_video):
                st.sidebar.error("File video tidak ditemukan!")
                stream_url = None
            else:
                stream_url = sumber_video
        
        if stream_url:
            cap = cv2.VideoCapture(stream_url)
            model_ppe = YOLO('train/weights/best_int8_openvino_model') 
            
            frame_count = 0 
            history_posisi = {}
            last_alert_time = 0
            COOLDOWN_TIME = 15 
            
            KELAS_MESIN = ['machine', 'mesin', 'forklift', 'excavator', 'truck', 'alat_berat', 'vehicle']
            
            while cap.isOpened() and not stop_button:
                ret, frame = cap.read()
                if not ret: break
                frame_count += 1
                
                results = model_ppe(frame, conf=0.25, verbose=False)
                annotated_frame = results[0].plot() 
                
                boxes_person = []
                boxes_pelanggaran = []
                mesin_boxes = []
                dict_pelanggaran = {} 
                current_kecelakaan = 0
                current_intrusi = 0 
                current_posisi = {}
                waktu_sekarang = time.time() 
                
                # DETEKSI ALAT BERBAHAYA
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    class_name = model_ppe.names[cls_id].lower()
                    xyxy = box.xyxy[0].cpu().numpy()
                    
                    if any(nama_alat in class_name for nama_alat in KELAS_MESIN):
                        mesin_boxes.append(xyxy)
                        x1_m, y1_m, x2_m, y2_m = map(int, xyxy)
                        cv2.rectangle(annotated_frame, (x1_m-40, y1_m-40), (x2_m+40, y2_m+40), (0, 0, 255), 2)
                        cv2.putText(annotated_frame, f"⚠️ ZONA {class_name.upper()}", (x1_m, max(20, y1_m-50)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # DETEKSI PEKERJA & INSIDEN
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    class_name = model_ppe.names[cls_id].lower()
                    xyxy = box.xyxy[0].cpu().numpy()
                    
                    if class_name in ['fall', 'fallen', 'man-down']:
                        current_kecelakaan += 1
                        
                    if class_name in ['person', 'worker', 'pekerja', 'man', 'human']:
                        boxes_person.append(xyxy)
                        x1, y1, x2, y2 = xyxy
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        tinggi, lebar = y2 - y1, x2 - x1
                        
                        # INTRUSI
                        for m_box in mesin_boxes:
                            mx1, my1, mx2, my2 = m_box
                            if (mx1 - 40) <= cx <= (mx2 + 40) and (my1 - 40) <= cy <= (my2 + 40):
                                current_intrusi += 1
                                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 165, 255), 4)
                                cv2.putText(annotated_frame, "AWAS MESIN!", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 3)
                                break 
                        
                        # JATUH
                        is_jatuh = False
                        if (lebar / (tinggi + 0.0001)) > 1.0: is_jatuh = True
                        id_terdekat, jarak_terdekat = None, float('inf')
                        for hist_id, hist_data in history_posisi.items():
                            jarak = hitung_jarak((cx, cy), (hist_data['cx'], hist_data['cy']))
                            if jarak < 50 and jarak < jarak_terdekat:
                                jarak_terdekat, id_terdekat = jarak, hist_id
                        
                        if id_terdekat is not None:
                            if (cy - history_posisi[id_terdekat]['cy']) > (history_posisi[id_terdekat]['tinggi'] * 0.3):
                                is_jatuh = True

                        current_posisi[int(cx)] = {'cx': cx, 'cy': cy, 'tinggi': tinggi}
                        if is_jatuh:
                            current_kecelakaan += 1
                            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 4)
                            cv2.putText(annotated_frame, "JATUH!", (int(x1), max(20, int(y1) - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
                    
                    elif 'no' in class_name or 'without' in class_name or 'bare' in class_name:
                        boxes_pelanggaran.append((class_name, xyxy))
                        dict_pelanggaran[class_name] = dict_pelanggaran.get(class_name, 0) + 1

                history_posisi = current_posisi.copy()

                current_pekerja = len(boxes_person)
                current_ganda = 0
                current_pelanggar_unik = 0 
                
                for p_box in boxes_person:
                    pelanggaran_orang_ini = sum(1 for _, pel_box in boxes_pelanggaran if is_inside(pel_box, p_box))
                    if pelanggaran_orang_ini > 0: current_pelanggar_unik += 1
                    if pelanggaran_orang_ini >= 2: current_ganda += 1

                current_aman = max(0, current_pekerja - current_pelanggar_unik)

                # TRIGGER TELEGRAM
                if (current_kecelakaan > 0 or current_intrusi > 0) and (waktu_sekarang - last_alert_time) > COOLDOWN_TIME:
                    if TELE_TOKEN and TELE_CHAT_ID:
                        str_waktu = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        str_insiden = []
                        if current_kecelakaan > 0: str_insiden.append(f"{current_kecelakaan} Orang Jatuh")
                        if current_intrusi > 0: str_insiden.append(f"{current_intrusi} Terlalu Dekat Alat Berbahaya")
                        str_pelanggaran = ", ".join([f"{v} {k.replace('no-', 'Tanpa ')}" for k, v in dict_pelanggaran.items()]) or "Aman (Sesuai APD)"

                        caption_tele = (
                            f"🚨 *LAPORAN INSIDEN K3*\n\n"
                            f"⏱️ *Waktu:* {str_waktu}\n"
                            f"💥 *Insiden Aktif:* {', '.join(str_insiden)}\n"
                            f"⚠️ *Status Pelanggaran Area:* {str_pelanggaran}"
                        )
                        trigger_photo_alert_background(TELE_TOKEN, TELE_CHAT_ID, annotated_frame, caption_tele)
                        last_alert_time = waktu_sekarang

                # RENDER VIDEO
                frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

                # UPDATE DATABASE & METRIK GRAFIK
                if frame_count % 30 == 0:
                    save_to_db(current_pekerja, current_aman, len(boxes_pelanggaran), current_kecelakaan, current_ganda, current_intrusi, dict_pelanggaran)

                if frame_count % 15 == 0 or frame_count == 1:
                    db_t, db_a, db_p, db_l, db_g, db_i = get_statistik_harian()
                    
                    metric_pekerja.metric("Total Pekerja", db_t)
                    metric_aman.metric("Pekerja Aman", db_a)
                    metric_pelanggaran.metric("Total Pelanggaran Item", db_p, delta="-", delta_color="inverse")
                    
                    total_bahaya = db_l + db_i
                    metric_laka.metric("Insiden Kritis", total_bahaya, delta="BAHAYA" if total_bahaya>0 else "Aman", delta_color="inverse" if total_bahaya>0 else "normal")
                    
                    score = (db_a / db_t * 100) if db_t > 0 else 100
                    metric_score.metric("Safety Score", f"{score:.1f}%")
                    
                    # GRAFIK 1 (Tinggi dipangkas jadi 200)
                    df_apd = pd.DataFrame({"Status": ["Aman", "Melanggar"], "Jumlah": [db_a, max(0, db_t - db_a)]})
                    fig_apd = px.pie(df_apd, values='Jumlah', names='Status', hole=0.5, color='Status', color_discrete_map={"Aman":"#00CC96", "Melanggar":"#EF553B"})
                    fig_apd.update_layout(title_text="Kepatuhan Pekerja", title_x=0.5, margin=dict(t=30, b=0, l=0, r=0), height=200)
                    chart_apd_placeholder.plotly_chart(fig_apd, use_container_width=True)
                    
                    # GRAFIK 2 (Tinggi dipangkas jadi 200)
                    db_selamat = max(0, db_t - db_l - db_i)
                    df_laka = pd.DataFrame({"Status": ["Normal", "Jatuh", "Intrusi"], "Jumlah": [db_selamat, db_l, db_i]}) if db_t > 0 else pd.DataFrame({"Status": ["Belum ada data"], "Jumlah": [1]})
                    fig_laka = px.pie(df_laka, values='Jumlah', names='Status', hole=0.5, color='Status', color_discrete_map={"Normal":"#636EFA", "Jatuh":"#EF553B", "Intrusi":"#FFA15A", "Belum ada data":"#333333"})
                    fig_laka.update_layout(title_text="Distribusi Insiden", title_x=0.5, margin=dict(t=30, b=0, l=0, r=0), height=200)
                    chart_laka_placeholder.plotly_chart(fig_laka, use_container_width=True)

                    # GRAFIK 3 (Tinggi dipangkas jadi 200)
                    df_bar = get_statistik_pelanggaran()
                    data_tambahan = pd.DataFrame({'jenis_pelanggaran': ['APD Lengkap', 'Pelanggaran Ganda'], 'total': [db_a, db_g]})
                    df_bar = pd.concat([df_bar, data_tambahan], ignore_index=True) if not df_bar.empty else data_tambahan
                    fig_bar = px.bar(df_bar, x='jenis_pelanggaran', y='total', color='jenis_pelanggaran', text='total', title="Statistik Pelanggaran", labels={'jenis_pelanggaran': '', 'total': ''})
                    fig_bar.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), height=200)
                    bar_chart_placeholder.plotly_chart(fig_bar, use_container_width=True)
                
            cap.release()
            
    except Exception as e:
        st.sidebar.error(f"Sistem terhenti: {e}")