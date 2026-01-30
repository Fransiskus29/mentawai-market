import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json

# 1. SETUP HALAMAN (Mode Lebar biar kayak Dashboard Profesional)
st.set_page_config(page_title="Mentawai Market Pro", page_icon="📈", layout="wide")

# Fungsi konversi waktu UTC ke WIB
def format_wib(waktu_utc):
    if waktu_utc:
        # Tambah 7 jam untuk WIB
        wib = waktu_utc + datetime.timedelta(hours=7)
        return wib.strftime("%d %b %Y - %H:%M WIB")
    return "-"

# 2. KONEKSI DATABASE (Hybrid: Laptop & Cloud)
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
    st.error(f"Gagal koneksi database: {e}")
    st.stop()

# --- SIDEBAR: AREA INPUT (KHUSUS WARGA/PENGEPUL) ---
with st.sidebar:
    st.header("📝 Input Laporan Warga")
    st.info("Fitur ini untuk kontributor harga di lapangan.")
    
    input_nama = st.selectbox("Komoditas", ["Kopra Kering", "Cengkeh", "Gurita", "Pinang", "Kakao", "Ikan Kerapu", "Lainnya"])
    input_harga = st.number_input("Harga per Kg (Rp)", min_value=0, step=500)
    input_lokasi = st.text_input("Lokasi (Kecamatan/Desa)", placeholder="Contoh: Sikakap")
    input_sumber = st.selectbox("Status Pelapor", ["Petani", "Pengepul Kecil", "Gudang Besar", "Masyarakat"])
    
    if st.button("Kirim Data 🚀", use_container_width=True):
        if input_harga > 0 and input_lokasi:
            db.collection("harga_realtime").add({
                "komoditas": input_nama,
                "harga_angka": input_harga, # Kita simpan angka murni buat statistik
                "range_harga": f"Rp {input_harga:,}".replace(",", "."),
                "judul_berita": f"Laporan: {input_nama}",
                "waktu_ambil": datetime.datetime.now(),
                "sumber": input_sumber,
                "lokasi": input_lokasi,
                "status": "User Report"
            })
            st.success("Data masuk! Terima kasih kontribusinya.")
            st.rerun()
        else:
            st.warning("Mohon isi harga dan lokasi dengan benar.")

# --- HALAMAN UTAMA: DASHBOARD EKSEKUTIF ---
st.title("📈 Mentawai Market Intelligence")
st.markdown("Dashboard monitoring harga komoditas real-time untuk pengambilan keputusan.")
st.divider()

# 3. LOGIKA FILTER (SEARCH ENGINE)
col_filter1, col_filter2 = st.columns([1, 2])

with col_filter1:
    filter_komoditas = st.selectbox("🔍 Pilih Komoditas:", ["Semua", "Kopra Kering", "Cengkeh", "Gurita", "Pinang", "Kakao"])

with col_filter2:
    filter_lokasi = st.text_input("📍 Cari Lokasi (Ketik nama desa/kecamatan):", placeholder="Cari Sikakap, Siberut, Sipora...")

# 4. AMBIL DATA DARI DATABASE
docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).limit(100).stream()

# Proses Data ke DataFrame
data_list = []
for doc in docs:
    d = doc.to_dict()
    # Handle data lama yang formatnya beda
    lokasi_fix = d.get('lokasi') if d.get('lokasi') else d.get('sumber', '-')
    harga_fix = d.get('harga_angka') if d.get('harga_angka') else 0
    
    data_list.append({
        "Komoditas": d.get('komoditas'),
        "Harga (Rp)": d.get('range_harga'),
        "Harga_Angka": harga_fix, # Kolom tersembunyi buat hitung-hitungan
        "Lokasi": lokasi_fix,
        "Sumber Info": d.get('sumber'),
        "Waktu Update": format_wib(d.get('waktu_ambil')),
        "Raw_Time": d.get('waktu_ambil') # Buat sorting
    })

df = pd.DataFrame(data_list)

# 5. TERAPKAN FILTER
if not df.empty:
    # Filter Komoditas
    if filter_komoditas != "Semua":
        df = df[df['Komoditas'] == filter_komoditas]
    
    # Filter Lokasi (Search Text)
    if filter_lokasi:
        df = df[df['Lokasi'].str.contains(filter_lokasi, case=False, na=False)]

    # 6. TAMPILKAN METRIK STATISTIK (PROFESIONAL LOOK)
    # Cuma muncul kalau user memilih filter spesifik (biar datanya relevan)
    if filter_komoditas != "Semua" and not df.empty:
        avg_price = df[df['Harga_Angka'] > 0]['Harga_Angka'].mean()
        max_price = df[df['Harga_Angka'] > 0]['Harga_Angka'].max()
        min_price = df[df['Harga_Angka'] > 0]['Harga_Angka'].min()
        
        st.subheader(f"Statistik Harga: {filter_komoditas}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Harga Tertinggi", f"Rp {max_price:,.0f}".replace(",", "."))
        m2.metric("Harga Rata-rata", f"Rp {avg_price:,.0f}".replace(",", "."))
        m3.metric("Harga Terendah", f"Rp {min_price:,.0f}".replace(",", "."))
        st.divider()

    # 7. TABEL DATA UTAMA
    st.subheader("📋 Data Pasar Terkini")
    
    # Tampilkan tabel tanpa kolom rahasia
    tabel_show = df[["Komoditas", "Harga (Rp)", "Lokasi", "Sumber Info", "Waktu Update"]]
    st.dataframe(
        tabel_show, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Waktu Update": st.column_config.TextColumn("Waktu Update", help="Waktu dalam WIB"),
            "Harga (Rp)": st.column_config.TextColumn("Harga (Rp)", width="medium")
        }
    )
    
    # Tombol Refresh Manual (Tetap perlu karena web socket mahal)
    if st.button('🔄 Sinkronisasi Server', help="Tarik data terbaru dari pusat"):
        st.rerun()

else:
    st.warning("Data tidak ditemukan. Coba ganti kata kunci pencarian.")
