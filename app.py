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
# Kalkulasi Target Konsentrat langsung dalam ML
target_konsentrat_ml = (persen_konse / 100) * target_total_ml
st.info(f"Target Total Konsentrat: **{target_konsentrat_ml:.2f} ML**")

# --- 2. FORMULA INPUT ---
st.subheader("📝 2. Input Persentase Bahan")
st.markdown("Masukkan persentase masing-masing bahan. Sistem akan menghitung takarannya secara otomatis.")
if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(columns=["Bahan", "Persentase (%)", "Satuan Timbangan"])

edited_df = st.data_editor(
    st.session_state.formula_df, num_rows="dynamic", use_container_width=True,
    column_config={
        "Bahan": st.column_config.TextColumn("Bahan (Ketik Manual)"),
        "Persentase (%)": st.column_config.NumberColumn("Persentase (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "Satuan Timbangan": st.column_config.SelectboxColumn("Satuan", options=["ml", "g"])
    }
)

# --- 3. LOGIKA KALKULASI OTOMATIS (ML SEBAGAI PUSAT) ---
df_calc = edited_df.dropna(subset=["Bahan"]).copy()
df_calc["Persentase (%)"] = pd.to_numeric(df_calc["Persentase (%)"], errors='coerce').fillna(0)
df_calc["Satuan Timbangan"] = df_calc["Satuan Timbangan"].fillna("ml")

# 1. Menghitung Volume Internal Murni dalam ML (Persentase x Total Konsentrat ML)
df_calc["Volume Internal (ML)"] = (df_calc["Persentase (%)"] / 100) * target_konsentrat_ml

# 2. Mengonversi tampilan fisik jika pengguna memilih menimbang dalam Gram
# Asumsi standar berat jenis (Specific Gravity) bahan parfum rata-rata adalah 0.9 g/ml.
def hitung_tampilan_fisik(row):
    if row["Satuan Timbangan"] == "g":
        # Massa (g) = Volume (ml) x Densitas (0.9)
        return row["Volume Internal (ML)"] * 0.9
    return row["Volume Internal (ML)"]

df_calc["Jumlah Dibutuhkan"] = df_calc.apply(hitung_tampilan_fisik, axis=1)

# --- 4. TAMPILAN ANALISA ---
if not df_calc.empty:
    st.divider()
    st.subheader("📊 3. Hasil Kalkulasi Racikan")
    
    # Menampilkan tabel hasil akhir dengan format yang bersih
    tabel_tampil = df_calc[["Bahan", "Persentase (%)", "Jumlah Dibutuhkan", "Satuan Timbangan", "Volume Internal (ML)"]]
    st.dataframe(tabel_tampil, use_container_width=True, hide_index=True)
    
    total_persen = df_calc["Persentase (%)"].sum()
    total_ml_internal = df_calc["Volume Internal (ML)"].sum()
    
    # Indikator Status Racikan
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
        # Mengirimkan data bersih tanpa membebani AI dengan angka teknis berlebih
        prompt = f"Formula Konsentrat: {df_calc[['Bahan', 'Persentase (%)']].to_string(index=False)}. Target Konsentrasi: {konsentrasi_target}. Analisa keseimbangan profil aroma ini dan berikan saran penyesuaian jika diperlukan."
        response = model.generate_content(prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"Terjadi masalah saat menghubungi AI: {e}")
