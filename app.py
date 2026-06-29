import streamlit as st
import pandas as pd
import json
from google import genai
import plotly.express as px

# Konfigurasi halaman dasar
st.set_page_config(page_title="Perfumer Studio", layout="wide")

# --- CUSTOM CSS UNTUK TEMA MINIMALIS & MEWAH ---
st.markdown("""
    <style>
    /* Mengubah font global aplikasi menjadi lebih clean */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Menghilangkan garis pembatas bawaan yang terlalu ramai */
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Desain Kotak Piramida Aroma Minimalis Tanpa Latar Belakang Warna-Warni Ramai */
    .note-box {
        padding: 18px 24px;
        border-radius: 6px;
        border-left: 3px solid #d4af37; /* Warna aksen emas mewah (Gold) */
        background-color: #1a1c23;
        margin-bottom: 12px;
    }
    .note-title {
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #d4af37;
        margin-bottom: 6px;
    }
    .note-content {
        font-size: 0.95rem;
        color: #e4e4e7;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)

# Judul Utama Minimalis
st.title("Perfumer Studio Pro")
st.write("Sistem formulasi presisi, pemetaan karakter aroma otomatis, dan manajemen biaya.")

# --- SIDEBAR: KONFIGURASI AI ---
st.sidebar.header("Konfigurasi API")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("Sistem Terhubung Otomatis")
else:
    api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

st.markdown("<hr>", unsafe_allow_html=True)

# --- 1. KONSENTRASI & UPLOAD DATA ---
st.header("Formulasi Dasar & Unggah Dokumen")
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Target Konsentrasi")
    concentration_type = st.selectbox(
        "Kategori Konsentrasi Target:",
        ["Custom (Ikuti Persentase Tabel 100%)", "Eau de Cologne (EDC - Target Bibit 3%)", "Eau de Toilette (EDT - Target Bibit 10%)", "Eau de Parfum (EDP - Target Bibit 20%)", "Extrait de Parfum (Target Bibit 30%)"],
        label_visibility="collapsed"
    )
    
    target_essential_oil = 0.0
    auto_scale = False
    
    if "EDC" in concentration_type:
        target_essential_oil = 3.0
        auto_scale = True
    elif "EDT" in concentration_type:
        target_essential_oil = 10.0
        auto_scale = True
    elif "EDP" in concentration_type:
        target_essential_oil = 20.0
        auto_scale = True
    elif "Extrait" in concentration_type:
        target_essential_oil = 30.0
        auto_scale = True

with col_g2:
    st.subheader("Berkas Bahan Baku")
    uploaded_file = st.file_uploader("Pilih file data bahan Anda", type=["csv", "xlsx"], label_visibility="collapsed")

# Data template awal bawaan aplikasi
initial_data = {
    "Nama Raw Material": ["Ambroxan", "Bergamot Oil", "Jasmine Absolute", "Cedarwood Oil", "Absolute/Pelarut", "Fixative/Pengikat"],
    "Kategori Notes (Manual/Bebas)": ["Base Notes", "Top Notes", "Heart Notes", "Base Notes", "Solvent / Pelarut", "Fixative / Pengikat"],
    "Volume Dibeli (ml)": [10.0, 50.0, 50.0, 50.0, 1000.0, 100.0],
    "Harga Beli (Rp)": [300000, 150000, 250000, 200000, 120000, 150000],
    "Rasio Racikan (%)": [5.0, 10.0, 10.0, 5.0, 68.0, 2.0]
}
df_template = pd.DataFrame(initial_data)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            uploaded_df = pd.read_csv(uploaded_file)
        else:
            uploaded_df = pd.read_excel(uploaded_file)
        
        rename_dict = {}
        for col in uploaded_df.columns:
            col_clean = str(col).strip().lower()
            if "nama" in col_clean or "material" in col_clean or "bahan" in col_clean:
                rename_dict[col] = "Nama Raw Material"
            elif "kategori" in col_clean or "notes" in col_clean or "jenis" in col_clean:
                rename_dict[col] = "Kategori Notes (Manual/Bebas)"
            elif "volume" in col_clean or "vol" in col_clean:
                rename_dict[col] = "Volume Dibeli (ml)"
            elif "harga" in col_clean or "beli" in col_clean or "modal" in col_clean:
                rename_dict[col] = "Harga Beli (Rp)"
            elif "rasio" in col_clean or "racikan" in col_clean or "persen" in col_clean or "%" in col_clean:
                rename_dict[col] = "Rasio Racikan (%)"
        
        uploaded_df = uploaded_df.rename(columns=rename_dict)
        for required_col in df_template.columns:
            if required_col not in uploaded_df.columns:
                uploaded_df[required_col] = df_template[required_col] if required_col == "Kategori Notes (Manual/Bebas)" else 0.0
        df_template = uploaded_df[df_template.columns]
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")

st.subheader("Matriks Formulasi Komponen")
edited_df = st.data_editor(
    df_template, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Kategori Notes (Manual/Bebas)": st.column_config.SelectboxColumn(
            options=["Top Notes", "Heart Notes", "Base Notes", "Solvent / Pelarut", "Fixative / Pengikat"], required=True
        ),
        "Harga Beli (Rp)": st.column_config.NumberColumn(format="Rp %d"),
        "Volume Dibeli (ml)": st.column_config.NumberColumn(format="%.1f ml"),
        "Rasio Racikan (%)": st.column_config.NumberColumn(format="%.2f %%")
    }
)

# Parsing Tipe Data
edited_df["Volume Dibeli (ml)"] = pd.to_numeric(edited_df["Volume Dibeli (ml)"], errors='coerce').fillna(1.0)
edited_df["Harga Beli (Rp)"] = pd.to_numeric(edited_df["Harga Beli (Rp)"], errors='coerce').fillna(0.0)
edited_df["Rasio Racikan (%)"] = pd.to_numeric(edited_df["Rasio Racikan (%)"], errors='coerce').fillna(0.0)
edited_df["Modal per ml (Rp)"] = edited_df["Harga Beli (Rp)"] / edited_df["Volume Dibeli (ml)"]

total_percentage = edited_df["Rasio Racikan (%)"].sum()
st.markdown("<hr>", unsafe_allow_html=True)

# --- FUNGSI CACHE AI ---
@st.cache_data
def get_ai_complex_accords(materials_list, api_key_input):
    if not api_key_input or not materials_list:
        return {}
    try:
        client = genai.Client(api_key=api_key_input)
        materials_json_input = ", ".join(materials_list)
        prompt = f"Kamu adalah sistem laboratorium perfumery internasional. Tugasmu mengelompokkan molekul raw material ke dalam rumpun aroma utama (Main Accords) yang kompleks berdasarkan profil olfaktori kimiawinya. Daftar komponen: [{materials_json_input}]. Bahan bisa memiliki lebih dari 1 karakter aroma (Maksimal 3). Pilihan kategori aroma resmi: [Citrus, Floral, Woody, Amber, Animalic, Green, Fruity, Musky, Spicy, Sweet / Vanilla, Powdery, Leather, Neutral]. Berikan hasil analisis HANYA dalam bentuk valid JSON object bersih dengan format seperti contoh berikut tanpa markdown codeblock dan tanpa teks penjelasan apa pun: {{\"Ambroxan\": [\"Amber\", \"Musky\"]}}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return {}

# --- ⚙️ LOGIKA OTOMATISASI KONSENTRASI PARFUM ---
fragrance_mask = edited_df["Kategori Notes (Manual/Bebas)"].isin(["Top Notes", "Heart Notes", "Base Notes"])
solvent_mask = edited_df["Kategori Notes (Manual/Bebas)"] == "Solvent / Pelarut"
fixative_mask = edited_df["Kategori Notes (Manual/Bebas)"] == "Fixative / Pengikat"

total_fragrance_tabel_pct = edited_df.loc[fragrance_mask, "Rasio Racikan (%)"].sum()
total_solvent_tabel_pct = edited_df.loc[solvent_mask, "Rasio Racikan (%)"].sum()
total_fixative_tabel_pct = edited_df.loc[fixative_mask, "Rasio Racikan (%)"].sum()

bottle_size_actual = 50.0

edited_df["Vol Needed per Bottle (ml)"] = 0.0
if auto_scale and total_fragrance_tabel_pct > 0:
    target_non_fragrance = 100.0 - target_essential_oil
    for idx, row in edited_df[fragrance_mask].iterrows():
        kontribusi = row["Rasio Racikan (%)"] / total_fragrance_tabel_pct
        edited_df.at[idx, "Vol Needed per Bottle (ml)"] = (kontribusi * target_essential_oil / 100.0) * bottle_size_actual
    total_support_pct = total_solvent_tabel_pct + total_fixative_tabel_pct
    if total_support_pct > 0:
        for idx, row in edited_df[solvent_mask | fixative_mask].iterrows():
            kontribusi = row["Rasio Racikan (%)"] / total_support_pct
            edited_df.at[idx, "Vol Needed per Bottle (ml)"] = (kontribusi * target_non_fragrance / 100.0) * bottle_size_actual
else:
    edited_df["Vol Needed per Bottle (ml)"] = (edited_df["Rasio Racikan (%)"] / 100.0) * bottle_size_actual

edited_df["Persentase Aktual Di Botol (%)"] = (edited_df["Vol Needed per Bottle (ml)"] / bottle_size_actual) * 100

# --- TABS LAYOUT MINIMALIS ---
tab_chat, tab_enc, tab_sec, tab0, tab1, tab2 = st.tabs([
    "Asisten Copilot",
    "Analisis Accords", 
    "Ensiklopedia Bahan", 
    "Riset Estimasi Harga", 
    "Akuntansi Produksi", 
    "Kontrol Stok Gudang"
])

active_materials = edited_df[edited_df["Rasio Racikan (%)"] > 0]["Nama Raw Material"].tolist()
active_materials_with_notes = []
for _, r in edited_df[edited_df["Rasio Racikan (%)"] > 0].iterrows():
    active_materials_with_notes.append(f"{r['Nama Raw Material']} ({r['Kategori Notes (Manual/Bebas)']} - {r['Persentase Aktual Di Botol (%)']:.1f}%)")
formula_summary_string = ", ".join(active_materials_with_notes)

# --- TAB 1: AI FRAGRANCE COPILOT MINIMALIS ELEGAN ---
with tab_chat:
    st.header("Fragrance Copilot & Pyramid Notes")
    
    st.write("### Arsitektur Piramida Olfaktori Aktual")
    
    active_df = edited_df[(edited_df["Rasio Racikan (%)"] > 0) & (edited_df["Kategori Notes (Manual/Bebas)"].isin(["Top Notes", "Heart Notes", "Base Notes"]))]
    
    if not active_df.empty:
        top_list = active_df[active_df["Kategori Notes (Manual/Bebas)"] == "Top Notes"]
        heart_list = active_df[active_df["Kategori Notes (Manual/Bebas)"] == "Heart Notes"]
        base_list = active_df[active_df["Kategori Notes (Manual/Bebas)"] == "Base Notes"]
        
        # Implementasi Kotak Info Premium HTML Minimalis Menggantikan Kotak Berwarna Tebal Lawas
        top_content = ", ".join([f"{r['Nama Raw Material']} ({r['Persentase Aktual Di Botol (%)']:.1f}%)" for _, r in top_list.iterrows()]) if not top_list.empty else "Tidak ada komponen aktif."
        st.markdown(f"""
            <div class="note-box">
                <div class="note-title">Top Notes — 15 Mnt Pertama</div>
                <div class="note-content">{top_content}</div>
            </div>
        """, unsafe_allow_html=True)
        
        heart_content = ", ".join([f"{r['Nama Raw Material']} ({r['Persentase Aktual Di Botol (%)']:.1f}%)" for _, r in heart_list.iterrows()]) if not heart_list.empty else "Tidak ada komponen aktif."
        st.markdown(f"""
            <div class="note-box">
                <div class="note-title">Heart Notes — Inti Formula</div>
                <div class="note-content">{heart_content}</div>
            </div>
        """, unsafe_allow_html=True)
        
        base_content = ", ".join([f"{r['Nama Raw Material']} ({r['Persentase Aktual Di Botol (%)']:.1f}%)" for _, r in base_list.iterrows()]) if not base_list.empty else "Tidak ada komponen aktif."
        st.markdown(f"""
            <div class="note-box">
                <div class="note-title">Base Notes — Jejak Wangi Terlama</div>
                <div class="note-content">{base_content}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Silakan isi komponen bahan aktif pada tabel di atas untuk memetakan arsitektur piramida.")
        
    st.markdown("<hr>", unsafe_allow_html=True)
    st.write("### Narasi Produk & Pengembangan Filosofi")

    if not api_key:
        st.warning("Konfigurasikan API Key pada sidebar untuk mengaktifkan modul asisten cerdas.")
    elif not active_materials:
        st.info("Form formulasi aktif kosong. Masukkan data terlebih dahulu.")
    else:
        if "current_formula_signature" not in st.session_state or st.session_state.current_formula_signature != formula_summary_string:
            st.session_state.current_formula_signature = formula_summary_string
            st.session_state.perfume_chat_history = []
            
            initial_prompt = f"""
            Kamu adalah Master Perfumer dunia dan Head Copywriter Fragrance House mewah. Analisis formula parfum berikut: [{formula_summary_string}]. Jenis Konsentrasi: {concentration_type}.
            Buatkan draf komersial awal dalam format Markdown yang indah dan bersih tanpa menggunakan emoji:
            1. 3 Usulan Nama Eksklusif Varian (Buat nama yang universal, elegan, dan menjual secara komersial).
            2. Narasi Filosofi Produk (2 Paragraf komersial mewah yang menceritakan esensi emosional wewangian ini).
            3. Penjelasan Taktis mengenai struktur kombinasi aroma tersebut.
            """
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model='gemini-2.5-flash', contents=initial_prompt)
                st.session_state.perfume_chat_history.append({"role": "assistant", "text": response.text})
            except Exception as e:
                st.error(f"Gagal memicu analisis awal: {e}")

        for message in st.session_state.perfume_chat_history:
            if message["role"] == "user":
                with st.chat_message("user"): st.write(message["text"])
            else:
                with st.chat_message("assistant"): st.markdown(message["text"])

        user_chat_input = st.chat_input("Ketik perubahan instruksi narasi (Contoh: 'Ubah tema cerita menjadi modern minimalis dengan nuansa clean look')")
        
        if user_chat_input:
            with st.chat_message("user"): st.write(user_chat_input)
            st.session_state.perfume_chat_history.append({"role": "user", "text": user_chat_input})
            
            with st.spinner("Menyusun ulang narasi eksklusif..."):
                try:
                    client = genai.Client(api_key=api_key)
                    conversation_context = f"Konteks Formula Aktif Saat Ini: [{formula_summary_string}]. Target Jenis: {concentration_type}.\n"
                    for msg in st.session_state.perfume_chat_history:
                        conversation_context += f"{'User' if msg['role']=='user' else 'AI'}: {msg['text']}\n"
                    conversation_context += "\nBerikan output revisi terbaru yang rapi dalam format Markdown sesuai permintaan terakhir user tanpa menyertakan emoji."
                    
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=conversation_context)
                    with st.chat_message("assistant"): st.markdown(response.text)
                    st.session_state.perfume_chat_history.append({"role": "assistant", "text": response.text})
                    st.rerun()
                except Exception as e: st.sidebar.error(f"Kesalahan komunikasi sistem: {e}")

# --- TAB ACCORDS PIE CHART ---
with tab_enc:
    st.header("Analisis Kluster Roda Aroma")
    if not api_key: st.warning("Masukkan API Key di sidebar.")
    elif not active_materials: st.info("Masukkan komponen bahan yang aktif di tabel atas.")
    else:
        ai_complex_mapping = get_ai_complex_accords(active_materials, api_key)
        if ai_complex_mapping:
            accord_rows = []
            for idx, row in edited_df.iterrows():
                mat_name = row["Nama Raw Material"]
                pct_val = row["Persentase Aktual Di Botol (%)"]
                if mat_name in ai_complex_mapping and pct_val > 0:
                    assigned_accords = ai_complex_mapping[mat_name]
                    num_accords = len(assigned_accords)
                    if num_accords == 1:
                        accord_rows.append({"Accords": assigned_accords[0], "Persentase Raw": pct_val})
                    elif num_accords == 2:
                        accord_rows.append({"Accords": assigned_accords[0], "Persentase Raw": pct_val * 0.65})
                        accord_rows.append({"Accords": assigned_accords[1], "Persentase Raw": pct_val * 0.35})
                    elif num_accords == 3:
                        accord_rows.append({"Accords": assigned_accords[0], "Persentase Raw": pct_val * 0.50})
                        accord_rows.append({"Accords": assigned_accords[1], "Persentase Raw": pct_val * 0.30})
                        accord_rows.append({"Accords": assigned_accords[2], "Persentase Raw": pct_val * 0.20})
            if accord_rows:
                accords_df = pd.DataFrame(accord_rows)
                accords_df = accords_df[accords_df["Accords"] != "Neutral"]
                if not accords_df.empty:
                    total_pure_fragrance_sum = accords_df["Persentase Raw"].sum()
                    if total_pure_fragrance_sum > 0:
                        accords_df["Persentase Aroma Komposisi (%)"] = (accords_df["Persentase Raw"] / total_pure_fragrance_sum) * 100
                        final_chart_data = accords_df.groupby("Accords")["Persentase Aroma Komposisi (%)"].sum().reset_index()
                        final_chart_data = final_chart_data.sort_values(by="Persentase Aroma Komposisi (%)", ascending=False)
                        
                        # Mengubah palet warna grafik lingkaran menjadi monokrom/muted tone agar terkesan mahal
                        fig = px.pie(final_chart_data, values="Persentase Aroma Komposisi (%)", names="Accords", hole=0.5, color_discrete_sequence=px.colors.sequential.Burgyl)
                        fig.update_traces(textinfo="percent+label", textposition="outside")
                        st.plotly_chart(fig, use_container_width=True)

# --- TAB ENSIKLOPEDIA ---
with tab_sec:
    st.header("Ensiklopedia Komponen & Batas Regulasi")
    if not api_key: st.warning("Masukkan API Key.")
    else:
        safety_search = st.text_input("Nama komponen kimia aroma atau minyak atsiri murni:")
        if st.button("Analisis Karakteristik Bahan"):
            with st.spinner("Mengambil berkas data laboratorium..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"Perfumer senior. Jelaskan bahan: {safety_search}. Output: 1. Karakteristik Aroma, 2. Persentase Aman Kulit, 3. Risiko Alergi."
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    st.markdown(response.text)
                except Exception as e: st.error(f"Eror: {e}")

# --- TAB RISET HARGA ---
with tab0:
    st.header("Analisis Estimasi Nilai Pasar Bahan Baku")
    if not api_key: st.warning("Masukkan API Key.")
    else:
        search_material = st.text_input("Nama bahan wewangian murni komersial:")
        if st.button("Cek Evaluasi Pasar"):
            with st.spinner("Menghubungkan ke jaringan pemasok lokal..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"Konsultan pengadaan Indonesia. Bahan: {search_material}. Analisis: 1. Perkiraan Harga Lokal, 2. Mutu, 3. Seller tepercaya."
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    st.markdown(response.text)
                except Exception as e: st.error(f"Eror: {e}")

# --- TAB HPP & LABA ---
with tab1:
    st.header("Kalkulasi Keuangan & Margin Laba Komersial")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        bottle_size = st.number_input("Ukuran Botol (ml)", min_value=5, value=50, key="bs")
        price_bottle = st.number_input("Biaya Kemasan + Stiker (per pcs)", min_value=0, value=6000, key="pb")
    with col_f2:
        pricing_method = st.radio("Metode Penentuan Harga Jual:", ["Target Markup (Kenaikan dari Modal)", "Target Margin Laba Kotor (%)"], key="pm")
        if pricing_method == "Target Markup (Kenaikan dari Modal)":
            markup_pct = st.slider("Persentase Kenaikan Harga (%)", 50, 500, 200, step=10, key="mp")
        else:
            margin_pct = st.slider("Target Margin Laba Kotor (%)", 10, 90, 60, step=5, key="map")

    edited_df["Vol Needed per Bottle (ml)"] = (edited_df["Persentase Aktual Di Botol (%)"] / 100.0) * bottle_size
    edited_df["Cost per Bottle (Rp)"] = edited_df["Vol Needed per Bottle (ml)"] * edited_df["Modal per ml (Rp)"]
    total_liquid_cost_per_bottle = edited_df["Cost per Bottle (Rp)"].sum()
    hpp_per_bottle = total_liquid_cost_per_bottle + price_bottle

    if pricing_method == "Target Markup (Kenaikan dari Modal)":
        suggested_price = hpp_per_bottle * (1 + (markup_pct / 100))
    else:
        suggested_price = hpp_per_bottle / (1 - (margin_pct / 100)) if margin_pct < 100 else hpp_per_bottle

    max_bottles_list = []
    for idx, row in edited_df.iterrows():
        if row["Vol Needed per Bottle (ml)"] > 0:
            max_bottles_list.append(row["Volume Dibeli (ml)"] // row["Vol Needed per Bottle (ml)"])
    auto_max_production = int(min(max_bottles_list)) if max_bottles_list else 0

    st.markdown("<hr>", unsafe_allow_html=True)
    st.write(f"### Kapasitas Batch Maksimal: **{auto_max_production} Botol** ({bottle_size} ml)")

    total_production_cost = hpp_per_bottle * auto_max_production
    total_revenue = suggested_price * auto_max_production
    total_profit = total_revenue - total_production_cost

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.write("**Rincian Kebutuhan Volume Batch:**")
        for _, row in edited_df.iterrows():
            if row["Vol Needed per Bottle (ml)"] > 0:
                total_vol_batch = row["Vol Needed per Bottle (ml)"] * auto_max_production
                st.write(f"* {row['Nama Raw Material']}: {row['Vol Needed per Bottle (ml)']:.2f} ml/botol (Total Batch: {total_vol_batch:.1f} ml)")
        
    with col_res2:
        st.metric(label="Harga Pokok Penjualan (HPP) / Pcs", value=f"Rp {hpp_per_bottle:,.0f}")
        st.metric(label="Rekomendasi Harga Jual Eksklusif", value=f"Rp {suggested_price:,.0f}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.write("### Proyeksi Neraca Profitabilitas Batch")
    p_col1, p_col2, p_col3 = st.columns(3)
    p_col1.metric(label="Total Investasi Modal Batch", value=f"Rp {total_production_cost:,.0f}")
    p_col2.metric(label="Estimasi Pendapatan Kotor", value=f"Rp {total_revenue:,.0f}")
    p_col3.metric(label="Estimasi Batas Net Profit", value=f"Rp {total_profit:,.0f}")

# --- TAB STOCK GUDANG ---
with tab2:
    st.header("Optimasi Bahan & Neraca Gudang")
    stok_list = []
    opt_cols = st.columns(2)
    count = 0
    for idx, row in edited_df.iterrows():
        if row["Vol Needed per Bottle (ml)"] > 0:
            current_col = opt_cols[0] if count % 2 == 0 else opt_cols[1]
            user_stok = current_col.number_input(f"Sisa Stok Gudang Berjalan: {row['Nama Raw Material']} (ml)", min_value=0.0, value=float(row['Volume Dibeli (ml)']), key=f"stok_v23_{idx}")
            stok_list.append((row['Nama Raw Material'], user_stok, row['Vol Needed per Bottle (ml)']))
            count += 1
    if stok_list:
        max_bottles_possible = [stok // vol if vol > 0 else float('inf') for _, stok, vol in stok_list]
        final_max_production = int(min(max_bottles_possible)) if max_bottles_possible else 0
        st.info(f"Kapasitas sisa stok gudang berjalan: {final_max_production} botol.")
