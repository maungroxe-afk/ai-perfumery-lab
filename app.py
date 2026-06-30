import streamlit as st
import pandas as pd
import json
from google import genai
import plotly.express as px
from supabase import create_client, Client

# --- 1. KONFIGURASI ---
SUPABASE_URL = "URL_PROYEK_ANDA"
SUPABASE_KEY = "KEY_PROYEK_ANDA"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="Perfumer Studio Pro", layout="wide", page_icon="🧪")

# --- 2. AUTHENTIKASI ---
if "user" not in st.session_state:
    try: st.session_state.user = supabase.auth.get_user()
    except: st.session_state.user = None

if not st.session_state.user:
    st.title("🔑 Perfumer Studio Pro - Login")
    email = st.text_input("Email"); password = st.text_input("Password", type="password")
    if st.button("Masuk"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user; st.rerun()
        except Exception as e: st.error(f"Login Gagal: {e}")
    st.stop()

# --- 3. FUNGSI DATABASE & AI ---
@st.cache_data(ttl=3600)
def check_ifra(materials, api_key):
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Analisis bahan: {', '.join(materials)}. Berikan IFRA Limit (fine fragrance) format JSON: {{\"Bahan\": \"Limit %\"}}. Jika tidak ada 100%."
        res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return json.loads(res.text.replace("```json", "").replace("```", "").strip())
    except: return None

# --- 4. ANTARMUKA UTAMA ---
st.title("Perfumer Studio Pro")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame({
        "Nama Raw Material": ["Ambroxan", "Bergamot Oil"],
        "Rasio Racikan (%)": [5.0, 10.0],
        "Harga Beli (Rp)": [300000, 150000]
    })

# PENGGABUNGAN SEMUA TAB
tabs = st.tabs(["Editor & IFRA", "Cloud Manager", "Asisten Copilot", "Analisis Accords", "Ensiklopedia", "Riset Harga", "Akuntansi", "Gudang"])

with tabs[0]: # Editor & IFRA Otomatis
    st.session_state.df_data = st.data_editor(st.session_state.df_data, num_rows="dynamic", use_container_width=True)
    if api_key:
        limits = check_ifra(st.session_state.df_data["Nama Raw Material"].tolist(), api_key)
        if limits:
            for _, row in st.session_state.df_data.iterrows():
                limit = float(limits.get(row["Nama Raw Material"], "100%").replace('%', ''))
                if row["Rasio Racikan (%)"] > limit: st.error(f"⚠️ {row['Nama Raw Material']} melebihi limit {limit}%!")
                else: st.success(f"✅ {row['Nama Raw Material']} aman")

with tabs[1]: # Cloud Manager
    name = st.text_input("Nama Formula")
    if st.button("Simpan Formula"):
        supabase.table("formulas").insert({"user_id": st.session_state.user.id, "name": name, "formula_data": st.session_state.df_data.to_json()}).execute()
        st.success("Tersimpan!")
    formulas = supabase.table("formulas").select("*").eq("user_id", st.session_state.user.id).execute().data
    for f in formulas:
        if st.button(f"Muat: {f['name']}"):
            st.session_state.df_data = pd.read_json(f['formula_data']); st.rerun()

with tabs[2]: # Asisten Copilot
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

with tabs[3]: # Analisis Accords
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

with tabs[4]: # Ensiklopedia
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

with tabs[5]: # Riset Harga
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
with tabs[6]: # Akuntansi
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

if st.sidebar.button("Logout"): supabase.auth.sign_out(); st.rerun()
