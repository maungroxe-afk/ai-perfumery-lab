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

# --- 1. SPESIFIKASI ---
st.subheader("⚙️ 1. Spesifikasi Produk")
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume (ml)", value=100.0)

persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_g = (persen_konse / 100) * (target_total_ml * 0.85)
st.info(f"Target Konsentrat: {target_konsentrat_g:.2f}g")

# --- 2. FORMULA INPUT ---
st.subheader("📝 2. Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Jumlah", "Satuan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.TextColumn("Pilih Bahan / Ketik Manual"),
        "Satuan": st.column_config.SelectboxColumn("Satuan", options=["g", "ml"]),
        "Jumlah": st.column_config.NumberColumn("Jumlah", min_value=0.0, format="%.3f")
    }
)

# --- 3. ANALISA & PERSENTASE TERINTEGRASI ---
# Bersihkan data: paksa kolom 'Jumlah' jadi angka, ganti None jadi 0
df_calc = edited_df.dropna(subset=["Bahan (Notes)"]).copy()
df_calc["Jumlah"] = pd.to_numeric(df_calc["Jumlah"], errors='coerce').fillna(0)
df_calc["Satuan"] = df_calc["Satuan"].fillna("g")

# Konversi ke gram
df_calc["Berat_Gram"] = df_calc.apply(lambda x: x["Jumlah"] * 0.9 if x["Satuan"] == "ml" else x["Jumlah"], axis=1)
total_g = df_calc["Berat_Gram"].sum()

if total_g > 0:
    # Hitung Persentase
    df_calc["% dalam Formula"] = (df_calc["Berat_Gram"] / total_g) * 100
    
    st.subheader("📊 3. Analisa & Persentase")
    st.dataframe(df_calc[["Bahan (Notes)", "Jumlah", "Satuan", "Berat_Gram", "% dalam Formula"]], use_container_width=True, hide_index=True)
    
    # Progress Bar ke Target
    st.progress(min(total_g / target_konsentrat_g, 1.0), text=f"Progres Konsentrat: {total_g:.2f}g / {target_konsentrat_g:.2f}g")

# --- 4. AI ASSISTANT ---
st.subheader("🤖 4. AI Perfumer Assistant")
if st.button("Analisa dengan AI"):
    try:
        # Kirim data bersih ke AI
        prompt = f"Formula Konsentrat:\n{df_calc[['Bahan (Notes)', 'Berat_Gram', '% dalam Formula']].to_string()}\nTarget Konsentrasi: {konsentrasi_target}. Berikan analisis teknis."
        response = model.generate_content(prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"Error AI: {e}")
