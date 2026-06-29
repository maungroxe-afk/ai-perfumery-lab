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
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- LANGKAH 1: SPESIFIKASI PRODUK (ml) ---
st.subheader("⚙️ 1. Tentukan Spesifikasi Produk")
col_a, col_b = st.columns(2)
with col_a:
    konsentrasi_target = st.selectbox(
        "Pilih Konsentrasi Parfum:",
        ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"]
    )
with col_b:
    target_total_ml = st.number_input("Total Volume Produk Jadi (ml)", value=100.0)

# Estimasi berat jenis parfum jadi sekitar 0.85 - 0.9 g/ml
target_total_gram = target_total_ml * 0.85 
persen_konsentrasi = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat = (persen_konsentrasi / 100) * target_total_gram

st.info(f"Untuk {target_total_ml}ml ({target_total_gram:.2f}g), target konsentrat Anda adalah **{target_konsentrat:.2f}g**.")

st.divider()

# --- LANGKAH 2: FORMULA BUILDER (Multi-Satuan) ---
st.subheader("📝 2. Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Jumlah", "Satuan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.SelectboxColumn("Pilih Bahan", options=list_bahan, width="large", required=True),
        "Satuan": st.column_config.SelectboxColumn("Satuan", options=["g", "ml"], required=True),
        "Jumlah": st.column_config.NumberColumn("Jumlah", min_value=0.0, format="%.3f")
    }
)

# --- ANALISA OTOMATIS & KONVERSI ---
# Mengonversi ml ke gram (asumsi berat jenis rata-rata 0.9)
def convert_to_gram(row):
    if row["Satuan"] == "ml":
        return row["Jumlah"] * 0.9
    return row["Jumlah"]

edited_df["Berat_Gram"] = edited_df.apply(convert_to_gram, axis=1)
current_konsentrat = edited_df["Berat_Gram"].sum()

if current_konsentrat > 0:
    st.divider()
    st.subheader("📊 3. Analisa & Kepatuhan")
    
    progress = min(current_konsentrat / target_konsentrat, 1.0)
    st.progress(progress, text=f"Progres Konsentrat: {current_konsentrat:.2f}g / {target_konsentrat:.2f}g")

    # Analisa IFRA
    analisa_df = edited_df.copy().dropna(subset=["Bahan (Notes)"])
    def get_info(nama):
        if not db.empty and nama in db["Bahan"].values:
            row = db[db["Bahan"] == nama].iloc[0]
            return row["Kategori"], row["IFRA_Max"]
        return "Custom/New", 100.0

    analisa_df[["Kategori", "Batas Maksimal IFRA (%)"]] = analisa_df["Bahan (Notes)"].apply(lambda x: pd.Series(get_info(x)))
    analisa_df["% Dalam Konsentrat"] = (analisa_df["Berat_Gram"] / current_konsentrat) * 100
    analisa_df["Status"] = analisa_df.apply(lambda r: "✅ Aman" if r["% Dalam Konsentrat"] <= r["Batas Maksimal IFRA (%)"] else "❌ OVER LIMIT", axis=1)
    
    st.dataframe(analisa_df[["Bahan (Notes)", "Kategori", "Jumlah", "Satuan", "Berat_Gram", "% Dalam Konsentrat", "Status"]], use_container_width=True, hide_index=True)

# --- AI ASSISTANT ---
st.divider()
st.subheader("🤖 4. AI Perfumer Assistant")
if st.button("Analisa dengan AI"):
    formula_text = edited_df.dropna(subset=["Bahan (Notes)"]).to_string(index=False)
    full_prompt = f"""
    Anda adalah master perfumer. User membuat parfum target konsentrasi {konsentrasi_target}.
    Total berat konsentrat saat ini: {current_konsentrat}g.
    
    Formula:
    {formula_text}
    
    Bantu saya menyeimbangkan aroma dan berikan saran jika ada bahan yang perlu disesuaikan.
    """
    response = model.generate_content(full_prompt)
    st.info(response.text)
