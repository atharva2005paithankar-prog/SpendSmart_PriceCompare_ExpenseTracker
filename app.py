from flask import Flask, render_template, request, redirect, url_for, jsonify
import amazon_price
import flipkart_price
from ebay_scraper import scrape_top_products
from aliexpress_scraper import scrape_top_products as scrape_top_products_aliexpress
from snapdeal_scraper import scrape_top_products as scrape_snapdeal
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'expenses.db')

# --- Helpers for Smart Recommendations ---
CATEGORY_KEYWORDS = {
    'Electronics': ['phone','iphone','mobile','laptop','tablet','camera','tv','earbuds','headphone','smartwatch','charger'],
    'Clothing': ['shoe','sandal','tshirt','shirt','jeans','dress','apparel','cloth','jacket','hoodie','sneaker'],
    'Groceries': ['grocery','food','snack','beverage','drink','rice','atta','oil','milk','bread'],
    'Home': ['mattress','bedsheet','pillow','furniture','sofa','chair','table','curtain'],
    'Beauty': ['cream','serum','lotion','shampoo','makeup','lipstick','conditioner'],
}

# --- Utilities ---

def month_key(dt: datetime | None = None) -> str:
    d = dt or datetime.now()
    return d.strftime('%Y-%m')

def infer_category_py(title: str) -> str:
    if not title:
        return 'Shopping'
    t = title.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in t for w in words):
            return cat
    return 'Shopping'

def get_category_averages():
    conn = get_db_connection()
    rows = conn.execute('SELECT category, AVG(amount) as avg_amt FROM expenses GROUP BY category').fetchall()
    conn.close()
    return { r['category']: float(r['avg_amt'] or 0) for r in rows }

def get_monthly_spend_by_category(ym: str | None = None):
    ym = ym or month_key()
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT category, IFNULL(SUM(amount),0) AS total FROM expenses WHERE substr(date,1,7)=? GROUP BY category",
        (ym,)
    ).fetchall()
    conn.close()
    return { r['category']: float(r['total'] or 0) for r in rows }

def get_budgets():
    conn = get_db_connection()
    rows = conn.execute('SELECT category, monthly_limit FROM budgets').fetchall()
    conn.close()
    return { r['category']: float(r['monthly_limit']) for r in rows }

# --- DB ---

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )
        """
    )
    # Ensure payment_method column exists
    cols = conn.execute("PRAGMA table_info(expenses)").fetchall()
    col_names = {c[1] for c in cols}
    if 'payment_method' not in col_names:
        conn.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT DEFAULT 'Other'")
    # Budgets table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            category TEXT PRIMARY KEY,
            monthly_limit REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

init_db()


@app.route('/')
def index():
    # Render the index page for user input
    return render_template('index.html')


@app.route('/compare', methods=['POST'])
def compare_prices():
    # Get the user's input from the form
    product_name = request.form['product_name']

    # Get prices from all platforms
    amazon_results = amazon_price.get_top_prices(product_name)
    flipkart_result = flipkart_price.get_price(product_name)
    ebay_results = scrape_top_products(product_name)
    aliexpress_results = scrape_top_products_aliexpress(product_name)
    snapdeal_results = scrape_snapdeal(product_name)

    # Fetch user averages and budgets for recommendations/guardrails
    avg_by_cat = get_category_averages()
    budgets = get_budgets()
    spent_this_month = get_monthly_spend_by_category()

    # Debug logs to verify scraper outputs
    try:
        print("AliExpress results:", aliexpress_results)
        if not aliexpress_results:
            print("AliExpress returned no results!")
        else:
            print("AliExpress sample:", aliexpress_results[:1])
        print("eBay results:", ebay_results)
        if not ebay_results:
            print("eBay returned no results!")
        else:
            print("eBay sample:", ebay_results[:1])
    except Exception as dbgerr:
        print("DEBUG ERROR:", dbgerr)

    def attach_recommendation(title: str, amount: float):
        category = infer_category_py(title)
        avg = avg_by_cat.get(category, 0)
        budget = budgets.get(category)
        spent = spent_this_month.get(category, 0)
        remaining = None
        if budget is not None:
            remaining = max(budget - spent, 0)
        rec_text = None
        rec_type = None
        try:
            amt = float(amount or 0)
        except Exception:
            amt = 0
        if avg and amt:
            if amt >= 1.1 * avg:
                diff = int(round(((amt - avg) / avg) * 100))
                rec_text = f"About {diff}% higher than your {category} average (₹{int(avg)}). Consider cheaper options."
                rec_type = 'warn'
            elif amt <= 0.9 * avg:
                diff = int(round(((avg - amt) / avg) * 100))
                rec_text = f"Good deal! ~{diff}% below your {category} average (₹{int(avg)})."
                rec_type = 'good'
        # Budget guardrail message has priority if exceeding
        if remaining is not None and amt:
            if amt > remaining:
                over = int(amt - remaining)
                rec_text = f"Exceeds {category} budget by ₹{over}. Remaining: ₹{int(remaining)}"
                rec_type = 'warn'
            elif remaining > 0 and remaining - amt <= 0.1 * (budget or 0):
                rec_text = f"Within ₹{int(remaining - amt)} of your {category} budget."
                rec_type = 'warn'
        return category, rec_text, rec_type, remaining, budget

    # Format results
    amazon_results_out = []
    for r in (amazon_results or []):
        amt_val = int(r.get('price', 0))
        category, rec_text, rec_type, remaining, budget = attach_recommendation(r.get('title',''), amt_val)
        amazon_results_out.append({
            'title': r.get('title', ''),
            'price': f"{product_name}: ₹{amt_val}",
            'url': r.get('url', ''),
            'amount': amt_val,
            'store': 'Amazon',
            'category': category,
            'rec_text': rec_text,
            'rec_type': rec_type,
            'budget_remaining': remaining,
            'budget_limit': budget
        })

    # --- Flipkart: multiple results ---
    flipkart_results = []
    if flipkart_result:
        for entry in flipkart_result:
            amt_val = int(entry.get('amount', 0))
            category, rec_text, rec_type, remaining, budget = attach_recommendation(entry.get('name',''), amt_val)
            flipkart_entry = {
                'name': entry.get('name', ''),
                'price': entry.get('price', ''),
                'url': entry.get('url', ''),
                'in_stock': entry.get('in_stock', True),
                'amount': amt_val,
                'store': 'Flipkart',
                'category': category,
                'rec_text': rec_text,
                'rec_type': rec_type,
                'budget_remaining': remaining,
                'budget_limit': budget
            }
            flipkart_results.append(flipkart_entry)

    ebay_results_out = []
    for r in (ebay_results or []):
        amt_val = float(r.get('price', 0))
        category, rec_text, rec_type, remaining, budget = attach_recommendation(r.get('title',''), amt_val)
        ebay_results_out.append({
            'title': r.get('title', ''),
            'price': f"{product_name}: ${amt_val}",
            'url': r.get('link', ''),
            'amount': amt_val,
            'store': 'eBay',
            'category': category,
            'rec_text': rec_text,
            'rec_type': rec_type,
            'budget_remaining': remaining,
            'budget_limit': budget
        })

    aliexpress_results_out = []
    for r in (aliexpress_results or []):
        amt_val = float(r.get('price', 0))
        category, rec_text, rec_type, remaining, budget = attach_recommendation(r.get('title',''), amt_val)
        aliexpress_results_out.append({
            'title': r.get('title', ''),
            'price': f"{product_name}: ${amt_val}",
            'url': r.get('link', ''),
            'amount': amt_val,
            'store': 'AliExpress',
            'category': category,
            'rec_text': rec_text,
            'rec_type': rec_type,
            'budget_remaining': remaining,
            'budget_limit': budget
        })

    snapdeal_results_out = []
    for r in snapdeal_results or []:
        amt_val = int(r.get('price', 0))
        category, rec_text, rec_type, remaining, budget = attach_recommendation(r.get('title',''), amt_val)
        snapdeal_results_out.append({
            'title': r.get('title', ''),
            'price': f"{product_name}: ₹{amt_val}",
            'url': r.get('url', ''),
            'amount': amt_val,
            'store': 'Snapdeal',
            'category': category,
            'rec_text': rec_text,
            'rec_type': rec_type,
            'budget_remaining': remaining,
            'budget_limit': budget
        })

    # Pass data to the template for display
    return render_template('index.html', 
                         amazon_results=amazon_results_out,
                         flipkart_results=flipkart_results,
                         ebay_results=ebay_results_out,
                         aliexpress_results=aliexpress_results_out,
                         snapdeal_results=snapdeal_results_out)


# Expense Tracker Routes
@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        date_str = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
        category = request.form.get('category', '').strip() or 'Other'
        amount = float(request.form.get('amount', '0') or 0)
        note = request.form.get('note', '').strip()
        payment_method = request.form.get('payment_method', 'Other').strip() or 'Other'
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO expenses (date, category, amount, note, payment_method) VALUES (?, ?, ?, ?, ?)',
            (date_str, category, amount, note, payment_method)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('expenses'))

    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM expenses ORDER BY date DESC, id DESC').fetchall()
    total = conn.execute('SELECT IFNULL(SUM(amount),0) as total FROM expenses').fetchone()['total']
    conn.close()
    budgets = get_budgets()
    spent = get_monthly_spend_by_category()
    # Build list for template: category, limit, spent, remaining
    budgets_list = []
    for cat, limit in budgets.items():
        s = spent.get(cat, 0)
        budgets_list.append({ 'category': cat, 'limit': limit, 'spent': s, 'remaining': max(limit - s, 0) })
    return render_template('expenses.html', expenses=rows, total=total, budgets=budgets_list)


@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('expenses'))


@app.route('/expenses/edit/<int:expense_id>', methods=['POST'])
def edit_expense(expense_id):
    date_str = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
    category = request.form.get('category', '').strip() or 'Other'
    amount = float(request.form.get('amount', '0') or 0)
    note = request.form.get('note', '').strip()
    payment_method = request.form.get('payment_method', 'Other').strip() or 'Other'

    conn = get_db_connection()
    conn.execute(
        'UPDATE expenses SET date = ?, category = ?, amount = ?, note = ?, payment_method = ? WHERE id = ?',
        (date_str, category, amount, note, payment_method, expense_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('expenses'))


@app.route('/budgets', methods=['POST'])
def upsert_budget():
    category = (request.form.get('budget_category') or '').strip()
    try:
        monthly_limit = float(request.form.get('budget_limit', '0') or 0)
    except Exception:
        monthly_limit = 0
    if category and monthly_limit >= 0:
        conn = get_db_connection()
        conn.execute('INSERT INTO budgets(category, monthly_limit) VALUES(?, ?) ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit', (category, monthly_limit))
        conn.commit()
        conn.close()
    return redirect(url_for('expenses'))


@app.route('/api/expenses/summary')
def expenses_summary():
    conn = get_db_connection()
    # Totals by category
    by_cat = conn.execute('SELECT category, SUM(amount) as total FROM expenses GROUP BY category').fetchall()
    # Totals by month (YYYY-MM)
    by_month = conn.execute(
        """
        SELECT substr(date,1,7) as ym, SUM(amount) as total
        FROM expenses
        GROUP BY ym
        ORDER BY ym
        """
    ).fetchall()
    conn.close()
    return jsonify({
        'byCategory': [{ 'category': r['category'], 'total': r['total'] } for r in by_cat],
        'byMonth': [{ 'month': r['ym'], 'total': r['total'] } for r in by_month]
    })


if __name__ == '__main__':
    app.run(debug=True)
