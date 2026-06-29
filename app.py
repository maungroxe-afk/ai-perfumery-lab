import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- UPDATE PROMPT AI ---
full_prompt = f"""
Anda adalah seorang Master Perfumer profesional. Berikut adalah formula konsentrat parfum:
{formula_text}

CATATAN: Jika Anda melihat bahan dengan Kategori 'Custom/New', mohon berikan edukasi mengenai bahan tersebut, 
prediksi profil aromanya, dan estimasi batas aman penggunaannya berdasarkan pengetahuan kimia Anda.

Pertanyaan: {user_prompt}
"""

# --- MODIFIKASI BAGIAN KALKULASI DI APP.PY ---

def get_bahan_info_safe(nama_bahan, db):
    # Cek apakah bahan ada di database
    if nama_bahan in db["Bahan"].values:
        info = db[db["Bahan"] == nama_bahan].iloc[0]
        return info["Kategori"], info["IFRA_Max"]
    else:
        # Jika tidak ada, kembalikan nilai default (100% agar tidak langsung error)
        # Atau bisa diset ke None untuk ditandai sebagai 'Perlu Analisa AI'
        return "Unknown", 100.0 

# Di dalam bagian tabel analisa:
def process_formula(edited_df, db):
    analisa_df = edited_df.copy()
    
    # Fungsi untuk mendapatkan info
    def fetch_data(nama):
        if nama in db["Bahan"].values:
            row = db[db["Bahan"] == nama].iloc[0]
            return pd.Series([row["Kategori"], row["IFRA_Max"]])
        else:
            return pd.Series(["Custom/New", 100.0])

    analisa_df[["Kategori", "Batas Maksimal IFRA (%)"]] = analisa_df["Bahan (Notes)"].apply(fetch_data)
    
    # Kalkulasi sisa... (seperti kode sebelumnya)
    return analisa_df
    
# 1. Membaca Database dari CSV
@st.cache_data
def load_data():
    # Pastikan file bahan_perfumery.csv sudah ada di folder yang sama
    df = pd.read_csv("bahan_perfumery.csv")
    return df

db = load_data()
list_bahan = db["Bahan"].tolist()

# 2. Fungsi untuk mengambil data IFRA secara otomatis
def get_bahan_info(nama_bahan):
    info = db[db["Bahan"] == nama_bahan].iloc[0]
    return info["Kategori"], info["IFRA_Max"]

# (Sisanya di bagian input tabel, gunakan kode ini)
"Bahan (Notes)": st.column_config.SelectboxColumn(
    "Pilih Bahan",
    options=list_bahan, # Ini akan menampilkan 500+ pilihan
    required=True,
),
# Konfigurasi Halaman
st.set_page_config(page_title="AI Perfumery Lab", layout="wide")

st.title("🧪 AI Perfumery Lab: Project UCP ALPHA")
st.markdown("Manajemen Formula dan Auto-Kalkulasi IFRA")

# --- MENGAMBIL API KEY (Pastikan sudah di-set di Streamlit Secrets) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    api_key = None
    st.sidebar.warning("⚠️ API Key belum dikonfigurasi di Streamlit Secrets.")

# --- DATABASE BAHAN (INTERNAL DATABASE) ---
# Ini adalah simulasi database. Anda bisa menambahkan bahan baru ke dalam daftar ini kapan saja.
database_bahan = {
    "Ambroxan": {"Kategori": "Base", "IFRA_Max": 100.0},
    "Cashmeran": {"Kategori": "Base", "IFRA_Max": 0.43},
    "Iso E Super": {"Kategori": "Heart", "IFRA_Max": 21.4},
    "Vanilla Absolute": {"Kategori": "Base", "IFRA_Max": 100.0},
    "Bergamot EO (Cold Pressed)": {"Kategori": "Top", "IFRA_Max": 0.4},
    "Bergamot EO (FCF - Aman Sinar Matahari)": {"Kategori": "Top", "IFRA_Max": 100.0},
    "Oakmoss Absolute": {"Kategori": "Base", "IFRA_Max": 0.1},
    "Coumarin": {"Kategori": "Base", "IFRA_Max": 1.5},
    "Linalool": {"Kategori": "Heart", "IFRA_Max": 100.0},
    "Galaxolide": {"Kategori": "Base", "IFRA_Max": 100.0},
    "Hedione": {"Kategori": "Heart", "IFRA_Max": 100.0},
    "Patchouli EO": {"Kategori": "Base", "IFRA_Max": 100.0},
    "Rose Absolute": {"Kategori": "Heart", "IFRA_Max": 0.2}, 
    "Citronellol": {"Kategori": "Heart", "IFRA_Max": 1.2},
    "Eugenol": {"Kategori": "Heart", "IFRA_Max": 0.5},
}

# Mengekstrak hanya nama bahan untuk dimasukkan ke opsi Dropdown
pilihan_bahan = list(database_bahan.keys())

# --- INISIALISASI TABEL KOSONG ---
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Berat (gram)"])

# --- BAGIAN 1: BUILDER FORMULA (INPUT PENGGUNA) ---
st.subheader("📝 Input Formula")
st.markdown("Klik tombol **+ Add Row** di bawah tabel. Pilih bahan dari *dropdown*, dan masukkan beratnya. Kalkulasi batas IFRA akan muncul otomatis di tabel analisa.")

# Tabel Editor (Hanya Input Bahan & Berat)
edited_df = st.data_editor(
    st.session_state.formula_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.SelectboxColumn(
            "Pilih Bahan (Dropdown)",
            help="Pilih bahan dari database internal",
            width="large",
            options=pilihan_bahan,
            required=True,
        ),
        "Berat (gram)": st.column_config.NumberColumn(
            "Berat (gram)",
            min_value=0.0,
            format="%.3f",
            required=True,
            default=0.0
        )
    }
)

# Simpan state saat ada perubahan baris
st.session_state.formula_df = edited_df

st.divider()

# --- BAGIAN 2: KALKULASI & PENGECEKAN IFRA OTOMATIS ---
st.subheader("📊 Analisa Formula & Kepatuhan IFRA")

# Hanya jalankan kalkulasi jika tabel tidak kosong dan ada berat yang dimasukkan
if not edited_df.empty and edited_df["Berat (gram)"].sum() > 0:
    # Buat salinan data agar tidak merusak tabel input
    analisa_df = edited_df.copy()
    
    # Bersihkan data: Hapus baris kosong atau yang beratnya masih 0
    analisa_df = analisa_df.dropna(subset=["Bahan (Notes)"])
    analisa_df = analisa_df[analisa_df["Berat (gram)"] > 0]
    
    if not analisa_df.empty:
        total_berat = analisa_df["Berat (gram)"].sum()
        
        # AUTO-FILL: Menarik data Kategori dan IFRA dari database_bahan
        analisa_df["Kategori"] = analisa_df["Bahan (Notes)"].map(lambda x: database_bahan[x]["Kategori"])
        analisa_df["Batas Maksimal IFRA (%)"] = analisa_df["Bahan (Notes)"].map(lambda x: database_bahan[x]["IFRA_Max"])
        
        # Kalkulasi persentase dalam komposisi
        analisa_df["% Dalam Formula"] = (analisa_df["Berat (gram)"] / total_berat) * 100
        
        # Cek Kepatuhan
        analisa_df["Status"] = analisa_df.apply(
            lambda row: "✅ Aman" if row["% Dalam Formula"] <= row["Batas Maksimal IFRA (%)"] 
            else "❌ MELAMPAUI BATAS", axis=1
        )
        
        # Merapikan urutan kolom tabel hasil analisa
        analisa_df = analisa_df[["Bahan (Notes)", "Kategori", "Berat (gram)", "% Dalam Formula", "Batas Maksimal IFRA (%)", "Status"]]
        
        # Tampilkan Tabel Hasil (Read-only)
        st.dataframe(analisa_df, use_container_width=True, hide_index=True)
        
        # Tampilkan Status Akhir
        st.metric("Total Berat Konsentrat", f"{total_berat:.3f} g")

        if "❌ MELAMPAUI BATAS" in analisa_df["Status"].values:
            st.error("⚠️ PERINGATAN: Terdapat komposisi yang melampaui batas aman IFRA. Kurangi takaran bahan yang bermasalah.")
        else:
            st.success("✅ Seluruh komposisi berada di dalam batas aman regulasi IFRA.")
else:
    st.info("Tabel analisa akan muncul di sini setelah Anda memilih bahan dan mengisi berat di tabel input di atas.")

st.divider()

# --- BAGIAN 3: ASISTEN AI ---
st.subheader("🤖 AI Perfumer Assistant")
user_prompt = st.text_input("Tanyakan AI tentang racikan di atas (contoh: 'Apakah racikan ini cocok untuk parfum musim panas?'):")

if st.button("Analisa dengan AI"):
    if not api_key:
        st.warning("API Key belum dikonfigurasi. Cek menu rahasia Streamlit Secrets Anda.")
    elif edited_df.empty or edited_df["Berat (gram)"].sum() == 0:
        st.warning("Formula masih kosong, masukkan minimal satu bahan.")
    else:
        with st.spinner("Menganalisa komposisi..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Mengirimkan data formula ke AI tanpa mengirimkan baris yang kosong
                data_bersih = edited_df.dropna(subset=["Bahan (Notes)"])
                data_bersih = data_bersih[data_bersih["Berat (gram)"] > 0]
                formula_text = data_bersih.to_string(index=False)
                
                full_prompt = f"""
                Anda adalah seorang Master Perfumer profesional. Berikut adalah formula konsentrat parfum:
                {formula_text}
                
                Pertanyaan: {user_prompt}
                
                Jawab dengan terminologi perfumery yang profesional dan aplikatif.
                """
                
                response = model.generate_content(full_prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Error AI: {e}")
