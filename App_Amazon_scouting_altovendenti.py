import streamlit as st
import pandas as pd
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Amazon Radar", page_icon="📈", layout="wide")

# --- INIZIALIZZAZIONE MEMORIA (SESSION STATE) ---
if 'libri_salvati' not in st.session_state:
    st.session_state.libri_salvati = set()

# --- FUNZIONE DI CARICAMENTO DATI ---
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

# Funzione callback per il pulsante "Cuore"
def toggle_salvataggio(asin):
    if asin in st.session_state.libri_salvati:
        st.session_state.libri_salvati.remove(asin)
    else:
        st.session_state.libri_salvati.add(asin)

# --- INTESTAZIONE ---
st.title("📈 Bestseller Amazon")
st.caption("Esplora i libri più recensiti e salva quelli più interessanti.")

file_amazon = "amazon_libri_multicat.csv"
df_amz = load_amazon_data(file_amazon)

if df_amz is None:
    st.warning("⚠️ Dati Amazon non ancora disponibili. Attendi che lo scraper generi il file CSV.")
else:
    # ==========================================
    # SIDEBAR: FILTRI E SALVATI
    # ==========================================
    st.sidebar.header("🛠️ Filtri Amazon")
    
    categorie_disponibili = ["Tutte"] + sorted(df_amz['Categoria'].unique().tolist())
    sel_cat_amz = st.sidebar.selectbox("Filtra per Categoria:", categorie_disponibili)
    
    max_recensioni = int(df_amz['Recensioni'].max()) if not df_amz.empty else 1000
    min_recensioni_filtro = st.sidebar.slider(
        "Minimo Recensioni:", 
        min_value=0, max_value=max_recensioni, value=60, step=50
    )

    st.sidebar.markdown("---")
    st.sidebar.header("💾 I tuoi salvataggi")
    
    mostra_solo_salvati = st.sidebar.checkbox(f"Mostra solo i salvati ({len(st.session_state.libri_salvati)})")
    
    if len(st.session_state.libri_salvati) > 0:
        if st.sidebar.button("🗑️ Svuota lista salvati"):
            st.session_state.libri_salvati.clear()
            st.rerun()

    # ==========================================
    # ELABORAZIONE DATI (FILTRI)
    # ==========================================
    df_filtrato = df_amz.copy()
    
    if mostra_solo_salvati:
        df_filtrato = df_filtrato[df_filtrato['ASIN'].isin(st.session_state.libri_salvati)]
    else:
        if sel_cat_amz != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['Categoria'] == sel_cat_amz]
        df_filtrato = df_filtrato[df_filtrato['Recensioni'] >= min_recensioni_filtro]
        
    df_filtrato = df_filtrato.sort_values(by='Recensioni', ascending=False)

    st.info(f"Mostrando **{len(df_filtrato)}** libri.")

    # ==========================================
    # RENDERING A GRIGLIA ALLINEATA (3 COLONNE)
    # ==========================================
    # Convertiamo il dataframe in una lista per iterarlo a blocchi di 3
    lista_libri = list(df_filtrato.iterrows())
    
    # Creiamo una nuova riga (row) ogni 3 libri, così le card sono sempre allineate in alto
    for i in range(0, len(lista_libri), 3):
        cols = st.columns(3)
        
        # Riempiamo le 3 colonne della riga corrente
        for j in range(3):
            if i + j < len(lista_libri):
                index, row_data = lista_libri[i + j]
                asin = row_data.get('ASIN', '')
                is_saved = asin in st.session_state.libri_salvati
                
                with cols[j]:
                    with st.container(border=True):
                        
                        # Sotto-colonne per mettere il cuore in alto a destra rispetto al titolo
                        c_titolo, c_cuore = st.columns([5, 1])
                        
                        with c_cuore:
                            st.button(
                                "❤️" if is_saved else "🤍", 
                                key=f"btn_{asin}", 
                                on_click=toggle_salvataggio, 
                                args=(asin,),
                                help="Salva/Rimuovi dalla tua lista"
                            )
                            
                        with c_titolo:
                            # Titolo più piccolo (solo grassetto anziché subheader) e separatore
                            st.markdown(f"**{row_data['Titolo']}**")
                        
                        st.markdown("---")
                        
                        # Copertina
                        url = row_data['Copertina']
                        if pd.notna(url) and str(url).startswith('http'):
                            st.image(str(url), width=120)
                        else:
                            st.markdown("🖼️ *No Img*")
                        
                        # Info Libro senza l'emoji della mano
                        st.markdown(f"**{row_data.get('Autore', 'N/D')}**")
                        st.markdown(f"📊 **{int(row_data['Recensioni'])}** recensioni")
                        st.caption(f"🏷️ {row_data.get('Categoria', 'N/D')} | 📅 {row_data.get('Data', 'N/D')}")
                        
                        # Link
                        amz_link = f"https://www.amazon.it/dp/{asin}" if pd.notna(asin) else "#"
                        st.markdown(f"[🛒 Apri su Amazon]({amz_link})")
                        
