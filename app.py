import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

st.set_page_config(page_title="AI Perfumery Lab Pro", layout="wide")
st.title("🧪 AI Perfumery Lab: Regulatory Compliance Edition")

# --- 1. SETUP ---
@st.cache_data
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        return pd.read_csv("bahan_perfumery.csv")
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4"])

db = load_db()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- 2. INPUT FORMULA ---
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk Jadi (ml)", value=100.0)

st.subheader("📝 Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(st.session_state.formula_df, num_rows="dynamic", use_container_width=True)

# --- 3. ANALISIS & VERIFIKASI AI ---
if st.button("Verifikasi Kepatuhan IFRA dengan AI"):
    df_calc = edited_df.dropna(subset=["Bahan"]).copy()
    
    # Menyiapkan data untuk dikirim ke AI
    formula_to_analyze = df_calc.to_string()
    
    with st.spinner("AI sedang melakukan audit regulasi terhadap formula Anda..."):
        prompt = f"""
        Anda adalah seorang ahli regulasi wewangian (Fragrance Regulatory Expert) yang sangat teliti.
        Tugas Anda adalah melakukan audit kepatuhan terhadap formula berikut:
        
        {formula_to_analyze}
        
        Target Produk: {konsentrasi_target} (Total volume {target_total_ml}ml).
        
        Lakukan langkah-langkah berikut:
        1. Analisis persentase bahan di produk akhir (Finished Product) dan bandingkan dengan standar IFRA Amendment 51 (Kategori 4).
        2. Berikan daftar bahan yang melanggar batas IFRA.
        3. Identifikasi adanya risiko akumulasi alergen (seperti Linalool, Limonene, dll).
        4. Berikan saran formula agar parfum ini tetap aman secara hukum namun aromanya tidak berubah drastis.
        
        Berikan jawaban dalam format tabel dan poin-poin penjelasan yang profesional.
        """
        
        try:
            response = model.generate_content(prompt)
            st.markdown("### 🛡️ Laporan Audit Kepatuhan AI")
            st.info(response.text)
        except Exception as e:
            st.error(f"Gagal menghubungi AI: {e}")

# --- 4. DATA DISPLAY ---
st.subheader("📊 Preview Formula")
st.dataframe(edited_df, use_container_width=True)
