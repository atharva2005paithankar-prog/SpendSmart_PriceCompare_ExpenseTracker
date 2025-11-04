import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
}

# Banned words are the same as for other scrapers (excluding accessories, lots, bundles, etc.)
BANNED = [
    'case', 'cover', 'charger', 'cable', 'protector', 'glass', 'film', 'adapter',
    'screen', 'battery', 'keyboard', 'mouse', 'headphones', 'earbuds', 'lot', 'lots',
    'set', 'bundle', 'replacement', 'pack', 'accessories','accessory', 'screen protector',
    'shell', 'housing', 'tempered', 'glue', 'repair', 'stand', 'holder', 'mount'
]

def is_valid_title(title, search_term):
    title_lower = title.lower()
    search_words = search_term.lower().split()
    if not all(word in title_lower for word in search_words):
        return False
    for b in BANNED:
        if b in title_lower:
            return False
    return True

def extract_price(text):
    numbers = re.findall(r'[\d,]+', text)
    for n in numbers:
        try:
            return int(n.replace(',', ''))
        except Exception:
            continue
    return float('inf')

def scrape_top_products(search_term):
    # Generate the search URL
    url = f'https://www.snapdeal.com/search?keyword={search_term.replace(" ", "%20")}&sort=plrty'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=18)
        if resp.status_code != 200:
            print(f"Snapdeal HTTP {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        for prod in soup.select("div.product-tuple-listing"):
            title_tag = prod.select_one(".product-title")
            price_tag = prod.select_one(".product-price")
            link_tag = prod.select_one("a.dp-widget-link")
            if title_tag and price_tag and link_tag:
                title = title_tag.get_text(strip=True)
                if not is_valid_title(title, search_term):
                    continue
                price = extract_price(price_tag.get_text(strip=True))
                link = link_tag['href']
                if not link.startswith("http"):
                    link = "https://www.snapdeal.com" + link
                if price == float('inf') or price <= 0 or price > 1e7:
                    continue
                results.append({'title': title, 'price': price, 'url': link})
            if len(results) >= 8:
                break
        results.sort(key=lambda x: x['price'])
        return results[:3]
    except Exception as e:
        print("Error in Snapdeal scraping:", str(e))
        return []
