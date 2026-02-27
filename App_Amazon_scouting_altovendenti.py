import streamlit as st
import pandas as pd
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scouting Amazon", layout="wide")

NOME_FOGLIO_GOOGLE = "Amazon_Wishlist" # <-- ASSICURATI CHE IL NOME SIA CORRETTO

# --- CONNESSIONE A GOOGLE SHEETS ---
@st.cache_resource
def get_gspread_client():
    """Autentica e restituisce il client Google Sheets usando i Secrets."""
    try:
        # Legge il JSON dai Secrets di Streamlit
        creds_dict = json.loads(st.secrets["GCP_CREDENTIALS"])
        
        # 🛠️ LA RIGA MAGICA: Ripara i rientri a capo della chiave privata
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")
        return None

def get_worksheet():
    client = get_gspread_client()
    if client:
        try:
            # Apre il foglio e seleziona la prima scheda
            sheet = client.open(NOME_FOGLIO_GOOGLE).sheet1
            return sheet
        except Exception as e:
            st.error(f"Foglio '{NOME_FOGLIO_GOOGLE}' non trovato. L'hai condiviso con l'email del bot?")
    return None

# --- FUNZIONI PER GESTIRE I PREFERITI SU GOOGLE SHEETS ---
def carica_preferiti_da_sheets():
    sheet = get_worksheet()
    if sheet:
        try:
            # Prende tutti i valori della colonna A (saltando l'intestazione "ASIN")
            valori = sheet.col_values(1)[1:] 
            return set(valori)
        except Exception:
            return set()
    return set()

def salva_preferito_su_sheets(asin):
    sheet = get_worksheet()
    if sheet:
        sheet.append_row([asin])

def rimuovi_preferito_da_sheets(asin):
    sheet = get_worksheet()
    if sheet:
        try:
            # Trova la cella con l'ASIN e ne elimina la riga
            cella = sheet.find(asin)
            if cella:
                sheet.delete_rows(cella.row)
        except Exception:
            pass # L'ASIN non era presente

def svuota_salvati():
    st.session_state.libri_salvati.clear()
    sheet = get_worksheet()
    if sheet:
        try:
            sheet.clear() # Cancella tutto
            try:
                # Nuova sintassi gspread per ricreare l'intestazione
                sheet.update(range_name='A1', values=[['ASIN']])
            except:
                # Vecchia sintassi gspread per ricreare l'intestazione
                sheet.update('A1', [['ASIN']])
        except Exception as e:
            st.error(f"Errore durante lo svuotamento del foglio: {e}")

# --- INIZIALIZZAZIONE MEMORIA ---
if 'libri_salvati' not in st.session_state:
    st.session_state.libri_salvati = carica_preferiti_da_sheets()

# Funzione callback per il pulsante "Cuore"
def toggle_salvataggio(asin):
    if asin in st.session_state.libri_salvati:
        st.session_state.libri_salvati.remove(asin)
        rimuovi_preferito_da_sheets(asin) # Rimuove da Google
    else:
        st.session_state.libri_salvati.add(asin)
        salva_preferito_su_sheets(asin) # Aggiunge a Google

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
    except Exception:
        return None

# --- INTESTAZIONE SHOP ---
st.title("I più venduti - Amazon")
st.caption("Esplora i libri con più recensioni e aggiungili ai preferiti per rivederli in un secondo momento")

file_amazon = "amazon_libri_multicat.csv"
df_amz = load_amazon_data(file_amazon)

if df_amz is None:
    st.warning("⚠️ Dati Amazon non ancora disponibili. Attendi che lo scraper generi il file CSV.")
else:
    # ==========================================
    # SIDEBAR: FILTRI E WISHLIST
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
    st.sidebar.metric(label="❤️ Wishlist", value=f"{len(st.session_state.libri_salvati)} libri")
    mostra_solo_salvati = st.sidebar.checkbox("Visualizza solo la tua Wishlist")
    
    if len(st.session_state.libri_salvati) > 0:
        st.sidebar.button("🗑️ Svuota Wishlist", on_click=svuota_salvati, type="secondary")

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

    st.markdown(f"**{len(df_filtrato)}** risultati trovati")
    st.markdown("---")

    # ==========================================
    # RENDERING A GRIGLIA ALLINEATA (SHOP STYLE)
    # ==========================================
    lista_libri = list(df_filtrato.iterrows())
    
    for i in range(0, len(lista_libri), 3):
        cols = st.columns(3)
        
        for j in range(3):
            if i + j < len(lista_libri):
                index, row_data = lista_libri[i + j]
                asin = row_data.get('ASIN', '')
                is_saved = asin in st.session_state.libri_salvati
                
                with cols[j]:
                    with st.container(border=True):
                        c_titolo, c_cuore = st.columns([5, 1])
                        with c_cuore:
                            st.button(
                                "❤️" if is_saved else "🤍", 
                                key=f"btn_{asin}", 
                                on_click=toggle_salvataggio, 
                                args=(asin,),
                                help="Aggiungi o rimuovi dalla Wishlist"
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
