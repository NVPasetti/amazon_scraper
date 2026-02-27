import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scouting Amazon", layout="wide")

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

# Inizializza il limite di libri da mostrare (150 alla volta)
if 'limite_libri' not in st.session_state:
    st.session_state.limite_libri = 150

# Inizializza le memorie per i filtri (per resettare il limite se cambi reparto)
if 'filtro_cat' not in st.session_state: st.session_state.filtro_cat = "Tutte"
if 'filtro_rec' not in st.session_state: st.session_state.filtro_rec = 60
if 'filtro_salvati' not in st.session_state: st.session_state.filtro_salvati = False

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
        df = df.drop_duplicates(subset=['ASIN'])
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
    # CONTROLLO CAMBIO FILTRI
    # ==========================================
    # Se l'utente cambia un filtro, resettiamo la vista ai primi 150 libri
    if (sel_cat_amz != st.session_state.filtro_cat or 
        min_recensioni_filtro != st.session_state.filtro_rec or 
        mostra_solo_salvati != st.session_state.filtro_salvati):
        
        st.session_state.limite_libri = 150
        st.session_state.filtro_cat = sel_cat_amz
        st.session_state.filtro_rec = min_recensioni_filtro
        st.session_state.filtro_salvati = mostra_solo_salvati

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

    totale_libri = len(df_filtrato)
    st.markdown(f"**{totale_libri}** risultati trovati")
    st.markdown("---")

    # Tagliamo il dataframe per mostrare solo i libri fino al limite attuale
    df_mostrato = df_filtrato.iloc[:st.session_state.limite_libri]

    # ==========================================
    # RENDERING A GRIGLIA ALLINEATA
    # ==========================================
    lista_libri = list(df_mostrato.iterrows())
    
    for i in range(0, len(lista_libri), 3):
        cols = st.columns(3)
        
        for j in range(3):
            if i + j < len(lista_libri):
                index, row_data = lista_libri[i + j]
                asin = row_data.get('ASIN', '')
                
                is_saved = asin in st.session_state.libri_salvati if isinstance(st.session_state.libri_salvati, set) else False
                
                with cols[j]:
                    with st.container(border=True):
                        # 1. RIGA TITOLO E CUORE
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
                            # Troncamento feroce a 45 caratteri per il titolo
                            titolo_intero = row_data['Titolo']
                            titolo_corto = titolo_intero[:45] + "..." if len(titolo_intero) > 45 else titolo_intero
                            
                            # Forziamo l'altezza del box del titolo a 55px in modo che 1 o 2 righe occupino lo stesso spazio
                            st.markdown(f"<div style='height: 55px; font-weight: bold; font-size: 1.05em;'>{titolo_corto}</div>", unsafe_allow_html=True)
                        
                        # 2. IMMAGINE GIGANTE (Nativa Streamlit)
                        url = row_data['Copertina']
                        if pd.notna(url) and str(url).startswith('http'):
                            st.image(str(url), use_container_width=True)
                        else:
                            st.markdown("<div style='height: 250px; text-align: center; line-height: 250px;'>🖼️ <i>Nessuna Immagine</i></div>", unsafe_allow_html=True)
                        
                        # 3. INFO E METADATI (Altezza fissa a 80px)
                        # Troncamento feroce a 35 caratteri per l'autore
                        autore_intero = row_data.get('Autore', 'N/D')
                        autore_corto = autore_intero[:35] + "..." if len(autore_intero) > 35 else autore_intero
                        
                        info_html = f"""
                        <div style='height: 80px; line-height: 1.4;'>
                            <span style='font-size: 0.85em; color: gray;'>Di: <b>{autore_corto}</b></span><br>
                            <span style='font-size: 0.9em;'>⭐⭐⭐⭐⭐ ({int(row_data['Recensioni'])})</span><br>
                            <span style='font-size: 0.8em; color: gray;'>Reparto: {row_data.get('Categoria', 'N/D')}</span>
                        </div>
                        """
                        st.markdown(info_html, unsafe_allow_html=True)
                        
                        # 4. PULSANTE AMAZON
                        amz_link = f"https://www.amazon.it/dp/{asin}" if pd.notna(asin) else "#"
                        st.link_button("Vedi su Amazon", amz_link, type="primary", use_container_width=True)

    # ==========================================
    # PULSANTE "CARICA ALTRI" IN FONDO
    # ==========================================
    if st.session_state.limite_libri < totale_libri:
        st.markdown("---")
        # Centriamo il pulsante usando le colonne
        col_vuota1, col_bottone, col_vuota2 = st.columns([1, 2, 1])
        with col_bottone:
            if st.button("⬇️ Carica altri libri", use_container_width=True):
                st.session_state.limite_libri += 150
                st.rerun()
