# Wholesale Beverage Distribution Management System

A local prototype combining the four assigned internship projects:
1. Active Inventory Tracking & Alert System — bubble sort, low-stock flags.
2. Fleet Logistics & Route Prioritizer — selection sort, descending crate demand, >50-crate heavy-route flag.
3. Customer Credit & Outstanding Payment Ledger — linear search and 15/25/30-day overdue thresholds.
4. Product Shelf-Life & Batch Expiry Monitor — bubble sort by expiry, expired and under-7-day flags.

## Requirements
- Python 3.10 or newer
- Internet access for the first installation of Python packages

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted folder in VS Code.
3. Open the VS Code terminal in that folder.
4. Create a virtual environment (recommended):

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Start the application:

   ```powershell
   python -m streamlit run app.py
   ```

7. Streamlit will print a local address, usually `http://localhost:8501`. Open it in your browser.

## First use
- Select **Load / reset demo data** in the sidebar to load fictional examples.
- Explore each tab.
- Add or update records using the forms.
- Download CSV reports from each module or the Export Data tab.

## Database and privacy
- Data is stored in `data/beverage_management.db` using SQLite.
- Demo data is fictional. Replace it with authorized business data only if you have permission.
- Do not upload real customer names, account balances, or payment records to a public repository.
- Back up the database before deleting or changing records.

## Important scope notes
- This is an educational decision-support prototype, not a production system.
- The route module prioritizes demand; it does not compute shortest road paths, vehicle capacity, or optimal fleet assignment.
- The credit module flags accounts for follow-up/review; it does not automatically enforce real credit restrictions.
- The expiry module flags records for review; staff must follow applicable safety and disposal rules.
- The prototype is not a substitute for a validated business process or accounting system.

## Suggested tests
1. Inventory quantity below, equal to, and above threshold.
2. Route crate counts of 50 and 51.
3. Customer account due today, 14, 15, 24, 25, 29, and 30 days ago.
4. Batch expiry yesterday, today, 6 days from now, and 7 days from now.
5. Try searching for a customer ID that exists and one that does not.
6. Try exporting each table with records and with no records.

## Mapping to the four assigned works
| Project | Module | Assigned technique |
|---|---|---|
| Active Inventory Tracking & Alert System | Inventory | Bubble sort |
| Fleet Logistics & Route Prioritizer | Delivery Routes | Selection sort |
| Customer Credit & Outstanding Payment Ledger System | Customer Ledger | Linear search |
| Product Shelf-Life & Batch Expiry Monitor System | Batch Expiry | Bubble sort |
