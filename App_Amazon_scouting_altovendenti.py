import streamlit as st
import pandas as pd
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Amazon Radar", page_icon="📈", layout="wide")

# --- INIZIALIZZAZIONE MEMORIA (SESSION STATE) ---
# Usiamo un "set" per memorizzare gli ASIN dei libri salvati senza duplicati
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

# Funzione callback per il pulsante "Salva/Rimuovi"
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
    
    # Checkbox per filtrare solo i libri salvati
    mostra_solo_salvati = st.sidebar.checkbox(f"Mostra solo i salvati ({len(st.session_state.libri_salvati)})")
    
    # Pulsante per resettare la lista
    if len(st.session_state.libri_salvati) > 0:
        if st.sidebar.button("🗑️ Svuota lista salvati"):
            st.session_state.libri_salvati.clear()
            st.rerun()

    # ==========================================
    # ELABORAZIONE DATI (FILTRI)
    # ==========================================
    df_filtrato = df_amz.copy()
    
    if mostra_solo_salvati:
        # Se la spunta è attiva, mostra solo i libri il cui ASIN è nel set di memoria
        df_filtrato = df_filtrato[df_filtrato['ASIN'].isin(st.session_state.libri_salvati)]
    else:
        # Altrimenti applica i filtri normali
        if sel_cat_amz != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['Categoria'] == sel_cat_amz]
        df_filtrato = df_filtrato[df_filtrato['Recensioni'] >= min_recensioni_filtro]
        
    # Ordinamento sempre per recensioni decrescenti
    df_filtrato = df_filtrato.sort_values(by='Recensioni', ascending=False)

    st.info(f"Mostrando **{len(df_filtrato)}** libri.")

    # ==========================================
    # RENDERING A GRIGLIA (3 COLONNE)
    # ==========================================
    # Creiamo 3 colonne
    cols = st.columns(3)
    
    for index, row in enumerate(df_filtrato.iterrows()):
        row_data = row[1]
        asin = row_data.get('ASIN', '')
        
        # Distribuisce le card sulle 3 colonne usando l'operatore modulo (%)
        col_idx = index % 3
        
        with cols[col_idx]:
            # Usa il container con bordo per un effetto "Card" (Streamlit 1.30+)
            with st.container(border=True):
                
                # Copertina centrata
                url = row_data['Copertina']
                if pd.notna(url) and str(url).startswith('http'):
                    st.image(str(url), width=130)
                else:
                    st.markdown("🖼️ *No Img*")
                
                # Info Libro
                st.subheader(row_data['Titolo'], divider="gray")
                st.markdown(f"✍️ **{row_data.get('Autore', 'N/D')}**")
                st.markdown(f"📊 **{int(row_data['Recensioni'])}** recensioni")
                st.caption(f"🏷️ {row_data.get('Categoria', 'N/D')} | 📅 {row_data.get('Data', 'N/D')}")
                
                # Link
                amz_link = f"https://www.amazon.it/dp/{asin}" if pd.notna(asin) else "#"
                st.markdown(f"[🛒 Apri su Amazon]({amz_link})")
                
                # Gestione pulsante Salva
                is_saved = asin in st.session_state.libri_salvati
                
                # Cambia testo e colore in base allo stato
                if is_saved:
                    btn_label = "✅ Salvato"
                    btn_type = "secondary"
                else:
                    btn_label = "💾 Salva Libro"
                    btn_type = "primary"
                
                # Il pulsante chiama la funzione `toggle_salvataggio`
                st.button(
                    btn_label, 
                    key=f"btn_{asin}", 
                    on_click=toggle_salvataggio, 
                    args=(asin,),
                    type=btn_type,
                    use_container_width=True
                )
                
