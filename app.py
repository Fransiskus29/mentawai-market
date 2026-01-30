import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json
import altair as alt

# 1. KONFIGURASI HALAMAN (Wajib Paling Atas)
st.set_page_config(
    page_title="Mentawai Smart Market", 
    page_icon="🌴", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS HACK: TAMPILAN PREMIUM & HILANGKAN ELEMENT GANGGUAN ---
st.markdown("""
<style>
    /* Metric Style */
    [data-testid="stMetricValue"] {
        font-size: 20px;
        color: #00CC96;
    }
    /* Sembunyikan Header Streamlit & Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tombol Lapor biar mencolok */
    div.stButton > button:first-child {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Fungsi Waktu WIB
def format_wib(waktu_utc):
    if waktu_utc:
        wib = waktu_utc + datetime.timedelta(hours=7)
        return wib.strftime("%d %b %H:%M")
    return "-"

# 2. KONEKSI DATABASE
try:
    if not firebase_admin._apps:
        if os.path.exists("kunci.json"):
            cred = credentials.Certificate("kunci.json")
        else:
            if "textkey" in st.secrets:
                key_dict = json.loads(st.secrets["textkey"])
                cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"⚠️ Koneksi Database Terputus: {e}")
    st.stop()

# --- HEADER APLIKASI ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("## 🌴 Mentawai Market Intelligence")
    st.markdown("*Platform Monitoring Harga Komoditas Real-Time*")
with col_head2:
    if st.button("🔄 Refresh Data"):
        st.rerun()

st.divider()

# --- NAVIGASI TAB ---
tab_monitor, tab_lapor = st.tabs(["📊 MONITOR PASAR", "📝 LAPOR HARGA"])

# ================= TAB 1: DASHBOARD MONITOR =================
with tab_monitor:
    
    # 1. TARIK SEMUA DATA DULU (Biar Grafik Global Tetap Muncul)
    docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).limit(300).stream()
    
    all_data = []
    for doc in docs:
        d = doc.to_dict()
        lokasi_raw = d.get('lokasi', '-')
        all_data.append({
            "Komoditas": d.get('komoditas'),
            "Harga": d.get('range_harga'),
            "Harga_Angka": d.get('harga_angka', 0),
            "Lokasi": lokasi_raw,
            "Sumber": d.get('sumber'),
            "Waktu": format_wib(d.get('waktu_ambil')),
            "Raw_Time": d.get('waktu_ambil')
        })
    
    df_global = pd.DataFrame(all_data)

    # --- BAGIAN PENCARIAN ---
    c1, c2 = st.columns([1, 2])
    with c1:
        pilih_komoditas = st.selectbox("🔍 Filter Komoditas:", 
            ["Semua", "Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Lainnya"])
    with c2:
        cari_lokasi = st.text_input("📍 Filter Lokasi (Desa/Kecamatan):", placeholder="Cari Taileleu, Sikakap, Siberut...")

    # --- LOGIKA FILTER ---
    df_view = df_global.copy()
    
    if not df_global.empty:
        # Filter Komoditas
        if pilih_komoditas != "Semua":
            df_view = df_view[df_view['Komoditas'] == pilih_komoditas]
        
        # Filter Lokasi
        if cari_lokasi:
            df_view = df_view[df_view['Lokasi'].str.contains(cari_lokasi, case=False, na=False)]

        # --- VISUALISASI GLOBAL (TETAP MUNCUL WALAU FILTER ZONK) ---
        # Kita tampilkan tren harga umum biar dashboard gak sepi
        if pilih_komoditas != "Semua" and not df_global[df_global['Komoditas'] == pilih_komoditas].empty:
            st.markdown(f"#### 📈 Tren Harga {pilih_komoditas} (Global Mentawai)")
            
            # Data untuk grafik (ambil dari global, bukan hasil filter lokasi biar user tau harga umum)
            chart_df = df_global[df_global['Komoditas'] == pilih_komoditas].sort_values('Raw_Time')
            
            c = alt.Chart(chart_df).mark_area(
                line={'color':'#00CC96'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#00CC96', offset=0),
                           alt.GradientStop(color='rgba(255,255,255,0)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('Waktu', title=''),
                y=alt.Y('Harga_Angka', title='Harga (Rp)'),
                tooltip=['Komoditas', 'Harga', 'Lokasi']
            ).properties(height=250)
            
            st.altair_chart(c, use_container_width=True)

        # --- HASIL PENCARIAN (TABEL) ---
        st.subheader("📋 Hasil Pencarian Laporan")
        
        if not df_view.empty:
            # Kalau ada data
            st.dataframe(
                df_view[['Komoditas', 'Harga', 'Lokasi', 'Sumber', 'Waktu']],
                use_container_width=True,
                hide_index=True
            )
        else:
            # --- PENANGANAN DATA KOSONG (EMPTY STATE) ---
            st.warning(f"⚠️ Belum ada data **{pilih_komoditas}** di lokasi **'{cari_lokasi}'**.")
            st.info("💡 **Tips untuk Bos:** Data 'Taileleu' belum muncul karena belum ada yang input. Coba klik Tab 'LAPOR HARGA' di atas dan jadilah pelapor pertama!")

    else:
        st.info("Database masih kosong. Yuk isi data pertama!")

# ================= TAB 2: INPUT DATA (FORM) =================
with tab_lapor:
    st.markdown("### 📝 Tambah Data Baru")
    
    with st.form("form_lapor"):
        col_in1, col_in2 = st.columns(2)
        
        with col_in1:
            in_nama = st.selectbox("Komoditas", 
                ["Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Lainnya"])
            in_harga = st.number_input("Harga (Rp)", min_value=0, step=500)
            in_sumber = st.selectbox("Sumber Info", ["Petani", "Pengepul", "Toke Besar", "Masyarakat"])
            
        with col_in2:
            in_dusun = st.text_input("Nama Dusun/Desa", placeholder="Cth: Taileleu")
            in_kecamatan = st.selectbox("Kecamatan", 
                ["Sikakap", "Pagai Utara", "Pagai Selatan", "Sipora Utara", "Sipora Selatan", "Siberut Selatan", "Siberut Barat", "Siberut Utara", "Siberut Tengah", "Siberut Barat Daya"])
        
        submitted = st.form_submit_button("KIRIM LAPORAN 🚀", type="primary", use_container_width=True)
        
        if submitted:
            if in_harga > 0 and in_dusun:
                lokasi_full = f"{in_dusun}, {in_kecamatan}"
                
                db.collection("harga_realtime").add({
                    "komoditas": in_nama,
                    "harga_angka": in_harga,
                    "range_harga": f"Rp {in_harga:,}".replace(",", "."),
                    "waktu_ambil": datetime.datetime.now(),
                    "sumber": in_sumber,
                    "lokasi": lokasi_full,
                    "status": "Verified"
                })
                st.success("✅ Data berhasil disimpan! Silakan cek di Tab Monitor.")
            else:
                st.error("❌ Harga dan Nama Dusun wajib diisi!")
