import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import datetime
import json
import os
import altair as alt

# 1. KONFIGURASI HALAMAN (Tampilan Full Screen & Ikon App)
st.set_page_config(
    page_title="Info Harga Mentawai", 
    page_icon="🌴", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS PRO: BIAR TAMPILAN KAYAK APLIKASI BENERAN ---
st.markdown("""
<style>
    /* Hilangkan Menu Streamlit Bawaan */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Style Kartu Metrik */
    div[data-testid="metric-container"] {
        background-color: #262730;
        border: 1px solid #444;
        padding: 10px;
        border-radius: 8px;
    }
    /* Tombol Lapor */
    div.stButton > button:first-child {
        background-color: #00CC96;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Fungsi Waktu WIB (Penting buat Real Time)
def format_wib(waktu_utc):
    if waktu_utc:
        wib = waktu_utc + datetime.timedelta(hours=7)
        return wib.strftime("%d %b %Y - %H:%M WIB")
    return "-"

# 2. KONEKSI DATABASE (Hybrid: Laptop & Cloud)
@st.cache_resource
def get_db():
    try:
        if not firebase_admin._apps:
            if os.path.exists("kunci.json"):
                cred = credentials.Certificate("kunci.json") # Laptop
            elif "textkey" in st.secrets:
                key_dict = json.loads(st.secrets["textkey"]) # Cloud
                cred = credentials.Certificate(key_dict)
            else:
                return None
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        return None

db = get_db()

if not db:
    st.error("⚠️ Koneksi Database Gagal. Cek Secrets/Kunci.")
    st.stop()

# --- HEADER APLIKASI ---
st.title("🌴 Pusat Informasi Harga Mentawai")
st.markdown("**Platform Transparansi Harga Hasil Bumi Antar-Desa**")
st.divider()

# --- NAVIGASI UTAMA ---
tab_monitor, tab_lapor = st.tabs(["📊 MONITOR PASAR (PUBLIK)", "📝 LAPOR HARGA (PETANI/TOKE)"])

# ================= TAB 1: DASHBOARD PUBLIK =================
with tab_monitor:
    # A. TARIK DATA DARI DATABASE
    docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).limit(500).stream()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        lokasi_raw = d.get('lokasi', '-')
        data_list.append({
            "Komoditas": d.get('komoditas'),
            "Harga": d.get('harga_angka', 0),
            "Teks Harga": d.get('range_harga'),
            "Lokasi": lokasi_raw,
            "Sumber": d.get('sumber'),
            "Waktu": format_wib(d.get('waktu_ambil')),
            "Raw_Time": d.get('waktu_ambil')
        })
    
    df = pd.DataFrame(data_list)

    # B. FILTER & PENCARIAN
    col_filter1, col_filter2 = st.columns([1, 2])
    with col_filter1:
        pilih_komoditas = st.selectbox("📦 Pilih Komoditas:", 
            ["Semua", "Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Manau", "Sagu", "Lainnya"])
    with col_filter2:
        cari_lokasi = st.text_input("📍 Cari Desa/Dusun:", placeholder="Ketik nama desa...")

    # C. LOGIKA FILTER
    df_view = df.copy()
    if not df.empty:
        if pilih_komoditas != "Semua":
            df_view = df_view[df_view['Komoditas'] == pilih_komoditas]
        if cari_lokasi:
            df_view = df_view[df_view['Lokasi'].str.contains(cari_lokasi, case=False, na=False)]

        # D. TAMPILAN STATISTIK & GRAFIK
        if not df_view.empty:
            # Statistik Harga
            avg_p = df_view['Harga'].mean()
            max_p = df_view['Harga'].max()
            min_p = df_view['Harga'].min()
            
            st.markdown(f"#### 📈 Statistik: {pilih_komoditas if pilih_komoditas != 'Semua' else 'Umum'}")
            m1, m2, m3 = st.columns(3)
            m1.metric("Harga Tertinggi", f"Rp {max_p:,.0f}".replace(",", "."))
            m2.metric("Rata-Rata", f"Rp {avg_p:,.0f}".replace(",", "."))
            m3.metric("Harga Terendah", f"Rp {min_p:,.0f}".replace(",", "."))
            
            # Grafik Tren Waktu
            st.markdown("#### 🌊 Pergerakan Harga")
            chart = alt.Chart(df_view).mark_line(point=True).encode(
                x=alt.X('Raw_Time', title='Waktu'),
                y=alt.Y('Harga', title='Harga (Rp)'),
                color='Lokasi',
                tooltip=['Komoditas', 'Harga', 'Lokasi', 'Waktu']
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

            # Tabel Data
            st.markdown("#### 📋 Data Terinci")
            st.dataframe(
                df_view[['Komoditas', 'Teks Harga', 'Lokasi', 'Sumber', 'Waktu']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("⚠️ Data tidak ditemukan. Belum ada laporan untuk pencarian ini.")
            st.info("Jadilah yang pertama melapor di tab 'LAPOR HARGA'!")
    else:
        st.info("Database masih kosong. Silakan input data pertama!")

    if st.button("🔄 Refresh Data"):
        st.rerun()

# ================= TAB 2: INPUT LAPORAN (FORMULIR) =================
with tab_lapor:
    st.markdown("### 📝 Form Lapor Harga Lapangan")
    st.write("Pastikan data yang dimasukkan valid dan nyata.")
    
    with st.form("form_lapor"):
        c1, c2 = st.columns(2)
        
        with c1:
            in_komoditas = st.selectbox("Jenis Komoditas", 
                ["Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Manau", "Sagu", "Lainnya"])
            in_harga = st.number_input("Harga per Kg (Rupiah)", min_value=0, step=500)
            in_sumber = st.selectbox("Status Pelapor", ["Petani", "Pengepul Desa", "Toke Besar", "Warga Biasa"])
            
        with c2:
            in_dusun = st.text_input("Nama Dusun / Desa", placeholder="Contoh: Dusun Bose, Desa Muara")
            # DROPDOWN KECAMATAN ASLI MENTAWAI (Biar Data Rapih)
            in_kecamatan = st.selectbox("Kecamatan (Wajib Pilih)", [
                "Sikakap", 
                "Pagai Utara", 
                "Pagai Selatan", 
                "Sipora Utara (Tuapejat)", 
                "Sipora Selatan", 
                "Siberut Selatan", 
                "Siberut Barat", 
                "Siberut Utara", 
                "Siberut Tengah", 
                "Siberut Barat Daya"
            ])
        
        # Tombol Submit
        submitted = st.form_submit_button("KIRIM LAPORAN SEKARANG 🚀")
        
        if submitted:
            if in_harga > 0 and in_dusun:
                lokasi_fix = f"{in_dusun}, {in_kecamatan}"
                
                # Simpan ke Firestore
                db.collection("harga_realtime").add({
                    "komoditas": in_komoditas,
                    "harga_angka": in_harga,
                    "range_harga": f"Rp {in_harga:,}".replace(",", "."),
                    "judul_berita": f"Info: {in_komoditas}",
                    "waktu_ambil": datetime.datetime.now(),
                    "sumber": in_sumber,
                    "lokasi": lokasi_fix,
                    "status": "Verified User"
                })
                
                st.success(f"✅ Mantap! Data {in_komoditas} di {lokasi_fix} berhasil disimpan.")
                st.balloons()
            else:
                st.error("❌ Gagal! Pastikan HARGA diisi dan NAMA DUSUN tidak kosong.")
