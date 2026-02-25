import streamlit as st
import pandas as pd
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Radar Editoria", page_icon="📚", layout="wide")

# --- FUNZIONI DI CARICAMENTO DATI (CON CACHE) ---
@st.cache_data(ttl=3600)
def load_ibs_data(file_name):
    if not os.path.exists(file_name):
        return None
    try:
        df = pd.read_csv(file_name)
        df['Titolo'] = df['Titolo'].fillna("Senza Titolo")
        df['Editore'] = df['Editore'].fillna("N/D")
        if 'Nuovo' not in df.columns:
            df['Nuovo'] = False
        else:
            df['Nuovo'] = df['Nuovo'].astype(bool)
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def load_amazon_data(file_name):
    if not os.path.exists(file_name):
        return None
    try:
        df = pd.read_csv(file_name)
        df['Titolo'] = df['Titolo'].fillna("Senza Titolo")
        df['Autore'] = df['Autore'].fillna("N/D")
        return df
    except Exception as e:
        return None

# --- MENU LATERALE PER LA NAVIGAZIONE ---
st.sidebar.title("🧭 Navigazione")
sezione = st.sidebar.radio("Scegli la dashboard:", ["📚 Novità (IBS)", "📈 Bestseller (Amazon)"])
st.sidebar.markdown("---")

# ==========================================
# SEZIONE 1: NOVITÀ IBS
# ==========================================
if sezione == "📚 Novità (IBS)":
    st.title("📚 Novità Saggistica (IBS)")
    
    file_ibs = "dati_per_app.csv"
    df_ibs = load_ibs_data(file_ibs)

    if df_ibs is None:
        st.error(f"⚠️ File '{file_ibs}' non trovato! Attendi l'aggiornamento automatico.")
    else:
        # Notifica Nuovi Arrivi
        nuovi_libri = df_ibs[df_ibs['Nuovo'] == True]
        num_nuovi = len(nuovi_libri)
        if num_nuovi > 0:
            st.success(f"🔔 **Aggiornamento:** Ci sono **{num_nuovi}** nuovi libri rispetto all'ultimo controllo!")
            with st.expander(f"👀 Vedi la lista dei {num_nuovi} nuovi arrivi"):
                for _, row in nuovi_libri.iterrows():
                    st.markdown(f"🆕 **{row['Titolo']}** - {row['Autore']} ({row['Editore']})")

        # Separazione Dati
        df_vip = df_ibs[df_ibs['Categoria_App'] == 'Editori Selezionati'].copy()
        df_altri = df_ibs[df_ibs['Categoria_App'] != 'Editori Selezionati'].copy()

        # Filtri Sidebar per IBS
        st.sidebar.header("🛠️ Strumenti IBS")
        search_query = st.sidebar.text_input("🔍 Cerca libro o autore")
        
        st.sidebar.subheader("Filtra Selezionati")
        editori_disponibili = sorted(df_vip['Editore'].unique())
        sel_editore = st.sidebar.multiselect("Seleziona Editore", editori_disponibili)
        
        sort_mode = st.sidebar.selectbox("Ordina per:", ["Titolo (A-Z)", "Titolo (Z-A)", "Editore (A-Z)", "Editore (Z-A)"])

        # Applicazione Filtri IBS
        if search_query:
            mask_vip = df_vip.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            df_vip = df_vip[mask_vip]
            mask_altri = df_altri.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            df_altri = df_altri[mask_altri]

        if sel_editore:
            df_vip = df_vip[df_vip['Editore'].isin(sel_editore)]

        if sort_mode == "Titolo (A-Z)": df_vip = df_vip.sort_values(by='Titolo', ascending=True)
        elif sort_mode == "Titolo (Z-A)": df_vip = df_vip.sort_values(by='Titolo', ascending=False)
        elif sort_mode == "Editore (A-Z)": df_vip = df_vip.sort_values(by='Editore', ascending=True)
        elif sort_mode == "Editore (Z-A)": df_vip = df_vip.sort_values(by='Editore', ascending=False)

        # Rendering Tabs
        tab1, tab2 = st.tabs([f"⭐ Editori Selezionati ({len(df_vip)})", f"📂 Altri Editori ({len(df_altri)})"])

        with tab1:
            if df_vip.empty: st.info("Nessun libro trovato con i filtri attuali.")
            for _, row in df_vip.iterrows():
                with st.container():
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        url = row['Copertina']
                        if pd.notna(url) and str(url).startswith('http'): st.image(str(url), width=120)
                        else: st.text("🖼️ No Img")
                    with c2:
                        badge = "🆕 " if row.get('Nuovo', False) else ""
                        st.subheader(f"{badge}{row['Titolo']}")
                        st.markdown(f"**{row.get('Autore', 'N/D')}** | *{row.get('Editore', 'N/D')}* ({row.get('Anno', '')})")
                        desc = str(row.get('Descrizione', ''))
                        if len(desc) > 10 and desc.lower() != "nan":
                            with st.expander("📖 Leggi trama"): st.write(desc)
                        link = row.get('Link')
                        if pd.notna(link) and str(link).startswith('http'): st.markdown(f"[➡️ Vedi su IBS]({link})")
                    st.divider()

        with tab2:
            if df_altri.empty: st.info("Nessun libro in questa categoria.")
            for _, row in df_altri.iterrows():
                with st.container():
                    c_img, c_info = st.columns([0.5, 5])
                    with c_img:
                        url = row['Copertina']
                        if pd.notna(url) and str(url).startswith('http'): st.image(str(url), width=60)
                    with c_info:
                        badge = "🆕 " if row.get('Nuovo', False) else ""
                        st.markdown(f"{badge}**{row['Titolo']}**")
                        st.markdown(f"{row.get('Autore', 'N/D')} - *{row.get('Editore', 'N/D')}*")
                        link = row.get('Link')
                        if pd.notna(link) and str(link).startswith('http'): st.markdown(f"[Link]({link})")
                    st.markdown("---")

# ==========================================
# SEZIONE 2: BESTSELLER AMAZON
# ==========================================
elif sezione == "📈 Bestseller (Amazon)":
    st.title("📈 I più recensiti su Amazon")
    st.caption("Stima delle copie vendute in base al volume di recensioni accumulate.")

    file_amazon = "amazon_libri_multicat.csv"
    df_amz = load_amazon_data(file_amazon)

    if df_amz is None:
        st.warning("⚠️ Dati Amazon non ancora disponibili. L'app è pronta, attendi che lo scraper generi il primo file CSV.")
    else:
        # Filtri Sidebar per Amazon
        st.sidebar.header("🛠️ Filtri Amazon")
        
        # Filtro Categoria
        categorie_disponibili = ["Tutte"] + sorted(df_amz['Categoria'].unique().tolist())
        sel_cat_amz = st.sidebar.selectbox("Filtra per Categoria:", categorie_disponibili)
        
        # Filtro Minimo Recensioni
        max_recensioni = int(df_amz['Recensioni'].max())
        min_recensioni_filtro = st.sidebar.slider(
            "Minimo Recensioni:", 
            min_value=0, max_value=max_recensioni, value=60, step=50
        )

        # Applicazione filtri Amazon
        if sel_cat_amz != "Tutte":
            df_amz = df_amz[df_amz['Categoria'] == sel_cat_amz]
        
        df_amz = df_amz[df_amz['Recensioni'] >= min_recensioni_filtro]
        
        # Ordinamento (sempre per numero recensioni decrescente)
        df_amz = df_amz.sort_values(by='Recensioni', ascending=False)

        st.info(f"Mostrando **{len(df_amz)}** libri che superano i filtri.")

        # Rendering Lista Amazon
        for _, row in df_amz.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 6])
                
                with c1:
                    url = row['Copertina']
                    if pd.notna(url) and str(url).startswith('http'):
                        st.image(str(url), width=100)
                    else:
                        st.text("🖼️ No Img")
                
                with c2:
                    st.subheader(row['Titolo'])
                    st.markdown(f"**{row.get('Autore', 'N/D')}**")
                    
                    # Generazione Link Amazon dinamico dall'ASIN
                    asin = row.get('ASIN', '')
                    amz_link = f"https://www.amazon.it/dp/{asin}" if pd.notna(asin) else "#"
                    
                    # Metriche visive
                    st.markdown(f"📊 **{int(row['Recensioni'])}** recensioni | 🏷️ Categoria: *{row.get('Categoria', 'N/D')}* | 📅 Data: {row.get('Data', 'N/D')}")
                    st.markdown(f"[🛒 Vedi su Amazon]({amz_link})")
                    
                st.divider()
        
