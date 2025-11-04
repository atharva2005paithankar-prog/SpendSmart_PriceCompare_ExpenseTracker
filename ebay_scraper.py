import requests
from bs4 import BeautifulSoup
import re

# Replace this with your actual ScraperAPI key
SCRAPER_API_KEY = '3ad116f162565665bf7a6883b7eb8a2b'

def is_valid_title(title, search_term):
    # Convert to lowercase for case-insensitive comparison
    title_lower = title.lower()
    search_lower = search_term.lower()
    
    # Split search term into words
    search_words = search_lower.split()
    
    # Check if all words from search term are in the title
    if not all(word in title_lower for word in search_words):
        return False
        
    # Filter out accessories and related items
    accessory_terms = ['case', 'cover', 'protector', 'screen', 'charger', 'cable', 
                      'adapter', 'stand', 'holder', 'mount', 'skin', 'tempered', 
                      'glass', 'film', 'stylus', 'pen', 'bag', 'pouch', 'strap',
                      'battery', 'power bank', 'dock', 'keyboard', 'mouse', 'headphones',
                      'earphones', 'earbuds', 'speaker', 'remote', 'controller',
                      'lot', 'bundle', 'pack', 'set']
    
    # If any accessory term is in the title, it's likely an accessory
    if any(term in title_lower for term in accessory_terms):
        return False
        
    return True

def extract_price(price_text):
    price_text = price_text.replace(',', '')
    match = re.search(r'[\d.]+', price_text)
    return float(match.group()) if match else float('inf')

def scrape_cheapest_product(search_term):
    base_url = 'https://www.ebay.com/sch/i.html'
    params = {'_nkw': search_term, '_ipg': 50}

    scraperapi_url = f'http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url='
    full_url = scraperapi_url + requests.Request('GET', base_url, params=params).prepare().url

    response = requests.get(full_url)

    if response.status_code != 200:
        print("Failed to fetch data")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    valid_items = []

    for item in soup.select('.s-item'):
        title_tag = item.select_one('.s-item__title')
        price_tag = item.select_one('.s-item__price')
        link_tag = item.select_one('a.s-item__link')

        if title_tag and price_tag and link_tag:
            title = title_tag.get_text(strip=True)
            if is_valid_title(title, search_term):
                price = extract_price(price_tag.get_text(strip=True))
                valid_items.append({
                    'title': title,
                    'price': price,
                    'link': link_tag['href']
                })

    if not valid_items:
        return None

    cheapest = sorted(valid_items, key=lambda x: x['price'])[0]
    return cheapest

# New: return top-3 cheapest valid items
def scrape_top_products(search_term):
    base_url = 'https://www.ebay.com/sch/i.html'
    params = {'_nkw': search_term, '_ipg': 50}
    scraperapi_url = f'http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url='
    full_url = scraperapi_url + requests.Request('GET', base_url, params=params).prepare().url
    response = requests.get(full_url)
    if response.status_code != 200:
        print("Failed to fetch data")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    valid_items = []
    for item in soup.select('.s-item'):
        title_tag = item.select_one('.s-item__title')
        price_tag = item.select_one('.s-item__price')
        link_tag = item.select_one('a.s-item__link')
        if title_tag and price_tag and link_tag:
            title = title_tag.get_text(strip=True)
            if is_valid_title(title, search_term):
                price = extract_price(price_tag.get_text(strip=True))
                valid_items.append({
                    'title': title,
                    'price': price,
                    'link': link_tag['href']
                })
    valid_items.sort(key=lambda x: x['price'])
    return valid_items[:3]

if __name__ == '__main__':
    search_term = input("Enter exact product (e.g., 'iphone 15' or 'iphone 15 pro'): ")
    result = scrape_cheapest_product(search_term)

    if result:
        print("\nCheapest matching result:")
        print(f"Title: {result['title']}")
        print(f"Price: ${result['price']}")
        print(f"Link: {result['link']}")
    else:
        print("No matching results found.")
