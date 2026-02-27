import streamlit as st
import pandas as pd
import os
import json
import textwrap  # <-- Aggiunto per il fix della chiave
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
        
        # --- SUPER FIX PER LA CHIAVE PRIVATA ---
        raw_key = creds_dict.get("private_key", "")
        raw_key = raw_key.replace("\\n", "\n").strip()
        
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Se la chiave contiene gli header, la ricostruiamo formattata alla perfezione
        if header in raw_key and footer in raw_key:
            # 1. Estrae solo il codice segreto centrale
            core_key = raw_key.split(header)[1].split(footer)[0]
            
            # 2. Rimuove qualsiasi spazio, tab o a capo "sporco"
            core_key = core_key.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
            
            # 3. Riformatta in blocchi esatti di 64 caratteri (lo standard PEM richiesto da Google)
            righe_pulite = "\n".join(textwrap.wrap(core_key, 64))
            
            # 4. Riassembla la chiave finale
