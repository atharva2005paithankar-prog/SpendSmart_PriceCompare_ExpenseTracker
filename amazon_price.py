from bs4 import BeautifulSoup
import requests
import re

# Headers for making requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'}

# Global variable to store the Amazon URL
amazon_url = None

def extract_lowest_price(price_text):
    price_text = price_text.replace(',', '')
    numbers = re.findall(r"[\d.]+", price_text)
    numbers = [float(n) for n in numbers]
    return min(numbers) if numbers else float('inf')

def is_valid_title(title, search_term):
    title_lower = title.lower()
    search_lower = search_term.lower()
    if not all(word in title_lower for word in search_lower.split()):
        return False
    banned = ['case', 'cover', 'charger', 'cable', 'protector', 'glass', 'film', 'adapter',
        'screen', 'battery', 'keyboard', 'mouse', 'headphones', 'earbuds',
        'lot', 'lots', 'set', 'bundle', 'replacement', 'pack', 'accessories',
        'accessory', 'screen protector', 'shell', 'housing', 'tempered', 'glue', 'repair', 'stand', 'holder', 'mount']
    for b in banned:
        if b in title_lower:
            return False
    return True

def amazon(name):
    try:
        global amazon_url
        name2 = name.replace(" ", "+")
        amazon_url = f'https://www.amazon.in/s?k={name2}'
        res = requests.get(amazon_url, headers=headers)
        print("\nSearching in Amazon...")
        soup = BeautifulSoup(res.text, 'html.parser')
        products = soup.select('.s-result-item')
        valid_items = []
        for product in products:
            try:
                title_tag = product.select_one('.a-text-normal')
                title = title_tag.getText().strip() if title_tag else None
                # price can be in .a-price .a-offscreen; fallbacks
                price_whole = product.select_one('.a-price-whole')
                price_offscreen = product.select_one('.a-price .a-offscreen')
                range_tag = product.select_one('.a-price-range')
                if range_tag and range_tag.text.strip():
                    price_text = range_tag.text.strip()
                elif price_offscreen and price_offscreen.text.strip():
                    price_text = price_offscreen.text.strip()
                elif price_whole and price_whole.text.strip():
                    price_text = price_whole.text.strip()
                else:
                    price_text = None
                link = product.select_one('a.a-link-normal')
                if title and price_text and link and is_valid_title(title, name):
                    price = extract_lowest_price(price_text)
                    url = 'https://www.amazon.in' + link['href'] if link['href'].startswith('/') else link['href']
                    valid_items.append({'title': title, 'price': price, 'url': url})
            except Exception:
                continue
        if not valid_items:
            return []
        valid_items.sort(key=lambda x: x['price'])
        # limit to top 3
        top3 = valid_items[:3]
        # normalize price to int for display
        for it in top3:
            try:
                it['price'] = int(round(it['price']))
            except Exception:
                pass
        return top3
    except Exception as e:
        print(f"Error in Amazon search: {str(e)}")
        return []

def convert(a):
    b = a.replace(" ", '')
    c = b.replace("INR", '')
    d = c.replace(",", '')
    f = d.replace("₹", '')
    g = int(float(f))
    return g

def compare_prices():
    name = input("Product Name:\n")
    results = amazon(name)
    if results:
        for r in results:
            print("\nAmazon price: ₹", r['price'])
            print("URL: ", r['url'])
    else:
        print("Amazon: No product found!")
    print("---------------------------------------------------------URLs--------------------------------------------------------------")
    print("Amazon : \n", amazon_url)
    print("---------------------------------------------------------------------------------------------------------------------------")

# Backward compatibility (not used by app anymore)
def get_price(product_name):
    results = amazon(product_name)
    if results:
        # Return the cheapest single item for legacy callers
        r = results[0]
        return f"{product_name}: ₹{r['price']}"
    return None

# New API for top results
def get_top_prices(product_name):
    return amazon(product_name)

if __name__ == "__main__":
    compare_prices()
