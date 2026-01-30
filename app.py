import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json

# 1. SETUP HALAMAN
st.set_page_config(page_title="Mentawai Market", page_icon="🌴", layout="wide")

# --- FITUR DIAGNOSA ERROR (AGAR TIDAK LAYAR PUTIH) ---
try:
    # 2. KONEKSI DATABASE (Hybrid: Laptop & Cloud)
    if not firebase_admin._apps:
        # Cek apakah ada file kunci.json (Berarti lagi di Laptop)
        if os.path.exists("kunci.json"):
            cred = credentials.Certificate("kunci.json")
        else:
            # Kalau gak ada file, berarti lagi di Internet (Pake Secrets)
            # Cek dulu apakah secrets 'textkey' ada?
            if "textkey" in st.secrets:
                key_dict = json.loads(st.secrets["textkey"])
                cred = credentials.Certificate(key_dict)
            else:
                raise Exception("Kunci 'textkey' tidak ditemukan di Secrets!")
            
        firebase_admin.initialize_app(cred)

    db = firestore.client()

except Exception as e:
    # KALAU ERROR, TAMPILKAN DI LAYAR (JANGAN BLANK)
    st.error("⚠️ TERJADI ERROR KONEKSI DATABASE!")
    st.code(f"Pesan Error: {e}")
    st.info("Saran: Cek kembali menu 'Secrets' di Streamlit. Pastikan formatnya benar.")
    st.stop() # Berhenti di sini biar gak lanjut crash

# --- BAGIAN BAWAH INI SAMA KAYAK SEBELUMNYA ---

# SIDEBAR INPUT
with st.sidebar:
    st.header("📝 Lapor Harga Baru")
    st.write("Bantu petani lain dengan update harga lapangan!")
    
    input_nama = st.selectbox("Pilih Komoditas", ["Kopra Kering", "Cengkeh", "Gurita", "Pinang", "Kakao", "Lainnya"])
    input_harga = st.number_input("Harga per Kg (Rp)", min_value=0, step=500)
    input_lokasi = st.text_input("Lokasi (Desa/Kecamatan)", "Sikakap")
    input_sumber = st.text_input("Sumber Info", "Pengepul Lokal")
    
    if st.button("Kirim Laporan 🚀"):
        if input_harga > 0:
            db.collection("harga_realtime").add({
                "komoditas": input_nama,
                "range_harga": f"Rp {input_harga:,}".replace(",", "."),
                "judul_berita": f"Laporan Warga: {input_nama}",
                "waktu_ambil": datetime.datetime.now(),
                "sumber": f"{input_sumber} ({input_lokasi})",
                "status": "Laporan Warga"
            })
            st.success("Mantap! Data berhasil dikirim.")
            st.rerun()
        else:
            st.error("Isi harganya dulu bro!")

# HALAMAN UTAMA
st.title("🌴 Pasar Mentawai Real-Time")
st.markdown("Pantau harga hasil bumi langsung dari laporan warga & berita.")

# Metrik
col1, col2, col3 = st.columns(3)
col1.metric("Lokasi Pantauan", "Pagai Utara & Selatan", "Sikakap")
col2.metric("Status Server", "Online", "Aktif")
col3.metric("Update Terakhir", datetime.datetime.now().strftime("%H:%M WIB"), "Hari ini")

st.divider()

# TAMPILKAN DATA
st.subheader("📊 Papan Harga Terkini")

docs = db.collection('harga_realtime').order_by('waktu_ambil', direction=firestore.Query.DESCENDING).stream()

data_list = []
for doc in docs:
    d = doc.to_dict()
    waktu = d.get('waktu_ambil')
    if waktu:
        waktu_str = waktu.strftime("%d %b %Y - %H:%M")
    else:
        waktu_str = "-"
        
    data_list.append({
        "Komoditas": d.get('komoditas'),
        "Harga Saat Ini": d.get('range_harga') if d.get('range_harga') else d.get('judul_berita'),
        "Lokasi/Sumber": d.get('sumber'),
        "Waktu Laporan": waktu_str
    })

if data_list:
    df = pd.DataFrame(data_list)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Belum ada data. Jadilah yang pertama melapor di menu sebelah kiri! 👈")

if st.button('🔄 Muat Ulang Data'):
    st.rerun()
