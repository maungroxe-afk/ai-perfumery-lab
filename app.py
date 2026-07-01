import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Perfumery Lab Pro", page_icon="🧪", layout="wide")

# --- MEMUAT DATABASE DARI CSV PRO ---
@st.cache_data
def load_database():
    try:
        # Menggunakan sep=None agar kebal terhadap format TAB maupun KOMA
        df = pd.read_csv("database_ifra_pro.csv", sep=None, engine='python')
        df['Kategori_IFRA_4'] = pd.to_numeric(df['Kategori_IFRA_4'], errors='coerce')
        return df
    except FileNotFoundError:
        st.error("File database_ifra_pro.csv tidak ditemukan di repository!")
        return pd.DataFrame()

df_ifra = load_database()

st.title("🧪 AI Perfumery Lab Pro & IFRA Analyzer")
st.markdown("Aplikasi peracikan parfum cerdas dengan kalkulasi Produk Akhir dan Visualisasi Profil Aroma.")

# --- TABS ---
tab_formula, tab_ai, tab_db = st.tabs(["⚖️ Kalkulator Formulasi", "🤖 AI Perfumer Assistant", "📚 Database IFRA Pro"])

# --- TAB 1: KALKULATOR FORMULASI ---
with tab_formula:
    st.header("Kalkulator Formulasi Parfum")
    
    # Pengaturan Target Parfum
    st.subheader("1. Pengaturan Target Produk Akhir")
    col_target1, col_target2 = st.columns(2)
    with col_target1:
        dict_konsentrasi = {
            "Eau de Cologne (EDC) - 5%": 5.0,
            "Eau de Toilette (EDT) - 10%": 10.0,
            "Eau de Parfum (EDP) - 20%": 20.0,
            "Extrait de Parfum - 30%": 30.0
        }
        pilihan_konsentrasi = st.selectbox("Konsentrasi Parfum", list(dict_konsentrasi.keys()))
        val_konsentrasi = dict_konsentrasi[pilihan_konsentrasi]
        
    with col_target2:
        dict_volume = {"10 ml": 10.0, "30 ml": 30.0, "50 ml": 50.0, "100 ml": 100.0}
        pilihan_volume = st.selectbox("Target Volume Botol", list(dict_volume.keys()))
        val_volume = dict_volume[pilihan_volume]

    st.markdown("---")
    st.subheader("2. Input Formula Konsentrat (Bibit)")
    st.write("Masukkan rasio bahan. Jika Anda menggunakan sistem persentase, pastikan total input mencapai 100.")
    
    if not df_ifra.empty:
        if 'formula' not in st.session_state:
            st.session_state.formula = []

        col1, col2 = st.columns([2, 1])
        with col1:
            daftar_bahan = df_ifra["Bahan"].dropna().tolist()
            bahan_pilihan = st.selectbox("Pilih Bahan Baku", daftar_bahan)
        with col2:
            jumlah_bahan = st.number_input("Input (Persentase % / Parts)", min_value=0.01, value=10.0, step=0.1)

        if st.button("➕ Tambah ke Formula"):
            st.session_state.formula.append({"Bahan": bahan_pilihan, "Input": jumlah_bahan})
            st.success(f"{bahan_pilihan} ditambahkan!")

        # Tampilkan Formula dan Analisis
        if st.session_state.formula:
            df_formula = pd.DataFrame(st.session_state.formula)
            df_formula = df_formula.groupby("Bahan", as_index=False).sum()
            
            total_input = df_formula["Input"].sum()
            
            # Progress Bar Formula
            st.metric(label="Total Input Formula Saat Ini", value=f"{total_input:.2f}")
            if total_input < 100:
                st.info(f"💡 Masih kurang {100 - total_input:.2f} lagi untuk mencapai formula 100%.")
            elif total_input > 100:
                st.warning(f"⚠️ Total formula melebihi 100 ({total_input:.2f}). Sistem akan otomatis menyesuaikannya menjadi persentase relatif.")
            else:
                st.success("✅ Total formula pas 100%!")

            df_formula["% di Bibit"] = (df_formula["Input"] / total_input) * 100
            df_formula["% di Produk Akhir"] = df_formula["% di Bibit"] * (val_konsentrasi / 100.0)
            
            kebutuhan_bibit_total = val_volume * (val_konsentrasi / 100.0)
            pelarut_total = val_volume - kebutuhan_bibit_total
            df_formula["Target Timbangan (g)"] = (df_formula["% di Bibit"] / 100.0) * kebutuhan_bibit_total
            
            # Gabungkan dengan database
            df_formula = pd.merge(df_formula, df_ifra[["Bahan", "Kategori_IFRA_4", "Aroma_Profile"]], on="Bahan", how="left")
            
            def cek_ifra(row):
                persen_akhir = row["% di Produk Akhir"]
                limit = row["Kategori_IFRA_4"]
                return "✅ Aman" if persen_akhir <= limit else "❌ Melebihi Batas!"

            df_formula["Status IFRA"] = df_formula.apply(cek_ifra, axis=1)
            df_formula.rename(columns={"Kategori_IFRA_4": "Batas IFRA (%)"}, inplace=True)
            
            kolom_numerik = ["Input", "% di Bibit", "Target Timbangan (g)", "% di Produk Akhir", "Batas IFRA (%)"]
            for col in kolom_numerik:
                df_formula[col] = df_formula[col].round(2)
            
            df_tampil = df_formula[["Bahan", "Input", "% di Bibit", "Target Timbangan (g)", "% di Produk Akhir", "Batas IFRA (%)", "Status IFRA"]]
            
            st.markdown("---")
            st.subheader(f"📊 Resep Final: {pilihan_volume} {pilihan_konsentrasi.split('-')[0].strip()}")
            st.info(f"💡 Timbang bahan satu per satu sesuai kolom **Target Timbangan (g)** hingga total **{kebutuhan_bibit_total:.2f} gram**, lalu tambahkan **{pelarut_total:.2f} gram Alkohol/Pelarut**.")
            
            st.dataframe(
                df_tampil.style
                .format({col: "{:.2f}" for col in kolom_numerik})
                .map(lambda x: "background-color: #ffcccc" if "❌" in str(x) else "background-color: #ccffcc" if "✅" in str(x) else "", subset=["Status IFRA"])
            )
            
            # --- FITUR BARU: VISUALISASI DIAGRAM AROMA LINGKARAN ---
            st.markdown("---")
            st.subheader("🕸️ Visualisasi Profil Aroma (Olfactory Accord)")
            
            kategori_aroma = {
                "Citrus / Fresh": ["citrus", "lemon", "orange", "bergamot", "lime", "grapefruit", "zesty", "fresh", "segar"],
                "Floral": ["floral", "rose", "mawar", "jasmine", "melati", "muguet", "tuberose", "ylang", "neroli", "white floral", "orchid"],
                "Woody": ["woody", "kayu", "cedar", "sandalwood", "patchouli", "vetiver", "earthy", "mossy", "pine"],
                "Spicy": ["spicy", "cinnamon", "clove", "pepper", "cardamom", "rempah", "pedas", "hangat"],
                "Fruity": ["fruity", "apple", "peach", "pear", "berry", "pisang", "nanas", "apel", "plum", "buah"],
                "Sweet / Gourmand": ["sweet", "manis", "vanilla", "gourmand", "caramel", "cokelat", "madu", "tonka", "almond", "creamy"],
                "Musk": ["musk", "musky", "powdery", "clean", "bersih"],
                "Amber / Balsamic": ["amber", "ambergris", "balsamic", "resin", "warm", "incense", "dupa", "mur"],
                "Green / Herbal": ["green", "hijau", "leaf", "grass", "rumput", "herbal", "lavender", "mint", "camphor", "tea"],
                "Animalic / Leather": ["animalic", "leathery", "leather", "kulit", "civet", "castoreum", "smoky", "fecal"],
                "Marine / Aquatic": ["marine", "watery", "ozone", "sea", "aquatic", "melon"]
            }
            
            skor_aroma = {k: 0.0 for k in kategori_aroma.keys()}
            
            # Hitung skor
            for idx, row in df_formula.iterrows():
                deskripsi = str(row["Aroma_Profile"]).lower()
                bobot = row["% di Bibit"]
                
                for kategori, keywords in kategori_aroma.items():
                    for word in keywords:
                        if word in deskripsi:
                            skor_aroma[kategori] += bobot
                            break 
                            
            df_radar = pd.DataFrame(list(skor_aroma.items()), columns=['Kategori Aroma', 'Skor Kekuatan'])
            df_radar = df_radar[df_radar['Skor Kekuatan'] > 0]
            
            if not df_radar.empty:
                # Menggunakan Diagram Lingkaran (Pie / Donut Chart)
                fig = px.pie(df_radar, values='Skor Kekuatan', names='Kategori Aroma', 
                             title="Komposisi Karakter Parfum Anda",
                             hole=0.4, # Membuatnya menjadi Donut Chart agar elegan
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                
                # Menampilkan label dan persentase di dalam potongan kue
                fig.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("Belum cukup data untuk membentuk profil aroma.")
            
            if st.button("🗑️ Hapus Semua Formula"):
                st.session_state.formula = []
                st.rerun()
    else:
        st.warning("Database bahan baku kosong atau file CSV belum di-upload ke GitHub.")

# --- TAB 2: AI PERFUMER ASSISTANT ---
with tab_ai:
    st.header("🤖 Asisten AI Perfumer")
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
                model = genai.GenerativeModel('gemini-pro')
                with st.spinner("AI sedang memikirkan racikan terbaik..."):
                    konteks_system = "Kamu adalah seorang Master Perfumer yang sangat ahli dalam meracik parfum dan hafal standar IFRA Kategori 4. "
                    response = model.generate_content(konteks_system + prompt_user)
                    st.success("Jawaban AI:")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Terjadi kesalahan pada AI: {e}. Pastikan API Key valid.")

# --- TAB 3: DATABASE IFRA ---
with tab_db:
    st.header("📚 Database Bahan Baku Profesional")
    if not df_ifra.empty:
        st.dataframe(df_ifra)
