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
        height: 45px;
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
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE STATO (PREFERITI) ---
if 'favorites' not in st.session_state:
    st.session_state.favorites = set()

def toggle_favorite(asin):
    if asin in st.session_state.favorites:
        st.session_state.favorites.remove(asin)
    else:
        st.session_state.favorites.add(asin)

# --- CARICAMENTO DATI ---
FILE_NAME = "amazon_libri_multicat.csv"

@st.cache_data
def load_data():
    if not os.path.exists(FILE_NAME):
        return None
    try:
        # Tentativo 1: Virgola
        df = pd.read_csv(FILE_NAME)
        # Tentativo 2: Punto e virgola
        if 'Categoria' not in df.columns:
             df = pd.read_csv(FILE_NAME, sep=';')
        
        # Check colonne
        if 'Categoria' not in df.columns:
            st.error(f"❌ Errore CSV: Colonna 'Categoria' mancante. Colonne trovate: {list(df.columns)}")
            return None

        # Pulizia
        df['Recensioni'] = pd.to_numeric(df['Recensioni'], errors='coerce').fillna(0).astype(int)
        df['ASIN'] = df['ASIN'].astype(str)
        
        # RIMOZIONE DUPLICATI (Cruciale per evitare crash dei bottoni)
        df.drop_duplicates(subset=['ASIN'], inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Errore lettura CSV: {e}")
        return None

df = load_data()

# --- INTERFACCIA ---
st.title("📚 Amazon Book Scout")

if df is None:
    st.warning(f"⚠️ File '{FILE_NAME}' non trovato o illeggibile.")
    st.stop()

# --- FUNZIONE GRIGLIA ---
def display_book_grid(dataframe, key_prefix="grid"):
    if dataframe.empty:
        st.info("Nessun libro trovato.")
        return

    COLS_PER_ROW = 4
    rows = [dataframe.iloc[i:i+COLS_PER_ROW] for i in range(0, len(dataframe), COLS_PER_ROW)]

    for row_idx, row_chunk in enumerate(rows):
        cols = st.columns(COLS_PER_ROW)
        for col, (_, book) in zip(cols, row_chunk.iterrows()):
            with col:
                with st.container(border=True):
                    # Copertina
                    img = book['Copertina']
                    if pd.isna(img) or str(img) == "nan" or str(img) == "":
                        st.text("No Image")
                    else:
                        st.image(img, use_container_width=True)
                    
                    # Titolo e Autore
                    st.markdown(f"<div class='book-title' title='{book['Titolo']}'>{book['Titolo']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='book-meta'>✍️ {book['Autore']}</div>", unsafe_allow_html=True)
                    
                    # Dati
                    st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; margin:8px 0;">
                            <span class='review-badge'>⭐ {book['Recensioni']}</span>
                            <span style='font-size:10px; color:#888;'>{book['Data']}</span>
                        </div>
                        <div style="font-size:11px; color:#666; margin-bottom:8px;">📂 {book['Categoria']}</div>
                    """, unsafe_allow_html=True)
                    
                    # Link
                    asin = str(book['ASIN'])
                    st.link_button("Vedi su Amazon 🛒", f"https://www.amazon.it/dp/{asin}", use_container_width=True)

                    # Tasto Preferiti
                    is_fav = asin in st.session_state.favorites
                    label = "❌ Rimuovi" if is_fav else "❤️ Salva"
                    kind = "secondary" if is_fav else "primary"
                    
                    st.button(label, key=f"{key_prefix}_{asin}", type=kind, on_click=toggle_favorite, args=(asin,))

# --- SIDEBAR E FILTRI ---
st.sidebar.header("🛠️ Filtri")

cats = sorted(df['Categoria'].dropna().unique()) if 'Categoria' in df.columns else []
selected_cats = st.sidebar.multiselect("Categoria", cats, default=cats)

max_r = int(df['Recensioni'].max()) if not df.empty else 100
min_r = st.sidebar.slider("Min Recensioni", 0, max_r, 60, step=10)

q = st.sidebar.text_input("🔍 Cerca").lower()
sort_opt = st.sidebar.selectbox("Ordina", ["Recensioni (Decrescente)", "Recensioni (Crescente)", "Data (Recenti)"])

# --- TABS ---
tab1, tab2 = st.tabs(["🔍 Esplora", "⭐ Salvati"])

with tab1:
    fdf = df.copy()
    if selected_cats: fdf = fdf[fdf['Categoria'].isin(selected_cats)]
    fdf = fdf[fdf['Recensioni'] >= min_r]
    if q: fdf = fdf[fdf['Titolo'].str.lower().str.contains(q) | fdf['Autore'].str.lower().str.contains(q)]
    
    if sort_opt == "Recensioni (Decrescente)": fdf = fdf.sort_values(by="Recensioni", ascending=False)
    elif sort_opt == "Recensioni (Crescente)": fdf = fdf.sort_values(by="Recensioni", ascending=True)
    else: fdf = fdf.sort_values(by="Data", ascending=False)

    st.caption(f"Libri: {len(fdf)}")
    display_book_grid(fdf, "exp")

with tab2:
    if not st.session_state.favorites:
        st.warning("Nessun libro salvato.")
    else:
        favs = df[df['ASIN'].isin(st.session_state.favorites)].copy()
        st.download_button("📥 Scarica CSV", favs.to_csv(index=False).encode('utf-8'), "preferiti.csv", "text/csv")
        display_book_grid(favs, "fav")
