import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

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
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- 1. SPESIFIKASI PRODUK ---
st.subheader("⚙️ 1. Tentukan Target")
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk (ml)", value=100.0)

target_total_g = target_total_ml * 0.85 
persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_g = (persen_konse / 100) * target_total_g
st.info(f"Target Total Konsentrat: **{target_konsentrat_g:.2f}g**")

# --- 2. FORMULA INPUT ---
st.subheader("📝 2. Input Formula (Persentase atau Gram/ML)")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Jumlah", "Satuan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.TextColumn("Bahan (Manual/Daftar)"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Jumlah": st.column_config.NumberColumn("Jumlah (Hasil Hitung)", format="%.3f", disabled=True),
        "Satuan": st.column_config.SelectboxColumn("Satuan", options=["g", "ml"])
    }
)

# --- 3. LOGIKA KALKULASI OTOMATIS ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()
df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
df_calc["Satuan"] = df_calc["Satuan"].fillna("g")

# Hitung jumlah berdasarkan persentase dari target konsentrat
# Jika satuan ml, bagi hasil gram dengan 0.9 (berat jenis)
def hitung_jumlah(row):
    gram = (row["Persentase (%)"] / 100) * target_konsentrat_g
    if row["Satuan"] == "ml":
        return gram / 0.9
    return gram

df_calc["Jumlah"] = df_calc.apply(hitung_jumlah, axis=1)

# --- 4. TAMPILAN ANALISA ---
if not df_calc.empty:
    st.divider()
    st.subheader("📊 3. Hasil Kalkulasi Racikan")
    st.dataframe(df_calc, use_container_width=True, hide_index=True)
    
    total_persen = df_calc["Persentase (%)"].sum()
    st.metric("Total Persentase Bahan", f"{total_persen:.2f}%", delta=f"{100 - total_persen:.2f}% sisa" if total_persen < 100 else "Over 100%")

# --- 5. AI ASSISTANT ---
st.subheader("🤖 4. AI Perfumer Assistant")
if st.button("Analisa Formula"):
    try:
        prompt = f"Formula Konsentrat: {df_calc.to_string()}. Target Konsentrasi: {konsentrasi_target}. Analisa profil aroma ini."
        response = model.generate_content(prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"Error AI: {e}")
