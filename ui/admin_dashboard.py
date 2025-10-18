import streamlit as st
import pandas as pd
from database_setup import query_db, update_data


def fetch_inventory():
    query = (
        "SELECT i.id AS inventory_id, v.id AS vehicle_id, v.make, v.model, v.trim, v.color, v.rate, "
        "d.dealership_name, d.city, d.zipcode, i.available_status, i.vin "
        "FROM Inventory i JOIN Vehicle v ON i.vehicle_id = v.id "
        "JOIN Dealership d ON i.dealership_id = d.dealership_id "
        "ORDER BY d.dealership_name, v.model, v.trim"
    )
    return query_db(query)


def fetch_test_drives():
    query = (
        "SELECT td.id, td.date, td.time, td.status, td.special_request, td.created_at, "
        "c.customer_name, c.email, c.phone, c.zipcode, "
        "v.make, v.model, v.trim, v.color, v.rate, "
        "d.dealership_name, d.city AS dealer_city, "
        "COALESCE(s.salesperson_name, ''), COALESCE(s.email, '') "
        "FROM TestDrive td JOIN Customer c ON td.customer_id = c.customer_id "
        "JOIN Vehicle v ON td.vehicle_id = v.id "
        "JOIN Dealership d ON td.dealership_id = d.dealership_id "
        "LEFT JOIN Salesperson s ON td.salesperson_id = s.salesperson_id "
        "ORDER BY td.date DESC, td.time DESC"
    )
    return query_db(query)


def update_inventory_status(inventory_id: int, new_status: str) -> bool:
    return update_data("UPDATE Inventory SET available_status = ? WHERE id = ?", (new_status, inventory_id)) > 0


def update_test_drive_status(td_id: int, new_status: str) -> bool:
    return update_data("UPDATE TestDrive SET status = ? WHERE id = ?", (new_status, td_id)) > 0


def release_inventory_for_test_drive(td_id: int) -> tuple[bool, int | None]:
    """Release a reserved inventory item associated with a test drive.
    Since TestDrive doesn't store inventory_id, we infer by (vehicle_id, dealership_id)
    and release one reserved item if present.

    Returns (released: bool, inventory_id or None)
    """
    # Find the test drive's vehicle and dealer
    td = query_db(
        "SELECT vehicle_id, dealership_id FROM TestDrive WHERE id = ? LIMIT 1",
        (td_id,),
    )
    if not td:
        return (False, None)
    vehicle_id, dealer_id = td[0]
    # Find a reserved inventory row matching
    inv = query_db(
        "SELECT id FROM Inventory WHERE vehicle_id = ? AND dealership_id = ? AND available_status = 'reserved' ORDER BY id LIMIT 1",
        (vehicle_id, dealer_id),
    )
    if not inv:
        return (False, None)
    inv_id = inv[0][0]
    # Release it
    updated = update_data(
        "UPDATE Inventory SET available_status = 'available' WHERE id = ?",
        (inv_id,),
    )
    return (updated > 0, inv_id)


def render_inventory_tab():
    st.subheader("🚗 Manage Inventory")
    data = fetch_inventory()
    if not data:
        st.info("No inventory data found.")
        return

    rows = []
    for (inv_id, veh_id, make, model, trim, color, rate, dealer, city, zipc, status, vin) in data:
        rows.append({
            "Inventory ID": inv_id,
            "Vehicle ID": veh_id,
            "Make": make,
            "Model": model,
            "Trim": trim,
            "Color": color,
            "Price": f"${rate:,.2f}",
            "Dealership": dealer,
            "City": city,
            "ZIP": zipc,
            "Status": status,
            "VIN": vin,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch')

    st.divider()
    st.subheader("✏️ Update Inventory Status")
    c1, c2, c3 = st.columns(3)
    with c1:
        inv_id = st.number_input("Inventory ID", min_value=1, step=1)
    with c2:
        new_status = st.selectbox("New Status", ["available", "unavailable", "sold", "reserved", "maintenance"])
    with c3:
        if st.button("Update Inventory"):
            if update_inventory_status(inv_id, new_status):
                st.success(f"Inventory {inv_id} set to '{new_status}'")
                st.rerun()
            else:
                st.error("Failed to update inventory status")


def render_test_drives_tab():
    st.subheader("📅 Manage Test Drives")
    data = fetch_test_drives()
    if not data:
        st.info("No test drives found.")
        return

    rows = []
    for (td_id, dt, tm, status, special, created, cust_name, email, phone, zipcode, make, model, trim, color, rate, dealer, dealer_city, sp_name, sp_email) in data:
        rows.append({
            "ID": td_id,
            "Date": dt,
            "Time": tm,
            "Status": status,
            "Customer": cust_name,
            "Email": email,
            "Phone": phone,
            "ZIP": zipcode,
            "Vehicle": f"{make} {model} {trim}",
            "Color": color,
            "Price": f"${rate:,.2f}",
            "Dealership": dealer,
            "Salesperson": sp_name or "Not assigned",
            "Special Request": special or "",
            "Created": created,
        })
    df = pd.DataFrame(rows)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_filter = st.selectbox("Filter Status", ["All"] + sorted(df["Status"].unique().tolist()))
    with c2:
        dealer_filter = st.selectbox("Filter Dealer", ["All"] + sorted(df["Dealership"].unique().tolist()))
    with c3:
        date_filter = st.text_input("Filter Date (YYYY-MM-DD)")
    with c4:
        limit = st.number_input("Show rows", min_value=10, max_value=200, value=50, step=10)

    filtered = df.copy()
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]
    if dealer_filter != "All":
        filtered = filtered[filtered["Dealership"] == dealer_filter]
    if date_filter:
        filtered = filtered[filtered["Date"] == date_filter]

    st.dataframe(filtered.head(limit), width='stretch')

    st.divider()
    st.subheader("🔄 Update Test Drive Status")
    c1, c2, c3 = st.columns(3)
    with c1:
        td_id = st.number_input("Test Drive ID", min_value=1, step=1)
    with c2:
        new_status = st.selectbox("New Status", ["scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled"])
    with c3:
        if st.button("Update Status"):
            if update_test_drive_status(td_id, new_status):
                st.success(f"Test Drive {td_id} set to '{new_status}'")
                # Auto-release reservation when cancelled or no-show
                if new_status in ("cancelled", "no_show"):
                    released, inv_id = release_inventory_for_test_drive(td_id)
                    if released:
                        st.info(f"Released reservation for Inventory #{inv_id}.")
                    else:
                        st.warning("No reserved inventory found to release for this booking.")
                st.rerun()
            else:
                st.error("Failed to update test drive status")

        # Manual release action (e.g., after rescheduling or admin intent)
        if st.button("Release Reservation For This Booking"):
            released, inv_id = release_inventory_for_test_drive(td_id)
            if released:
                st.success(f"Reservation released for Inventory #{inv_id}.")
                st.rerun()
            else:
                st.warning("No reserved inventory found for this booking.")


def render_analytics_tab():
    st.subheader("📊 Analytics")
    c1, c2, c3, c4 = st.columns(4)
    total_available = query_db("SELECT COUNT(*) FROM Inventory WHERE available_status = 'available'")[0][0]
    total_td = query_db("SELECT COUNT(*) FROM TestDrive")[0][0]
    pending_td = query_db("SELECT COUNT(*) FROM TestDrive WHERE status = 'scheduled'")[0][0]
    completed_td = query_db("SELECT COUNT(*) FROM TestDrive WHERE status = 'completed'")[0][0]
    with c1:
        st.metric("Available Vehicles", total_available)
    with c2:
        st.metric("Total Test Drives", total_td)
    with c3:
        st.metric("Pending", pending_td)
    with c4:
        st.metric("Completed", completed_td)

    st.divider()
    st.caption("Recent activity")
    recent = query_db(
        "SELECT td.created_at, c.customer_name, v.model, v.trim, td.status, d.dealership_name "
        "FROM TestDrive td JOIN Customer c ON td.customer_id = c.customer_id "
        "JOIN Vehicle v ON td.vehicle_id = v.id "
        "JOIN Dealership d ON td.dealership_id = d.dealership_id "
        "ORDER BY td.created_at DESC LIMIT 10"
    )
    if recent:
        st.dataframe(pd.DataFrame(recent, columns=["Date/Time", "Customer", "Model", "Trim", "Status", "Dealership"]), width='stretch')


def run_admin_dashboard():
    st.title("🧑‍💼 Toyota Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["Inventory", "Test Drives", "Analytics"])
    with tab1:
        render_inventory_tab()
    with tab2:
        render_test_drives_tab()
    with tab3:
        render_analytics_tab()


if __name__ == "__main__":
    run_admin_dashboard()