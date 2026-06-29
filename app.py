import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px

st.set_page_config(page_title="AI Perfumery Lab", layout="wide")
st.title("🧪 AI Perfumery Lab: Final Production Build")

# --- 1. SETUP DATA & AI ---
@st.cache_data(ttl=60)
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        df = pd.read_csv("bahan_perfumery.csv")
        return df.fillna({"Kategori_IFRA_4": 100.0, "Aroma_Profile": "Unknown"})
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4", "Aroma_Profile"])

db = load_db()
list_bahan = db["Bahan"].unique().tolist()

# Inisialisasi AI dari Secrets
try:
    # Mengambil kunci dari Streamlit Secrets
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("API Key tidak ditemukan di Streamlit Secrets. Pastikan sudah diset!")
    model = None

# --- 2. INPUT TARGET ---
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume (ml)", value=100.0)

# --- 3. INPUT FORMULA ---
st.subheader("📝 Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.SelectboxColumn("Bahan", options=list_bahan, width="large"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)

# --- 4. ANALISIS ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()
if not df_calc.empty:
    df_merged = pd.merge(df_calc, db, on="Bahan", how="left").fillna({"Kategori_IFRA_4": 100.0, "Aroma_Profile": "Unknown"})
    
    st.subheader("📊 Hasil Analisa")
    st.dataframe(df_merged[["Bahan", "Aroma_Profile", "Persentase (%)"]], use_container_width=True)
    
    st.plotly_chart(px.pie(df_merged, values="Persentase (%)", names="Aroma_Profile", title="Proporsi Aroma"))

    # --- 5. AUDIT AI ---
    if model and st.button("Analisa & Optimasi Formula oleh AI"):
        with st.spinner("AI sedang memeriksa formula..."):
            prompt = f"Sebagai Master Perfumer, analisa formula ini: {df_merged.to_string()}. Berikan saran optimasi aroma."
            try:
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Error AI: {e}")
