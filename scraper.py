import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime

# --- BAGIAN 1: KONEKSI DATABASE ---
# Cek dulu apakah sudah connect biar gak error kalau dijalankan berkali-kali
if not firebase_admin._apps:
    cred = credentials.Certificate("kunci.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- BAGIAN 2: FUNGSI SCRAPING (PENCARI HARGA) ---
def sikat_harga_internet():
    print("🕵️  Sedang memata-matai harga pasar...")
    
    # Target URL (Kita pakai InfoSawit sebagai contoh CPO)
    url = "https://www.infosawit.com/news/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

    harga_dapat = False
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        artikel_list = soup.find_all('h3', class_='entry-title', limit=5)
        
        for artikel in artikel_list:
            judul = artikel.text.strip()
            
            # Logika: Kalau nemu kata "Harga" atau "Tender", kita simpan!
            if "Harga" in judul or "Tender" in judul:
                print(f"✅ MENEMUKAN DATA BERITA: {judul}")
                
                # Simpan ke database
                data_baru = {
                    "sumber": "InfoSawit (Berita)",
                    "judul_berita": judul,
                    "komoditas": "CPO/Sawit",
                    "waktu_ambil": datetime.datetime.now(),
                    "status": "Valid"
                }
                
                db.collection("harga_realtime").add(data_baru)
                harga_dapat = True
        
        # --- BAGIAN UPDATE (SESUAI REQUEST LU) ---
        if not harga_dapat:
            print("⚠️ Berita lagi kosong. Menggunakan DATA UPDATE JANUARI 2026...")
            
            # Kita masukkan data range harga yang lu temuin di Google tadi
            db.collection("harga_realtime").add({
                "sumber": "Estimasi Pasar (Januari 2026)",
                "judul_berita": "Update Harga Kopra Awal Tahun 2026",
                "komoditas": "Kopra Kering",
                "harga_rata_rata": 16500, # Kita ambil tengah-tengah
                "range_harga": "Rp 15.000 - Rp 17.650",
                "catatan": "Harga bisa berubah tergantung kadar air",
                "waktu_ambil": datetime.datetime.now()
            })
            
        print("\n🚀 SELESAI! Data Kopra (Rp 16.500) sudah dikirim ke Database!")

    except Exception as e:
        print(f"Error gawat: {e}")

# JALANKAN PROGRAM
if __name__ == "__main__":
    sikat_harga_internet()