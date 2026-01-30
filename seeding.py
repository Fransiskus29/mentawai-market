import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import random
import datetime
import json
import streamlit as st

# --- KONFIGURASI KONEKSI (SAMA KAYAK APP.PY) ---
# Kita pakai secrets dari Streamlit Cloud nanti, atau file lokal kalau di laptop
if not firebase_admin._apps:
    try:
        # Coba baca dari Streamlit Secrets (kalau dijalankan di Cloud)
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except:
        # Fallback ke file lokal (kalau dijalankan di laptop)
        cred = credentials.Certificate("kunci.json")
        firebase_admin.initialize_app(cred)

db = firestore.client()

# --- DATA GENERATOR ---
komoditas_list = ["Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", "Lobster", "Nilam", "Rotan", "Sagu"]
lokasi_list = [
    "Dusun Taileleu, Siberut Barat Daya", "Desa Sikakap, Sikakap", 
    "Desa Muara Siberut, Siberut Selatan", "Desa Betumonga, Pagai Utara",
    "Desa Saumanganya, Pagai Utara", "Desa Bosua, Sipora Selatan",
    "Tuapejat, Sipora Utara", "Desa Maileppet, Siberut Selatan"
]
sumber_list = ["Petani", "Pengepul Desa", "Toke Besar", "Dinas Pasar"]

st.title("💉 Data Injector (Isi Database Otomatis)")

if st.button("SUNTIK 50 DATA DUMMY SEKARANG 🚀"):
    progress_text = "Sedang mengisi database..."
    my_bar = st.progress(0, text=progress_text)

    for i in range(50):
        # Random Data
        item = random.choice(komoditas_list)
        loc = random.choice(lokasi_list)
        src = random.choice(sumber_list)
        
        # Harga acak tapi masuk akal (plus minus 20%)
        base_price = 10000 
        if item == "Cengkeh": base_price = 120000
        elif item == "Kopra Kering": base_price = 8000
        elif item == "Gurita": base_price = 45000
        elif item == "Lobster": base_price = 300000
        elif item == "Pinang": base_price = 4000
        
        variation = random.randint(-2000, 2000)
        final_price = base_price + variation
        
        # Waktu acak (Mundur 1-7 hari ke belakang biar grafiknya terbentuk)
        days_back = random.randint(0, 7)
        waktu_fake = datetime.datetime.now() - datetime.timedelta(days=days_back, hours=random.randint(1, 12))

        # PUSH KE DATABASE
        db.collection("harga_realtime").add({
            "komoditas": item,
            "harga_angka": final_price,
            "range_harga": f"Rp {final_price:,}".replace(",", "."),
            "waktu_ambil": waktu_fake,
            "sumber": src,
            "lokasi": loc,
            "status": "Dummy Data"
        })
        
        # Update progress bar
        my_bar.progress((i + 1) / 50, text=f"Menginput: {item} di {loc}")

    st.success("✅ SELESAI! 50 Data berhasil disuntikkan. Silakan cek Dashboard utama.")
