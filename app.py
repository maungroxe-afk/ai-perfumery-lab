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
    else:
        # Data kosong jika file belum ada
        return pd.DataFrame(columns=["Bahan", "Kategori", "IFRA_Max"])

db = load_db()
list_bahan = db["Bahan"].tolist() if not db.empty else []

# --- CONFIG AI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- FORMULA BUILDER ---
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan (Notes)", "Berat (gram)"])

st.subheader("📝 Input Formula")
edited_df = st.data_editor(
    st.session_state.formula_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Bahan (Notes)": st.column_config.SelectboxColumn(
            "Pilih Bahan",
            options=list_bahan,
            width="large",
            required=True,
        ),
        "Berat (gram)": st.column_config.NumberColumn(
            "Berat (gram)",
            min_value=0.0,
            format="%.3f"
        )
    }
)

# --- ANALISA OTOMATIS ---
# Memastikan kolom numerik agar tidak error
edited_df["Berat (gram)"] = pd.to_numeric(edited_df["Berat (gram)"], errors='coerce').fillna(0)

if not edited_df.empty and edited_df["Berat (gram)"].sum() > 0:
    analisa_df = edited_df.copy().dropna(subset=["Bahan (Notes)"])
    total_berat = analisa_df["Berat (gram)"].sum()
    
    def get_info(nama):
        if not db.empty and nama in db["Bahan"].values:
            row = db[db["Bahan"] == nama].iloc[0]
            return row["Kategori"], row["IFRA_Max"]
        return "Custom/New", 100.0

    # Mapping Data
    analisa_df[["Kategori", "Batas Maksimal IFRA (%)"]] = analisa_df["Bahan (Notes)"].apply(
        lambda x: pd.Series(get_info(x))
    )
    analisa_df["% Dalam Formula"] = (analisa_df["Berat (gram)"] / total_berat) * 100
    analisa_df["Status"] = analisa_df.apply(
        lambda r: "✅ Aman" if r["% Dalam Formula"] <= r["Batas Maksimal IFRA (%)"] else "❌ OVER LIMIT", axis=1
    )

    st.subheader("📊 Analisa Formula")
    st.dataframe(analisa_df, use_container_width=True, hide_index=True)
    
    if "❌ OVER LIMIT" in analisa_df["Status"].values:
        st.error("⚠️ Peringatan: Batas IFRA terlampaui!")

# --- AI ASSISTANT ---
st.subheader("🤖 AI Perfumer Assistant")
user_prompt = st.text_input("Tanyakan AI tentang formula Anda:")

if st.button("Analisa dengan AI"):
    formula_text = edited_df.dropna(subset=["Bahan (Notes)"]).to_string(index=False)
    full_prompt = f"""
    Anda adalah master perfumer. Berikut formula konsentrat parfum saya:
    {formula_text}
    
    Jika ada bahan 'Custom/New', mohon berikan edukasi mengenai bahan tersebut, 
    prediksi profil aromanya, dan estimasi batas aman penggunaannya.
    
    Pertanyaan: {user_prompt}
    """
    response = model.generate_content(full_prompt)
    st.info(response.text)
