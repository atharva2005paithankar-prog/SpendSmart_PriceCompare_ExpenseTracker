from bs4 import BeautifulSoup
import requests
import re
import random
import time
import json

# List of user agents to rotate (more modern and diverse browser signatures)
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
]


def get_random_headers():
    """Generate random headers to avoid detection"""
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1'
    }


def search_flipkart(query):
    """Search Flipkart for a product and return the search results page HTML"""
    search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}&otracker=search&otracker1=search&marketplace=FLIPKART"

    try:
        # Create a session to maintain cookies
        session = requests.Session()

        # Add a cookie consent cookie to bypass any cookie warnings
        session.cookies.set('COOKIE_CONSENT', 'true', domain='www.flipkart.com')

        # Get the search results page
        response = session.get(search_url, headers=get_random_headers(), timeout=15)

        # Save the HTML to debug
        with open("flipkart_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"Status code: {response.status_code}")
        return response.text
    except Exception as e:
        print(f"Error searching Flipkart: {e}")
        return None


def debug_html(html):
    """Print a sample of the HTML to help debug"""
    if html:
        print("\n--- HTML Sample (first 500 chars) ---")
        print(html[:500])
        print("--- End of Sample ---\n")

        # Look for common Flipkart elements
        soup = BeautifulSoup(html, 'html.parser')

        # Check for product grid
        product_grid = soup.find('div', class_='_1YokD2')
        print(f"Product grid found: {product_grid is not None}")

        # Check for individual products
        products = soup.find_all('div', class_='_1AtVbE')
        print(f"Product divs found: {len(products)}")

        # Check for prices
        prices = soup.find_all('div', class_=lambda x: x and ('_30jeq3' in x))
        print(f"Price elements found: {len(prices)}")

        # Check if we're blocked or facing a captcha
        captcha = soup.find('div', id='captcha-form')
        blocked_msg = soup.find(string=re.compile('blocked|captcha|robot|human', re.IGNORECASE))
        if captcha or blocked_msg:
            print("WARNING: Possible captcha or blocking detected!")


def extract_products_aggressive(html):
    """More aggressive approach to find products regardless of class names"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    products = []

    # Look for any element that might contain price with ₹ symbol
    price_elements = soup.find_all(string=re.compile('₹[0-9,]+'))
    print(f"Found {len(price_elements)} potential price elements")

    for price_elem in price_elements:
        try:
            # Get the parent element that contains the price
            container = price_elem.parent

            # Try to find a nearby element that could be a product name
            # Search up to 3 levels up and then back down for potential product names
            potential_container = container
            for _ in range(3):
                if potential_container.parent:
                    potential_container = potential_container.parent

            # Look for elements that might contain product names (longer text)
            name_elem = None
            for elem in potential_container.find_all(['a', 'h1', 'h2', 'h3', 'div', 'span']):
                text = elem.get_text().strip()
                # Product names are usually longer than 15 chars and don't contain special symbols
                if len(text) > 15 and not re.match(r'[₹$€£¥]', text) and not elem.find_all():
                    name_elem = elem
                    break

            # Find the closest <a> tag that might have the product URL
            link_elem = None
            for parent in price_elem.parents:
                if parent.name == 'a' and 'href' in parent.attrs:
                    link_elem = parent
                    break

                # If not a direct parent, check siblings and children
                link_check = parent.find('a', href=True)
                if link_check:
                    link_elem = link_check
                    break

            # Extract data
            price = price_elem.strip()
            name = name_elem.get_text().strip() if name_elem else "Unknown Product"
            price_value = int(re.sub(r'[^\d]', '', price))

            # Construct URL
            if link_elem and 'href' in link_elem.attrs:
                url = link_elem['href']
                if not url.startswith('http'):
                    url = f"https://www.flipkart.com{url}"
            else:
                url = None

            products.append({
                "name": name,
                "price": price,
                "price_value": price_value,
                "url": url
            })

        except Exception as e:
            print(f"Error processing price element: {e}")

    return products


def extract_lowest_price(price_text):
    price_text = price_text.replace(",", "")
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


def extract_products(html):
    """Extract product information from Flipkart search results page"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    products = []

    grid = soup.find('div', class_='_1YokD2')
    containers = []

    containers = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['_1AtVbE', '_2kHMtA', '_4ddWXP', '_1xHGtK']))
    if not containers:
        print("Using fallback approach for product extraction")
        price_elements = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['_30jeq3', '_1_WHN1', 'Nx9bgj']))
        for price_elem in price_elements:
            for parent in price_elem.parents:
                if parent.name == 'div' and parent.find('a'):
                    containers.append(parent)
                    break
    print(f"Found {len(containers)} potential product containers")

    for container in containers:
        try:
            name_element = container.find(['div', 'a', 'h1', 'h2', 'h3', 'span'],
                                          class_=lambda x: x and any(
                                              c in x for c in ['_4rR01T', 's1Q9rs', 'IRpwTa', 'VU-Ztz', '6EbuvT']))
            if not name_element:
                links = container.find_all('a')
                for link in links:
                    if link.get_text().strip() and len(link.get_text().strip()) > 15:
                        name_element = link
                        break
            price_element = container.find('div', class_=lambda x: x and any(
                c in x for c in ['_30jeq3', '_1_WHN1', 'Nx9bgj', 'CxhGGd']))
            link_element = container.find('a', href=True)
            if (name_element or price_element) and link_element:
                name = name_element.get_text().strip() if name_element else "Name not found"
                if not is_valid_title(name, ""):
                    continue
                price = price_element.get_text().strip() if price_element else "Price not found"
                price_value = 0
                if price != "Price not found":
                    price_value = extract_lowest_price(price)
                url = link_element['href']
                if not url.startswith('http'):
                    url = f"https://www.flipkart.com{url}"
                products.append({
                    "name": name,
                    "price": price,
                    "price_value": price_value,
                    "url": url
                })
        except Exception as e:
            print(f"Error extracting product: {e}")
    if not products:
        print("Using aggressive approach for product extraction")
        products = extract_products_aggressive(html)
    return products


def filter_products(products, query):
    """Filter out any results that clearly aren't actual products and those that are sold out"""
    filtered = []

    # Normalize the query (e.g., lowercase) to make comparisons case-insensitive
    query_lower = query.lower()

    for product in products:
        # Skip products with "unknown product" name or without a valid URL
        if product["name"] == "Unknown Product" or not product["url"]:
            continue

        # Skip category pages rather than actual products
        if '/pr?' in product["url"] and 'marketplace=FLIPKART' not in product["url"]:
            continue

        # Mark out-of-stock or sold-out products
        name_lower = product["name"].lower()
        if "sold out" in name_lower or "out of stock" in name_lower:
            product["in_stock"] = False
        else:
            product["in_stock"] = True

        # Only include products that match the query closely (avoid other models like Pro or Pro Max)
        if query_lower in product["name"].lower() and "pro" not in product["name"].lower() and "max" not in product["name"].lower():
            filtered.append(product)

    return filtered


def strictest_main_match(products, query):
    # Helper: counts extra words beyond query, ignores order.
    query_words = set(w.lower() for w in query.split() if w)
    best_products = []
    min_extra = None
    for p in products:
        name_words = set(w.lower() for w in p["name"].split() if w)
        # Only keep those containing all query words
        if not query_words.issubset(name_words):
            continue
        # Count extra tokens
        extra = len(name_words - query_words)
        if min_extra is None or extra < min_extra:
            best_products = [p]
            min_extra = extra
        elif extra == min_extra:
            best_products.append(p)
    # fallback: If for some reason nothing matches all query words, fallback to original list
    if best_products:
        return best_products
    return products


def flipkart_price_comparison(query):
    """Search for a product on Flipkart and return top 3 price comparison results for best main product matches"""
    print(f"Searching for '{query}' on Flipkart...")
    html = search_flipkart(query)
    if not html:
        print("Failed to retrieve search results from Flipkart.")
        return []
    debug_html(html)
    products = extract_products(html)
    filtered = [p for p in products if is_valid_title(p["name"], query)]
    main_matches = strictest_main_match(filtered, query)
    if not main_matches:
        print("No products found on Flipkart.")
        return []
    main_matches = sorted(main_matches, key=lambda x: x["price_value"])
    # Return up to 3 cheapest unique name+price matches (avoid duplicates)
    seen = set()
    shortlist = []
    for item in main_matches:
        key = (item["name"].lower(), item["price_value"])
        if key in seen:
            continue
        seen.add(key)
        shortlist.append(item)
        if len(shortlist) >= 3:
            break
    return shortlist


def main():
    # Get user input
    query = input("Enter product to search on Flipkart: ")

    # Search for the product
    products = flipkart_price_comparison(query)

    # Display results
    if products:
        # Sort products by price (ASCENDING order - lowest first)
        products.sort(key=lambda x: x["price_value"])
        
        # Display only the cheapest product
        print(f"\nFound {len(products)} products on Flipkart. Showing the cheapest item:")
        print("-" * 80)
        print(f"Product: {products[0]['name']}")
        print(f"Price: {products[0]['price']}")
        print(f"URL: {products[0]['url']}")
        print("-" * 80)
        
        # Return the cheapest product for get_price function
        return products[0]
    else:
        print("No products found. Try a different search term.")
        return None

    # Write output to file for debugging
    with open("flipkart_products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
        print("Debug output written to flipkart_products.json")


def get_price(product_name):
    # Return a list of up to 3 cheapest/best items
    products = flipkart_price_comparison(product_name)
    if products:
        # Return as list of dicts (serialized)
        return [{
            'name': p['name'],
            'price': p['price'],
            'url': p['url'],
            'in_stock': p.get('in_stock', True),
            'amount': p.get('price_value', 0)
        } for p in products]
    else:
        return []




# flipkart_price.py


if __name__ == "__main__":
    main()