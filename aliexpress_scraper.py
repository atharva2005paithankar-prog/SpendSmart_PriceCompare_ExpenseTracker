import requests
from bs4 import BeautifulSoup
import re

SCRAPER_API_KEY = '3ad116f162565665bf7a6883b7eb8a2b'

def extract_lowest_price(price_text):
    # Extract the lowest value in a price range. Picks minimum value.
    price_text = price_text.replace(',', '').replace('\u202f', ' ').replace('\xa0', ' ')
    matches = re.findall(r'[\d\.]+', price_text)
    numbers = [float(p) for p in matches]
    if numbers:
        return min(numbers)
    return float('inf')

def is_valid_title(title, search_term):
    """Checks if title both matches query and isn't an accessory or bundle."""
    title_lower = title.lower()
    search_lower = search_term.lower()
    search_words = search_lower.split()
    if not all(word in title_lower for word in search_words):
        return False
    banned_words = [
        'case', 'cover', 'charger', 'cable', 'protector', 'glass', 'film', 'adapter',
        'screen', 'battery', 'keyboard', 'mouse', 'headphones', 'earbuds', 'lot', 'lots',
        'set', 'bundle', 'replacement', 'pack', 'accessories', 'accessory', 'screen protector',
        'shell', 'housing', 'tempered', 'glue', 'repair', 'stand', 'holder', 'mount'
    ]
    for word in banned_words:
        if word in title_lower:
            return False
    return True

def scrape_cheapest_product(search_term):
    """Scrape AliExpress and return the cheapest valid, real product listing."""
    base_url = 'https://www.aliexpress.com/w/wholesale-' + search_term.replace(' ', '+') + '.html'
    scraperapi_url = f'http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={base_url}'
    response = requests.get(scraperapi_url)
    if response.status_code != 200:
        print('AliExpress: Failed to fetch data')
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    valid_items = []
    for item in soup.select('div[data-widget-type="productCard"]'):
        link_tag = item.find('a', href=True)
        title_tag = link_tag
        price_tag = None
        for pclass in ['._37W_B', '._1WkRf', '._2cXOy', '._1LY7D', '.mGXnE', '.aSZFC_S1', 'span', 'div._12A8D']:
            price_tag = item.select_one(pclass) if pclass.startswith('.') else item.find(pclass)
            if price_tag and price_tag.get_text(strip=True):
                break
        if title_tag and price_tag and link_tag:
            title = title_tag.get_text(strip=True)
            if not is_valid_title(title, search_term):
                continue
            price = extract_lowest_price(price_tag.get_text(strip=True))
            if price == float('inf') or price <= 0 or price > 1e6:
                continue
            link = link_tag['href']
            if link.startswith('//'):
                link = 'https:' + link
            elif not link.startswith('http'):
                link = 'https://www.aliexpress.com' + link
            valid_items.append({
                'title': title,
                'price': price,
                'link': link
            })
    if not valid_items:
        print('AliExpress: No valid items found')
        return None
    cheapest = sorted(valid_items, key=lambda x: x['price'])[0]
    return cheapest

# New: return top-3 cheapest valid results
def scrape_top_products(search_term):
    base_url = 'https://www.aliexpress.com/w/wholesale-' + search_term.replace(' ', '+') + '.html'
    scraperapi_url = f'http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={base_url}'
    response = requests.get(scraperapi_url)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    valid_items = []
    for item in soup.select('div[data-widget-type="productCard"]'):
        link_tag = item.find('a', href=True)
        title_tag = link_tag
        price_tag = None
        for pclass in ['._37W_B', '._1WkRf', '._2cXOy', '._1LY7D', '.mGXnE', '.aSZFC_S1', 'span', 'div._12A8D']:
            price_tag = item.select_one(pclass) if pclass.startswith('.') else item.find(pclass)
            if price_tag and price_tag.get_text(strip=True):
                break
        if title_tag and price_tag and link_tag:
            title = title_tag.get_text(strip=True)
            if not is_valid_title(title, search_term):
                continue
            price = extract_lowest_price(price_tag.get_text(strip=True))
            if price == float('inf') or price <= 0 or price > 1e6:
                continue
            link = link_tag['href']
            if link.startswith('//'):
                link = 'https:' + link
            elif not link.startswith('http'):
                link = 'https://www.aliexpress.com' + link
            valid_items.append({'title': title, 'price': price, 'link': link})
    valid_items.sort(key=lambda x: x['price'])
    # round for display
    for it in valid_items:
        try:
            it['price'] = round(it['price'], 2)
        except Exception:
            pass
    return valid_items[:3]
