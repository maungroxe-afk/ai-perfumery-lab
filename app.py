import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px
import io
import json

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
            df_formula = pd.merge(df_formula, df_ifra[["Bahan", "Kategori_IFRA_4", "Aroma_Profile", "Tipe_Note"]], on="Bahan", how="left")
            
            def cek_ifra(row):
                persen_akhir = row["% di Produk Akhir"]
                limit = row["Kategori_IFRA_4"]
                return "✅ Aman" if persen_akhir <= limit else "❌ Melebihi Batas!"

            df_formula["Status IFRA"] = df_formula.apply(cek_ifra, axis=1)
            df_formula.rename(columns={"Kategori_IFRA_4": "Batas IFRA (%)", "Tipe_Note": "Tipe Note"}, inplace=True)
            
            kolom_numerik = ["Input", "% di Bibit", "Target Timbangan (g)", "% di Produk Akhir", "Batas IFRA (%)"]
            for col in kolom_numerik:
                df_formula[col] = df_formula[col].round(2)
            
            df_tampil = df_formula[["Bahan", "Tipe Note", "Input", "% di Bibit", "Target Timbangan (g)", "% di Produk Akhir", "Batas IFRA (%)", "Status IFRA"]]
            
            st.markdown("---")
            st.subheader(f"📊 Resep Final: {pilihan_volume} {pilihan_konsentrasi.split('-')[0].strip()}")
            st.info(f"💡 Timbang bahan satu per satu sesuai kolom **Target Timbangan (g)** hingga total **{kebutuhan_bibit_total:.2f} gram**, lalu tambahkan **{pelarut_total:.2f} gram Alkohol/Pelarut**.")
            
            st.dataframe(
                df_tampil.style
                .format({col: "{:.2f}" for col in kolom_numerik})
                .map(lambda x: "background-color: #ffcccc" if "❌" in str(x) else "background-color: #ccffcc" if "✅" in str(x) else "", subset=["Status IFRA"])
            )
            
            # --- FITUR DOWNLOAD KE EXCEL ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_tampil.to_excel(writer, index=False, sheet_name='Resep Perfume')
            
            st.download_button(
                label="📥 Download Resep (Excel / .xlsx)",
                data=buffer.getvalue(),
                file_name="resep_parfum_ai_lab.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # --- KELOLA & HAPUS BAHAN ---
            st.markdown("---")
            st.subheader("🛠️ Kelola Formula")
            
            bahan_dalam_formula = df_formula["Bahan"].tolist()
            col_del1, col_del2, col_del3 = st.columns([2, 1, 1])
            
            with col_del1:
                bahan_hapus = st.selectbox("Pilih bahan yang ingin dikeluarkan:", bahan_dalam_formula)
            with col_del2:
                st.write("") 
                st.write("")
                if st.button("🗑️ Hapus Bahan Ini"):
                    st.session_state.formula = [item for item in st.session_state.formula if item["Bahan"] != bahan_hapus]
                    st.rerun()
            with col_del3:
                st.write("")
                st.write("")
                if st.button("🚨 Hapus Semua Formula"):
                    st.session_state.formula = []
                    st.rerun()

            # --- VISUALISASI DIAGRAM AROMA LINGKARAN & PIRAMIDA ---
            st.markdown("---")
            st.subheader("🕸️ Visualisasi Karakter & Piramida Aroma")
            
            col_viz1, col_viz2 = st.columns(2)
            
            with col_viz1:
                top_score = 0.0
                heart_score = 0.0
                base_score = 0.0
                
                for idx, row in df_formula.iterrows():
                    tipe = str(row["Tipe Note"]).lower()
                    bobot = row["% di Bibit"]
                    
                    if "top" in tipe and "heart" in tipe:
                        top_score += bobot * 0.5
                        heart_score += bobot * 0.5
                    elif "heart" in tipe and "base" in tipe:
                        heart_score += bobot * 0.5
                        base_score += bobot * 0.5
                    elif "top" in tipe:
                        top_score += bobot
                    elif "heart" in tipe:
                        heart_score += bobot
                    elif "base" in tipe:
                        base_score += bobot
                
                df_pyramid = pd.DataFrame({
                    "Tahapan": ["Top Notes (Awal)", "Heart Notes (Tengah)", "Base Notes (Akhir)"],
                    "Persentase": [top_score, heart_score, base_score]
                })
                
                df_pyramid = df_pyramid.iloc[::-1]
                
                if top_score > 0 or heart_score > 0 or base_score > 0:
                    fig_pyr = px.funnel(df_pyramid, x='Persentase', y='Tahapan', 
                                        title="Piramida Aroma Parfum",
                                        color_discrete_sequence=['#b596d6'])
                    st.plotly_chart(fig_pyr, use_container_width=True)
                else:
                    st.write("Belum ada data tipe note untuk membuat piramida.")

            with col_viz2:
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
                    fig = px.pie(df_radar, values='Skor Kekuatan', names='Kategori Aroma', 
                                 title="Komposisi Karakter (Accord)",
                                 hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                    
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("Belum cukup data untuk membentuk profil aroma.")

        # --- FITUR BARU: SIMPAN & MUAT FORMULA (LOAD/SAVE) ---
        st.markdown("---")
        st.subheader("💾 Simpan & Muat Formula (Backup/Restore)")
        st.write("Gunakan fitur ini untuk menyimpan formula Anda ke perangkat, lalu memuatnya kembali di lain waktu.")
        
        col_save1, col_save2 = st.columns(2)
        
        with col_save1:
            st.info("**1. Backup Formula Saat Ini**")
            if st.session_state.formula:
                # Mengubah formula menjadi teks JSON
                formula_json = json.dumps(st.session_state.formula, indent=4)
                st.download_button(
                    label="📥 Download Data Formula (.json)",
                    data=formula_json,
                    file_name="backup_formula_parfum.json",
                    mime="application/json",
                    help="Simpan file ini di HP/Komputer Anda."
                )
            else:
                st.write("⚠️ *Belum ada bahan di formula untuk disimpan.*")
                
        with col_save2:
            st.info("**2. Muat Formula Tersimpan**")
            uploaded_file = st.file_uploader("Pilih file backup formula (.json)", type=["json"])
            if uploaded_file is not None:
                try:
                    loaded_formula = json.load(uploaded_file)
                    if st.button("🔄 Pulihkan Formula Ini"):
                        st.session_state.formula = loaded_formula
                        st.success("🎉 Formula berhasil dipulihkan! Halaman akan dimuat ulang...")
                        st.rerun()
                except Exception as e:
                    st.error("⚠️ File tidak valid atau format rusak.")
    else:
        st.warning("Database bahan baku kosong atau file CSV belum di-upload ke GitHub.")

# --- TAB 2: AI PERFUMER ASSISTANT ---
with tab_ai:
    st.header("🤖 Asisten AI Perfumer")
    st.markdown("Konsultasi formula, cari inspirasi nama, atau dapatkan filosofi parfum Anda.")
    
    formula_context = ""
    if 'formula' in st.session_state and st.session_state.formula:
        df_f = pd.DataFrame(st.session_state.formula)
        df_f = df_f.groupby("Bahan", as_index=False).sum()
        list_bahan = ", ".join([f"{row['Bahan']} ({row['Input']} parts)" for idx, row in df_f.iterrows()])
        formula_context = f"\n\n[INFO SISTEM] Formula parfum yang sedang diracik pengguna saat ini: {list_bahan}."
        
        st.success("✅ AI terhubung dengan Kalkulator. AI sudah mengenali formula yang sedang Anda racik.")
        
        st.markdown("### ✨ Inspirasi Mahakarya")
        if st.button("✨ Hasilkan Nama & Filosofi Parfum Otomatis"):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                with st.spinner("AI sedang merenungkan filosofi wangi racikan Anda..."):
                    prompt_filosofi = f"Saya baru saja meracik parfum dengan bahan-bahan berikut: {list_bahan}. Tolong buatkan 3 pilihan nama parfum yang sangat elegan, mewah, dan berkelas. Untuk setiap nama, tuliskan satu paragraf filosofi/cerita parfum (storytelling) dengan bahasa Indonesia yang sangat puitis, memikat, profesional, dan terasa ditulis oleh manusia sungguhan. Fokus pada emosi, suasana, visual, dan karakter wangi yang dihasilkan dari bahan-bahan tersebut. JANGAN menyebutkan angka persentase."
                    response = model.generate_content(prompt_filosofi)
                    st.markdown("#### Hasil Karya Konseptual Anda:")
                    st.write(response.text)
            except KeyError:
                st.error("⚠️ API Key belum disetel di Secrets.")
            except Exception as e:
                st.error(f"Terjadi kesalahan pada AI: {e}")
    else:
        st.info("💡 Masukkan bahan di Tab Kalkulator agar AI bisa menganalisis racikan Anda dan membuatkan filosofinya.")

    st.markdown("---")
    st.markdown("### 💬 Tanya Jawab Interaktif")
    prompt_user = st.text_area("Tanyakan sesuatu ke AI... (Contoh: 'Bahan apa yang harus saya tambahkan agar racikan ini lebih segar?')")
    
    if st.button("Tanya AI"):
        if not prompt_user:
            st.warning("Silakan ketik pertanyaan Anda.")
        else:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                with st.spinner("AI sedang memikirkan jawaban..."):
                    konteks_system = "Kamu adalah seorang Master Perfumer kelas dunia yang sangat ahli, elegan, dan profesional. "
                    prompt_lengkap = konteks_system + formula_context + "\n\nPertanyaan pengguna: " + prompt_user
                    response = model.generate_content(prompt_lengkap)
                    st.success("Jawaban AI:")
                    st.write(response.text)
            except KeyError:
                st.error("⚠️ API Key belum disetel di menu pengaturan rahasia (Secrets) Streamlit Anda.")
            except Exception as e:
                st.error(f"Terjadi kesalahan pada AI: {e}.")

# --- TAB 3: DATABASE IFRA ---
with tab_db:
    st.header("📚 Database Bahan Baku Profesional")
    if not df_ifra.empty:
        st.dataframe(df_ifra)
