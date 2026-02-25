import sys
import time
import pandas as pd
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE TEST DIAGNOSTICO ---
NUM_PAGINE_PER_CATEGORIA = 2  # Solo 2 pagine per fare in fretta il test
MIN_RECENSIONI = 60            

CATEGORIES = [
    {
        "name": "Politica",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508811031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508811031&s=popularity-rank&dc&page={page}"
    }
]

# --- FIX ENCODING ---
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # --- ANTI-BOT POTENZIATO ---
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def main():
    print("=== START TEST DIAGNOSTICO AMAZON ===")
    driver = setup_driver()
    try:
        cat = CATEGORIES[0]
        print(f"\n--- TEST SU CATEGORIA: {cat['name']} ---")
        
        for page in range(1, NUM_PAGINE_PER_CATEGORIA + 1):
            url = cat['start'] if page == 1 else cat['template'].format(page=page)
            print(f"\nApertura Pagina {page}...")
            
            driver.get(url)
            time.sleep(3) # Pausa per far caricare la pagina
            
            # --- LA SPIA: COSA VEDE IL BOT? ---
            titolo_pagina = driver.title
            print(f"👀 TITOLO PAGINA VISTO DAL BOT: '{titolo_pagina}'")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Proviamo due selettori diversi che Amazon usa
            results_list = soup.find_all('div', {'data-component-type': 's-search-result'})
            results_grid = soup.find_all('div', class_='s-result-item')
            
            print(f"📊 Elementi trovati con metodo A (Lista): {len(results_list)}")
            print(f"📊 Elementi trovati con metodo B (Griglia/Totale): {len(results_grid)}")
            
            if len(results_list) == 0 and len(results_grid) == 0:
                print("⚠️  HTML TRONCATO O BLOCCATO! Ecco un pezzetto di quello che ha scaricato:")
                print(soup.get_text()[:300].replace('\n', ' ')) # Stampa i primi 300 caratteri del testo
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
    
