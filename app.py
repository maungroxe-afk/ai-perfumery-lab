import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

st.set_page_config(page_title="AI Perfumery Lab Pro", layout="wide")
st.title("🧪 AI Perfumery Lab: Regulatory Compliance Edition")

# --- 1. SETUP DATA & AI ---
@st.cache_data
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        return pd.read_csv("bahan_perfumery.csv")
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4"])

db = load_db()
list_bahan = db["Bahan"].unique().tolist() if not db.empty else []

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- 2. INPUT TARGET ---
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk Jadi (ml)", value=100.0)

persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_ml = (persen_konse / 100) * target_total_ml
st.info(f"Target Konsentrat: **{target_konsentrat_ml:.2f} ML**")

# --- 3. INPUT FORMULA (HYBRID) ---
st.subheader("📝 Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.SelectboxColumn("Bahan (Pilih atau Ketik)", options=list_bahan, width="large"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)

# --- 4. ANALISIS IFRA & KALKULASI ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()
if not df_calc.empty:
    df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
    
    # Kalkulasi Volume (ML)
    df_calc["Volume Internal (ML)"] = (df_calc["Persentase (%)"] / 100) * target_konsentrat_ml
    
    # Kalkulasi Timbangan (g) jika dipilih gram
    df_calc["Jumlah Dibutuhkan"] = df_calc.apply(lambda r: r["Volume Internal (ML)"] * 0.9 if r["Satuan Timbangan"] == "g" else r["Volume Internal (ML)"], axis=1)

    # Cek IFRA dari Database
    def get_ifra(nama):
        match = db[db["Bahan"].str.lower() == str(nama).lower()]
        return match.iloc[0]["Kategori_IFRA_4"] if not match.empty else 100.0

    df_calc["Batas IFRA 4 (%)"] = df_calc["Bahan"].apply(get_ifra)
    df_calc["Status IFRA"] = df_calc.apply(lambda r: "✅ Aman" if r["Persentase (%)"] <= r["Batas IFRA 4 (%)"] else "❌ OVER LIMIT", axis=1)

    st.subheader("📊 Hasil Kalkulasi & Kepatuhan")
    st.dataframe(df_calc[["Bahan", "Persentase (%)", "Batas IFRA 4 (%)", "Jumlah Dibutuhkan", "Satuan Timbangan", "Status IFRA"]], use_container_width=True)

# --- 5. VERIFIKASI AI ---
if st.button("Audit Regulasi dengan AI"):
    with st.spinner("AI sedang melakukan audit regulasi..."):
        prompt = f"""
        Anda adalah Fragrance Regulatory Expert. Audit formula berikut terhadap IFRA Amendment 51 (Kategori 4):
        {df_calc.to_string()}
        
        Target: {konsentrasi_target} ({target_total_ml}ml).
        Identifikasi pelanggaran batas IFRA, risiko alergen, dan berikan saran perbaikan formula.
        """
        try:
            response = model.generate_content(prompt)
            st.markdown("### 🛡️ Laporan Audit Kepatuhan AI")
            st.info(response.text)
        except Exception as e:
            st.error(f"Gagal menghubungi AI: {e}")
