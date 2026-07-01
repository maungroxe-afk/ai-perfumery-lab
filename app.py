import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Perfumery Lab Pro", page_icon="🧪", layout="wide")

# --- MEMUAT DATABASE DARI CSV PRO ---
@st.cache_data
def load_database():
    try:
        # Membaca dari file CSV. sep=None dan engine='python' agar bisa otomatis 
        # membaca file yang dipisahkan oleh Koma (,) maupun Tab (jarak spasi panjang).
        df = pd.read_csv("database_ifra_pro.csv", sep=None, engine='python')
        return df
    except FileNotFoundError:
        st.error("File database_ifra_pro.csv tidak ditemukan di repository!")
        return pd.DataFrame()

df_ifra = load_database()

st.title("🧪 AI Perfumery Lab Pro & IFRA Analyzer")
st.markdown("Aplikasi peracikan parfum cerdas dengan database profesional dan Asisten AI.")

# --- TABS ---
tab_formula, tab_ai, tab_db = st.tabs(["⚖️ Kalkulator Formulasi", "🤖 AI Perfumer Assistant", "📚 Database IFRA Pro"])

# --- TAB 1: KALKULATOR FORMULASI ---
with tab_formula:
    st.header("Kalkulator Formulasi Parfum")
    
    if not df_ifra.empty:
        if 'formula' not in st.session_state:
            st.session_state.formula = []

        col1, col2 = st.columns([2, 1])
        with col1:
            daftar_bahan = df_ifra["Bahan"].tolist()
            bahan_pilihan = st.selectbox("Pilih Bahan Baku", daftar_bahan)
        with col2:
            jumlah_bahan = st.number_input("Jumlah (Gram / Tetes)", min_value=0.01, value=1.0, step=0.1)

        if st.button("➕ Tambah ke Formula"):
            st.session_state.formula.append({"Bahan": bahan_pilihan, "Jumlah (g)": jumlah_bahan})
            st.success(f"{bahan_pilihan} ditambahkan!")

        # Tampilkan Formula dan Analisis
        if st.session_state.formula:
            df_formula = pd.DataFrame(st.session_state.formula)
            df_formula = df_formula.groupby("Bahan", as_index=False).sum()
            
            total_jumlah = df_formula["Jumlah (g)"].sum()
            df_formula["Persentase (%)"] = (df_formula["Jumlah (g)"] / total_jumlah) * 100
            
            # Gabungkan dengan limit IFRA dan detail lain dari database CSV
            df_formula = pd.merge(df_formula, df_ifra[["Bahan", "Kategori_IFRA_4", "Tipe_Note"]], on="Bahan", how="left")
            
            def cek_ifra(row):
                persen = row["Persentase (%)"]
                limit = row["Kategori_IFRA_4"]
                return "✅ Aman" if persen <= limit else "❌ Melebihi Batas!"

            df_formula["Status IFRA"] = df_formula.apply(cek_ifra, axis=1)
            
            # Merapikan tampilan tabel
            df_formula.rename(columns={"Kategori_IFRA_4": "Batas IFRA (%)", "Tipe_Note": "Tipe Note"}, inplace=True)
            
            # Menyusun urutan kolom agar lebih enak dibaca
            df_tampil = df_formula[["Bahan", "Tipe Note", "Jumlah (g)", "Persentase (%)", "Batas IFRA (%)", "Status IFRA"]]
            
            st.subheader("Detail Formulasi Anda")
            st.write(f"**Total Berat Formula:** {total_jumlah:.2f} Gram")
            st.dataframe(df_tampil.style.map(lambda x: "background-color: #ffcccc" if "❌" in str(x) else "background-color: #ccffcc" if "✅" in str(x) else "", subset=["Status IFRA"]))
            
            if st.button("🗑️ Hapus Semua Formula"):
                st.session_state.formula = []
                st.rerun()
    else:
        st.warning("Database bahan baku kosong atau file CSV belum di-upload ke GitHub.")

# --- TAB 2: AI PERFUMER ASSISTANT ---
with tab_ai:
    st.header("🤖 Asisten AI Perfumer")
    st.markdown("Konsultasi formula, cari inspirasi *accord*, analisis IFRA, atau cari bahan pengganti.")
    
    api_key = st.text_input("Masukkan Google Gemini API Key Anda", type="password")
    prompt_user = st.text_area("Tanyakan sesuatu ke AI... (Contoh: 'Buatkan saya formula parfum floral musky dengan 5 bahan')")
    
    if st.button("Tanya AI"):
        if not api_key:
            st.error("Masukkan API Key Gemini terlebih dahulu!")
        elif not prompt_user:
            st.warning("Silakan ketik pertanyaan Anda.")
        else:
            try:
                genai.configure(api_key=api_key)
                # Menggunakan model Gemini Pro
                model = genai.GenerativeModel('gemini-pro')
                with st.spinner("AI sedang memikirkan racikan terbaik..."):
                    # Menambahkan konteks agar AI menjawab layaknya ahli parfum
                    konteks_system = "Kamu adalah seorang Master Perfumer yang sangat ahli dalam meracik parfum dan hafal standar IFRA Kategori 4. "
                    response = model.generate_content(konteks_system + prompt_user)
                    st.success("Jawaban AI:")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Terjadi kesalahan pada AI: {e}. Pastikan API Key valid.")

# --- TAB 3: DATABASE IFRA ---
with tab_db:
    st.header("📚 Database Bahan Baku Profesional")
    st.write("Diambil otomatis dari file `database_ifra_pro.csv`. Anda bisa memperbarui file ini kapan saja di GitHub tanpa mengubah kode aplikasi.")
    if not df_ifra.empty:
        # Menampilkan seluruh database
        st.dataframe(df_ifra)
