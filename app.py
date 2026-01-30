import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json
import altair as alt # Buat bikin grafik keren

# 1. SETUP HALAMAN (Full Screen & Judul Keren)
st.set_page_config(
    page_title="Mentawai Smart Market", 
    page_icon="🌴", 
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar nutup dulu biar luas
)

# --- CSS HACK (BIAR TAMPILAN MAKIN CANGGIH & BERSIH) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #00CC96;
    }
    .stAlert {
        border-radius: 10px;
    }
    /* Sembunyikan menu standar biar kayak aplikasi native */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
    st.error(f"Database Error: {e}")
    st.stop()

# --- LOGIKA NAVIGASI (TAB MENU) ---
# Biar petani gak bingung, kita bagi jadi 2 Tab Besar
tab1, tab2 = st.tabs(["📊 CEK HARGA PASAR", "📝 LAPOR HARGA BARU"])

# ================= TAB 1: DASHBOARD PETANI (VIEW ONLY) =================
with tab1:
    # Header Hero
    st.markdown("# 🌴 Mentawai Market Intelligence")
    st.markdown("### *Pusat Data Harga Komoditas Real-Time Antar-Desa*")
    st.caption(f"Update Terakhir: {datetime.datetime.now().strftime('%H:%M WIB')}")
    st.divider()

    # --- SEARCH ENGINE CANGGIH ---
    col_search1, col_search2, col_search3 = st.columns([2,2,1])
    
    with col_search1:
        # List Komoditas Lengkap
        pilih_komoditas = st.selectbox("🔍 Mau cek harga apa?", 
            ["Semua", "Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", 
             "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Manau", "Gaharu", "Sagu"])
    
    with col_search2:
        cari_lokasi = st.text_input("📍 Cari Dusun/Desa/Kecamatan:", placeholder="Ketik: Taileleu, Sikakap, Siberut...")
    
    with col_search3:
        st.write("") # Spacer
        st.write("")
        tombol_refresh = st.button("🔄 Refresh Data")

    # --- TARIK DATA ---
    docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).limit(200).stream()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        lokasi_raw = d.get('lokasi', '-')
        # Gabungin sumber & lokasi biar informatif
        sumber_lengkap = f"{d.get('sumber')} ({lokasi_raw})"
        
        data_list.append({
            "Komoditas": d.get('komoditas'),
            "Harga": d.get('range_harga'),
            "Harga_Angka": d.get('harga_angka', 0),
            "Lokasi": lokasi_raw,
            "Detail Sumber": sumber_lengkap,
            "Waktu": format_wib(d.get('waktu_ambil')),
            "Raw_Time": d.get('waktu_ambil')
        })
    
    df = pd.DataFrame(data_list)

    # --- FILTER LOGIC ---
    if not df.empty:
        if pilih_komoditas != "Semua":
            df = df[df['Komoditas'] == pilih_komoditas]
        if cari_lokasi:
            df = df[df['Lokasi'].str.contains(cari_lokasi, case=False, na=False)]

        # --- FITUR "WOW": STATISTIK & GRAFIK ---
        if pilih_komoditas != "Semua" and not df.empty:
            # 1. Kartu Statistik
            avg = df['Harga_Angka'].mean()
            max_p = df['Harga_Angka'].max()
            min_p = df['Harga_Angka'].min()
            
            st.markdown(f"#### Statistik Harga: {pilih_komoditas}")
            k1, k2, k3 = st.columns(3)
            k1.metric("Tertinggi", f"Rp {max_p:,.0f}".replace(",", "."))
            k2.metric("Rata-Rata", f"Rp {avg:,.0f}".replace(",", "."))
            k3.metric("Terendah", f"Rp {min_p:,.0f}".replace(",", "."))
            
            # 2. Grafik Tren Harga (Line Chart)
            st.markdown("#### 📈 Tren Pergerakan Harga")
            chart_data = df.sort_values('Raw_Time')
            
            c = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('Waktu', title='Waktu Laporan'),
                y=alt.Y('Harga_Angka', title='Harga (Rp)'),
                tooltip=['Komoditas', 'Harga', 'Lokasi', 'Waktu']
            ).interactive()
            
            st.altair_chart(c, use_container_width=True)

        # --- TABEL DATA ---
        st.markdown("### 📋 Laporan Terbaru")
        st.dataframe(
            df[['Komoditas', 'Harga', 'Detail Sumber', 'Waktu']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Komoditas": st.column_config.TextColumn("Komoditas", width="small"),
                "Detail Sumber": st.column_config.TextColumn("Lokasi & Sumber", width="large"),
            }
        )
    else:
        st.info("🚧 Belum ada data untuk pencarian ini. Jadilah yang pertama melapor di Tab sebelah! 👉")

# ================= TAB 2: FORM LAPOR (INPUT) =================
with tab2:
    col_form1, col_form2 = st.columns([1,1])
    
    with col_form1:
        st.subheader("📝 Form Kontributor")
        st.write("Bagi Petani, Pengepul, atau Warga yang ingin berbagi info harga valid.")
        
        in_nama = st.selectbox("Jenis Komoditas", 
            ["Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Ikan Kerapu", "Lobster", "Nilam", "Rotan", "Manau", "Gaharu", "Sagu", "Lainnya"])
        
        in_harga = st.number_input("Harga per Kg (Rupiah)", min_value=0, step=500, help="Masukkan angka saja tanpa titik/koma")
        
    with col_form2:
        st.write("") # Spacer biar sejajar
        st.write("") 
        # Lokasi lebih spesifik
        in_dusun = st.text_input("Nama Dusun / Desa", placeholder="Contoh: Dusun Bose, Desa Muara Sikabaluan")
        in_kecamatan = st.selectbox("Kecamatan", ["Sikakap", "Pagai Utara", "Pagai Selatan", "Sipora Utara", "Sipora Selatan", "Siberut Selatan", "Siberut Barat", "Siberut Utara", "Siberut Tengah", "Siberut Barat Daya"])
        
        in_sumber = st.radio("Status Anda:", ["Petani", "Pengepul Desa", "Toke Besar", "Warga Biasa"], horizontal=True)

    # Tombol Kirim Besar
    if st.button("KIRIM LAPORAN SEKARANG 🚀", type="primary", use_container_width=True):
        if in_harga > 0 and in_dusun:
            lokasi_fix = f"{in_dusun}, {in_kecamatan}"
            
            db.collection("harga_realtime").add({
                "komoditas": in_nama,
                "harga_angka": in_harga,
                "range_harga": f"Rp {in_harga:,}".replace(",", "."),
                "judul_berita": f"Info: {in_nama}",
                "waktu_ambil": datetime.datetime.now(),
                "sumber": in_sumber,
                "lokasi": lokasi_fix,
                "status": "Verified User"
            })
            st.balloons() # Efek balon biar seru
            st.success(f"Mantap! Harga {in_nama} di {lokasi_fix} berhasil disimpan.")
            
            # Auto refresh biar datanya langsung kelihatan
            import time
            time.sleep(2)
            st.rerun()
        else:
            st.error("Waduh, Harga dan Nama Dusun wajib diisi ya bro!")
