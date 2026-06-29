import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px

st.set_page_config(page_title="AI Perfumery Lab Pro", layout="wide")
st.title("🧪 AI Perfumery Lab: Professional Edition")

# --- 1. SIDEBAR: API KEY INPUT ---
st.sidebar.header("⚙️ Konfigurasi")
api_key_input = st.sidebar.text_input("Masukkan Gemini API Key Anda:", type="password")

# --- 2. SETUP DATA ---
@st.cache_data(ttl=60)
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        df = pd.read_csv("bahan_perfumery.csv")
        required = ["Bahan", "Kategori_IFRA_4", "Aroma_Profile"]
        for col in required:
            if col not in df.columns:
                df[col] = 100.0 if col == "Kategori_IFRA_4" else "Unknown"
        return df
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4", "Aroma_Profile"])

db = load_db()
list_bahan = db["Bahan"].unique().tolist()

# --- 3. INISIALISASI AI ---
model = None
if api_key_input:
    try:
        genai.configure(api_key=api_key_input)
        model = genai.GenerativeModel('gemini-1.0-pro')
    except Exception as e:
        st.sidebar.error(f"API Key tidak valid: {e}")
else:
    st.sidebar.warning("Silakan masukkan API Key di kolom atas untuk mengaktifkan fitur AI.")

# --- 4. INPUT TARGET ---
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk Jadi (ml)", value=100.0)

persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_ml = (persen_konse / 100) * target_total_ml
total_berat_produk_g = target_total_ml * 0.85 

# --- 5. INPUT FORMULA (HYBRID) ---
st.subheader("📝 Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.SelectboxColumn("Bahan", options=list_bahan, width="large"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)

# --- 6. LOGIKA KALKULASI & ANALISA ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()

if not df_calc.empty:
    df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
    df_merged = pd.merge(df_calc, db, on="Bahan", how="left").fillna({
        "Kategori_IFRA_4": 100.0, 
        "Aroma_Profile": "Unknown"
    })

    df_merged["Volume_Internal_ML"] = (df_merged["Persentase (%)"] / 100) * target_konsentrat_ml
    df_merged["Berat_Aktual_g"] = df_merged["Volume_Internal_ML"] * 0.9
    df_merged["Persen_Produk_Akhir"] = (df_merged["Berat_Aktual_g"] / total_berat_produk_g) * 100
    df_merged["Status"] = df_merged.apply(lambda r: "✅ Aman" if r["Persen_Produk_Akhir"] <= r["Kategori_IFRA_4"] else "❌ OVER LIMIT", axis=1)

    st.subheader("📊 Hasil Analisa")
    st.dataframe(df_merged[["Bahan", "Aroma_Profile", "Persentase (%)", "Status"]], use_container_width=True)

    fig = px.pie(df_merged, values="Persentase (%)", names="Aroma_Profile", title="Proporsi Aroma")
    st.plotly_chart(fig)

    # --- 7. AUDIT AI ---
    if model and st.button("Analisa & Optimasi Formula oleh AI"):
        with st.spinner("AI sedang memeriksa formula..."):
            prompt = f"Sebagai Master Perfumer, analisa formula ini: {df_merged[['Bahan', 'Persentase (%)', 'Status']].to_string()}. Berikan saran penyesuaian aroma dan kepatuhan IFRA."
            try:
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Error AI: {e}")
