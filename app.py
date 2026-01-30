import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json
import altair as alt

# 1. PAGE CONFIG (Layout Wide Wajib!)
st.set_page_config(
    page_title="Sistem Pantau Harga Mentawai", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS PRO (BIAR KAYA DASHBOARD PEMERINTAH) ---
st.markdown("""
<style>
    /* Hilangkan padding atas biar full screen */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    /* Style Metric Card biar kotak-kotak kayak Bappebti */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    /* Warna Judul Metric */
    div[data-testid="metric-container"] > label {
        color: #AAAAAA;
    }
    /* Warna Angka Metric */
    div[data-testid="metric-container"] > div {
        color: #00CC96; /* Hijau Saham */
    }
    /* Running Text Style */
    .ticker-wrap {
        width: 100%;
        background-color: #D32F2F; /* Merah Breaking News */
        color: white;
        padding: 10px;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Fungsi Waktu WIB
def format_wib(waktu_utc):
    if waktu_utc:
        wib = waktu_utc + datetime.timedelta(hours=7)
        return wib.strftime("%d-%m-%Y %H:%M")
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
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# --- AMBIL DATA GLOBAL (CACHING BIAR CEPAT) ---
docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).limit(500).stream()
all_data = []
ticker_items = []

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
    # Ambil 5 data terbaru buat Running Text
    if len(ticker_items) < 5:
        ticker_items.append(f"{d.get('komoditas')} ({lokasi_raw}): {d.get('range_harga')}")

df = pd.DataFrame(all_data)

# --- HEADER & RUNNING TEXT (ALA BERITA TV) ---
st.markdown("## 🏛️ PUSAT INFORMASI HARGA KOMODITI MENTAWAI")
st.markdown("##### *Dashboard Monitoring Real-Time (Beta Version)*")

# Ticker Text (Running Text HTML)
text_jalan = "  |  ".join(ticker_items) if ticker_items else "Belum ada data terbaru hari ini."
st.markdown(f"""
<div class="ticker-wrap">
    <marquee direction="left" scrollamount="8">
    UPDATE TERKINI: {text_jalan} | 📢 Silakan lapor harga terbaru melalui menu di bawah.
    </marquee>
</div>
""", unsafe_allow_html=True)

# --- NAVIGASI UTAMA (TAB GAYA DASHBOARD) ---
# Kita pakai Tab buat misahin "View Data" dan "Input Data" biar bersih
tab_dash, tab_input = st.tabs(["📊 DASHBOARD HARGA (PUBLIK)", "📝 INPUT DATA (PETANI/ADMIN)"])

# ================= TAB 1: DASHBOARD EKSEKUTIF =================
with tab_dash:
    # --- ROW 1: FILTER CONTROL PANEL ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            filter_komoditas = st.selectbox("📦 Pilih Komoditas:", ["Semua"] + sorted(list(set(df['Komoditas']))) if not df.empty else ["Semua"])
        with c2:
            filter_lokasi = st.text_input("📍 Filter Wilayah (Kecamatan/Desa):", placeholder="Cari lokasi...")
        with c3:
            st.write("") # Spacer
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

    # LOGIKA FILTER
    df_view = df.copy()
    if not df.empty:
        if filter_komoditas != "Semua":
            df_view = df_view[df_view['Komoditas'] == filter_komoditas]
        if filter_lokasi:
            df_view = df_view[df_view['Lokasi'].str.contains(filter_lokasi, case=False, na=False)]

    # --- ROW 2: KARTU METRIK (STATISTIK) ---
    st.markdown("### Ringkasan Statistik")
    
    if not df_view.empty:
        # Hitung Statistik
        rata_rata = df_view['Harga_Angka'].mean()
        tertinggi = df_view['Harga_Angka'].max()
        terendah = df_view['Harga_Angka'].min()
        volum = len(df_view)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rata-Rata Harga", f"Rp {rata_rata:,.0f}".replace(",", "."))
        m2.metric("Harga Tertinggi", f"Rp {tertinggi:,.0f}".replace(",", "."))
        m3.metric("Harga Terendah", f"Rp {terendah:,.0f}".replace(",", "."))
        m4.metric("Total Laporan", f"{volum} Data")
    else:
        st.warning("Data tidak ditemukan. Silakan ubah filter atau input data baru.")

    # --- ROW 3: GRAFIK & TABEL (SPLIT VIEW) ---
    col_chart, col_table = st.columns([2, 1])

    with col_chart:
        st.markdown("#### 📈 Tren Pergerakan Harga")
        if not df_view.empty:
            chart_data = df_view.sort_values('Raw_Time')
            c = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('Waktu', title='Waktu'),
                y=alt.Y('Harga_Angka', title='Harga (Rp)'),
                color='Komoditas',
                tooltip=['Komoditas', 'Harga', 'Lokasi', 'Waktu']
            ).interactive()
            st.altair_chart(c, use_container_width=True)
        else:
            st.info("Grafik tidak tersedia (Data Kosong)")

    with col_table:
        st.markdown("#### 📋 Tabel Data Terinci")
        if not df_view.empty:
            st.dataframe(
                df_view[['Komoditas', 'Harga', 'Lokasi', 'Waktu']],
                use_container_width=True,
                hide_index=True,
                height=350 # Biar ada scrollbar kalau panjang
            )
        else:
            st.write("Belum ada data.")

# ================= TAB 2: FORM INPUT (KHUSUS KONTRIBUTOR) =================
with tab_input:
    st.info("ℹ️ Fitur ini digunakan oleh Petani, Pengepul, atau Admin Dinas untuk update harga lapangan.")
    
    with st.form("input_form"):
        c_in1, c_in2 = st.columns(2)
        
        with c_in1:
            in_komoditas = st.selectbox("Jenis Komoditas", 
                ["Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Lobster", "Nilam", "Rotan", "Sagu", "Lainnya"])
            in_harga = st.number_input("Harga Rupiah (per Kg)", min_value=0, step=100)
            in_sumber = st.selectbox("Sumber Data", ["Petani", "Pengepul", "Dinas Pasar", "Masyarakat"])
        
        with c_in2:
            in_dusun = st.text_input("Nama Dusun / Desa", placeholder="Cth: Taileleu")
            in_kecamatan = st.selectbox("Kecamatan", 
                ["Sikakap", "Pagai Utara", "Pagai Selatan", "Sipora Utara", "Sipora Selatan", "Siberut Selatan", "Siberut Barat", "Siberut Utara", "Siberut Tengah"])
        
        btn_kirim = st.form_submit_button("KIRIM DATA KE SERVER 🚀", type="primary", use_container_width=True)

        if btn_kirim:
            if in_harga > 0 and in_dusun:
                lokasi_fix = f"{in_dusun}, {in_kecamatan}"
                
                db.collection("harga_realtime").add({
                    "komoditas": in_komoditas,
                    "harga_angka": in_harga,
                    "range_harga": f"Rp {in_harga:,}".replace(",", "."),
                    "waktu_ambil": datetime.datetime.now(),
                    "sumber": in_sumber,
                    "lokasi": lokasi_fix,
                    "status": "Verified"
                })
                st.success(f"✅ Data {in_komoditas} di {lokasi_fix} berhasil disimpan!")
                st.caption("Silakan pindah ke Tab Dashboard untuk melihat hasilnya.")
            else:
                st.error("❌ Harga dan Lokasi wajib diisi.")
