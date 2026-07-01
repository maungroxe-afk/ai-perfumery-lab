import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Perfumery Lab Pro", page_icon="🧪", layout="wide")

# --- DATABASE IFRA SEMENTARA (MOCK DB) ---
# Kategori 4 adalah untuk Fine Fragrance (Parfum semprot)
# Nilai limit dalam persentase (%)
IFRA_DATABASE = {
    "Bergamot Oil": {"limit_cat4": 100.0, "type": "Top Note", "odor": "Citrus, Fresh"},
    "Rose Absolute": {"limit_cat4": 2.5, "type": "Heart Note", "odor": "Floral, Rich"},
    "Vanillin": {"limit_cat4": 10.0, "type": "Base Note", "odor": "Sweet, Gourmand"},
    "Oakmoss Extract": {"limit_cat4": 0.1, "type": "Base Note", "odor": "Woody, Earthy, Mossy"},
    "Coumarin": {"limit_cat4": 1.6, "type": "Base Note", "odor": "Sweet, Hay, Tonka"},
    "Iso E Super": {"limit_cat4": 21.4, "type": "Heart/Base", "odor": "Woody, Amber, Velvety"},
    "Linalool": {"limit_cat4": 4.3, "type": "Top/Heart", "odor": "Floral, Lavender, Citrus"},
    "Galaxolide (Musk)": {"limit_cat4": 20.0, "type": "Base Note", "odor": "Musk, Clean, Sweet"}
}

st.title("🧪 AI Perfumery Lab Pro & IFRA Analyzer")
st.markdown("Aplikasi peracikan parfum cerdas dengan analisis batas aman IFRA (Kategori 4 - Fine Fragrance) dan Asisten AI.")

# --- TABS ---
tab_formula, tab_ai, tab_db = st.tabs(["⚖️ Kalkulator Formulasi", "🤖 AI Perfumer Assistant", "📚 Database IFRA"])

# --- TAB 1: KALKULATOR FORMULASI ---
with tab_formula:
    st.header("Kalkulator Formulasi Parfum")
    st.write("Masukkan bahan dan jumlahnya (dalam gram atau tetes). Aplikasi akan menghitung persentase dan membandingkannya dengan batas aman IFRA.")
    
    # Inisialisasi session state untuk formula
    if 'formula' not in st.session_state:
        st.session_state.formula = []

    col1, col2 = st.columns([2, 1])
    with col1:
        bahan_pilihan = st.selectbox("Pilih Bahan Baku", list(IFRA_DATABASE.keys()))
    with col2:
        jumlah_bahan = st.number_input("Jumlah (Gram)", min_value=0.01, value=1.0, step=0.1)

    if st.button("➕ Tambah ke Formula"):
        st.session_state.formula.append({"Bahan": bahan_pilihan, "Jumlah": jumlah_bahan})
        st.success(f"{bahan_pilihan} ditambahkan!")

    # Tampilkan Formula dan Analisis
    if st.session_state.formula:
        df_formula = pd.DataFrame(st.session_state.formula)
        # Menggabungkan bahan yang sama
        df_formula = df_formula.groupby("Bahan", as_index=False).sum()
        
        total_jumlah = df_formula["Jumlah"].sum()
        df_formula["Persentase (%)"] = (df_formula["Jumlah"] / total_jumlah) * 100
        
        # Tambahkan batas IFRA dan Status Peringatan
        def cek_ifra(row):
            bahan = row["Bahan"]
            persentase = row["Persentase (%)"]
            limit = IFRA_DATABASE[bahan]["limit_cat4"]
            status = "✅ Aman" if persentase <= limit else "❌ Melebihi Batas IFRA!"
            return limit, status

        df_formula[["Batas IFRA (%)", "Status IFRA"]] = df_formula.apply(cek_ifra, axis=1, result_type='expand')
        
        st.subheader("Detail Formulasi Anda")
        st.write(f"**Total Berat Formula:** {total_jumlah:.2f} Gram")
        st.dataframe(df_formula.style.applymap(lambda x: "background-color: #ffcccc" if "❌" in str(x) else "background-color: #ccffcc" if "✅" in str(x) else "", subset=["Status IFRA"]))
        
        if st.button("🗑️ Hapus Semua Formula"):
            st.session_state.formula = []
            st.rerun()

# --- TAB 2: AI PERFUMER ASSISTANT ---
with tab_ai:
    st.header("🤖 Asisten AI Perfumer")
    st.markdown("Gunakan AI untuk mengevaluasi formula Anda, mencari inspirasi *accord*, atau mencari alternatif bahan. *Catatan: Butuh Google Gemini API Key.*")
    
    api_key = st.text_input("Masukkan Google Gemini API Key Anda", type="password")
    prompt_user = st.text_area("Apa yang ingin Anda tanyakan ke AI? (Contoh: 'Tolong buatkan accord wangi Vanilla Floral yang elegan')")
    
    if st.button("Tanya AI"):
        if not api_key:
            st.error("Silakan masukkan API Key Gemini terlebih dahulu!")
        elif not prompt_user:
            st.warning("Silakan ketik pertanyaan Anda.")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                with st.spinner("AI sedang berpikir dan meracik jawaban..."):
                    response = model.generate_content(prompt_user)
                    st.success("Jawaban AI:")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Terjadi kesalahan saat menghubungi AI: {e}")

# --- TAB 3: DATABASE IFRA ---
with tab_db:
    st.header("📚 Database Bahan Baku (IFRA Kategori 4)")
    st.write("Daftar bahan baku, aroma, dan batas maksimal penggunaan untuk produk Fine Fragrance (Parfum semprot).")
    
    db_list = []
    for bahan, data in IFRA_DATABASE.items():
        db_list.append({
            "Bahan Baku": bahan,
            "Tipe Note": data["type"],
            "Karakter Aroma": data["odor"],
            "Batas Maksimal IFRA Kategori 4 (%)": data["limit_cat4"]
        })
        
    df_db = pd.DataFrame(db_list)
    st.dataframe(df_db)
