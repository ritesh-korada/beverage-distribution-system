import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# 1. APPLICATION CONFIGURATION
# ============================================================

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "data" / "beverage_management.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="Beverage Distribution Manager",
    page_icon="📦",
    layout="wide"
)


# ============================================================
# 2. DATABASE FUNCTIONS
# ============================================================

def connect():
    """Connect to SQLite and return dictionary-compatible rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create database tables if they do not exist."""
    with connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS inventory (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                crates INTEGER NOT NULL DEFAULT 0,
                threshold INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS routes (
                route_id TEXT PRIMARY KEY,
                crates INTEGER NOT NULL DEFAULT 0,
                destination TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ledger (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                amount_due REAL NOT NULL DEFAULT 0,
                due_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                expiry_date TEXT NOT NULL
            );
        """)


def rows(query, params=()):
    """Return database records as dictionaries."""
    with connect() as con:
        return [
            dict(row)
            for row in con.execute(query, params).fetchall()
        ]


def execute(query, params=()):
    """Execute an INSERT, UPDATE, or DELETE query."""
    with connect() as con:
        con.execute(query, params)
        con.commit()


# ============================================================
# 3. SEARCHING AND SORTING ALGORITHMS
# ============================================================

def bubble_sort_low_stock(items):
    """Bubble sort: prioritize products requiring restocking."""
    items = list(items)

    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            left = (
                items[j]["crates"] > items[j]["threshold"],
                items[j]["crates"] - items[j]["threshold"]
            )

            right = (
                items[j + 1]["crates"] > items[j + 1]["threshold"],
                items[j + 1]["crates"] - items[j + 1]["threshold"]
            )

            if left > right:
                items[j], items[j + 1] = items[j + 1], items[j]

    return items


def selection_sort_routes(items):
    """Selection sort: arrange routes by descending crate quantity."""
    items = list(items)

    for i in range(len(items)):
        max_idx = i

        for j in range(i + 1, len(items)):
            if items[j]["crates"] > items[max_idx]["crates"]:
                max_idx = j

        items[i], items[max_idx] = items[max_idx], items[i]

    return items


def linear_search_customer(items, customer_id):
    """Linear search for a customer ID."""
    for item in items:
        if str(item["customer_id"]).lower() == str(customer_id).strip().lower():
            return item

    return None


def bubble_sort_batches(items):
    """Bubble sort: arrange batches by earliest expiry date."""
    items = list(items)

    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            date1 = items[j]["expiry_date"]
            date2 = items[j + 1]["expiry_date"]

            if date1 > date2:
                items[j], items[j + 1] = items[j + 1], items[j]

    return items


# ============================================================
# 4. COMMON HELPER FUNCTIONS
# ============================================================

def show_table(data, columns=None):
    """Display records in a table."""
    if data:
        df = pd.DataFrame(data, columns=columns)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No records available.")


def download_csv(data, filename, button_key):
    """Create a CSV download button."""
    if data:
        df = pd.DataFrame(data)

        st.download_button(
            label=f"Download {filename}",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv",
            key=button_key
        )
    else:
        st.info("No data available to export.")


def get_payment_status(due_date, amount):
    """Calculate a customer's payment follow-up status."""
    if float(amount) <= 0:
        return "Paid"

    overdue_days = (date.today() - date.fromisoformat(due_date)).days

    if overdue_days <= 0:
        return "Payment Pending"
    elif overdue_days <= 14:
        return "Payment Reminder"
    elif overdue_days <= 24:
        return "Follow-up Required"
    elif overdue_days <= 29:
        return "Urgent Follow-up"
    else:
        return "Credit Restriction Review"


def get_expiry_status(expiry_date):
    """Calculate a batch's expiry status."""
    days_remaining = (date.fromisoformat(expiry_date) - date.today()).days

    if days_remaining < 0:
        return "Expired"
    elif days_remaining == 0:
        return "Expires Today"
    elif days_remaining < 7:
        return "Critical - Review"
    elif days_remaining <= 30:
        return "Expiring Soon"
    else:
        return "Safe"


def find_record(records, field, value):
    """Find a dictionary record by its ID."""
    return next(
        (record for record in records if record[field] == value),
        None
    )


# ============================================================
# 5. INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# 6. APPLICATION HEADER
# ============================================================

st.title("📦 Wholesale Beverage Distribution Management System")

st.caption(
    "Inventory tracking | Delivery route prioritization | "
    "Customer credit management | Batch expiry monitoring"
)

st.info(
    "Use the tabs below to manage records. "
    "Use fictional customer data while testing."
)


# ============================================================
# 7. SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Quick Actions")

    if st.button("Load / Reset Demo Data", use_container_width=True):
        today = date.today()

        with connect() as con:
            con.execute("DELETE FROM inventory")
            con.execute("DELETE FROM routes")
            con.execute("DELETE FROM ledger")
            con.execute("DELETE FROM batches")

            con.executemany(
                "INSERT INTO inventory VALUES (?, ?, ?, ?)",
                [
                    ("P101", "Cola 750 ml", 8, 20),
                    ("P102", "Orange Drink", 35, 15),
                    ("P103", "Soda Water", 5, 10),
                    ("P104", "Lemon Soda", 18, 18)
                ]
            )

            con.executemany(
                "INSERT INTO routes VALUES (?, ?, ?)",
                [
                    ("R01", 20, "North Market"),
                    ("R02", 75, "Central Market"),
                    ("R03", 45, "East Market"),
                    ("R04", 58, "South Market")
                ]
            )

            con.executemany(
                "INSERT INTO ledger VALUES (?, ?, ?, ?)",
                [
                    ("C101", "Customer A", 5000,
                     (today - timedelta(days=10)).isoformat()),
                    ("C102", "Customer B", 8000,
                     (today - timedelta(days=18)).isoformat()),
                    ("C103", "Customer C", 12000,
                     (today - timedelta(days=27)).isoformat()),
                    ("C104", "Customer D", 15000,
                     (today - timedelta(days=35)).isoformat())
                ]
            )

            con.executemany(
                "INSERT INTO batches VALUES (?, ?, ?, ?)",
                [
                    ("B101", "Expired Sample Product", 10,
                     (today - timedelta(days=2)).isoformat()),
                    ("B102", "Near Expiry Product", 15,
                     (today + timedelta(days=4)).isoformat()),
                    ("B103", "Regular Product", 25,
                     (today + timedelta(days=20)).isoformat())
                ]
            )

        st.success("Demo data loaded successfully.")
        st.rerun()

    st.caption(f"Database: {DB_PATH.relative_to(APP_DIR)}")


# ============================================================
# 8. APPLICATION TABS
# ============================================================

tabs = st.tabs([
    "Overview",
    "1 · Inventory",
    "2 · Delivery Routes",
    "3 · Customer Ledger",
    "4 · Batch Expiry",
    "Export Data"
])


# ============================================================
# TAB 1: OVERVIEW
# ============================================================

with tabs[0]:
    st.header("Business Overview")

    inventory = rows("SELECT * FROM inventory")
    routes = rows("SELECT * FROM routes")
    customers = rows("SELECT * FROM ledger")
    batches = rows("SELECT * FROM batches")

    low_stock = [
        p for p in inventory
        if p["crates"] <= p["threshold"]
    ]

    overdue = [
        c for c in customers
        if c["amount_due"] > 0
        and date.fromisoformat(c["due_date"]) < date.today()
    ]

    expiring = [
        b for b in batches
        if (date.fromisoformat(b["expiry_date"]) - date.today()).days < 7
    ]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Products", len(inventory))
    c2.metric("Low-Stock Products", len(low_stock))
    c3.metric("Overdue Customers", len(overdue))
    c4.metric("Expired / Critical Batches", len(expiring))

    st.subheader("Low-Stock Alerts")

    if low_stock:
        show_table([
            {
                "Product ID": p["product_id"],
                "Product": p["product_name"],
                "Crates": p["crates"],
                "Threshold": p["threshold"]
            }
            for p in low_stock
        ])
    else:
        st.success("No low-stock products.")

    st.subheader("Overdue Customer Accounts")

    if overdue:
        show_table([
            {
                "Customer ID": c["customer_id"],
                "Customer": c["customer_name"],
                "Amount Due": f'₹{c["amount_due"]:,.2f}',
                "Due Date": c["due_date"],
                "Status": get_payment_status(
                    c["due_date"], c["amount_due"]
                )
            }
            for c in overdue
        ])
    else:
        st.success("No overdue customer accounts.")

    st.subheader("Batch Expiry Alerts")

    if expiring:
        show_table([
            {
                "Batch ID": b["batch_id"],
                "Product": b["product_name"],
                "Expiry Date": b["expiry_date"],
                "Status": get_expiry_status(b["expiry_date"])
            }
            for b in expiring
        ])
    else:
        st.success("No batches require an expiry review.")


# ============================================================
# TAB 2: INVENTORY
# ============================================================

with tabs[1]:
    st.header("Inventory Management")

    with st.expander("Add New Product"):
        with st.form("add_inventory_form"):
            pid = st.text_input("Product ID")
            pname = st.text_input("Product Name")
            crates = st.number_input("Current Crates", min_value=0, step=1)
            threshold = st.number_input("Minimum Threshold", min_value=0, step=1)

            submitted = st.form_submit_button("Add Product")

            if submitted:
                if not pid.strip() or not pname.strip():
                    st.error("Product ID and name are required.")
                else:
                    try:
                        execute(
                            "INSERT INTO inventory VALUES (?, ?, ?, ?)",
                            (pid.strip(), pname.strip(), int(crates), int(threshold))
                        )
                        st.success("Product added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Product ID already exists. Use Search and Edit Product.")

    st.subheader("Search and Edit Product")

    products = rows("SELECT * FROM inventory ORDER BY product_name")
    search = st.text_input("Search by Product ID or Product Name", key="inv_search")

    matches = [
        p for p in products
        if search.strip().lower() in
        f'{p["product_id"]} {p["product_name"]}'.lower()
    ]

    if matches:
        selected_id = st.selectbox(
            "Select Product",
            [p["product_id"] for p in matches],
            format_func=lambda x: f'{x} - {find_record(matches, "product_id", x)["product_name"]}',
            key="inv_selected"
        )

        selected = find_record(matches, "product_id", selected_id)

        with st.form("edit_inventory_form"):
            st.text_input("Product ID (cannot be changed)", value=selected["product_id"], disabled=True)
            name = st.text_input("Product Name", value=selected["product_name"])
            qty = st.number_input("Current Crates", min_value=0, value=int(selected["crates"]), step=1)
            limit = st.number_input("Minimum Threshold", min_value=0, value=int(selected["threshold"]), step=1)

            if st.form_submit_button("Save Product Changes"):
                if not name.strip():
                    st.error("Product name cannot be empty.")
                else:
                    execute(
                        "UPDATE inventory SET product_name=?, crates=?, threshold=? WHERE product_id=?",
                        (name.strip(), int(qty), int(limit), selected_id)
                    )
                    st.success("Product updated.")
                    st.rerun()

    elif search.strip():
        st.warning("No matching product found.")

    st.subheader("Inventory Records")

    inventory_sorted = bubble_sort_low_stock(
        rows("SELECT * FROM inventory")
    )

    inventory_df = pd.DataFrame([
        {
            "Product ID": p["product_id"],
            "Product Name": p["product_name"],
            "Crates": p["crates"],
            "Threshold": p["threshold"],
            "Status": "LOW STOCK" if p["crates"] <= p["threshold"] else "Sufficient"
        }
        for p in inventory_sorted
    ])

    st.dataframe(inventory_df, use_container_width=True, hide_index=True)

    if not inventory_df.empty:
        st.download_button(
            "Download Inventory CSV",
            inventory_df.to_csv(index=False).encode("utf-8"),
            "inventory_report.csv",
            "text/csv",
            key="inventory_csv"
        )

    with st.expander("Delete Product"):
        if products:
            delete_id = st.selectbox(
                "Select Product ID",
                [p["product_id"] for p in products],
                key="delete_product_id"
            )

            confirm = st.checkbox("Confirm product deletion", key="confirm_product_delete")

            if st.button("Delete Product", key="delete_product_button"):
                if confirm:
                    execute("DELETE FROM inventory WHERE product_id=?", (delete_id,))
                    st.success("Product deleted.")
                    st.rerun()
                else:
                    st.warning("Confirm before deleting.")


# ============================================================
# TAB 3: DELIVERY ROUTES
# ============================================================

with tabs[2]:
    st.header("Delivery Route Management")

    with st.expander("Add New Delivery Route"):
        with st.form("add_route_form"):
            route_id = st.text_input("Route ID")
            destination = st.text_input("Destination")
            crates = st.number_input("Number of Crates", min_value=0, step=1)

            if st.form_submit_button("Add Route"):
                if not route_id.strip() or not destination.strip():
                    st.error("Route ID and destination are required.")
                else:
                    try:
                        execute(
                            "INSERT INTO routes VALUES (?, ?, ?)",
                            (route_id.strip(), int(crates), destination.strip())
                        )
                        st.success("Route added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Route ID already exists. Use Search and Edit Route.")

    st.subheader("Search and Edit Route")

    route_records = rows("SELECT * FROM routes ORDER BY route_id")
    route_search = st.text_input("Search by Route ID or Destination", key="route_search")

    matching_routes = [
        r for r in route_records
        if route_search.strip().lower() in
        f'{r["route_id"]} {r["destination"]}'.lower()
    ]

    if matching_routes:
        selected_route_id = st.selectbox(
            "Select Route",
            [r["route_id"] for r in matching_routes],
            format_func=lambda x: f'{x} - {find_record(matching_routes, "route_id", x)["destination"]}',
            key="selected_route"
        )

        selected_route = find_record(matching_routes, "route_id", selected_route_id)

        with st.form("edit_route_form"):
            st.text_input("Route ID (cannot be changed)", value=selected_route["route_id"], disabled=True)
            new_destination = st.text_input("Destination", value=selected_route["destination"])
            new_crates = st.number_input("Number of Crates", min_value=0, value=int(selected_route["crates"]), step=1)

            if st.form_submit_button("Save Route Changes"):
                if not new_destination.strip():
                    st.error("Destination cannot be empty.")
                else:
                    execute(
                        "UPDATE routes SET crates=?, destination=? WHERE route_id=?",
                        (int(new_crates), new_destination.strip(), selected_route_id)
                    )
                    st.success("Route updated.")
                    st.rerun()

    elif route_search.strip():
        st.warning("No matching route found.")

    st.subheader("All Delivery Routes")

    sorted_routes = selection_sort_routes(rows("SELECT * FROM routes"))

    route_df = pd.DataFrame([
        {
            "Route ID": r["route_id"],
            "Crates": r["crates"],
            "Destination": r["destination"],
            "Status": "Heavy Route" if r["crates"] > 50 else "Normal Route"
        }
        for r in sorted_routes
    ])

    st.dataframe(route_df, use_container_width=True, hide_index=True)

    if not route_df.empty:
        st.download_button(
            "Download Routes CSV",
            route_df.to_csv(index=False).encode("utf-8"),
            "delivery_routes.csv",
            "text/csv",
            key="routes_csv"
        )

    with st.expander("Delete Delivery Route"):
        if route_records:
            delete_route_id = st.selectbox(
                "Select Route ID to Delete",
                [r["route_id"] for r in route_records],
                key="delete_route_id"
            )

            confirm = st.checkbox("Confirm route deletion", key="confirm_route_delete")

            if st.button("Delete Route", key="delete_route_button"):
                if confirm:
                    execute("DELETE FROM routes WHERE route_id=?", (delete_route_id,))
                    st.success("Route deleted.")
                    st.rerun()
                else:
                    st.warning("Confirm before deleting.")


# ============================================================
# TAB 4: CUSTOMER LEDGER
# ============================================================

with tabs[3]:
    st.header("Customer Ledger Management")

    with st.expander("Add New Customer"):
        with st.form("add_customer_form"):
            customer_id = st.text_input("Customer ID")
            customer_name = st.text_input("Customer Name")
            amount_due = st.number_input("Amount Due (₹)", min_value=0.0, step=100.0)
            due_date = st.date_input("Payment Due Date")

            if st.form_submit_button("Add Customer"):
                if not customer_id.strip() or not customer_name.strip():
                    st.error("Customer ID and name are required.")
                else:
                    try:
                        execute(
                            "INSERT INTO ledger VALUES (?, ?, ?, ?)",
                            (
                                customer_id.strip(),
                                customer_name.strip(),
                                float(amount_due),
                                due_date.isoformat()
                            )
                        )
                        st.success("Customer added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Customer ID already exists. Use Search and Edit Customer.")

    st.subheader("Search and Edit Customer")

    customer_records = rows("SELECT * FROM ledger ORDER BY customer_name")
    customer_search = st.text_input("Search by Customer ID or Name", key="customer_search")

    matching_customers = [
        c for c in customer_records
        if customer_search.strip().lower() in
        f'{c["customer_id"]} {c["customer_name"]}'.lower()
    ]

    if matching_customers:
        selected_customer_id = st.selectbox(
            "Select Customer",
            [c["customer_id"] for c in matching_customers],
            format_func=lambda x: f'{x} - {find_record(matching_customers, "customer_id", x)["customer_name"]}',
            key="selected_customer"
        )

        selected_customer = find_record(
            matching_customers, "customer_id", selected_customer_id
        )

        with st.form("edit_customer_form"):
            st.text_input("Customer ID (cannot be changed)", value=selected_customer["customer_id"], disabled=True)
            new_name = st.text_input("Customer Name", value=selected_customer["customer_name"])
            new_amount = st.number_input(
                "Amount Due (₹)",
                min_value=0.0,
                value=float(selected_customer["amount_due"]),
                step=100.0
            )
            new_due_date = st.date_input(
                "Payment Due Date",
                value=date.fromisoformat(selected_customer["due_date"])
            )

            if st.form_submit_button("Save Customer Changes"):
                if not new_name.strip():
                    st.error("Customer name cannot be empty.")
                else:
                    execute(
                        """
                        UPDATE ledger
                        SET customer_name=?, amount_due=?, due_date=?
                        WHERE customer_id=?
                        """,
                        (
                            new_name.strip(),
                            float(new_amount),
                            new_due_date.isoformat(),
                            selected_customer_id
                        )
                    )
                    st.success("Customer updated.")
                    st.rerun()

    elif customer_search.strip():
        st.warning("No matching customer found.")

    st.subheader("Customer Payment Ledger")

    customer_records = rows("SELECT * FROM ledger ORDER BY customer_name")

    customer_df = pd.DataFrame([
        {
            "Customer ID": c["customer_id"],
            "Customer Name": c["customer_name"],
            "Amount Due (₹)": c["amount_due"],
            "Due Date": c["due_date"],
            "Payment Status": get_payment_status(c["due_date"], c["amount_due"])
        }
        for c in customer_records
    ])

    st.dataframe(customer_df, use_container_width=True, hide_index=True)

    if not customer_df.empty:
        st.download_button(
            "Download Customer Ledger CSV",
            customer_df.to_csv(index=False).encode("utf-8"),
            "customer_ledger.csv",
            "text/csv",
            key="customer_csv"
        )

    st.subheader("Find Customer by ID")

    search_customer_id = st.text_input("Enter Customer ID", key="linear_customer_search")

    if st.button("Find Customer", key="find_customer_button"):
        found = linear_search_customer(customer_records, search_customer_id)

        if found:
            st.success("Customer found.")
            st.write(f'**Customer ID:** {found["customer_id"]}')
            st.write(f'**Name:** {found["customer_name"]}')
            st.write(f'**Amount Due:** ₹{found["amount_due"]:,.2f}')
            st.write(f'**Due Date:** {found["due_date"]}')
        else:
            st.warning("Customer not found.")

    with st.expander("Delete Customer"):
        if customer_records:
            delete_customer_id = st.selectbox(
                "Select Customer",
                [c["customer_id"] for c in customer_records],
                format_func=lambda x: f'{x} - {find_record(customer_records, "customer_id", x)["customer_name"]}',
                key="delete_customer_id"
            )

            confirm = st.checkbox("Confirm customer deletion", key="confirm_customer_delete")

            if st.button("Delete Customer", key="delete_customer_button"):
                if confirm:
                    execute(
                        "DELETE FROM ledger WHERE customer_id=?",
                        (delete_customer_id,)
                    )
                    st.success("Customer deleted.")
                    st.rerun()
                else:
                    st.warning("Confirm before deleting.")


# ============================================================
# TAB 5: BATCH EXPIRY MANAGEMENT
# ============================================================

with tabs[4]:
    st.header("Batch Expiry Management")

    with st.expander("Add New Batch"):
        with st.form("add_batch_form"):
            batch_id = st.text_input("Batch ID")
            product_name = st.text_input("Product Name")
            quantity = st.number_input("Batch Quantity", min_value=0, step=1)
            expiry_date = st.date_input(
                "Expiry Date",
                value=date.today() + timedelta(days=30)
            )

            if st.form_submit_button("Add Batch"):
                if not batch_id.strip() or not product_name.strip():
                    st.error("Batch ID and product name are required.")
                else:
                    try:
                        execute(
                            "INSERT INTO batches VALUES (?, ?, ?, ?)",
                            (
                                batch_id.strip(),
                                product_name.strip(),
                                int(quantity),
                                expiry_date.isoformat()
                            )
                        )
                        st.success("Batch added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Batch ID already exists. Use Search and Edit Batch.")

    st.subheader("Search and Edit Batch")

    batch_records = rows("SELECT * FROM batches ORDER BY product_name")
    batch_search = st.text_input("Search by Batch ID or Product Name", key="batch_search")

    matching_batches = [
        b for b in batch_records
        if batch_search.strip().lower() in
        f'{b["batch_id"]} {b["product_name"]}'.lower()
    ]

    if matching_batches:
        selected_batch_id = st.selectbox(
            "Select Batch",
            [b["batch_id"] for b in matching_batches],
            format_func=lambda x: f'{x} - {find_record(matching_batches, "batch_id", x)["product_name"]}',
            key="selected_batch"
        )

        selected_batch = find_record(matching_batches, "batch_id", selected_batch_id)

        with st.form("edit_batch_form"):
            st.text_input("Batch ID (cannot be changed)", value=selected_batch["batch_id"], disabled=True)
            new_product_name = st.text_input("Product Name", value=selected_batch["product_name"])
            new_quantity = st.number_input(
                "Batch Quantity",
                min_value=0,
                value=int(selected_batch["quantity"]),
                step=1
            )
            new_expiry = st.date_input(
                "Expiry Date",
                value=date.fromisoformat(selected_batch["expiry_date"])
            )

            if st.form_submit_button("Save Batch Changes"):
                if not new_product_name.strip():
                    st.error("Product name cannot be empty.")
                else:
                    execute(
                        """
                        UPDATE batches
                        SET product_name=?, quantity=?, expiry_date=?
                        WHERE batch_id=?
                        """,
                        (
                            new_product_name.strip(),
                            int(new_quantity),
                            new_expiry.isoformat(),
                            selected_batch_id
                        )
                    )
                    st.success("Batch updated.")
                    st.rerun()

    elif batch_search.strip():
        st.warning("No matching batch found.")

    st.subheader("All Batches and Expiry Status")

    sorted_batches = bubble_sort_batches(rows("SELECT * FROM batches"))

    batch_df = pd.DataFrame([
        {
            "Batch ID": b["batch_id"],
            "Product Name": b["product_name"],
            "Quantity": b["quantity"],
            "Expiry Date": b["expiry_date"],
            "Status": get_expiry_status(b["expiry_date"])
        }
        for b in sorted_batches
    ])

    st.dataframe(batch_df, use_container_width=True, hide_index=True)

    if not batch_df.empty:
        expired_count = (batch_df["Status"] == "Expired").sum()
        critical_count = (batch_df["Status"] == "Critical - Review").sum()
        soon_count = (batch_df["Status"] == "Expiring Soon").sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Expired", int(expired_count))
        c2.metric("Critical", int(critical_count))
        c3.metric("Expiring Soon", int(soon_count))

        st.download_button(
            "Download Batch Expiry CSV",
            batch_df.to_csv(index=False).encode("utf-8"),
            "batch_expiry_report.csv",
            "text/csv",
            key="batch_csv"
        )

    with st.expander("Delete Batch"):
        if batch_records:
            delete_batch_id = st.selectbox(
                "Select Batch",
                [b["batch_id"] for b in batch_records],
                format_func=lambda x: f'{x} - {find_record(batch_records, "batch_id", x)["product_name"]}',
                key="delete_batch_id"
            )

            confirm = st.checkbox("Confirm batch deletion", key="confirm_batch_delete")

            if st.button("Delete Batch", key="delete_batch_button"):
                if confirm:
                    execute("DELETE FROM batches WHERE batch_id=?", (delete_batch_id,))
                    st.success("Batch deleted.")
                    st.rerun()
                else:
                    st.warning("Confirm before deleting.")


# ============================================================
# TAB 6: EXPORT DATA
# ============================================================

with tabs[5]:
    st.header("Export Management Data")

    st.write(
        "Download CSV reports for inventory, routes, customer accounts, "
        "and batch expiry records."
    )

    inventory_records = rows("SELECT * FROM inventory ORDER BY product_id")
    route_records = rows("SELECT * FROM routes ORDER BY route_id")
    ledger_records = rows("SELECT * FROM ledger ORDER BY customer_id")
    batch_records = rows("SELECT * FROM batches ORDER BY batch_id")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Inventory")
        st.metric("Products", len(inventory_records))
        download_csv(inventory_records, "inventory_export.csv", "export_inventory")

        st.subheader("Delivery Routes")
        st.metric("Routes", len(route_records))
        download_csv(route_records, "routes_export.csv", "export_routes")

    with c2:
        st.subheader("Customer Ledger")
        st.metric("Customers", len(ledger_records))
        download_csv(ledger_records, "customer_ledger_export.csv", "export_ledger")

        st.subheader("Batch Expiry")
        st.metric("Batches", len(batch_records))
        download_csv(batch_records, "batch_export.csv", "export_batches")

    st.warning(
        "Protect exported customer financial information. "
        "Do not publish real customer records to a public repository."
    )