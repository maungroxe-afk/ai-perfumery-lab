import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

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

# --- 1. SPESIFIKASI PRODUK (BASIS ML) ---
st.subheader("⚙️ 1. Tentukan Target (Berbasis Volume)")
col1, col2 = st.columns(2)
konsentrasi_target = col1.selectbox("Konsentrasi:", ["Eau de Cologne (5%)", "Eau de Toilette (10%)", "Eau de Parfum (20%)", "Extrait de Parfum (30%)"])
target_total_ml = col2.number_input("Total Volume Produk Jadi (ml)", value=100.0)

persen_konse = int(konsentrasi_target.split('(')[1].replace('%)', ''))
target_konsentrat_ml = (persen_konse / 100) * target_total_ml
st.info(f"Target Total Konsentrat: **{target_konsentrat_ml:.2f} ML**")

# --- 2. FORMULA INPUT ---
st.subheader("📝 2. Input Persentase Bahan")
st.markdown("Masukkan persentase masing-masing bahan. Sistem akan otomatis mengalkulasi takarannya dan mengecek batas IFRA.")

kolom_harapan = ["Bahan", "Persentase (%)", "Satuan Timbangan"]
if "formula_df" not in st.session_state or list(st.session_state.formula_df.columns) != kolom_harapan:
    st.session_state.formula_df = pd.DataFrame(columns=kolom_harapan)

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.TextColumn("Bahan (Ketik Manual)"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)

# --- 3. LOGIKA KALKULASI & IFRA ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()

if "Satuan Timbangan" in df_calc.columns:
    df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
    df_calc["Satuan Timbangan"] = df_calc["Satuan Timbangan"].fillna("ml")

    # Kalkulasi Fisik
    df_calc["Volume Internal (ML)"] = (df_calc["Persentase (%)"] / 100) * target_konsentrat_ml
    def hitung_tampilan_fisik(row):
        if row["Satuan Timbangan"] == "g":
            return row["Volume Internal (ML)"] * 0.9
        return row["Volume Internal (ML)"]
    df_calc["Jumlah Dibutuhkan"] = df_calc.apply(hitung_tampilan_fisik, axis=1)

    # --- PENGECEKAN IFRA ---
    def get_ifra_info(nama):
        # Gunakan lowercase untuk pencarian yang lebih kebal typo
        if not db.empty:
            match = db[db["Bahan"].str.lower() == str(nama).lower()]
            if not match.empty:
                return match.iloc[0]["Kategori"], match.iloc[0]["IFRA_Max"]
        return "Custom/New", 100.0

    df_calc[["Kategori", "Batas IFRA (%)"]] = df_calc["Bahan"].apply(lambda x: pd.Series(get_ifra_info(x)))
    
    # Cek apakah Persentase melebih batas IFRA
    df_calc["Status IFRA"] = df_calc.apply(
        lambda r: "✅ Aman" if r["Persentase (%)"] <= r["Batas IFRA (%)"] else "❌ OVER LIMIT", axis=1
    )

    # --- 4. TAMPILAN ANALISA ---
    if not df_calc.empty:
        st.divider()
        st.subheader("📊 3. Hasil Kalkulasi & Kepatuhan Regulasi")
        
        # Menyusun urutan kolom agar enak dibaca
        tabel_tampil = df_calc[["Bahan", "Kategori", "Persentase (%)", "Batas IFRA (%)", "Jumlah Dibutuhkan", "Satuan Timbangan", "Status IFRA"]]
        st.dataframe(tabel_tampil, use_container_width=True, hide_index=True)
        
        # Menampilkan peringatan jika ada yang melanggar
        if "❌ OVER LIMIT" in df_calc["Status IFRA"].values:
            st.error("⚠️ PERINGATAN: Terdapat bahan yang melampaui batas aman IFRA! Silakan kurangi persentase bahan tersebut.")
        else:
            st.success("✅ Seluruh komposisi berada di dalam batas aman regulasi IFRA.")

        total_persen = df_calc["Persentase (%)"].sum()
        total_ml_internal = df_calc["Volume Internal (ML)"].sum()
        
        col_a, col_b = st.columns(2)
        if total_persen < 100:
            status_persen = f"Sisa {100 - total_persen:.2f}%"
        elif total_persen > 100:
            status_persen = "⚠️ Over 100%"
        else:
            status_persen = "✅ Pas 100%"
            
        col_a.metric("Total Persentase Formula", f"{total_persen:.2f}%", delta=status_persen, delta_color="off" if total_persen==100 else "normal")
        col_b.metric("Total Volume Konsentrat", f"{total_ml_internal:.2f} ML / {target_konsentrat_ml:.2f} ML")

# --- 5. AI ASSISTANT ---
st.divider()
st.subheader("🤖 4. AI Perfumer Assistant")
if st.button("Analisa Formula"):
    try:
        # Kirim data ke AI termasuk status IFRA-nya
        prompt = f"Formula: {df_calc[['Bahan', 'Kategori', 'Persentase (%)', 'Status IFRA']].to_string(index=False)}. Target: {konsentrasi_target}. Berikan analisa teknis mendalam mengenai keseimbangan notes dan saran jika ada bahan Custom/New."
        response = model.generate_content(prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"Terjadi masalah saat menghubungi AI: {e}")
