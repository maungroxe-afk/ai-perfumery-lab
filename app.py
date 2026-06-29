import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px

st.set_page_config(page_title="AI Perfumery Lab Pro", layout="wide")
st.title("🧪 AI Perfumery Lab: Professional Edition")

# --- KONFIGURASI ---
st.sidebar.header("⚙️ Konfigurasi")
api_key_input = st.sidebar.text_input("Masukkan Gemini API Key Anda:", type="password")

@st.cache_data(ttl=60)
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        df = pd.read_csv("bahan_perfumery.csv")
        # Proteksi kolom agar tidak error
        for col in ["Kategori_IFRA_4", "Aroma_Profile"]:
            if col not in df.columns: df[col] = "Unknown" if col == "Aroma_Profile" else 100.0
        return df
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4", "Aroma_Profile"])

db = load_db()
list_bahan = db["Bahan"].unique().tolist()

# Inisialisasi Model AI yang lebih stabil
model = None
if api_key_input:
    genai.configure(api_key=api_key_input)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- INPUT & LOGIKA ---
col1, col2 = st.columns(2)
target_total_ml = col2.number_input("Total Volume (ml)", value=100.0)
edited_df = st.data_editor(st.session_state.get("formula_df", pd.DataFrame(columns=["Bahan", "Persentase (%)"])), num_rows="dynamic")

if not edited_df.dropna(subset=["Bahan"]).empty:
    df_calc = edited_df.dropna(subset=["Bahan"]).copy()
    df_merged = pd.merge(df_calc, db, on="Bahan", how="left").fillna({"Kategori_IFRA_4": 100.0, "Aroma_Profile": "Unknown"})
    
    st.dataframe(df_merged)
    
    if st.button("Analisa & Optimasi Formula oleh AI"):
        if model:
            prompt = f"Analisa formula parfum ini: {df_merged.to_string()}"
            try:
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Masukkan API Key di sidebar terlebih dahulu!")
