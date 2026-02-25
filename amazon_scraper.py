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

# --- CONFIGURAZIONE ---
NUM_PAGINE_PER_CATEGORIA = 300  # 300 pagine per ogni categoria
MIN_RECENSIONI = 60             # Soglia minima recensioni

# --- DEFINIZIONE CATEGORIE ---
CATEGORIES = [
    {
        "name": "Politica",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508811031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508811031&s=popularity-rank&dc&page={page}"
    },
    {
        "name": "Società e scienze sociali",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508879031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508879031&s=popularity-rank&dc&page={page}"
    },
    {
        "name": "Storia",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508796031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508796031&s=popularity-rank&dc&page={page}"
    },
    {
        "name": "Diari, biografie, memorie",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508714031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508714031&s=popularity-rank&dc&page={page}"
    },
    {
        "name": "Arte, cinema e fotografia",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508758031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508758031&s=popularity-rank&dc&page={page}"
    },
    {
        "name": "Scienze, tecnologia, medicina",
        "start": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508867031&s=popularity-rank&dc",
        "template": "https://www.amazon.it/s?i=stripbooks&rh=n%3A411663031%2Cn%3A508867031&s=popularity-rank&dc&page={page}"
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
    
    # --- OPZIONI CLOUD ---
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # --- ANTI-BOT ---
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def check_captcha(driver, soup):
    # Modificata per non usare input() su GitHub Actions
    if soup.find('input', id='captchacharacters') or "inserisci i caratteri" in soup.get_text().lower():
        print("\n" + "!"*50)
        print("⚠️  AMAZON CAPTCHA RILEVATO!  ⚠️")
        print("Il server è stato bloccato. Salto alla prossima categoria.")
        print("!"*50 + "\n")
        return True
    return False

def clean_reviews_count(text):
    if not text: return 0
    clean = re.sub(r'[^\d]', '', text)
    try:
        return int(clean)
    except:
        return 0

def is_multiple_author(author_text):
    if not author_text: return True 
    text = author_text.lower()
    if ',' in text: return True
    if ' e ' in text: return True
    if ' et ' in text or ' and ' in text: return True
    return False

def extract_date(text):
    if not text: return ""
    match = re.search(r'(\d{1,2}\s+[a-zA-Z]{3}\.?\s+\d{4})', text)
    if match:
        return match.group(1)
    return ""

def get_amazon_data(driver):
    all_books = []
    visti_asin = set()

    for cat in CATEGORIES:
        print(f"\n\n{'='*20} SCANSIONE: {cat['name'].upper()} {'='*20}")
        
        for page in range(1, NUM_PAGINE_PER_CATEGORIA + 1):
            if page == 1:
                url = cat['start']
            else:
                url = cat['template'].format(page=page)

            print(f"\n{cat['name']} - Pagina {page}/{NUM_PAGINE_PER_CATEGORIA}...")
            driver.get(url)
            
            time.sleep(random.uniform(2.0, 4.0))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            if check_captcha(driver, soup):
                # Se c'è un captcha, interrompiamo il loop di questa categoria
                break

            results = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            if not results:
                print("❌ Nessun risultato trovato in questa pagina.")
                if page > 5: 
                    print("Probabile fine catalogo per questa categoria.")
                    break
                continue
                
            print(f"  -> {len(results)} elementi trovati. Elaborazione...")

            count_ok = 0
            for card in results:
                try:
                    asin = card.get('data-asin')
                    if not asin or asin in visti_asin: continue
                    
                    title_tag = card.find('h2')
                    title = title_tag.get_text(strip=True) if title_tag else "N/D"
                    
                    author = "N/D"
                    author_rows = card.find_all('div', class_='a-row')
                    for row in author_rows:
                        row_text = row.get_text(" ", strip=True)
                        if re.match(r'^di\s+', row_text, re.IGNORECASE):
                            raw_auth = re.sub(r'^di\s+', '', row_text, flags=re.IGNORECASE)
                            raw_auth = raw_auth.split('|')[0].split('(')[0]
                            author = raw_auth.strip()
                            break
                    
                    if author == "N/D": continue
                    if is_multiple_author(author): continue

                    full_card_text = card.get_text(" ", strip=True)
                    date_found = extract_date(full_card_text)

                    reviews_count = 0
                    review_tag = card.find(lambda tag: tag.name == 'a' and tag.has_attr('aria-label') and ('valutazioni' in tag['aria-label'] or 'voti' in tag['aria-label']))
                    
                    if review_tag:
                        label_text = review_tag['aria-label']
                        reviews_count = clean_reviews_count(label_text.split()[0])
                    else:
                        review_span = card.find('span', class_='s-underline-text')
                        if review_span:
                            reviews_count = clean_reviews_count(review_span.get_text())

                    if reviews_count < MIN_RECENSIONI: continue

                    img_tag = card.find('img', class_='s-image')
                    img_url = img_tag['src'] if img_tag else ""

                    visti_asin.add(asin)
                    all_books.append({
                        'ASIN': asin,
                        'Copertina': img_url,
                        'Titolo': title,
                        'Autore': author,
                        'Data': date_found,
                        'Recensioni': reviews_count,
                        'Categoria': cat['name'] 
                    })
                    count_ok += 1

                except Exception:
                    continue
            
            print(f"  -> {count_ok} nuovi libri aggiunti.")

    return pd.DataFrame(all_books)

def save_csv_amazon(df, filename):
    print(f"\n--- Salvataggio CSV: {filename} ---")
    if df.empty:
        print("❌ Nessun dato da salvare.")
        return

    df = df.sort_values(by=['Categoria', 'Recensioni'], ascending=[True, False])
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"✅ File CSV salvato correttamente: {len(df)} righe.")

def main():
    print("=== START AMAZON SCRAPER (HEADLESS MODE) ===")
    driver = setup_driver()
    try:
        df = get_amazon_data(driver)
        if not df.empty:
            save_csv_amazon(df, "amazon_libri_multicat.csv")
        else:
            print("Nessun libro trovato (o blocco CAPTCHA su tutte le categorie).")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
