import streamlit as st
import pandas as pd
import json
from google import genai
import plotly.express as px
from supabase import create_client, Client

# ==============================================================================
# 1. KONFIGURASI SUPABASE (KREDENSIAL PROYEK ANDA)
# ==============================================================================
SUPABASE_URL = "https://gsnkaocpxqccwgvyttbv.supabase.co"
SUPABASE_KEY = "sb_publishable_OwoDrB5hvUEXJt6krNZAug_DD6bpLbJ"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Gagal inisialisasi Supabase. Periksa URL dan Key Anda. Error: {e}")

# Konfigurasi halaman dasar
st.set_page_config(page_title="Perfumer Studio Pro", layout="wide")

# ==============================================================================
# 2. SISTEM MANAJEMEN SESI & AUTENTIKASI PENGGUNA
# ==============================================================================
if "user" not in st.session_state:
    try:
        # Coba ambil session aktif yang tersimpan otomatis di browser cache
        st.session_state.user = supabase.auth.get_user()
    except:
        st.session_state.user = None

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.success("Login Berhasil!")
        st.rerun()
    except Exception as e:
        st.error(f"Login Gagal: {e}")

def sign_up(email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        st.success("Akun berhasil dibuat! Silakan langsung login menggunakan akun tersebut.")
    except Exception as e:
        st.error(f"Pendaftaran Gagal: {e}")

# Tampilan Halaman Login / Registrasi jika belum terautentikasi
if not st.session_state.user or not hasattr(st.session_state.user, 'id'):
    st.title("🔑 Akses Perfumer Studio Pro")
    tab_auth1, tab_auth2 = st.tabs(["Masuk (Login)", "Daftar Akun Baru"])
    
    with tab_auth1:
        email_input = st.text_input("Email", key="login_email_auth")
        pass_input = st.text_input("Password", type="password", key="login_pass_auth")
        if st.button("Masuk", use_container_width=True):
            login(email_input, pass_input)
            
    with tab_auth2:
        new_email = st.text_input("Email Baru", key="reg_email_auth")
        new_pass = st.text_input("Password Baru", type="password", key="reg_pass_auth")
        if st.button("Daftar Sekarang", use_container_width=True):
            sign_up(new_email, new_pass)
            
    st.stop() # Menghentikan rendering sisa aplikasi jika belum login

# ==============================================================================
# 3. FUNGSI DATABASE (SIMPAN, AMBIL, & MUAT FORMULA)
# ==============================================================================
def save_formula_to_db(name, df):
    try:
        data = {
            "user_id": st.session_state.user.id,
            "name": name,
            "formula_data": df.to_json()
        }
        supabase.table("formulas").insert(data).execute()
        st.success(f"Formula '{name}' berhasil disimpan ke database cloud!")
    except Exception as e:
        st.error(f"Gagal menyimpan formula: {e}")

def get_user_formulas():
    try:
        res = supabase.table("formulas").select("*").eq("user_id", st.session_state.user.id).execute()
        return res.data
    except Exception as e:
        st.sidebar.error(f"Gagal mengambil daftar formula: {e}")
        return []

def load_formula_from_db(formula_id):
    try:
        res = supabase.table("formulas").select("formula_data").eq("id", formula_id).single().execute()
        if res.data:
            return pd.read_json(res.data['formula_data'])
    except Exception as e:
        st.error(f"Gagal memuat detail data dari database: {e}")
    return None

# ==============================================================================
# 4. CUSTOM CSS UNTUK TEMA MINIMALIS & MEWAH
# ==============================================================================
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .note-box {
        padding: 18px 24px;
        border-radius: 6px;
        border-left: 3px solid #d4af37; 
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

# Sidebar Sesi Pengguna & Log out
st.sidebar.subheader("Sesi Pengguna")
st.sidebar.info(f"📧 {st.session_state.user.email}")
if st.sidebar.button("Keluar (Logout)", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

st.sidebar.markdown("---")

# Judul Utama Aplikasi
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

# ==============================================================================
# 5. INISIALISASI & INPUT DATA FORMULASI
# ==============================================================================
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

# Data template awal bawaan aplikasi di simpan dalam session state agar presisten saat load data
if "df_template" not in st.session_state:
    initial_data = {
        "Nama Raw Material": ["Ambroxan", "Bergamot Oil", "Jasmine Absolute", "Cedarwood Oil", "Absolute/Pelarut", "Fixative/Pengikat"],
        "Kategori Notes (Manual/Bebas)": ["Base Notes", "Top Notes", "Heart Notes", "Base Notes", "Solvent / Pelarut", "Fixative / Pengikat"],
        "Volume Dibeli (ml)": [10.0, 50.0, 50.0, 50.0, 1000.0, 100.0],
        "Harga Beli (Rp)": [300000, 150000, 250000, 200000, 120000, 150000],
        "Rasio Racikan (%)": [5.0, 10.0, 10.0, 5.0, 68.0, 2.0]
    }
    st.session_state.df_template = pd.DataFrame(initial_data)

with col_g2:
    st.subheader("Berkas Bahan Baku")
    uploaded_file = st.file_uploader("Pilih file data bahan Anda", type=["csv", "xlsx"], label_visibility="collapsed")

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
        for required_col in st.session_state.df_template.columns:
            if required_col not in uploaded_df.columns:
                uploaded_df[required_col] = st.session_state.df_template[required_col] if required_col == "Kategori Notes (Manual/Bebas)" else 0.0
        st.session_state.df_template = uploaded_df[st.session_state.df_template.columns]
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")

st.subheader("Matriks Formulasi Komponen")
edited_df = st.data_editor(
    st.session_state.df_template, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Kategori Notes (Manual/Bebas)": st.column_config.SelectboxColumn(
            options=["Top Notes", "Heart Notes", "Base Notes", "Solvent / Pelarut", "Fixative / Pengikat"], required=True
        ),
        "Harga Beli (Rp)": st.column_config.NumberColumn(format="Rp %d", min_value=0),
        "Volume Dibeli (ml)": st.column_config.NumberColumn(format="%.1f ml", min_value=0.1),
        "Rasio Racikan (%)": st.column_config.NumberColumn(format="%.2f %%", min_value=0.0, max_value=100.0)
    }
)

# Parsing Tipe Data & Perhitungan Atribut Dasar
edited_df["Volume Dibeli (ml)"] = pd.to_numeric(edited_df["Volume Dibeli (ml)"], errors='coerce').fillna(1.0)
edited_df["Harga Beli (Rp)"] = pd.to_numeric(edited_df["Harga Beli (Rp)"], errors='coerce').fillna(0.0)
edited_df["Rasio Racikan (%)"] = pd.to_numeric(edited_df["Rasio Racikan (%)"], errors='coerce').fillna(0.0)
edited_df["Modal per ml (Rp)"] = edited_df["Harga Beli (Rp)"] / edited_df["Volume Dibeli (ml)"]
total_percentage = edited_df["Rasio Racikan (%)"].sum()

# ==============================================================================
# LOGIKA OTOMATISASI KONSENTRASI PARFUM (DIPINDAHKAN KE ATAS DEMI AKURASI IFRA)
# ==============================================================================
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

# ==============================================================================
# PENGECEKAN KEAMANAN IFRA AUTOMATIC AI (KUMULATIF PRODUK JADI DI ATAS TAB)
# ==============================================================================
@st.cache_data(ttl=3600)
def check_ifra_safety(materials_list, api_key_input):
    if not api_key_input or not materials_list:
        return None
    try:
        client = genai.Client(api_key=api_key_input)
        materials_str = ", ".join(materials_list)
        prompt = f"""
        Analisis bahan parfum: {materials_str}. 
        Berikan batas aman IFRA kategori fine fragrance dalam persentase format JSON: {{"Nama Bahan": "Limit %"}}. 
        PENTING: 
        1. Gunakan nama bahan PERSIS seperti yang diinput, jangan diubah ejaannya.
        2. Jika aman/tidak dibatasi, tulis "100%". 
        3. Output HANYA JSON valid tanpa teks markdown.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception:
        return None

if api_key:
    active_df = edited_df[edited_df["Persentase Aktual Di Botol (%)"] > 0]
    if not active_df.empty:
        akumulasi_bahan = active_df.groupby("Nama Raw Material")["Persentase Aktual Di Botol (%)"].sum().reset_index()
        active_mats = akumulasi_bahan["Nama Raw Material"].tolist()
        
        with st.spinner("AI sedang memverifikasi total kumulatif batas aman IFRA pada produk jadi..."):
            ifra_limits = check_ifra_safety(active_mats, api_key)
            if ifra_limits:
                has_warning = False
                for _, row in akumulasi_bahan.iterrows():
                    bahan = row["Nama Raw Material"]
                    limit_str = ifra_limits.get(bahan, "100%")
                    try:
                        limit_val = float(str(limit_str).replace('%', '').strip())
                    except ValueError:
                        limit_val = 100.0
                    
                    kadar_aktual = row["Persentase Aktual Di Botol (%)"]
                    
                    if kadar_aktual > limit_val:
                        st.error(f"⚠️ PERINGATAN IFRA: '{bahan}' melebihi batas aman! (Total kumulatif di Produk Jadi: {kadar_aktual:.2f}% | Batas Maksimal IFRA: {limit_val}%)")
                        has_warning = True
                
                if not has_warning:
                    st.success("✅ Seluruh total komposisi bahan di dalam produk jadi telah memenuhi standar aman IFRA.")

# ==============================================================================
# 6. EXPANDER: MANAJEMEN PENYIMPANAN CLOUD DATABASE
# ==============================================================================
with st.expander("💾 Manajemen Penyimpanan Database Formula Cloud"):
    col_db1, col_db2 = st.columns(2)
    
    with col_db1:
        st.write("**Simpan Racikan Aktif**")
        formula_name_input = st.text_input("Beri Nama Formula Anda:")
        if st.button("Simpan Permanen ke Database", use_container_width=True):
            if formula_name_input.strip() != "":
                save_formula_to_db(formula_name_input, edited_df)
            else:
                st.error("Nama formula tidak boleh kosong untuk dapat disimpan.")
                
    with col_db2:
        st.write("**Muat Riwayat Formula Anda**")
        user_saved_formulas = get_user_formulas()
        if user_saved_formulas:
            formula_options = {f['name']: f['id'] for f in user_saved_formulas}
            selected_formula_name = st.selectbox("Pilih formula lama untuk ditarik:", options=list(formula_options.keys()))
            
            if st.button("Tarik & Ganti Formulasi Utama", use_container_width=True):
                target_id = formula_options[selected_formula_name]
                retrieved_df = load_formula_from_db(target_id)
                if retrieved_df is not None:
                    st.session_state.df_template = retrieved_df
                    st.success(f"Formula '{selected_formula_name}' berhasil dimuat!")
                    st.rerun()
        else:
            st.info("Belum ada formula yang disimpan oleh akun ini.")

st.markdown("<hr>", unsafe_allow_html=True)

# --- FUNGSI CACHE AI ANCHOR ---
@st.cache_data(ttl=3600)
def get_ai_complex_accords(materials_list, api_key_input):
    if not api_key_input or not materials_list:
        return None
    
    try:
        client = genai.Client(api_key=api_key_input)
        materials_json_input = ", ".join(materials_list)
        
        prompt = (
            f"Analisis daftar bahan parfum berikut: [{materials_json_input}]. "
            "Kelompokkan ke dalam kategori: [Citrus, Floral, Woody, Amber, Animalic, Green, Fruity, Musky, Spicy, Sweet, Powdery, Leather]. "
            "Berikan output HANYA berupa JSON valid tanpa markdown atau teks penjelasan. "
            "Contoh format: {\"Ambroxan\": [\"Amber\"], \"Peach\": [\"Fruity\"]}"
        )
        
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
        
    except Exception as e:
        st.sidebar.error(f"Koneksi API Gagal: {str(e)}")
        return None

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
                    st.session_state.perfume_chat_history.append({"role": "assistant", "text": response.text})
                    st.rerun()
                except Exception as e: st.sidebar.error(f"Kesalahan komunikasi sistem: {e}")

# --- TAB ACCORDS PIE CHART ---
with tab_enc:
    st.header("Analisis Kluster Roda Aroma")
    
    if not api_key:
        st.warning("Masukkan API Key di sidebar untuk mengaktifkan analisis AI.")
    elif edited_df[edited_df["Rasio Racikan (%)"] > 0].empty:
        st.info("Silakan masukkan data bahan dan rasio racikan pada tabel utama untuk melihat roda aroma.")
    else:
        with st.spinner("Menganalisis profil olfaktori..."):
            ai_complex_mapping = get_ai_complex_accords(active_materials, api_key)
            
            if ai_complex_mapping:
                accord_rows = []
                for _, row in edited_df.iterrows():
                    mat_name = row["Nama Raw Material"]
                    pct_val = row["Persentase Aktual Di Botol (%)"]
                    if mat_name in ai_complex_mapping and pct_val > 0:
                        assigned_accords = ai_complex_mapping[mat_name]
                        share = pct_val / len(assigned_accords)
                        for accord in assigned_accords:
                            accord_rows.append({"Accords": accord, "Persentase": share})
                
                if accord_rows:
                    accords_df = pd.DataFrame(accord_rows)
                    final_chart_data = accords_df.groupby("Accords")["Persentase"].sum().reset_index()
                    
                    fig = px.pie(
                        final_chart_data, 
                        values="Persentase", 
                        names="Accords", 
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    
                    fig.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.success("Analisis profil aroma berhasil dipetakan.")
                else:
                    st.error("Data aroma tidak dapat dikelompokkan. Pastikan bahan baku sudah terisi dengan benar.")
            else:
                st.error("Gagal mendapatkan respons dari sistem AI. Periksa koneksi API Anda.")
                
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
