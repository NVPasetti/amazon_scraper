import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scouting Amazon", layout="wide")

# --- FIX SCROLL VERSO L'ALTO (HACK SENZA IFRAME) ---
if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

if st.session_state.scroll_to_top:
    # Trucco dell'immagine finta per lanciare JS aggirando i blocchi di sicurezza
    scroll_script = """
    <img src="dummy_image" style="display:none;" onerror="
        let main = document.querySelector('.main');
        if (main) {
            main.scrollTo({top: 0, behavior: 'smooth'});
            main.scrollTop = 0;
        }
        window.scrollTo({top: 0, behavior: 'smooth'});
    ">
    """
    st.markdown(scroll_script, unsafe_allow_html=True)
    st.session_state.scroll_to_top = False

# --- CONNESSIONE A SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Errore di connessione a Supabase: {e}")
    supabase = None

# --- FUNZIONI DATABASE ---
def carica_preferiti_db():
    if supabase:
        try:
            # Scarica tutta la colonna 'asin' dalla tabella 'wishlist'
            risposta = supabase.table("wishlist").select("asin").execute()
            return set(r["asin"] for r in risposta.data)
        except Exception:
            return set()
    return set()

def salva_preferito_db(asin):
    if supabase:
        try:
            supabase.table("wishlist").insert({"asin": asin}).execute()
        except Exception:
            pass # Probabilmente esiste già (Primary Key)

def rimuovi_preferito_db(asin):
    if supabase:
        try:
            supabase.table("wishlist").delete().eq("asin", asin).execute()
        except Exception:
            pass

def svuota_salvati_db():
    st.session_state.libri_salvati.clear()
    if supabase:
        try:
            # Elimina tutti i record dove l'asin non è nullo (svuota la tabella)
            supabase.table("wishlist").delete().neq("asin", "dummy_value").execute()
        except Exception as e:
            st.error(f"Errore nello svuotamento: {e}")

# --- INIZIALIZZAZIONE MEMORIA GLOBALE ---
if 'libri_salvati' not in st.session_state:
    st.session_state.libri_salvati = carica_preferiti_db()

# Funzione callback per il pulsante "Cuore"
def toggle_salvataggio(asin):
    if asin in st.session_state.libri_salvati:
        st.session_state.libri_salvati.remove(asin)
        rimuovi_preferito_db(asin)
    else:
        st.session_state.libri_salvati.add(asin)
        salva_preferito_db(asin)

# --- FUNZIONE DI CARICAMENTO DATI ---
@st.cache_data(ttl=3600)
def load_amazon_data(file_name):
    if not os.path.exists(file_name):
        return None
    try:
        df = pd.read_csv(file_name)
        df['Titolo'] = df['Titolo'].fillna("Senza Titolo")
        df['Autore'] = df['Autore'].fillna("N/D")
        
        # --- RIMOZIONE DUPLICATI ---
        # Rimuove i cloni esatti (stesso codice ASIN)
        df = df.drop_duplicates(subset=['ASIN'])
        # Rimuove eventuali doppioni con lo stesso Titolo esatto
        df = df.drop_duplicates(subset=['Titolo'])
        
        return df
    except Exception:
        return None

# --- INTESTAZIONE SHOP ---
st.title("I più venduti - Amazon")
st.caption("Esplora i libri con più recensioni e aggiungili ai Salvati.")

file_amazon = "amazon_libri_multicat.csv"
df_amz = load_amazon_data(file_amazon)

if df_amz is None:
    st.warning("⚠️ Dati Amazon non ancora disponibili. Attendi che lo scraper generi il file CSV.")
else:
    # ==========================================
    # SIDEBAR: FILTRI E SALVATI
    # ==========================================
    st.sidebar.header("Menu")
    
    categorie_disponibili = ["Tutte"] + sorted(df_amz['Categoria'].unique().tolist())
    sel_cat_amz = st.sidebar.selectbox("Reparto:", categorie_disponibili)
    
    max_recensioni = int(df_amz['Recensioni'].max()) if not df_amz.empty else 1000
    min_recensioni_filtro = st.sidebar.slider(
        "Filtra per popolarità (min. recensioni):", 
        min_value=0, max_value=max_recensioni, value=60, step=50
    )

    st.sidebar.markdown("---")
    
    # Sicurezza per evitare che un riavvio lento rompa il conteggio
    num_salvati = len(st.session_state.libri_salvati) if isinstance(st.session_state.libri_salvati, set) else 0
    st.sidebar.metric(label="❤️ Salvati", value=f"{num_salvati} libri")
    
    mostra_solo_salvati = st.sidebar.checkbox("Visualizza solo i Salvati")
    
    if num_salvati > 0:
        st.sidebar.button("🗑️ Svuota Salvati", on_click=svuota_salvati_db, type="secondary")

    # ==========================================
    # ELABORAZIONE DATI (FILTRI)
    # ==========================================
    df_filtrato = df_amz.copy()
    
    if mostra_solo_salvati:
        salvati_set = st.session_state.libri_salvati if isinstance(st.session_state.libri_salvati, set) else set()
        df_filtrato = df_filtrato[df_filtrato['ASIN'].isin(salvati_set)]
    else:
        if sel_cat_amz != "Tutte":
            df_filtrato = df_filtrato[df_filtrato['Categoria'] == sel_cat_amz]
        df_filtrato = df_filtrato[df_filtrato['Recensioni'] >= min_recensioni_filtro]
        
    df_filtrato = df_filtrato.sort_values(by='Recensioni', ascending=False)

    # ==========================================
    # SISTEMA DI PAGINAZIONE
    # ==========================================
    LIBRI_PER_PAGINA = 30
    
    if 'pagina_corrente' not in st.session_state:
        st.session_state.pagina_corrente = 0

    totale_libri = len(df_filtrato)
    totale_pagine = (totale_libri // LIBRI_PER_PAGINA) + (1 if totale_libri % LIBRI_PER_PAGINA > 0 else 0)

    # Se i filtri cambiano e la pagina salvata sfora il nuovo limite, resettiamo a 0
    if st.session_state.pagina_corrente >= totale_pagine and totale_pagine > 0:
        st.session_state.pagina_corrente = 0

    st.markdown(f"**{totale_libri}** risultati trovati")
    st.markdown("---")

    # Tagliamo il dataframe per mostrare solo i libri di questa pagina
    inizio_idx = st.session_state.pagina_corrente * LIBRI_PER_PAGINA
    fine_idx = inizio_idx + LIBRI_PER_PAGINA
    df_pagina = df_filtrato.iloc[inizio_idx:fine_idx]

    # ==========================================
    # RENDERING A GRIGLIA ALLINEATA
    # ==========================================
    lista_libri = list(df_pagina.iterrows())
    
    for i in range(0, len(lista_libri), 3):
        cols = st.columns(3)
        
        for j in range(3):
            if i + j < len(lista_libri):
                index, row_data = lista_libri[i + j]
                asin = row_data.get('ASIN', '')
                
                is_saved = asin in st.session_state.libri_salvati if isinstance(st.session_state.libri_salvati, set) else False
                
                with cols[j]:
                    with st.container(border=True):
                        c_titolo, c_cuore = st.columns([5, 1])
                        with c_cuore:
                            st.button(
                                "❤️" if is_saved else "🤍", 
                                key=f"btn_{asin}", 
                                on_click=toggle_salvataggio, 
                                args=(asin,),
                                help="Aggiungi o rimuovi dai Salvati"
                            )
                        with c_titolo:
                            titolo_corto = row_data['Titolo'][:60] + "..." if len(row_data['Titolo']) > 60 else row_data['Titolo']
                            st.markdown(f"**{titolo_corto}**")
                        
                        url = row_data['Copertina']
                        if pd.notna(url) and str(url).startswith('http'):
                            st.image(str(url), use_container_width=True)
                        else:
                            st.markdown("🖼️ *Nessuna Immagine*")
                        
                        st.caption(f"Di: **{row_data.get('Autore', 'N/D')}**")
                        st.markdown(f"⭐⭐⭐⭐⭐ ({int(row_data['Recensioni'])})")
                        st.caption(f"Reparto: {row_data.get('Categoria', 'N/D')}")
                        
                        amz_link = f"https://www.amazon.it/dp/{asin}" if pd.notna(asin) else "#"
                        st.link_button("Vedi su Amazon", amz_link, type="primary", use_container_width=True)

    # ==========================================
    # PUL
