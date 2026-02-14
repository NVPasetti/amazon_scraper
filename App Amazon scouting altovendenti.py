import streamlit as st
import pandas as pd
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Amazon Book Scout",
    page_icon="📚",
    layout="wide"
)

# --- CSS CUSTOM ---
st.markdown("""
<style>
    div[data-testid="stImage"] {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .book-title {
        font-weight: bold;
        font-size: 15px;
        margin-top: 8px;
        height: 45px; /* Altezza fissa per allineamento */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.2;
    }
    .book-meta {
        font-size: 13px;
        color: #555;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .review-badge {
        background-color: #f0f2f6;
        padding: 3px 6px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
        color: #333;
    }
    /* Stile bottoni */
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE STATO (PREFERITI) ---
if 'favorites' not in st.session_state:
    st.session_state.favorites = set()

def toggle_favorite(asin):
    """Callback: Aggiunge o rimuove un ASIN dai preferiti"""
    if asin in st.session_state.favorites:
        st.session_state.favorites.remove(asin)
    else:
        st.session_state.favorites.add(asin)

# --- CARICAMENTO DATI (FIX ROBUSTEZZA) ---
FILE_NAME = "amazon_libri_multicat.csv"

@st.cache_data
def load_data():
    if not os.path.exists(FILE_NAME):
        return None
    
    try:
        # TENTATIVO 1: Separatore virgola (Standard)
        df = pd.read_csv(FILE_NAME)
        
        # Se fallisce il riconoscimento delle colonne (es. trova solo 1 colonna), prova il punto e virgola
        if 'Categoria' not in df.columns:
             df = pd.read_csv(FILE_NAME, sep=';')
        
        # Se ancora non trova la colonna, il file ha un problema di intestazione
        if 'Categoria' not in df.columns:
            st.error(f"❌ Errore: Colonna 'Categoria' non trovata nel CSV. Colonne lette: {list(df.columns)}")
            return None

        # Pulizia dati
        df['Recensioni'] = pd.to_numeric(df['Recensioni'], errors='coerce').fillna(0).astype(int)
        # Assicuriamoci che ASIN sia stringa
        df['ASIN'] = df['ASIN'].astype(str)
        
        return df

    except Exception as e:
        st.error(f"Errore grave nella lettura del file CSV: {e}")
        return None

df = load_data()

# --- TITOLO ---
st.title("📚 Amazon Book Scout")

# Se il dataframe non è stato caricato correttamente, ferma l'app
if df is None:
    st.warning(f"⚠️ File '{FILE_NAME}' non trovato o corrotto. Verifica che sia presente su GitHub.")
    st.stop()

# --- FUNZIONE PER DISEGNARE LA GRIGLIA ---
def display_book_grid(dataframe, key_prefix="grid"):
    """Funzione riutilizzabile per mostrare i libri in griglia"""
    if dataframe.empty:
        st.info("Nessun libro da visualizzare qui.")
        return

    COLS_PER_ROW = 4
    rows = [dataframe.iloc[i:i+COLS_PER_ROW] for i in range(0, len(dataframe), COLS_PER_ROW)]

    for row_idx, row_chunk in enumerate(rows):
        cols = st.columns(COLS_PER_ROW)
        
        for col, (_, book) in zip(cols, row_chunk.iterrows()):
            with col:
                with st.container(border=True):
                    # 1. Copertina
                    img_url = book['Copertina']
                    if pd.isna(img_url) or str(img_url).strip() == "" or str(img_url) == "nan":
                        st.text("No Image")
                    else:
                        st.image(img_url, use_container_width=True)
                    
                    # 2. Info Testuali
                    st.markdown(f"<div class='book-title' title='{book['Titolo']}'>{book['Titolo']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='book-meta'>✍️ {book['Autore']}</div>", unsafe_allow_html=True)
                    
                    # 3. Badge e Categoria
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0;">
                            <span class='review-badge'>⭐ {book['Recensioni']}</span>
                            <span style="font-size: 10px; color: #888;">{book['Data']}</span>
                        </div>
                        <div style="font-size: 11px; color: #666; margin-bottom: 8px;">
                            📂 {book['Categoria']}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # 4. Link Amazon
                    asin = str(book['ASIN'])
                    amazon_link = f"https://www.amazon.it/dp/{asin}"
                    st.link_button("Vedi su Amazon 🛒", amazon_link, use_container_width=True)

                    # 5. Tasto Preferiti (Logica Ottimizzata)
                    is_fav = asin in st.session_state.favorites
                    btn_label = "❌ Rimuovi" if is_fav else "❤️ Salva"
                    btn_type = "secondary" if is_fav else "primary"
                    
                    # Usa on_click per gestire lo stato PRIMA del ricaricamento
                    st.button(
                        btn_label, 
                        key=f"{key_prefix}_btn_{asin}", 
                        type=btn_type,
                        on_click=toggle_favorite,
                        args=(asin,)
                    )

# --- SIDEBAR FILTRI ---
st.sidebar.header("🛠️ Filtri")

# Verifica sicurezza: se la colonna Categoria esiste ma è vuota
if 'Categoria' in df.columns and not df['Categoria'].isnull().all():
    cats = sorted(df['Categoria'].dropna().unique())
else:
    cats = []

selected_cats = st.sidebar.multiselect("Categoria", cats, default=cats)

# Slider Recensioni (Safety check per max vuoto)
if not df.empty:
    max_rev = int(df['Recensioni'].max())
    if max_rev < 10: max_rev = 100
    min_rev_filter = st.sidebar.slider("Minimo Recensioni", 0, max_rev, 60, step=10)
else:
    min_rev_filter = 0

search_query = st.sidebar.text_input("🔍 Cerca Titolo o Autore")
sort_option = st.sidebar.selectbox("Ordina per", ["Recensioni (Decrescente)", "Recensioni (Crescente)", "Data (Recenti)"])

# --- CREAZIONE TABS ---
tab1, tab2 = st.tabs(["🔍 Esplora", "⭐ Contenuti salvati"])

# === TAB 1: ESPLORA (Tutti i libri filtrati) ===
with tab1:
    # Applica filtri al DataFrame principale
    filtered_df = df.copy()
    
    if selected_cats:
        filtered_df = filtered_df[filtered_df['Categoria'].isin(selected_cats)]
    
    filtered_df = filtered_df[filtered_df['Recensioni'] >= min_rev_filter]

    if search_query:
        q = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['Titolo'].str.lower().str.contains(q) |
            filtered_df['Autore'].str.lower().str.contains(q)
        ]

    # Ordinamento
    if sort_option == "Recensioni (Decrescente)":
        filtered_df = filtered_df.sort_values(by="Recensioni", ascending=False)
    elif sort_option == "Recensioni (Crescente)":
        filtered_df = filtered_df.sort_values(by="Recensioni", ascending=True)
    elif sort_option == "Data (Recenti)":
        filtered_df = filtered_df.sort_values(by="Data", ascending=False)

    # Metriche rapide
    st.caption(f"Visualizzati {len(filtered_df)} libri su {len(df)} totali.")
    
    # Mostra Griglia
    display_book_grid(filtered_df, key_prefix="explore")

# === TAB 2: CONTENUTI SALVATI ===
with tab2:
    if not st.session_state.favorites:
        st.warning("Non hai ancora salvato nessun libro. Torna su 'Esplora' e clicca su ❤️ Salva.")
    else:
        # Filtra il DataFrame originale tenendo solo gli ASIN salvati
        fav_df = df[df['ASIN'].isin(st.session_state.favorites)].copy()
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.success(f"Hai salvato **{len(fav_df)}** libri interessanti.")
        with c2:
            # Tasto per scaricare la lista dei preferiti
            csv = fav_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Scarica Preferiti (CSV)",
                data=csv,
                file_name="i_miei_libri_preferiti.csv",
                mime="text/csv"
            )
        
        st.divider()
        # Mostra Griglia Preferiti
        display_book_grid(fav_df, key_prefix="favs")
