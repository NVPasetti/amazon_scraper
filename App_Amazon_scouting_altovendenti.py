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
            risposta = supabase.table("wishlist").select("asin").execute()
            return set(r["asin"] for r in risposta.data)
        except Exception:
            return set()
    return set()

def salva_preferito_db(asin):
    if supabase:
        try:
            supabase.table("wishlist").insert({"asin": asin}).execute()
        except Exception as e:
            st.toast(f"⚠️ Errore salvataggio nel DB: {e}")

def rimuovi_preferito_db(asin):
    if supabase:
        try:
            supabase.table("wishlist").delete().eq("asin", asin).execute()
        except Exception as e:
            st.toast(f"⚠️ Errore rimozione dal DB: {e}")

def svuota_salvati_db():
    st.session_state.libri_salvati.clear()
    if supabase:
        try:
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
df_amz = load
