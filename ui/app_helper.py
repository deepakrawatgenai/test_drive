import streamlit as st
import sqlite3
from datetime import datetime
from utils.emailer import send_email_bg
from tools.inventory import inventory_lookup
import json

# ---------------- Chat Helpers ----------------
def render_chat_message(message: dict):
    if message["role"] == "agent":
        st.markdown(f"**Agent:** {message['text']}")
    else:
        st.markdown(f"**{message['name']} (you):** {message['text']}")

def append_user_message(text: str, name: str = "Customer"):
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "user", "name": name, "text": text})

def append_agent_message(text: str):
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "agent", "text": text})

def display_chat_history():
    if "messages" in st.session_state:
        for m in st.session_state.messages:
            render_chat_message(m)

# ---------------- Inventory Helper ----------------
def inventory_tool(zipcode: str, model: str = None):
    items = inventory_lookup(zipcode, model)
    for r in items:
        if isinstance(r.get('features'), str):
            try:
                r['features'] = json.loads(r['features'])
            except Exception:
                r['features'] = []
    return items

# ---------------- Test Drive Helper ----------------
def schedule_test_drive(customer_name, email, phone, zipcode, inventory_id, dealership_id, salesperson_id, dt: datetime):
    conn = sqlite3.connect('toyota_dealership.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO Customer(customer_name, email, phone, zipcode) VALUES (?,?,?,?)',
                (customer_name, email, phone, zipcode))
    conn.commit()
    cur.execute('''INSERT INTO TestDrive(customer_id, dealership_id, salesperson_id, vehicle_id, date, time, status)
                   VALUES ((SELECT customer_id FROM Customer WHERE email=?), ?, ?, ?, ?, ?, 'scheduled')''',
                (email, dealership_id, salesperson_id, inventory_id, dt.date().isoformat(), dt.time().isoformat()))
    conn.commit()
    cur.execute('SELECT date, time FROM TestDrive WHERE rowid=last_insert_rowid()')
    res = cur.fetchone()
    conn.close()
    return {'date': res[0], 'time': res[1]}

# ---------------- Email Helper ----------------
def generate_and_send_emails_bg(customer_name, customer_email, customer_phone, model, trim, inventory_item, date, time):
    content = f"""Subject: Test Drive Scheduled for {model} {trim}
Hello {customer_name},
Your test drive for {model} {trim} is scheduled on {date} at {time}.
Thank you!"""
    send_email_bg(customer_email, content)

# Note: The above email content is simplified for demonstration.
# In production, use proper email templates and formatting.

# ----------------- Tool Definitions -----------------
inventory_tool = inventory_tool
schedule_test_drive = schedule_test_drive
generate_and_send_emails_bg = generate_and_send_emails_bg

# The above functions can now be imported and used in agents/agent_tools.py

