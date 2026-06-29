import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px

# Konfigurasi Halaman
st.set_page_config(page_title="AI Perfumery Lab Pro", layout="wide")
st.title("🧪 AI Perfumery Lab: Final Professional Edition")

# --- 1. FUNGSI DATABASE (DENGAN PROTEKSI CACHE) ---
@st.cache_data(ttl=60) # ttl=60 memaksa sistem cek ulang file tiap 60 detik
def load_db():
    if os.path.exists("bahan_perfumery.csv"):
        df = pd.read_csv("bahan_perfumery.csv")
        # Pastikan kolom standar ada
        required_cols = ["Bahan", "Kategori_IFRA_4", "Aroma_Profile"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = "Unknown" if col != "Kategori_IFRA_4" else 100.0
        return df
    return pd.DataFrame(columns=["Bahan", "Kategori_IFRA_4", "Aroma_Profile"])

db = load_db()
list_bahan = db["Bahan"].unique().tolist() if not db.empty else []

# --- 2. KONFIGURASI AI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.sidebar.error("API Key belum diset di Streamlit Secrets!")

# --- 3. INPUT TARGET PRODUK ---
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Pilih Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk Jadi (ml)", value=100.0)

persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_ml = (persen_konse / 100) * target_total_ml
total_berat_produk_g = target_total_ml * 0.85 

st.info(f"Target Konsentrat: **{target_konsentrat_ml:.2f} ML**")

# --- 4. INPUT FORMULA (HYBRID) ---
st.subheader("📝 Input Formula")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.SelectboxColumn("Bahan (Pilih/Ketik)", options=list_bahan, width="large"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)
st.session_state.formula_df = edited_df

# --- 5. ANALISIS & DIAGRAM ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()

if not df_calc.empty:
    df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
    
    # Merge DB
    df_merged = df_calc.merge(db, on="Bahan", how="left").fillna({"Aroma_Profile": "Unknown", "Kategori_IFRA_4": 100.0})
    
    # Kalkulasi Volume
    df_merged["Volume Internal (ML)"] = (df_merged["Persentase (%)"] / 100) * target_konsentrat_ml
    df_merged["Jumlah Dibutuhkan"] = df_merged.apply(lambda r: r["Volume Internal (ML)"] * 0.9 if r["Satuan Timbangan"] == "g" else r["Volume Internal (ML)"], axis=1)
    
    # Kalkulasi IFRA (Produk Akhir)
    df_merged["Berat Bahan Aktual (g)"] = df_merged["Volume Internal (ML)"] * 0.9
    df_merged["% di Produk Akhir"] = (df_merged["Berat Bahan Aktual (g)"] / total_berat_produk_g) * 100
    df_merged["Status IFRA"] = df_merged.apply(lambda r: "✅ Aman" if r["% di Produk Akhir"] <= r["Kategori_IFRA_4"] else "❌ OVER LIMIT", axis=1)

    st.subheader("📊 Hasil Analisa")
    st.dataframe(df_merged[["Bahan", "Aroma_Profile", "Persentase (%)", "Status IFRA"]], use_container_width=True)

    # Diagram Profil Aroma
    st.subheader("📊 Diagram Profil Aroma")
    aroma_counts = df_merged.groupby("Aroma_Profile")["Persentase (%)"].sum().reset_index()
    fig = px.pie(aroma_counts, values="Persentase (%)", names="Aroma_Profile", hole=0.3)
    st.plotly_chart(fig)

    # --- 6. AUDIT AI ---
    if st.button("Analisa & Optimasi Formula oleh AI"):
        with st.spinner("AI sedang melakukan audit profesional..."):
            prompt = f"""
            Anda adalah Master Perfumer. Analisa formula berikut:
            {df_merged[['Bahan', 'Persentase (%)', 'Aroma_Profile', 'Status IFRA']].to_string()}
            
            1. Evaluasi apakah profil aroma (Citrus, Floral, dll) sudah seimbang?
            2. Berikan saran penambahan/pengurangan bahan untuk memperbaiki aroma.
            3. Berikan saran perbaikan jika ada 'Status IFRA' yang melanggar.
            """
            try:
                response = model.generate_content(prompt)
                st.markdown("### 🛡️ Laporan Audit Kepatuhan AI")
                st.info(response.text)
            except Exception as e:
                st.error(f"Gagal menghubungi AI: {e}")
