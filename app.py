import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os # <--- TAMBAHAN BARU
import json # <--- TAMBAHAN BARU

# 1. SETUP HALAMAN
st.set_page_config(page_title="Mentawai Market", page_icon="🌴", layout="wide")

# 2. KONEKSI DATABASE (Hybrid: Laptop & Cloud)
if not firebase_admin._apps:
    # Cek apakah ada file kunci.json (Berarti lagi di Laptop)
    if os.path.exists("kunci.json"):
        cred = credentials.Certificate("kunci.json")
    else:
        # Kalau gak ada file, berarti lagi di Internet (Pake Secrets)
        # Kita ambil kuncinya dari brankas rahasia Streamlit
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        
    firebase_admin.initialize_app(cred)

db = firestore.client()