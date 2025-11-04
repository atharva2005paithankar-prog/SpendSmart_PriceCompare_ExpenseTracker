# SpendSmart_PriceCompare_ExpenseTracker
SpendSmart is a web-based intelligent expense management and product price comparison application built using Flask and SQLite. It helps users track their spending, set monthly budgets, and make smarter purchase decisions by comparing product prices across major e-commerce platforms.
The system integrates expense tracking and price comparison features in one platform, using smart recommendations to help users save money.

~Key Features:
--Expense Tracking

Users can add, edit, or delete daily expenses, including date, category, amount, note, and payment method.

Automatically categorizes expenses (e.g., Electronics, Clothing, Groceries, etc.) based on keywords.

Displays total spending and a breakdown of expenses by category.

Summarizes data monthly and provides visual summaries via an API endpoint (/api/expenses/summary).

--Budget Management

Users can set monthly budget limits for each category.

The app shows how much of each budget is spent and how much remains.

Provides warnings when spending nears or exceeds category limits.

--Smart Price Comparison

Compares product prices across Amazon, Flipkart, eBay, AliExpress, and Snapdeal.

Displays prices, product titles, and store links for easy navigation.

Offers smart purchase recommendations:

Highlights good deals if prices are below average.

Warns when prices are significantly higher than the user’s past spending in that category.

Alerts users if a product’s cost exceeds the remaining budget.

--Data Intelligence

Uses stored expenses to compute:

Average spend per category

Monthly spending trends

Budget utilization

Employs dynamic category inference for products and expenses using keyword-based mapping.

~ Technology Stack:

Backend: Flask (Python)

Database: SQLite3

Frontend: HTML (via Flask templates)

Data Sources: Web scrapers for Amazon, Flipkart, eBay, AliExpress, and Snapdeal

Libraries Used: flask, sqlite3, datetime, custom scraper modules

~Unique Aspects:

Combines price comparison and budget-based expense analysis—two typically separate systems.

Provides personalized recommendations using user spending history.

Offers a budget guardrail system that advises before overspending.
