import sqlite3
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "data" / "beverage_management.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Beverage Distribution Manager", page_icon="📦", layout="wide")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS inventory (
            product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL,
            crates INTEGER NOT NULL DEFAULT 0, threshold INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY, crates INTEGER NOT NULL DEFAULT 0,
            destination TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ledger (
            customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL,
            amount_due REAL NOT NULL DEFAULT 0, due_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY, product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0, expiry_date TEXT NOT NULL
        );
        """)

def rows(query, params=()):
    with connect() as con:
        return [dict(r) for r in con.execute(query, params).fetchall()]

def execute(query, params=()):
    with connect() as con:
        con.execute(query, params)
        con.commit()

def bubble_sort_low_stock(items):
    """Assigned algorithm: bubble sort, prioritizing products at/below threshold."""
    a = list(items)
    for i in range(len(a)):
        for j in range(0, len(a) - i - 1):
            left = (a[j]["crates"] > a[j]["threshold"], a[j]["crates"] - a[j]["threshold"])
            right = (a[j+1]["crates"] > a[j+1]["threshold"], a[j+1]["crates"] - a[j+1]["threshold"])
            if left > right:
                a[j], a[j+1] = a[j+1], a[j]
    return a

def selection_sort_routes(items):
    """Assigned algorithm: selection sort by descending crate demand."""
    a = list(items)
    for i in range(len(a)):
        max_idx = i
        for j in range(i + 1, len(a)):
            if a[j]["crates"] > a[max_idx]["crates"]:
                max_idx = j
        a[i], a[max_idx] = a[max_idx], a[i]
    return a

def linear_search_customer(items, customer_id):
    """Assigned algorithm: linear search by customer ID."""
    for item in items:
        if item["customer_id"].lower() == customer_id.strip().lower():
            return item
    return None

def bubble_sort_batches(items):
    """Assigned algorithm: bubble sort by days remaining until expiry."""
    a = list(items)
    for i in range(len(a)):
        for j in range(0, len(a) - i - 1):
            d1 = (date.fromisoformat(a[j]["expiry_date"]) - date.today()).days
            d2 = (date.fromisoformat(a[j+1]["expiry_date"]) - date.today()).days
            if d1 > d2:
                a[j], a[j+1] = a[j+1], a[j]
    return a

init_db()

st.title("📦 Wholesale Beverage Distribution Management System")
st.caption("Four practical modules: stock alerts, delivery prioritization, customer credit follow-up, and batch expiry monitoring.")
st.info("This is a local prototype using SQLite. Start with sample data or enter your own records. Use fictional/sample customer information until the business approves handling real data.")

with st.sidebar:
    st.header("Quick actions")
    if st.button("Load / reset demo data", use_container_width=True):
        with connect() as con:
            con.execute("DELETE FROM inventory")
            con.execute("DELETE FROM routes")
            con.execute("DELETE FROM ledger")
            con.execute("DELETE FROM batches")
            con.executemany("INSERT INTO inventory VALUES (?,?,?,?)", [
                ("P101","Cola 750 ml",8,20), ("P102","Orange Drink",35,15),
                ("P103","Soda Water",5,10), ("P104","Lemon Soda",18,18)])
            con.executemany("INSERT INTO routes VALUES (?,?,?)", [
                ("R01",20,"North Market"), ("R02",75,"Central Market"),
                ("R03",45,"East Market"), ("R04",58,"South Market")])
            con.executemany("INSERT INTO ledger VALUES (?,?,?,?)", [
                ("C101","Customer A",5000,(date.today().replace(day=max(1,date.today().day-10))).isoformat()),
                ("C102","Customer B",8000,(date.today().replace(day=max(1,date.today().day-18))).isoformat()),
                ("C103","Customer C",12000,(date.today().replace(day=max(1,date.today().day-27))).isoformat()),
                ("C104","Customer D",15000,(date.today().replace(day=max(1,date.today().day-35))).isoformat())])
            con.executemany("INSERT INTO batches VALUES (?,?,?,?)", [
                ("B101","Expired sample product",10,(date.today().replace(day=max(1,date.today().day-2))).isoformat()),
                ("B102","Near-expiry sample product",15,(date.today().replace(day=min(28,date.today().day+4))).isoformat()),
                ("B103","Regular sample product",25,(date.today().replace(day=min(28,date.today().day+20))).isoformat())])
            con.commit()
        st.success("Demo data loaded. Refreshing views…")
        st.rerun()
    st.caption(f"Database: {DB_PATH.relative_to(APP_DIR)}")

tabs = st.tabs(["Overview", "1 · Inventory", "2 · Delivery Routes", "3 · Customer Ledger", "4 · Batch Expiry", "Export Data"])

with tabs[0]:
    inv = rows("SELECT * FROM inventory")
    routes = rows("SELECT * FROM routes")
    led = rows("SELECT * FROM ledger")
    batches = rows("SELECT * FROM batches")
    low = [x for x in inv if x["crates"] <= x["threshold"]]
    overdue = []
    for x in led:
        days = (date.today() - date.fromisoformat(x["due_date"])).days
        if days > 0:
            overdue.append((x, days))
    expiring = []
    for x in batches:
        days = (date.fromisoformat(x["expiry_date"]) - date.today()).days
        if days < 7:
            expiring.append((x, days))
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Products tracked", len(inv))
    c2.metric("Low-stock products", len(low))
    c3.metric("Overdue accounts", len(overdue))
    c4.metric("Expired / <7-day batches", len(expiring))
    st.subheader("Action queue")
    queue = []
    for x in low:
        queue.append({"Area":"Inventory","Record":f'{x["product_id"]} — {x["product_name"]}',"Action":f'Restock: {x["crates"]} crates (threshold {x["threshold"]})'})
    for x,days in overdue:
        label = "Credit restriction review" if days >= 30 else ("Urgent follow-up" if days >= 25 else ("Follow-up" if days >= 15 else "Payment reminder"))
        queue.append({"Area":"Customer credit","Record":f'{x["customer_id"]} — {x["customer_name"]}',"Action":f'{label}; {days} day(s) overdue; ₹{x["amount_due"]:,.2f}'})
    for x,days in expiring:
        status = "EXPIRED / DISCARD REVIEW" if days <= 0 else "CRITICAL LIQUIDATION REVIEW"
        queue.append({"Area":"Batch expiry","Record":f'{x["batch_id"]} — {x["product_name"]}',"Action":f'{status}; {days} day(s) to expiry'})
    if queue:
        st.dataframe(pd.DataFrame(queue), use_container_width=True, hide_index=True)
    else:
        st.success("No action items currently flagged, or no records have been added.")
    st.caption("Flags are decision-support prompts. Confirm actions against the enterprise's actual procedures and applicable safety rules.")

with tabs[1]:
    st.subheader("Inventory Tracking & Low-Stock Alerts")
    with st.form("add_inventory", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        pid = c1.text_input("Product ID")
        pname = c2.text_input("Product name")
        crates = c3.number_input("Current crates", min_value=0, step=1)
        threshold = c4.number_input("Minimum threshold", min_value=0, step=1)
        submitted = st.form_submit_button("Add / update product")
        if submitted:
            if not pid.strip() or not pname.strip():
                st.error("Product ID and product name are required.")
            else:
                execute("INSERT INTO inventory VALUES (?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET product_name=excluded.product_name, crates=excluded.crates, threshold=excluded.threshold",
                        (pid.strip(), pname.strip(), int(crates), int(threshold)))
                st.success("Inventory record saved.")
                st.rerun()
    inv = bubble_sort_low_stock(rows("SELECT * FROM inventory"))
    if inv:
        df = pd.DataFrame([{"Product ID":x["product_id"],"Product":x["product_name"],"Crates":x["crates"],"Threshold":x["threshold"],"Status":"LOW STOCK" if x["crates"] <= x["threshold"] else "Sufficient"} for x in inv])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download inventory CSV", df.to_csv(index=False).encode("utf-8"), "inventory_report.csv", "text/csv")
    else:
        st.write("No inventory records yet.")
    with st.expander("Delete a product"):
        del_id = st.text_input("Product ID to delete", key="del_inv")
        if st.button("Delete inventory record"):
            execute("DELETE FROM inventory WHERE product_id=?", (del_id.strip(),))
            st.success("If the ID existed, it was deleted.")
            st.rerun()

with tabs[2]:
    st.subheader("Fleet Logistics & Route Prioritizer")
    with st.form("add_route", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        rid = c1.text_input("Route ID")
        destination = c2.text_input("Destination")
        route_crates = c3.number_input("Crates required", min_value=0, step=1)
        submitted = st.form_submit_button("Add / update route")
        if submitted:
            if not rid.strip() or not destination.strip():
                st.error("Route ID and destination are required.")
            else:
                execute("INSERT INTO routes VALUES (?,?,?) ON CONFLICT(route_id) DO UPDATE SET crates=excluded.crates,destination=excluded.destination",
                        (rid.strip(), int(route_crates), destination.strip()))
                st.success("Route saved.")
                st.rerun()
    route_data = selection_sort_routes(rows("SELECT * FROM routes"))
    if route_data:
        df = pd.DataFrame([{"Route ID":x["route_id"],"Destination":x["destination"],"Crates":x["crates"],"Priority":"HIGH DEMAND" if i < max(1, len(route_data)//3) else "Standard","Load flag":"HEAVY ROUTE (>50)" if x["crates"] > 50 else "Within 50 crates"} for i,x in enumerate(route_data)])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total crates across listed routes", sum(x["crates"] for x in route_data))
        st.download_button("Download route dispatch CSV", df.to_csv(index=False).encode("utf-8"), "route_dispatch.csv", "text/csv")
    else:
        st.write("No routes yet.")
    with st.expander("Delete a route"):
        del_id = st.text_input("Route ID to delete", key="del_route")
        if st.button("Delete route"):
            execute("DELETE FROM routes WHERE route_id=?", (del_id.strip(),))
            st.rerun()

with tabs[3]:
    st.subheader("Customer Credit & Outstanding Payment Ledger")
    with st.form("add_customer", clear_on_submit=True):
        c1,c2 = st.columns(2)
        cid = c1.text_input("Customer ID")
        cname = c2.text_input("Customer name")
        c3,c4 = st.columns(2)
        amount = c3.number_input("Outstanding amount (₹)", min_value=0.0, step=100.0)
        due = c4.date_input("Payment due date", value=date.today())
        submitted = st.form_submit_button("Add / update customer account")
        if submitted:
            if not cid.strip() or not cname.strip():
                st.error("Customer ID and name are required.")
            else:
                execute("INSERT INTO ledger VALUES (?,?,?,?) ON CONFLICT(customer_id) DO UPDATE SET customer_name=excluded.customer_name,amount_due=excluded.amount_due,due_date=excluded.due_date",
                        (cid.strip(), cname.strip(), float(amount), due.isoformat()))
                st.success("Customer account saved.")
                st.rerun()
    ledger = rows("SELECT * FROM ledger")
    search_id = st.text_input("Search customer by ID (linear search)")
    if search_id:
        found = linear_search_customer(ledger, search_id)
        if found:
            st.success(f'Found {found["customer_name"]} — ₹{found["amount_due"]:,.2f} due, due date {found["due_date"]}.')
        else:
            st.warning("Customer ID not found.")
    out = []
    for x in ledger:
        days = (date.today() - date.fromisoformat(x["due_date"])).days
        if days <= 0:
            status = "Not overdue"
            overdue_days = 0
        elif days >= 30:
            status, overdue_days = "CREDIT RESTRICTION REVIEW", days
        elif days >= 25:
            status, overdue_days = "Urgent follow-up", days
        elif days >= 15:
            status, overdue_days = "Follow-up", days
        else:
            status, overdue_days = "Payment reminder", days
        out.append({"Customer ID":x["customer_id"],"Customer":x["customer_name"],"Amount Due (₹)":x["amount_due"],"Due Date":x["due_date"],"Days Overdue":overdue_days,"Status":status})
    if out:
        df = pd.DataFrame(out).sort_values(["Days Overdue","Amount Due (₹)"], ascending=[False,False])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total outstanding amount", f'₹{sum(x["amount_due"] for x in ledger):,.2f}')
        st.download_button("Download customer ledger CSV", df.to_csv(index=False).encode("utf-8"), "customer_ledger.csv", "text/csv")
    else:
        st.write("No customer accounts yet.")
    with st.expander("Record a payment / update balance"):
        pay_id = st.text_input("Customer ID", key="pay_id")
        new_amount = st.number_input("New outstanding balance (₹)", min_value=0.0, step=100.0, key="new_balance")
        if st.button("Update outstanding balance"):
            execute("UPDATE ledger SET amount_due=? WHERE customer_id=?", (float(new_amount), pay_id.strip()))
            st.success("Balance updated if the customer ID existed.")
            st.rerun()

with tabs[4]:
    st.subheader("Product Shelf-Life & Batch Expiry Monitor")
    with st.form("add_batch", clear_on_submit=True):
        c1,c2 = st.columns(2)
        bid = c1.text_input("Batch ID")
        product = c2.text_input("Product name")
        c3,c4 = st.columns(2)
        qty = c3.number_input("Quantity (crates)", min_value=0, step=1)
        expiry = c4.date_input("Expiry date", value=date.today())
        submitted = st.form_submit_button("Add / update batch")
        if submitted:
            if not bid.strip() or not product.strip():
                st.error("Batch ID and product name are required.")
            else:
                execute("INSERT INTO batches VALUES (?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET product_name=excluded.product_name,quantity=excluded.quantity,expiry_date=excluded.expiry_date",
                        (bid.strip(), product.strip(), int(qty), expiry.isoformat()))
                st.success("Batch saved.")
                st.rerun()
    batch_data = bubble_sort_batches(rows("SELECT * FROM batches"))
    out = []
    for x in batch_data:
        days = (date.fromisoformat(x["expiry_date"]) - date.today()).days
        if days <= 0:
            status = "EXPIRED / DISCARD REVIEW"
        elif days < 7:
            status = "CRITICAL LIQUIDATION REVIEW"
        else:
            status = "Normal monitoring"
        out.append({"Batch ID":x["batch_id"],"Product":x["product_name"],"Quantity (crates)":x["quantity"],"Expiry Date":x["expiry_date"],"Days Remaining":days,"Status":status})
    if out:
        df = pd.DataFrame(out)
        st.dataframe(df, use_container_width=True, hide_index=True)
        flagged_qty = sum(x["quantity"] for x in batch_data if (date.fromisoformat(x["expiry_date"]) - date.today()).days < 7)
        st.metric("Crates in expired / under-7-day batches", flagged_qty)
        st.download_button("Download batch expiry CSV", df.to_csv(index=False).encode("utf-8"), "batch_expiry_report.csv", "text/csv")
    else:
        st.write("No batches yet.")
    st.caption("The application flags batches for review. Follow business and food/beverage safety procedures before disposal, sale, or other action.")
    with st.expander("Delete a batch"):
        del_id = st.text_input("Batch ID to delete", key="del_batch")
        if st.button("Delete batch"):
            execute("DELETE FROM batches WHERE batch_id=?", (del_id.strip(),))
            st.rerun()

with tabs[5]:
    st.subheader("Export and backup")
    export_tables = {
        "Inventory": ("SELECT * FROM inventory", "inventory.csv"),
        "Routes": ("SELECT * FROM routes", "routes.csv"),
        "Customer ledger": ("SELECT * FROM ledger", "customer_ledger.csv"),
        "Batches": ("SELECT * FROM batches", "batches.csv"),
    }
    for label, (query, filename) in export_tables.items():
        data = rows(query)
        df = pd.DataFrame(data)
        st.write(f"**{label}** — {len(data)} record(s)")
        if not df.empty:
            st.download_button(f"Download {label} CSV", df.to_csv(index=False).encode("utf-8"), filename, "text/csv", key=f"export_{filename}")
        else:
            st.caption("No records to export.")
    st.warning("The SQLite database is stored locally in the project's data folder. Back it up securely and do not commit real customer payment data to a public repository.")
