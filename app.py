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

    st.markdown("#### Find and edit an existing product")
    inv_search = st.text_input("Search by Product ID or product name", key="inv_edit_search",
                               placeholder="e.g. P101 or Cola")
    inv_all_for_edit = rows("SELECT * FROM inventory ORDER BY product_name")
    inv_matches = [x for x in inv_all_for_edit
                   if inv_search.strip().lower() in
                   (x["product_id"] + " " + x["product_name"]).lower()] if inv_search.strip() else inv_all_for_edit
    if inv_matches:
        inv_choice = st.selectbox(
            "Select product to edit",
            options=[x["product_id"] for x in inv_matches],
            format_func=lambda value: next(
                f'{x["product_id"]} — {x["product_name"]}' for x in inv_matches
                if x["product_id"] == value),
            key="inv_edit_choice")
        inv_selected = next(x for x in inv_matches if x["product_id"] == inv_choice)
        with st.form(f"edit_inventory_{inv_choice}"):
            ec1, ec2, ec3, ec4 = st.columns(4)
            edit_pname = ec1.text_input("Product name", value=inv_selected["product_name"], key=f"inv_name_{inv_choice}")
            edit_crates = ec2.number_input("Current crates", min_value=0, step=1, value=int(inv_selected["crates"]), key=f"inv_crates_{inv_choice}")
            edit_threshold = ec3.number_input("Minimum threshold", min_value=0, step=1, value=int(inv_selected["threshold"]), key=f"inv_threshold_{inv_choice}")
            ec4.text_input("Product ID (fixed)", value=inv_choice, disabled=True, key=f"inv_id_display_{inv_choice}")
            save_inv = st.form_submit_button("Save product changes")
            if save_inv:
                if not edit_pname.strip():
                    st.error("Product name is required.")
                else:
                    execute("UPDATE inventory SET product_name=?, crates=?, threshold=? WHERE product_id=?",
                            (edit_pname.strip(), int(edit_crates), int(edit_threshold), inv_choice))
                    st.success("Product updated.")
                    st.rerun()
    elif inv_search.strip():
        st.warning("No products match that search.")
    else:
        st.caption("Add a product first to use the editor.")


    st.markdown("### Search and Edit Existing Product")
    search_product = st.text_input("Search by Product ID or Name", key="search_product")
    products = rows("SELECT * FROM inventory ORDER BY product_name")
    filtered_products = [
        p for p in products
        if search_product.strip().lower() in
        (p["product_id"] + " " + p["product_name"]).lower()
    ] if search_product.strip() else products

    if filtered_products:
        selected_id = st.selectbox(
            "Select Product",
            options=[p["product_id"] for p in filtered_products],
            format_func=lambda pid: next(
                f'{p["product_id"]} - {p["product_name"]}'
                for p in filtered_products if p["product_id"] == pid
            ),
            key="selected_product"
        )
        selected_product = next(p for p in filtered_products if p["product_id"] == selected_id)

        with st.form("edit_product_form"):
            st.text_input("Product ID", value=selected_product["product_id"], disabled=True)
            updated_name = st.text_input("Product Name", value=selected_product["product_name"])
            updated_crates = st.number_input("Current Crates", min_value=0, step=1, value=int(selected_product["crates"]))
            updated_threshold = st.number_input("Minimum Threshold", min_value=0, step=1, value=int(selected_product["threshold"]))
            save_product = st.form_submit_button("Save Product Changes")

            if save_product:
                if not updated_name.strip():
                    st.error("Product name cannot be empty.")
                else:
                    execute(
                        "UPDATE inventory SET product_name=?, crates=?, threshold=? WHERE product_id=?",
                        (updated_name.strip(), int(updated_crates), int(updated_threshold), selected_id)
                    )
                    st.success("Product updated successfully!")
                    st.rerun()
    elif search_product.strip():
        st.warning("No matching product found.")

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

    st.markdown("#### Find and edit an existing route")
    route_search = st.text_input("Search by Route ID or destination", key="route_edit_search",
                                placeholder="e.g. R01 or North Market")
    route_all_for_edit = rows("SELECT * FROM routes ORDER BY route_id")
    route_matches = [x for x in route_all_for_edit
                     if route_search.strip().lower() in
                     (x["route_id"] + " " + x["destination"]).lower()] if route_search.strip() else route_all_for_edit
    if route_matches:
        route_choice = st.selectbox(
            "Select route to edit",
            options=[x["route_id"] for x in route_matches],
            format_func=lambda value: next(
                f'{x["route_id"]} — {x["destination"]}' for x in route_matches
                if x["route_id"] == value),
            key="route_edit_choice")
        route_selected = next(x for x in route_matches if x["route_id"] == route_choice)
        with st.form(f"edit_route_{route_choice}"):
            er1, er2, er3 = st.columns(3)
            edit_destination = er1.text_input("Destination", value=route_selected["destination"], key=f"route_dest_{route_choice}")
            edit_route_crates = er2.number_input("Crates required", min_value=0, step=1, value=int(route_selected["crates"]), key=f"route_crates_{route_choice}")
            er3.text_input("Route ID (fixed)", value=route_choice, disabled=True, key=f"route_id_display_{route_choice}")
            save_route = st.form_submit_button("Save route changes")
            if save_route:
                if not edit_destination.strip():
                    st.error("Destination is required.")
                else:
                    execute("UPDATE routes SET destination=?, crates=? WHERE route_id=?",
                            (edit_destination.strip(), int(edit_route_crates), route_choice))
                    st.success("Route updated.")
                    st.rerun()
    elif route_search.strip():
        st.warning("No routes match that search.")
    else:
        st.caption("Add a route first to use the editor.")


    st.markdown("### Search and Edit Existing Route")
    search_route = st.text_input("Search by Route ID or Destination", key="search_route")
    routes_for_edit = rows("SELECT * FROM routes ORDER BY route_id")
    filtered_routes = [
        r for r in routes_for_edit
        if search_route.strip().lower() in
        (r["route_id"] + " " + r["destination"]).lower()
    ] if search_route.strip() else routes_for_edit

    if filtered_routes:
        selected_route_id = st.selectbox(
            "Select Route",
            options=[r["route_id"] for r in filtered_routes],
            format_func=lambda rid: next(
                f'{r["route_id"]} - {r["destination"]}'
                for r in filtered_routes if r["route_id"] == rid
            ),
            key="selected_route"
        )
        selected_route = next(r for r in filtered_routes if r["route_id"] == selected_route_id)

        with st.form("edit_route_form"):
            st.text_input("Route ID", value=selected_route["route_id"], disabled=True)
            updated_destination = st.text_input("Destination", value=selected_route["destination"])
            updated_route_crates = st.number_input("Crates Required", min_value=0, step=1, value=int(selected_route["crates"]))
            save_route = st.form_submit_button("Save Route Changes")

            if save_route:
                if not updated_destination.strip():
                    st.error("Destination cannot be empty.")
                else:
                    execute(
                        "UPDATE routes SET destination=?, crates=? WHERE route_id=?",
                        (updated_destination.strip(), int(updated_route_crates), selected_route_id)
                    )
                    st.success("Route updated successfully!")
                    st.rerun()
    elif search_route.strip():
        st.warning("No matching route found.")

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

    st.markdown("#### Find and edit an existing customer account")
    customer_search = st.text_input("Search by Customer ID or customer name", key="customer_edit_search",
                                    placeholder="e.g. C101 or Customer A")
    customers_for_edit = rows("SELECT * FROM ledger ORDER BY customer_name")
    customer_matches = [x for x in customers_for_edit
                        if customer_search.strip().lower() in
                        (x["customer_id"] + " " + x["customer_name"]).lower()] if customer_search.strip() else customers_for_edit
    if customer_matches:
        customer_choice = st.selectbox(
            "Select customer account",
            options=[x["customer_id"] for x in customer_matches],
            format_func=lambda value: next(
                f'{x["customer_id"]} — {x["customer_name"]}' for x in customer_matches
                if x["customer_id"] == value),
            key="customer_edit_choice")
        customer_selected = next(x for x in customer_matches if x["customer_id"] == customer_choice)
        with st.form(f"edit_customer_{customer_choice}"):
            cc1, cc2 = st.columns(2)
            edit_customer_name = cc1.text_input("Customer name", value=customer_selected["customer_name"], key=f"customer_name_{customer_choice}")
            edit_amount = cc2.number_input("Outstanding amount (₹)", min_value=0.0, step=100.0, value=float(customer_selected["amount_due"]), key=f"customer_amount_{customer_choice}")
            edit_due = st.date_input("Payment due date", value=date.fromisoformat(customer_selected["due_date"]), key=f"customer_due_{customer_choice}")
            st.text_input("Customer ID (fixed)", value=customer_choice, disabled=True, key=f"customer_id_display_{customer_choice}")
            save_customer = st.form_submit_button("Save customer changes")
            if save_customer:
                if not edit_customer_name.strip():
                    st.error("Customer name is required.")
                else:
                    execute("UPDATE ledger SET customer_name=?, amount_due=?, due_date=? WHERE customer_id=?",
                            (edit_customer_name.strip(), float(edit_amount), edit_due.isoformat(), customer_choice))
                    st.success("Customer account updated.")
                    st.rerun()
    elif customer_search.strip():
        st.warning("No customer accounts match that search.")
    else:
        st.caption("Add a customer account first to use the editor.")


    st.markdown("### Search and Edit Existing Customer")
    search_customer = st.text_input("Search by Customer ID or Name", key="search_customer")
    customers_for_edit = rows("SELECT * FROM ledger ORDER BY customer_name")
    filtered_customers = [
        c for c in customers_for_edit
        if search_customer.strip().lower() in
        (c["customer_id"] + " " + c["customer_name"]).lower()
    ] if search_customer.strip() else customers_for_edit

    if filtered_customers:
        selected_customer_id = st.selectbox(
            "Select Customer",
            options=[c["customer_id"] for c in filtered_customers],
            format_func=lambda cid: next(
                f'{c["customer_id"]} - {c["customer_name"]}'
                for c in filtered_customers if c["customer_id"] == cid
            ),
            key="selected_customer"
        )
        selected_customer = next(c for c in filtered_customers if c["customer_id"] == selected_customer_id)

        with st.form("edit_customer_form"):
            st.text_input("Customer ID", value=selected_customer["customer_id"], disabled=True)
            updated_customer_name = st.text_input("Customer Name", value=selected_customer["customer_name"])
            updated_amount = st.number_input("Outstanding Amount (₹)", min_value=0.0, step=100.0, value=float(selected_customer["amount_due"]))
            updated_due_date = st.date_input("Payment Due Date", value=date.fromisoformat(selected_customer["due_date"]))
            save_customer = st.form_submit_button("Save Customer Changes")

            if save_customer:
                if not updated_customer_name.strip():
                    st.error("Customer name cannot be empty.")
                else:
                    execute(
                        "UPDATE ledger SET customer_name=?, amount_due=?, due_date=? WHERE customer_id=?",
                        (updated_customer_name.strip(), float(updated_amount), updated_due_date.isoformat(), selected_customer_id)
                    )
                    st.success("Customer account updated successfully!")
                    st.rerun()
    elif search_customer.strip():
        st.warning("No matching customer found.")

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

    st.markdown("#### Find and edit an existing batch")
    batch_search = st.text_input("Search by Batch ID or product name", key="batch_edit_search",
                                 placeholder="e.g. B101 or Cola")
    batches_for_edit = rows("SELECT * FROM batches ORDER BY product_name")
    batch_matches = [x for x in batches_for_edit
                     if batch_search.strip().lower() in
                     (x["batch_id"] + " " + x["product_name"]).lower()] if batch_search.strip() else batches_for_edit
    if batch_matches:
        batch_choice = st.selectbox(
            "Select batch to edit",
            options=[x["batch_id"] for x in batch_matches],
            format_func=lambda value: next(
                f'{x["batch_id"]} — {x["product_name"]}' for x in batch_matches
                if x["batch_id"] == value),
            key="batch_edit_choice")
        batch_selected = next(x for x in batch_matches if x["batch_id"] == batch_choice)
        with st.form(f"edit_batch_{batch_choice}"):
            bc1, bc2 = st.columns(2)
            edit_batch_product = bc1.text_input("Product name", value=batch_selected["product_name"], key=f"batch_product_{batch_choice}")
            edit_batch_qty = bc2.number_input("Quantity (crates)", min_value=0, step=1, value=int(batch_selected["quantity"]), key=f"batch_qty_{batch_choice}")
            edit_expiry = st.date_input("Expiry date", value=date.fromisoformat(batch_selected["expiry_date"]), key=f"batch_expiry_{batch_choice}")
            st.text_input("Batch ID (fixed)", value=batch_choice, disabled=True, key=f"batch_id_display_{batch_choice}")
            save_batch = st.form_submit_button("Save batch changes")
            if save_batch:
                if not edit_batch_product.strip():
                    st.error("Product name is required.")
                else:
                    execute("UPDATE batches SET product_name=?, quantity=?, expiry_date=? WHERE batch_id=?",
                            (edit_batch_product.strip(), int(edit_batch_qty), edit_expiry.isoformat(), batch_choice))
                    st.success("Batch updated.")
                    st.rerun()
    elif batch_search.strip():
        st.warning("No batches match that search.")
    else:
        st.caption("Add a batch first to use the editor.")


    st.markdown("### Search and Edit Existing Batch")
    search_batch = st.text_input("Search by Batch ID or Product Name", key="search_batch")
    batches_for_edit = rows("SELECT * FROM batches ORDER BY product_name")
    filtered_batches = [
        b for b in batches_for_edit
        if search_batch.strip().lower() in
        (b["batch_id"] + " " + b["product_name"]).lower()
    ] if search_batch.strip() else batches_for_edit

    if filtered_batches:
        selected_batch_id = st.selectbox(
            "Select Batch",
            options=[b["batch_id"] for b in filtered_batches],
            format_func=lambda bid: next(
                f'{b["batch_id"]} - {b["product_name"]}'
                for b in filtered_batches if b["batch_id"] == bid
            ),
            key="selected_batch"
        )
        selected_batch = next(b for b in filtered_batches if b["batch_id"] == selected_batch_id)

        with st.form("edit_batch_form"):
            st.text_input("Batch ID", value=selected_batch["batch_id"], disabled=True)
            updated_batch_product = st.text_input("Product Name", value=selected_batch["product_name"])
            updated_quantity = st.number_input("Quantity (Crates)", min_value=0, step=1, value=int(selected_batch["quantity"]))
            updated_expiry_date = st.date_input("Expiry Date", value=date.fromisoformat(selected_batch["expiry_date"]))
            save_batch = st.form_submit_button("Save Batch Changes")

            if save_batch:
                if not updated_batch_product.strip():
                    st.error("Product name cannot be empty.")
                else:
                    execute(
                        "UPDATE batches SET product_name=?, quantity=?, expiry_date=? WHERE batch_id=?",
                        (updated_batch_product.strip(), int(updated_quantity), updated_expiry_date.isoformat(), selected_batch_id)
                    )
                    st.success("Batch updated successfully!")
                    st.rerun()
    elif search_batch.strip():
        st.warning("No matching batch found.")

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
