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

# --- LANGKAH 1: PEMILIHAN KONSENTRASI ---
st.subheader("⚙️ 1. Tentukan Spesifikasi Produk")
col_a, col_b = st.columns(2)
with col_a:
    konsentrasi_target = st.selectbox(
        "Pilih Konsentrasi Parfum:",
        ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"]
    )
with col_b:
    target_total_berat = st.number_input("Total Berat Produk Jadi (gram)", value=100.0)

persen_konsentrasi = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat = (persen_konsentrasi / 100) * target_total_berat

st.info(f"Untuk target {konsentrasi_target} pada total {target_total_berat}g, Anda membutuhkan **{target_konsentrat:.2f}g konsentrat parfum**.")

st.divider()

# --- LANGKAH 2: FORMULA BUILDER ---
st.subheader("📝 2. Input Formula (Konsentrat)")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Berat (gram)"])

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
    st.divider()
    st.subheader("📊 3. Analisa & Kepatuhan")
    
    # Progress Bar
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
    analisa_df["% Dalam Konsentrat"] = (analisa_df["Berat (gram)"] / current_konsentrat) * 100
    analisa_df["Status"] = analisa_df.apply(lambda r: "✅ Aman" if r["% Dalam Konsentrat"] <= r["Batas Maksimal IFRA (%)"] else "❌ OVER LIMIT", axis=1)
    
    st.dataframe(analisa_df, use_container_width=True, hide_index=True)

# --- AI ASSISTANT ---
st.divider()
st.subheader("🤖 4. AI Perfumer Assistant")
user_prompt = st.text_input("Tanyakan saran atau minta AI menyeimbangkan formula:")

if st.button("Analisa dengan AI"):
    formula_text = edited_df.dropna(subset=["Bahan (Notes)"]).to_string(index=False)
    full_prompt = f"""
    Anda adalah master perfumer. User ingin membuat parfum dengan konsentrasi {konsentrasi_target}.
    Target konsentrat adalah {target_konsentrat}g. Saat ini sudah ada {current_konsentrat}g.
    
    Formula saat ini:
    {formula_text}
    
    Berikan rekomendasi bahan tambahan (notes) untuk mencapai target berat dan menyeimbangkan profil aroma 
    berdasarkan target konsentrasi tersebut.
    """
    response = model.generate_content(full_prompt)
    st.info(response.text)
