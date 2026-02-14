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

# --- CARICAMENTO DATI (VERSIONE BLINDATA) ---
FILE_NAME = "amazon_libri_multicat.csv"

@st.cache_data
def load_data():
    if not os.path.exists(FILE_NAME):
        return None
    
    df = None
    try:
        # TENTATIVO 1: Lettura standard (virgola)
        df = pd.read_csv(FILE_NAME)
        
        # Se non trova le colonne, o se c'è l'errore di parsing, proviamo strategie più aggressive
        if 'Categoria' not in df.columns or len(df.columns) < 2:
            raise ValueError("Separatore standard fallito")

    except:
        try:
            # TENTATIVO 2: Separatore punto e virgola (Excel)
            df = pd.read_csv(FILE_NAME, sep=';')
            if 'Categoria' not in df.columns:
                raise ValueError("Separatore Excel fallito")
        except:
            # TENTATIVO 3 (ULTIMA SPIAGGIA): Motore Python + Ignora errori
            # Questo risolve l'errore "Expected 1 fields in line 41"
            try:
                df = pd.read_csv(
                    FILE_NAME, 
                    sep=None,           # Cerca di indovinare
                    engine='python',    # Più robusto
                    on_bad_lines='skip' # Salta le righe rotte invece di crashare
                )
            except Exception as e:
                st.error(f"❌ Impossibile leggere il file CSV. Errore: {e}")
                return None

    # Controllo finale colonne
    if df is not None and 'Categoria' in df.columns:
        # Pulizia Dati
        try:
            # Pulisce recensioni da eventuali caratteri non numerici
            df['Recensioni'] = pd.to_numeric(df['Recensioni'], errors='coerce').fillna(0).astype(int)
            df['ASIN'] = df['ASIN'].astype(str)
            
            # Rimuove duplicati (importante per evitare crash dei bottoni)
            df.drop_duplicates(subset=['ASIN'], inplace=True)
            return df
        except Exception as e:
             st.error(f"Errore nella pulizia dati: {e}")
             return None
    else:
        st.error("❌ Il file CSV non contiene la colonna 'Categoria'. Controlla il file.")
        return None

df = load_data()

# --- INTERFACCIA ---
st.title("📚 Amazon Book Scout")

if df is None:
    st.warning(f"⚠️ File '{FILE_NAME}' non trovato o corrotto. Verifica su GitHub.")
    st.stop()

# --- FUNZIONE GRIGLIA ---
def display_book_grid(dataframe, key_prefix="grid"):
    if dataframe.empty:
        st.info("Nessun libro trovato con questi filtri.")
        return

    COLS_PER_ROW = 4
    rows = [dataframe.iloc[i:i+COLS_PER_ROW] for i in range(0, len(dataframe), COLS_PER_ROW)]

    for row_idx, row_chunk in enumerate(rows):
        cols = st.columns(COLS_PER_ROW)
        for col, (_, book) in zip(cols, row_chunk.iterrows()):
            with col:
                with st.container(border=True):
                    # Copertina
                    img = book.get('Copertina', '')
                    if pd.isna(img) or str(img) == "nan" or str(img).strip() == "":
                        st.text("No Image")
                    else:
                        st.image(str(img), use_container_width=True)
                    
                    # Titolo e Autore
                    title = book.get('Titolo', 'Senza Titolo')
                    author = book.get('Autore', 'Sconosciuto')
                    st.markdown(f"<div class='book-title' title='{title}'>{title}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='book-meta'>✍️ {author}</div>", unsafe_allow_html=True)
                    
                    # Dati
                    reviews = book.get('Recensioni', 0)
                    date = book.get('Data', 'N/D')
                    cat = book.get('Categoria', 'Generico')
                    
                    st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; margin:8px 0;">
                            <span class='review-badge'>⭐ {reviews}</span>
                            <span style='font-size:10px; color:#888;'>{date}</span>
                        </div>
                        <div style="font-size:11px; color:#666; margin-bottom:8px;">📂 {cat}</div>
                    """, unsafe_allow_html=True)
                    
                    # Link
                    asin = str(book.get('ASIN', ''))
                    if asin:
                        st.link_button("Vedi su Amazon 🛒", f"https://www.amazon.it/dp/{asin}", use_container_width=True)

                        # Tasto Preferiti
                        is_fav = asin in st.session_state.favorites
                        label = "❌ Rimuovi" if is_fav else "❤️ Salva"
                        kind = "secondary" if is_fav else "primary"
                        
                        st.button(label, key=f"{key_prefix}_{asin}", type=kind, on_click=toggle_favorite, args=(asin,))

# --- SIDEBAR E FILTRI ---
st.sidebar.header("🛠️ Filtri")

if not df.empty and 'Categoria' in df.columns:
    cats = sorted(df['Categoria'].dropna().unique())
else:
    cats = []

selected_cats = st.sidebar.multiselect("Categoria", cats, default=cats)

if not df.empty:
    max_r = int(df['Recensioni'].max()) if df['Recensioni'].max() > 0 else 100
    min_r = st.sidebar.slider("Min Recensioni", 0, max_r, 60, step=10)
else:
    min_r = 0

q = st.sidebar.text_input("🔍 Cerca").lower()
sort_opt = st.sidebar.selectbox("Ordina", ["Recensioni (Decrescente)", "Recensioni (Crescente)", "Data (Recenti)"])

# --- TABS ---
tab1, tab2 = st.tabs(["🔍 Esplora", "⭐ Salvati"])

with tab1:
    fdf = df.copy()
    if selected_cats: fdf = fdf[fdf['Categoria'].isin(selected_cats)]
    fdf = fdf[fdf['Recensioni'] >= min_r]
    
    if q: 
        fdf = fdf[
            fdf['Titolo'].astype(str).str.lower().str.contains(q) | 
            fdf['Autore'].astype(str).str.lower().str.contains(q)
        ]
    
    if sort_opt == "Recensioni (Decrescente)": fdf = fdf.sort_values(by="Recensioni", ascending=False)
    elif sort_opt == "Recensioni (Crescente)": fdf = fdf.sort_values(by="Recensioni", ascending=True)
    elif 'Data' in fdf.columns: fdf = fdf.sort_values(by="Data", ascending=False)

    st.caption(f"Libri visualizzati: {len(fdf)}")
    display_book_grid(fdf, "exp")

with tab2:
    if not st.session_state.favorites:
        st.warning("Nessun libro salvato nei preferiti.")
    else:
        favs = df[df['ASIN'].isin(st.session_state.favorites)].copy()
        if not favs.empty:
            st.download_button("📥 Scarica CSV", favs.to_csv(index=False).encode('utf-8'), "preferiti.csv", "text/csv")
            display_book_grid(favs, "fav")
