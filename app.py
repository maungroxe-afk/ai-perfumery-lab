import streamlit as st
import pandas as pd
import json
from google import genai
import plotly.express as px

# Konfigurasi halaman dasar
st.set_page_config(page_title="Perfumer Studio Pro", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .note-box { padding: 18px 24px; border-radius: 6px; border-left: 3px solid #d4af37; background-color: #1a1c23; margin-bottom: 12px; }
    .note-title { font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #d4af37; margin-bottom: 6px; }
    .note-content { font-size: 0.95rem; color: #e4e4e7; line-height: 1.5; }
    </style>
""", unsafe_allow_html=True)

st.title("Perfumer Studio Pro")

# --- SIDEBAR: KONFIGURASI API ---
st.sidebar.header("Konfigurasi API")
api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("Google Gemini API Key", type="password")

# --- FUNGSI AI ---
@st.cache_data
def get_ai_complex_accords(materials_list, api_key_input):
    if not api_key_input or not materials_list: return {}
    try:
        client = genai.Client(api_key=api_key_input)
        prompt = f"Kelompokkan bahan ini ke dalam kategori aroma (Citrus, Floral, Woody, dll): {', '.join(materials_list)}. Output JSON saja: {{\"Material\": [\"Kategori\"]}}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except: return {}

@st.cache_data
def check_ifra_compliance(materials_list, api_key_input):
    if not api_key_input or not materials_list: return "API Key diperlukan."
    try:
        client = genai.Client(api_key=api_key_input)
        prompt = f"Analisis bahan berikut terhadap standar IFRA terbaru: {', '.join(materials_list)}. Berikan tabel: Bahan | Status | Kategori 4 | Batasan % | Referensi."
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

# --- INPUT DATA ---
df_template = pd.DataFrame({
    "Nama Raw Material": ["Ambroxan", "Bergamot Oil", "Jasmine Absolute"],
    "Kategori Notes (Manual/Bebas)": ["Base Notes", "Top Notes", "Heart Notes"],
    "Volume Dibeli (ml)": [10.0, 50.0, 50.0],
    "Harga Beli (Rp)": [300000, 150000, 250000],
    "Rasio Racikan (%)": [5.0, 10.0, 10.0]
})

st.subheader("Matriks Formulasi")
edited_df = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)
edited_df["Modal per ml (Rp)"] = edited_df["Harga Beli (Rp)"] / edited_df["Volume Dibeli (ml)"]

# --- TABS ---
tab_chat, tab_enc, tab_ifra, tab_sec, tab0, tab1 = st.tabs([
    "Asisten Copilot", "Analisis Accords", "Kepatuhan IFRA", "Ensiklopedia Bahan", "Riset Harga", "Akuntansi"
])

active_materials = edited_df[edited_df["Rasio Racikan (%)"] > 0]["Nama Raw Material"].tolist()

with tab_chat:
    st.header("Fragrance Copilot")
    # Logika Piramida dan Chat bot sama seperti sebelumnya...

with tab_ifra:
    st.header("Verifikasi Kepatuhan IFRA")
    if st.button("Jalankan Pengecekan Kepatuhan"):
        with st.spinner("Menganalisis standar regulasi..."):
            st.markdown(check_ifra_compliance(active_materials, api_key))
    st.info("Catatan: Selalu verifikasi kembali dengan dokumen IFRA resmi.")

with tab_enc:
    st.header("Analisis Kluster Roda Aroma")
    # Logika Plotly Chart sama seperti sebelumnya...

with tab_sec:
    st.header("Ensiklopedia & Regulasi")
    # Logika Ensiklopedia...

with tab0:
    st.header("Analisis Pasar")
    # Logika Riset Harga...

with tab1:
    st.header("Akuntansi Produksi")
    # Logika Keuangan...
