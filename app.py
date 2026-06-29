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

# --- FITUR KONSENTRASI ---
st.sidebar.header("⚖️ Target Produksi")
target_total_berat = st.sidebar.number_input("Total Berat Parfum (gram)", value=100.0)
konsentrasi_target = st.sidebar.selectbox(
    "Pilih Konsentrasi Parfum:",
    ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"]
)

# Ekstrak nilai persen dari string
persen_konsentrasi = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat = (persen_konsentrasi / 100) * target_total_berat
target_alkohol = target_total_berat - target_konsentrat

st.sidebar.info(f"Target Konsentrat: {target_konsentrat:.2f}g | Alkohol/Solvent: {target_alkohol:.2f}g")

# --- FORMULA BUILDER ---
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Berat (gram)"])

st.subheader("📝 Input Formula (Konsentrat)")
edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.SelectboxColumn("Pilih Bahan", options=list_bahan, width="large", required=True),
        "Berat (gram)": st.column_config.NumberColumn("Berat (gram)", min_value=0.0, format="%.3f")
    }
)

# --- ANALISA & REKOMENDASI ---
edited_df["Berat (gram)"] = pd.to_numeric(edited_df["Berat (gram)"], errors='coerce').fillna(0)
current_konsentrat = edited_df["Berat (gram)"].sum()

if current_konsentrat > 0:
    st.subheader("📊 Analisa & Kalkulasi")
    
    # Menghitung sisa/kurang berat ke target
    selisih = target_konsentrat - current_konsentrat
    if selisih > 0:
        st.warning(f"Anda masih membutuhkan {selisih:.2f}g lagi untuk mencapai target konsentrasi {konsentrasi_target}.")
    else:
        st.success("Target konsentrasi telah tercapai.")

    # Analisa IFRA
    analisa_df = edited_df.copy().dropna(subset=["Bahan (Notes)"])
    def get_info(nama):
        if not db.empty and nama in db["Bahan"].values:
            row = db[db["Bahan"] == nama].iloc[0]
            return row["Kategori"], row["IFRA_Max"]
        return "Custom/New", 100.0

    analisa_df[["Kategori", "Batas Maksimal IFRA (%)"]] = analisa_df["Bahan (Notes)"].apply(lambda x: pd.Series(get_info(x)))
    analisa_df["% Dalam Konsentrat"] = (analisa_df["Berat (gram)"] / current_konsentrat) * 100
    st.dataframe(analisa_df, use_container_width=True, hide_index=True)

# --- AI ASSISTANT ---
st.subheader("🤖 AI Perfumer Assistant")
user_prompt = st.text_input("Tanyakan saran formulasi:")

if st.button("Dapatkan Rekomendasi AI"):
    formula_text = edited_df.to_string(index=False)
    full_prompt = f"""
    Anda adalah master perfumer. User ingin membuat parfum dengan konsentrasi {konsentrasi_target}.
    Total berat konsentrat saat ini: {current_konsentrat}g dari target {target_konsentrat}g.
    
    Formula saat ini:
    {formula_text}
    
    Berikan rekomendasi bahan tambahan (notes) untuk mencapai target berat dan menyeimbangkan profil aroma 
    berdasarkan target konsentrasi tersebut.
    """
    response = model.generate_content(full_prompt)
    st.info(response.text)
