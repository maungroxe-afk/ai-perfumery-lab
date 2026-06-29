import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# Konfigurasi Halaman
st.set_page_config(page_title="AI Perfumery Lab", layout="wide")

st.title("🧪 AI Perfumery Lab: Project UCP ALPHA")

# --- LOAD DATA ---
@st.cache_data
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        return pd.read_csv("bahan_perfumery.csv")
    return pd.DataFrame(columns=["Bahan", "Kategori", "IFRA_Max"])

db = load_db()
list_bahan = db["Bahan"].tolist() if not db.empty else []

# --- CONFIG AI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Menggunakan daftar model untuk memastikan yang kita panggil tersedia
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.sidebar.error(f"Error Konfigurasi: {e}")

# --- LANGKAH 1: SPESIFIKASI PRODUK ---
st.subheader("⚙️ 1. Tentukan Spesifikasi Produk")
col_a, col_b = st.columns(2)
with col_a:
    konsentrasi_target = st.selectbox(
        "Pilih Konsentrasi Parfum:",
        ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"]
    )
with col_b:
    target_total_ml = st.number_input("Total Volume Produk Jadi (ml)", value=100.0)

target_total_gram = target_total_ml * 0.85 
persen_konsentrasi = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat = (persen_konsentrasi / 100) * target_total_gram

st.info(f"Target konsentrat: **{target_konsentrat:.2f}g** (untuk {target_total_ml}ml produk jadi).")

st.divider()

# --- LANGKAH 2: FORMULA BUILDER ---
st.subheader("📝 2. Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Jumlah", "Satuan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.SelectboxColumn("Pilih Bahan", options=list_bahan, width="large"),
        "Satuan": st.column_config.SelectboxColumn("Satuan", options=["g", "ml"]),
        "Jumlah": st.column_config.NumberColumn("Jumlah", min_value=0.0, format="%.3f")
    }
)

# --- ANALISA OTOMATIS & PERBAIKAN ERROR ---
# Bersihkan data: hapus baris yang tidak punya bahan, isi angka kosong dengan 0
df_clean = edited_df.dropna(subset=["Bahan (Notes)"]).copy()
df_clean["Jumlah"] = pd.to_numeric(df_clean["Jumlah"], errors='coerce').fillna(0)

# Fungsi konversi yang lebih aman
def convert_to_gram(row):
    val = row["Jumlah"]
    # Jika satuan ml, kali 0.9. Jika g, tetap.
    return val * 0.9 if row["Satuan"] == "ml" else val

if not df_clean.empty:
    df_clean["Berat_Gram"] = df_clean.apply(convert_to_gram, axis=1)
    current_konsentrat = df_clean["Berat_Gram"].sum()

    st.divider()
    st.subheader("📊 3. Analisa & Kepatuhan")
    
    progress = min(current_konsentrat / target_konsentrat, 1.0)
    st.progress(progress, text=f"Progres: {current_konsentrat:.2f}g / {target_konsentrat:.2f}g")

    # Analisa IFRA
    def get_info(nama):
        if not db.empty and nama in db["Bahan"].values:
            row = db[db["Bahan"] == nama].iloc[0]
            return row["Kategori"], row["IFRA_Max"]
        return "Custom/New", 100.0

    df_clean[["Kategori", "Batas Maksimal IFRA (%)"]] = df_clean["Bahan (Notes)"].apply(lambda x: pd.Series(get_info(x)))
    df_clean["% Dalam Konsentrat"] = (df_clean["Berat_Gram"] / current_konsentrat) * 100
    df_clean["Status"] = df_clean.apply(lambda r: "✅ Aman" if r["% Dalam Konsentrat"] <= r["Batas Maksimal IFRA (%)"] else "❌ OVER LIMIT", axis=1)
    
    st.dataframe(df_clean[["Bahan (Notes)", "Kategori", "Jumlah", "Satuan", "Berat_Gram", "% Dalam Konsentrat", "Status"]], use_container_width=True, hide_index=True)

# --- AI ASSISTANT ---
st.divider()
st.subheader("🤖 4. AI Perfumer Assistant")
if st.button("Analisa dengan AI"):
    try:
        # Menghapus kolom yang tidak perlu sebelum dikirim ke AI
        data_untuk_ai = df_clean.drop(columns=["Kategori", "Batas Maksimal IFRA (%)", "Status"], errors='ignore')
        formula_text = data_untuk_ai.to_string(index=False)
        
        full_prompt = f"""
        Anda adalah Master Perfumer. Berikut adalah data formula saya:
        {formula_text}
        
        Berikan saran profesional mengenai keseimbangan aroma dan kepatuhan IFRA jika ada bahan yang perlu diperhatikan.
        """
        
        # Panggil API
        response = model.generate_content(full_prompt)
        st.info(response.text)
        
    except Exception as e:
        st.error("Gagal menghubungi AI. Detail error:")
        st.code(str(e))
