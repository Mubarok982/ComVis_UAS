import streamlit as st
import cv2
import pandas as pd
import plotly.express as px
import yt_dlp
from ultralytics import YOLO  # Tambahan library YOLO

# ==========================================
# FUNGSI EKSTRAK STREAM YOUTUBE
# ==========================================
@st.cache_data
def get_youtube_stream_url(youtube_url):
    """Mengambil direct stream URL dari video YouTube menggunakan yt-dlp"""
    ydl_opts = {
        'format': 'best[ext=mp4]', 
        'quiet': True,
        'no_warnings': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Smart Factory Safety Monitor", layout="wide", page_icon="🛡️")

st.title("🛡️ Smart Factory Safety Monitor")
st.markdown("Dashboard deteksi *real-time* Keselamatan dan Kesehatan Kerja (K3) menggunakan YOLOv8.")
st.markdown("---")

# ==========================================
# LAYOUTING: Metric Cards
# ==========================================
col1, col2, col3 = st.columns(3)
metric_pekerja = col1.empty()
metric_pelanggaran = col2.empty()
metric_zona = col3.empty()

st.markdown("---")

video_col, chart_col = st.columns([2, 1])
video_placeholder = video_col.empty()
chart_placeholder = chart_col.empty()

# ==========================================
# SIDEBAR: Kontrol Panel
# ==========================================
st.sidebar.header("🛠️ Kontrol Panel")
youtube_url = st.sidebar.text_input("🔗 Link Video YouTube", "https://www.youtube.com/watch?v=YOUR_VIDEO_ID")
start_button = st.sidebar.button("▶️ Mulai Deteksi")
stop_button = st.sidebar.button("⏹️ Hentikan")

# ==========================================
# ENGINE DETEKSI
# ==========================================
if start_button and youtube_url:
    try:
        st.sidebar.info("Mengekstrak stream YouTube... Harap tunggu.")
        stream_url = get_youtube_stream_url(youtube_url)
        
        cap = cv2.VideoCapture(stream_url)
        st.sidebar.success("Stream berhasil dibuka!")
        
        # INISIALISASI MODEL YOLO
        # Sesuaikan path ini dengan lokasi file best.pt hasil training lu
        model_ppe = YOLO('train/weights/best_int8_openvino_model') 
        
        while cap.isOpened() and not stop_button:
            ret, frame = cap.read()
            if not ret:
                st.warning("Video selesai atau buffering terputus.")
                break
            
            # 1. PROSES INFERENSI YOLO
            results = model_ppe(frame, conf=0.25, verbose=False)
            
            # YOLO otomatis menggambar Bounding Box ke atas frame!
            annotated_frame = results[0].plot() 
            
            # 2. LOGIKA PERHITUNGAN METRIK
            total_pekerja = 0
            total_pelanggaran = 0
            
            # Membaca setiap kotak yang terdeteksi di frame ini
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = model_ppe.names[cls_id].lower()
                
                # Hitung jumlah pekerja (sesuaikan dengan nama class lu, misal 'person' atau 'worker')
                if class_name in ['person', 'worker']:
                    total_pekerja += 1
                    
                # Kalau nama class ada unsur 'no-' (misal: no-helmet, no-gloves), catat sebagai pelanggaran
                if 'no-' in class_name:
                    total_pelanggaran += 1

            # Kalkulasi logika visual
            pekerja_aman = max(0, total_pekerja - total_pelanggaran)
            status_zona = "Aman" # (Bisa dikembangkan nanti pakai logika koordinat polygon)
            
            # 3. UPDATE LAYAR VIDEO (Gunakan frame yang sudah ada Bounding Box-nya)
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
            
            # 4. UPDATE METRIC CARDS
            metric_pekerja.metric("Total Pekerja Aktif", total_pekerja)
            metric_pelanggaran.metric("Total Pelanggaran APD", total_pelanggaran, delta="-", delta_color="inverse")
            
            if status_zona == "Aman":
                metric_zona.metric("Status Zona Bahaya", "✅ AMAN")
            else:
                metric_zona.metric("Status Zona Bahaya", "🚨 INTRUSI!")
                
            # 5. UPDATE PIE CHART
            df_chart = pd.DataFrame({
                "Status": ["Aman (Sesuai APD)", "Melanggar APD"],
                "Jumlah": [pekerja_aman, total_pelanggaran]
            })
            
            # Jika belum ada data sama sekali, beri dummy agar chart tidak error
            if pekerja_aman == 0 and total_pelanggaran == 0:
                df_chart = pd.DataFrame({"Status": ["Mendeteksi..."], "Jumlah": [1]})
                
            fig = px.pie(
                df_chart, 
                values='Jumlah', 
                names='Status', 
                hole=0.4, 
                color='Status', 
                color_discrete_map={"Aman (Sesuai APD)":"#00CC96", "Melanggar APD":"#EF553B", "Mendeteksi...":"#333333"}
            )
            fig.update_layout(title_text="Rasio Kepatuhan Pekerja", title_x=0.2)
            
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            
        cap.release()
        
    except Exception as e:
        st.sidebar.error(f"Gagal memuat sistem: {e}")