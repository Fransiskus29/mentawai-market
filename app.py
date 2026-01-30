import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import datetime
import os
import json
import altair as alt
import random

# ============================================================================
# 1. PAGE CONFIG (Layout Wide untuk Dashboard Profesional)
# ============================================================================
st.set_page_config(
    page_title="Mentawai Market Intelligence", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# 2. CUSTOM CSS - GOVERNMENT DASHBOARD STYLE
# ============================================================================
st.markdown("""
<style>
    /* Import Font Profesional */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hilangkan padding atas untuk full screen */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: #e0e0e0;
        margin: 5px 0 0 0;
        font-size: 1rem;
    }
    
    /* Metric Card Professional Style */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    
    div[data-testid="metric-container"] > label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    
    div[data-testid="metric-container"] > div {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    /* Running Text/Ticker Style */
    .ticker-wrap {
        width: 100%;
        background: linear-gradient(90deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        padding: 12px;
        font-weight: 600;
        border-radius: 8px;
        margin-bottom: 25px;
        box-shadow: 0 2px 8px rgba(255,107,107,0.3);
    }
    
    .ticker-content {
        font-size: 1rem;
        letter-spacing: 0.5px;
    }
    
    /* Card Container */
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    /* Table Styling */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102,126,234,0.4);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Info Box */
    .info-box {
        background: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Success Box */
    .success-box {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. UTILITY FUNCTIONS
# ============================================================================
def format_wib(waktu_utc):
    """Convert UTC to WIB timezone"""
    if waktu_utc:
        wib = waktu_utc + datetime.timedelta(hours=7)
        return wib.strftime("%d-%m-%Y %H:%M")
    return "-"

def format_rupiah(angka):
    """Format number to Indonesian Rupiah format"""
    return f"Rp {angka:,.0f}".replace(",", ".")

# ============================================================================
# 4. FIREBASE CONNECTION (Hybrid: Cloud & Local)
# ============================================================================
@st.cache_resource
def init_firebase():
    """Initialize Firebase with hybrid authentication"""
    try:
        if not firebase_admin._apps:
            # Try local file first
            if os.path.exists("kunci.json"):
                cred = credentials.Certificate("kunci.json")
                st.sidebar.success("🔐 Connected via Local Key")
            # Fallback to Streamlit Secrets (for Cloud Deploy)
            elif "textkey" in st.secrets:
                key_dict = json.loads(st.secrets["textkey"])
                cred = credentials.Certificate(key_dict)
                st.sidebar.success("☁️ Connected via Cloud Secrets")
            else:
                st.error("❌ No Firebase credentials found!")
                st.stop()
            
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"🔥 Firebase Connection Failed: {e}")
        st.stop()

db = init_firebase()

# ============================================================================
# 5. DATA SEEDING FUNCTION (AUTO POPULATE DATABASE)
# ============================================================================
def seed_dummy_data(jumlah=50):
    """Generate and insert dummy data to Firestore"""
    
    komoditas_list = [
        "Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", 
        "Lobster", "Nilam", "Rotan", "Sagu", "Kelapa Utuh",
        "Ikan Tuna", "Vanili", "Pala", "Kayu Manis"
    ]
    
    desa_mentawai = [
        "Taileleu", "Matotonan", "Silabu", "Sirilogui", "Rokdok",
        "Madobag", "Saumanganyak", "Saibi Samukop", "Bulasat", "Sigapokna",
        "Bojakan", "Pokai", "Simalegi", "Sitioitoi", "Ugai"
    ]
    
    kecamatan_list = [
        "Sikakap", "Pagai Utara", "Pagai Selatan", "Sipora Utara", 
        "Sipora Selatan", "Siberut Selatan", "Siberut Barat", 
        "Siberut Utara", "Siberut Tengah"
    ]
    
    sumber_list = ["Petani", "Pengepul", "Dinas Pasar", "Masyarakat"]
    
    # Harga range per komoditas (untuk realistis)
    harga_ranges = {
        "Kopra Kering": (8000, 15000),
        "Cengkeh": (80000, 150000),
        "Pinang": (15000, 25000),
        "Gurita": (45000, 80000),
        "Kakao": (25000, 40000),
        "Lobster": (200000, 400000),
        "Nilam": (150000, 250000),
        "Rotan": (5000, 12000),
        "Sagu": (8000, 15000),
        "Kelapa Utuh": (3000, 6000),
        "Ikan Tuna": (35000, 60000),
        "Vanili": (500000, 800000),
        "Pala": (80000, 120000),
        "Kayu Manis": (40000, 70000)
    }
    
    batch = db.batch()
    success_count = 0
    
    for i in range(jumlah):
        komoditas = random.choice(komoditas_list)
        harga_min, harga_max = harga_ranges.get(komoditas, (10000, 50000))
        harga = random.randint(harga_min, harga_max)
        
        # Randomize waktu dalam 30 hari terakhir
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        waktu = datetime.datetime.now() - datetime.timedelta(days=days_ago, hours=hours_ago)
        
        lokasi = f"{random.choice(desa_mentawai)}, {random.choice(kecamatan_list)}"
        
        doc_ref = db.collection("harga_realtime").document()
        batch.set(doc_ref, {
            "komoditas": komoditas,
            "harga_angka": harga,
            "range_harga": format_rupiah(harga),
            "waktu_ambil": waktu,
            "sumber": random.choice(sumber_list),
            "lokasi": lokasi,
            "status": "Verified" if random.random() > 0.1 else "Pending"
        })
        success_count += 1
        
        # Commit batch setiap 500 operasi (Firestore limit)
        if (i + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()
    
    # Commit sisa data
    batch.commit()
    return success_count

# ============================================================================
# 6. DATA FETCHING (with Caching)
# ============================================================================
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_market_data(limit=1000):
    """Fetch market data from Firestore with caching"""
    try:
        docs = db.collection('harga_realtime').order_by(
            'waktu_ambil', 
            direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        
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
                "Status": d.get('status', 'Verified'),
                "Waktu": format_wib(d.get('waktu_ambil')),
                "Raw_Time": d.get('waktu_ambil')
            })
            
            # Ambil 10 data terbaru untuk running text
            if len(ticker_items) < 10:
                ticker_items.append(
                    f"{d.get('komoditas')} ({lokasi_raw}): {d.get('range_harga')}"
                )
        
        return pd.DataFrame(all_data), ticker_items
    
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), []

# ============================================================================
# 7. MAIN APPLICATION
# ============================================================================

# Fetch Data
df, ticker_items = fetch_market_data()

# ============================================================================
# HEADER SECTION
# ============================================================================
st.markdown("""
<div class="main-header">
    <h1>📊 MENTAWAI MARKET INTELLIGENCE</h1>
    <p>Real-Time Commodity Price Monitoring System | Kabupaten Kepulauan Mentawai</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# RUNNING TEXT / TICKER
# ============================================================================
if ticker_items:
    ticker_text = "  •  ".join(ticker_items)
else:
    ticker_text = "Belum ada data terbaru. Silakan input data atau klik 'Generate Sample Data' untuk simulasi."

st.markdown(f"""
<div class="ticker-wrap">
    <marquee direction="left" scrollamount="6" class="ticker-content">
        🔴 LIVE UPDATE: {ticker_text} | 📢 Laporkan harga terbaru melalui menu INPUT DATA
    </marquee>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# QUICK STATS (Top Row)
# ============================================================================
if not df.empty:
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
    
    with col_stat1:
        st.metric("📦 Total Data", f"{len(df):,}")
    
    with col_stat2:
        unique_komoditas = df['Komoditas'].nunique()
        st.metric("🌾 Jenis Komoditas", f"{unique_komoditas}")
    
    with col_stat3:
        unique_lokasi = df['Lokasi'].nunique()
        st.metric("📍 Lokasi Tercatat", f"{unique_lokasi}")
    
    with col_stat4:
        verified = len(df[df['Status'] == 'Verified'])
        st.metric("✅ Data Terverifikasi", f"{verified}")
    
    with col_stat5:
        today_data = df[df['Raw_Time'] >= datetime.datetime.now() - datetime.timedelta(days=1)]
        st.metric("📅 Update Hari Ini", f"{len(today_data)}")

st.markdown("---")

# ============================================================================
# TAB NAVIGATION
# ============================================================================
tab_dash, tab_input, tab_admin = st.tabs([
    "📊 DASHBOARD PUBLIK", 
    "📝 INPUT DATA LAPANGAN", 
    "⚙️ ADMIN PANEL"
])

# ============================================================================
# TAB 1: DASHBOARD PUBLIK
# ============================================================================
with tab_dash:
    # Filter Section
    with st.container():
        st.markdown("### 🔍 Filter & Pencarian")
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
        
        with col_f1:
            filter_komoditas = st.selectbox(
                "📦 Komoditas:", 
                ["Semua"] + sorted(df['Komoditas'].unique().tolist()) if not df.empty else ["Semua"]
            )
        
        with col_f2:
            filter_lokasi = st.text_input(
                "📍 Cari Lokasi:", 
                placeholder="Contoh: Sikakap, Taileleu..."
            )
        
        with col_f3:
            filter_hari = st.slider(
                "📅 Data Berapa Hari Terakhir:",
                min_value=1,
                max_value=30,
                value=7
            )
        
        with col_f4:
            st.write("")  # Spacer
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
    
    st.markdown("---")
    
    # Apply Filters
    df_view = df.copy()
    if not df.empty:
        # Filter by date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=filter_hari)
        df_view = df_view[df_view['Raw_Time'] >= cutoff_date]
        
        # Filter by komoditas
        if filter_komoditas != "Semua":
            df_view = df_view[df_view['Komoditas'] == filter_komoditas]
        
        # Filter by lokasi
        if filter_lokasi:
            df_view = df_view[df_view['Lokasi'].str.contains(filter_lokasi, case=False, na=False)]
    
    # Statistics Cards
    if not df_view.empty:
        st.markdown("### 📈 Analisis Harga")
        
        m1, m2, m3, m4 = st.columns(4)
        
        rata_rata = df_view['Harga_Angka'].mean()
        tertinggi = df_view['Harga_Angka'].max()
        terendah = df_view['Harga_Angka'].min()
        median = df_view['Harga_Angka'].median()
        
        m1.metric("💰 Rata-Rata Harga", format_rupiah(rata_rata))
        m2.metric("📈 Harga Tertinggi", format_rupiah(tertinggi))
        m3.metric("📉 Harga Terendah", format_rupiah(terendah))
        m4.metric("📊 Median Harga", format_rupiah(median))
        
        st.markdown("---")
        
        # Charts Section
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            st.markdown("#### 📈 Tren Pergerakan Harga")
            
            # Line chart with Altair
            chart_data = df_view.sort_values('Raw_Time').tail(100)  # Last 100 records
            
            line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('Waktu:T', title='Waktu', axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Harga_Angka:Q', title='Harga (Rp)', scale=alt.Scale(zero=False)),
                color=alt.Color('Komoditas:N', legend=alt.Legend(title="Komoditas")),
                tooltip=[
                    alt.Tooltip('Komoditas:N', title='Komoditas'),
                    alt.Tooltip('Harga:N', title='Harga'),
                    alt.Tooltip('Lokasi:N', title='Lokasi'),
                    alt.Tooltip('Waktu:N', title='Waktu'),
                    alt.Tooltip('Sumber:N', title='Sumber')
                ]
            ).properties(
                height=400
            ).interactive()
            
            st.altair_chart(line_chart, use_container_width=True)
        
        with col_chart2:
            st.markdown("#### 🥧 Distribusi per Komoditas")
            
            # Pie/Bar chart
            komoditas_count = df_view['Komoditas'].value_counts().reset_index()
            komoditas_count.columns = ['Komoditas', 'Jumlah']
            
            bar_chart = alt.Chart(komoditas_count.head(10)).mark_bar().encode(
                x=alt.X('Jumlah:Q', title='Jumlah Data'),
                y=alt.Y('Komoditas:N', sort='-x', title=''),
                color=alt.Color('Komoditas:N', legend=None),
                tooltip=['Komoditas', 'Jumlah']
            ).properties(
                height=400
            )
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        st.markdown("---")
        
        # Data Table
        st.markdown("#### 📋 Tabel Data Lengkap")
        
        # Add search and sort options
        col_search, col_sort = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("🔍 Cari dalam tabel:", placeholder="Ketik untuk mencari...")
        with col_sort:
            sort_by = st.selectbox("Urutkan:", ["Waktu (Terbaru)", "Harga (Tertinggi)", "Harga (Terendah)"])
        
        # Apply search
        if search_term:
            mask = df_view.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            df_display = df_view[mask]
        else:
            df_display = df_view
        
        # Apply sorting
        if sort_by == "Waktu (Terbaru)":
            df_display = df_display.sort_values('Raw_Time', ascending=False)
        elif sort_by == "Harga (Tertinggi)":
            df_display = df_display.sort_values('Harga_Angka', ascending=False)
        else:
            df_display = df_display.sort_values('Harga_Angka', ascending=True)
        
        # Display table
        st.dataframe(
            df_display[['Komoditas', 'Harga', 'Lokasi', 'Sumber', 'Status', 'Waktu']],
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Download button
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data (CSV)",
            data=csv,
            file_name=f"mentawai_market_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
        
    else:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter. Silakan ubah pengaturan filter atau tambah data baru.")

# ============================================================================
# TAB 2: INPUT DATA LAPANGAN
# ============================================================================
with tab_input:
    st.markdown("""
    <div class="info-box">
        <strong>ℹ️ Panduan Input Data:</strong><br>
        Fitur ini digunakan oleh Petani, Pengepul, atau Petugas Dinas untuk melaporkan harga komoditas langsung dari lapangan.
        Data yang diinput akan langsung tampil di Dashboard Publik.
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("input_form", clear_on_submit=True):
        col_in1, col_in2 = st.columns(2)
        
        with col_in1:
            st.markdown("**📦 Informasi Komoditas**")
            in_komoditas = st.selectbox(
                "Jenis Komoditas *", 
                [
                    "Kopra Kering", "Cengkeh", "Pinang", "Gurita", "Kakao", 
                    "Lobster", "Nilam", "Rotan", "Sagu", "Kelapa Utuh",
                    "Ikan Tuna", "Vanili", "Pala", "Kayu Manis", "Lainnya"
                ]
            )
            
            in_harga = st.number_input(
                "Harga (Rupiah per Kg) *", 
                min_value=0, 
                step=500,
                help="Masukkan harga dalam Rupiah per kilogram"
            )
            
            in_sumber = st.selectbox(
                "Sumber Data *", 
                ["Petani", "Pengepul", "Dinas Pasar", "Pedagang", "Masyarakat"]
            )
        
        with col_in2:
            st.markdown("**📍 Informasi Lokasi**")
            in_kecamatan = st.selectbox(
                "Kecamatan *", 
                [
                    "Sikakap", "Pagai Utara", "Pagai Selatan", 
                    "Sipora Utara", "Sipora Selatan", 
                    "Siberut Selatan", "Siberut Barat", 
                    "Siberut Utara", "Siberut Tengah"
                ]
            )
            
            in_dusun = st.text_input(
                "Nama Desa/Dusun *", 
                placeholder="Contoh: Taileleu, Madobag, dll"
            )
            
            in_catatan = st.text_area(
                "Catatan Tambahan (Opsional)",
                placeholder="Kondisi cuaca, kualitas produk, dll",
                height=100
            )
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns([1, 3])
        
        with col_btn1:
            btn_kirim = st.form_submit_button(
                "🚀 KIRIM DATA", 
                type="primary", 
                use_container_width=True
            )
        
        with col_btn2:
            st.caption("*) Wajib diisi | Data akan langsung masuk ke sistem setelah dikirim")
        
        if btn_kirim:
            if in_harga > 0 and in_dusun.strip():
                lokasi_lengkap = f"{in_dusun.strip()}, {in_kecamatan}"
                
                try:
                    # Add to Firestore
                    doc_data = {
                        "komoditas": in_komoditas,
                        "harga_angka": in_harga,
                        "range_harga": format_rupiah(in_harga),
                        "waktu_ambil": datetime.datetime.now(),
                        "sumber": in_sumber,
                        "lokasi": lokasi_lengkap,
                        "status": "Verified",
                        "catatan": in_catatan if in_catatan else "-"
                    }
                    
                    db.collection("harga_realtime").add(doc_data)
                    
                    st.markdown(f"""
                    <div class="success-box">
                        <strong>✅ Data Berhasil Disimpan!</strong><br>
                        {in_komoditas} - {format_rupiah(in_harga)}<br>
                        Lokasi: {lokasi_lengkap}<br>
                        Waktu: {format_wib(datetime.datetime.now())}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.cache_data.clear()  # Clear cache to show new data
                    
                    st.info("💡 Silakan refresh halaman atau pindah ke Tab Dashboard untuk melihat data terbaru.")
                    
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan data: {e}")
            else:
                st.error("❌ Harga dan Nama Desa wajib diisi dengan benar!")

# ============================================================================
# TAB 3: ADMIN PANEL
# ============================================================================
with tab_admin:
    st.markdown("### ⚙️ Panel Administrasi Sistem")
    
    st.warning("🔐 **PERHATIAN**: Fitur ini hanya untuk Administrator Sistem!")
    
    col_admin1, col_admin2 = st.columns(2)
    
    with col_admin1:
        st.markdown("#### 🎲 Generate Sample Data")
        st.info("""
        Gunakan fitur ini untuk mengisi database dengan data dummy (simulasi) 
        agar dashboard terlihat lebih hidup. Cocok untuk testing dan demo.
        """)
        
        jumlah_data = st.number_input(
            "Jumlah Data yang akan digenerate:", 
            min_value=10, 
            max_value=500, 
            value=50,
            step=10
        )
        
        if st.button("🎲 GENERATE SAMPLE DATA", type="primary", use_container_width=True):
            with st.spinner("Sedang mengisi database dengan data dummy..."):
                try:
                    count = seed_dummy_data(jumlah_data)
                    st.success(f"✅ Berhasil menambahkan {count} data dummy ke database!")
                    st.cache_data.clear()
                    st.balloons()
                    st.info("💡 Refresh halaman atau pindah ke Tab Dashboard untuk melihat data baru.")
                except Exception as e:
                    st.error(f"❌ Gagal generate data: {e}")
    
    with col_admin2:
        st.markdown("#### 🗑️ Database Management")
        st.warning("""
        **DANGER ZONE**: Operasi di bawah ini bersifat permanen dan tidak dapat di-undo!
        """)
        
        st.markdown("**Statistik Database:**")
        if not df.empty:
            st.write(f"- Total Records: **{len(df)}**")
            st.write(f"- Komoditas Unik: **{df['Komoditas'].nunique()}**")
            st.write(f"- Lokasi Unik: **{df['Lokasi'].nunique()}**")
            st.write(f"- Rentang Waktu: **{df['Waktu'].min()} - {df['Waktu'].max()}**")
        else:
            st.write("Database kosong")
        
        st.markdown("---")
        
        # Clear old data
        days_to_keep = st.number_input(
            "Hapus data lebih lama dari (hari):", 
            min_value=7, 
            max_value=365, 
            value=90
        )
        
        if st.button("🧹 BERSIHKAN DATA LAMA", use_container_width=True):
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            with st.spinner("Menghapus data lama..."):
                try:
                    # Query old documents
                    old_docs = db.collection('harga_realtime').where(
                        'waktu_ambil', '<', cutoff
                    ).stream()
                    
                    deleted = 0
                    batch = db.batch()
                    
                    for doc in old_docs:
                        batch.delete(doc.reference)
                        deleted += 1
                        
                        if deleted % 500 == 0:
                            batch.commit()
                            batch = db.batch()
                    
                    batch.commit()
                    
                    st.success(f"✅ Berhasil menghapus {deleted} data lama")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Gagal menghapus data: {e}")
        
        st.markdown("---")
        
        # Clear all data (extreme caution)
        with st.expander("⚠️ HAPUS SEMUA DATA (DANGER)", expanded=False):
            st.error("**WARNING**: Ini akan menghapus SEMUA data di database!")
            
            confirm_text = st.text_input(
                "Ketik 'DELETE ALL' untuk konfirmasi:",
                type="password"
            )
            
            if st.button("💀 HAPUS SEMUA DATA SEKARANG", use_container_width=True):
                if confirm_text == "DELETE ALL":
                    with st.spinner("Menghapus seluruh database..."):
                        try:
                            all_docs = db.collection('harga_realtime').stream()
                            deleted = 0
                            batch = db.batch()
                            
                            for doc in all_docs:
                                batch.delete(doc.reference)
                                deleted += 1
                                
                                if deleted % 500 == 0:
                                    batch.commit()
                                    batch = db.batch()
                            
                            batch.commit()
                            
                            st.success(f"✅ Berhasil menghapus {deleted} data")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Gagal menghapus data: {e}")
                else:
                    st.error("❌ Konfirmasi salah! Ketik 'DELETE ALL' dengan benar.")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>Mentawai Market Intelligence System v2.0</strong></p>
    <p>Dikembangkan untuk Kabupaten Kepulauan Mentawai | 
    Data realtime dari lapangan untuk kebijakan yang lebih baik</p>
    <p style="font-size: 0.8rem;">
        🔗 Powered by Streamlit + Firebase Firestore | 
        📧 Support: dinas.pasar@mentawaikab.go.id
    </p>
</div>
""", unsafe_allow_html=True)
