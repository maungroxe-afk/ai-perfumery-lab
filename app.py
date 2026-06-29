import streamlit as st
import pandas as pd
import google.generativeai as genai

# Konfigurasi Halaman
st.set_page_config(page_title="AI Perfumery Lab", layout="wide")

st.title("🧪 AI Perfumery Lab: Project UCP ALPHA")
st.markdown("Manajemen Formula, Kalkulasi Biaya, Cek IFRA, & Asisten AI Real-Time")

# --- MENGAMBIL API KEY SECARA OTOMATIS ---
try:
    # Membaca API Key dari Streamlit Secrets
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ API Key belum dikonfigurasi di Streamlit Secrets!")
    api_key = None

# --- INISIALISASI DATA FORMULA ---
# Menggunakan beberapa bahan contoh (bisa diedit di aplikasi)
default_data = {
    "Bahan (Notes)": ["Bergamot EO", "Ambroxan", "Iso E Super", "Vanilla Absolute"],
    "Kategori": ["Top", "Base", "Heart", "Base"],
    "Berat (gram)": [15.0, 5.0, 20.0, 2.0],
    "Harga per Gram (IDR)": [3000, 15000, 2500, 50000],
    "Batas Maksimal IFRA (%)": [0.4, 100.0, 21.4, 100.0] # 100 artinya tidak dibatasi
}

if "formula_df" not in st.session_state:
    st.session_state.formula_df = pd.DataFrame(default_data)

# --- BAGIAN 1: BUILDER FORMULA & REAL-TIME CALCULATION ---
st.subheader("📝 Formula Builder")
st.markdown("Edit tabel di bawah ini. Anda bisa menambah baris baru atau mengubah angka. Kalkulasi berjalan otomatis.")

# Data Editor interaktif
edited_df = st.data_editor(st.session_state.formula_df, num_rows="dynamic", use_container_width=True)

# Kalkulasi Real-Time
total_berat = edited_df["Berat (gram)"].sum()

if total_berat > 0:
    # Menghitung persentase tiap bahan dalam formula
    edited_df["% Dalam Formula"] = (edited_df["Berat (gram)"] / total_berat) * 100
    
    # Pengecekan IFRA
    edited_df["Status IFRA"] = edited_df.apply(
        lambda row: "✅ Aman" if row["% Dalam Formula"] <= row["Batas Maksimal IFRA (%)"] 
        else "❌ MELAMPAUI BATAS", axis=1
    )
    
    # Menghitung Biaya
    edited_df["Total Harga (IDR)"] = edited_df["Berat (gram)"] * edited_df["Harga per Gram (IDR)"]
    total_biaya = edited_df["Total Harga (IDR)"].sum()
    harga_per_kg = (total_biaya / total_berat) * 1000

    # Tampilkan Ringkasan
    st.write("### 📊 Ringkasan Formula")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Berat Konsentrat", f"{total_berat:.2f} g")
    col2.metric("Total Biaya Formula", f"Rp {total_biaya:,.0f}")
    col3.metric("Estimasi Harga per Kg", f"Rp {harga_per_kg:,.0f}")

    # Tampilkan status peringatan jika ada pelanggaran IFRA
    if "❌ MELAMPAUI BATAS" in edited_df["Status IFRA"].values:
        st.error("⚠️ PERINGATAN: Ada bahan yang melampaui batas aman IFRA! Cek tabel di atas.")
    else:
        st.success("✅ Semua bahan berada di dalam batas aman regulasi IFRA.")

# Simpan state terbaru
st.session_state.formula_df = edited_df.drop(columns=["% Dalam Formula", "Status IFRA", "Total Harga (IDR)"], errors='ignore')

st.divider()

# --- BAGIAN 2: ASISTEN AI (PERFUMER'S BRAIN) ---
st.subheader("🤖 AI Perfumer Assistant")
st.markdown("Minta AI untuk menganalisis racikan di atas, memberikan saran bahan tambahan, atau memprediksi profil aromanya.")

user_prompt = st.text_input("Tanyakan sesuatu ke AI tentang formula ini (contoh: 'Apa notes tambahan agar aromanya lebih segar?'):")

if st.button("Tanya AI"):
    if not api_key:
        st.warning("Silakan masukkan API Key di menu samping (Sidebar) terlebih dahulu.")
    elif total_berat == 0:
        st.warning("Formula masih kosong!")
    else:
        with st.spinner("AI sedang menganalisis komposisi aroma..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Menggabungkan data formula ke dalam prompt AI
                formula_text = edited_df[["Bahan (Notes)", "Kategori", "% Dalam Formula"]].to_string(index=False)
                
                full_prompt = f"""
                Anda adalah seorang Master Perfumer profesional. Berikut adalah formula parfum yang sedang saya racik:
                {formula_text}
                
                Pertanyaan/Permintaan saya: {user_prompt}
                
                Berikan jawaban yang profesional, aplikatif, dan gunakan terminologi perfumery yang tepat.
                """
                
                response = model.generate_content(full_prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"Terjadi kesalahan saat menghubungi AI: {e}")
