
import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
from jinja2 import Template

# Optional LangChain (if available)
try:
    from langchain.llms import OpenAI
    from langchain.agents import Tool, initialize_agent
    from langchain.agents.agent_types import AgentType
except Exception:
    OpenAI = None
    Tool = None
    initialize_agent = None
    AgentType = None

DB_PATH = "toyota_sales.db"  # point to your existing DB

# ---------------------- DB HELPERS ----------------------

def get_db_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()

# ---------------------- TOOLS ----------------------

def serper_fetch(model: str) -> Dict[str, Any]:
    """
    Placeholder for Serper (or any web tool) fetching latest model info.
    Replace this with real API calls to Serper or another car-spec service.
    Returns a dict with 'model', 'features'(list), 'summary', 'trims'.
    """
    # Example static response — in production call the external API.
    sample = {
        "model": model,
        "summary": f"{model} is a reliable Toyota model with hybrid options.",
        "features": ["Hybrid", "AWD", "Panoramic Roof", "Heated Seats", "12.3in Infotainment"],
        "trims": ["Base", "XLE", "XSE", "Limited"]
    }
    return sample


def inventory_tool(zipcode: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return list of available inventory items near the zipcode (simple VIN-level search).
    """
    cur = conn.cursor()
    # Find dealerships in zipcode or same city — simple approach
    cur.execute("SELECT dealership_id, dealership_name, city, zipcode, address, email, phone FROM Dealership WHERE zipcode = ? LIMIT 20", (zipcode,))
    dealers = cur.fetchall()
    dealer_ids = [d[0] for d in dealers]
    if not dealer_ids:
        return []

    q = "SELECT Inventory.id as inventory_id, Inventory.vin, Inventory.available_status, Vehicle.id as vehicle_id, Vehicle.make, Vehicle.model, Vehicle.trim, Vehicle.features, Vehicle.rate, Dealership.dealership_name, Dealership.address, Dealership.phone FROM Inventory JOIN Vehicle ON Inventory.vehicle_id = Vehicle.id JOIN Dealership ON Inventory.dealership_id = Dealership.dealership_id WHERE Inventory.dealership_id IN ({seq})"
    seq = ",".join(["?"] * len(dealer_ids))
    if model:
        q += " AND Vehicle.model LIKE ?"
        params = dealer_ids + [f"%{model}%"]
    else:
        params = dealer_ids
    cur.execute(q.format(seq=seq), params)
    rows = cur.fetchall()
    results = []
    for r in rows:
        features = []
        try:
            features = json.loads(r[7]) if r[7] else []
        except Exception:
            try:
                features = json.loads(r[7].replace("'", '"'))
            except Exception:
                features = []
        results.append({
            "inventory_id": r[0],
            "vin": r[1],
            "available_status": r[2],
            "vehicle_id": r[3],
            "make": r[4],
            "model": r[5],
            "trim": r[6],
            "features": features,
            "rate": r[8],
            "dealership_name": r[9],
            "address": r[10],
            "phone": r[11]
        })
    return results


def feature_match_tool(target_features: List[str], candidate_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score candidate models by feature overlap and return sorted list."""
    scored = []
    target_set = set([f.lower() for f in target_features])
    for v in candidate_models:
        candidate_set = set([f.lower() for f in v.get("features", [])])
        overlap = len(target_set.intersection(candidate_set))
        scored.append((overlap, v))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for score, v in scored]

# ---------------------- BUSINESS LOGIC ----------------------

def find_similar_models(model_name: str, zipcode: str) -> List[Dict[str, Any]]:
    """Find similar models available in inventory near zipcode using serper + inventory."""
    serper_info = serper_fetch(model_name)
    target_features = serper_info.get("features", [])
    # Pull inventory broadly and score
    candidates = inventory_tool(zipcode)
    similar = feature_match_tool(target_features, candidates)
    return similar


def create_or_get_customer(name: str, email: str, phone: str, zipcode: str, city: str = "") -> int:
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM Customer WHERE email = ?", (email,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO Customer (customer_name, email, phone, zipcode, city) VALUES (?, ?, ?, ?, ?)", (name, email, phone, zipcode, city))
    conn.commit()
    return cur.lastrowid


def schedule_test_drive(customer_name: str, customer_email: str, customer_phone: str, zipcode: str, inventory_id: int, dealership_id: int, salesperson_id: Optional[int], dt: datetime, special_request: str = "") -> Dict[str, Any]:
    # ensure customer exists
    customer_id = create_or_get_customer(customer_name, customer_email, customer_phone, zipcode)
    cur = conn.cursor()
    date_str = dt.date().isoformat()
    time_str = dt.time().isoformat()
    cur.execute("INSERT INTO TestDrive (customer_id, dealership_id, salesperson_id, vehicle_id, date, time, special_request) VALUES (?, ?, ?, ?, ?, ?, ?)", (customer_id, dealership_id, salesperson_id, inventory_id, date_str, time_str, special_request))
    conn.commit()
    testdrive_id = cur.lastrowid
    return {
        "testdrive_id": testdrive_id,
        "customer_id": customer_id,
        "dealership_id": dealership_id,
        "salesperson_id": salesperson_id,
        "vehicle_inventory_id": inventory_id,
        "date": date_str,
        "time": time_str
    }

# ---------------------- EMAIL & TEMPLATES ----------------------

def render_email_customer(customer_name: str, model: str, trim: str, dealership_name: str, address: str, date: str, time: str, salesperson_name: str = "Sales Team") -> str:
    tpl = Template("""
Subject: Test Drive Confirmation – {{ model }} {{ trim }}

Dear {{ customer_name }},

Your test drive for the {{ model }} {{ trim }} is confirmed for {{ date }} at {{ time }}.

Dealership: {{ dealership_name }}
Address: {{ address }}
Salesperson: {{ salesperson_name }}

Thank you for choosing Toyota.

Warm regards,
Toyota SmartDrive Assistant
""")
    return tpl.render(customer_name=customer_name, model=model, trim=trim, dealership_name=dealership_name, address=address, date=date, time=time, salesperson_name=salesperson_name)


def render_email_dealer(customer_name: str, customer_email: str, customer_phone: str, model: str, trim: str, date: str, time: str) -> str:
    tpl = Template("""
Subject: New Test Drive Scheduled – {{ model }} {{ trim }}

Hello Team,

A test drive has been scheduled.

Customer: {{ customer_name }}
Email: {{ customer_email }}
Phone: {{ customer_phone }}
Model: {{ model }} {{ trim }}
Date: {{ date }}
Time: {{ time }}

Please reach out to prepare the vehicle.

Regards,
Toyota SmartDrive Assistant
""")
    return tpl.render(customer_name=customer_name, customer_email=customer_email, customer_phone=customer_phone, model=model, trim=trim, date=date, time=time)


def send_email_smtp(to_email: str, content: str):
    """Very small SMTP sender, replace or expand in production. Uses env variables."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not (host and user and password):
        print("SMTP not configured. Email content below:\n", content)
        return False
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(content)
    # naive parse first line as subject
    first_line = content.splitlines()[0].replace("Subject:", "").strip()
    msg["Subject"] = first_line
    msg["From"] = user
    msg["To"] = to_email

    s = smtplib.SMTP(host, port)
    s.starttls()
    s.login(user, password)
    s.sendmail(user, [to_email], msg.as_string())
    s.quit()
    return True


def generate_and_send_emails_bg(customer_name: str, customer_email: str, customer_phone: str, model: str, trim: str, dealership: Dict[str, Any], date: str, time: str, salesperson_name: str = "Sales Team"):
    # Render
    cust_email = render_email_customer(customer_name, model, trim, dealership.get("dealership_name"), dealership.get("address"), date, time, salesperson_name)
    dealer_email = render_email_dealer(customer_name, customer_email, customer_phone, model, trim, date, time)

    # Send in background: two separate sends
    def job():
        send_email_smtp(customer_email, cust_email)
        if dealership.get("email"):
            send_email_smtp(dealership.get("email"), dealer_email)
        else:
            print("Dealer email not found; dealer email content:\n", dealer_email)
    t = threading.Thread(target=job, daemon=True)
    t.start()

# ---------------------- STREAMLIT UI ----------------------

st.set_page_config(page_title="Toyota SmartDrive Agent", layout="wide")
st.title("Toyota SmartDrive — Agentic Chat & Test Drive")

# Left: chat + actions
col1, col2 = st.columns([2, 1])

with col1:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for item in st.session_state.chat_history:
        if item["role"] == "agent":
            st.markdown(f"**Agent:** {item['text']}")
        else:
            st.markdown(f"**{item['name']} (you):** {item['text']}")

    user_name = st.text_input("Your name", value=st.session_state.get("user_name", ""))
    user_zip = st.text_input("Your ZIP code", value=st.session_state.get("user_zip", ""))
    user_query = st.text_input("Ask me about Toyota cars, availability, or schedule a test drive:")

    if st.button("Send"):
        # append user message
        uname = user_name.strip() or "Customer"
        st.session_state.user_name = uname
        st.session_state.user_zip = user_zip
        st.session_state.chat_history.append({"role": "user", "name": uname, "text": user_query})

        # Simple rule-based routing: detect intent keywords
        qlower = user_query.lower()
        if any(k in qlower for k in ["test drive", "schedule", "book", "drive"]):
            # Ask which model
            st.session_state.chat_history.append({"role": "agent", "text": f"Sure {uname}! Would you like to schedule a test drive for a particular model, or are you looking to explore other cars as well?"})
        elif any(k in qlower for k in ["available", "stock", "inventory", "near"]):
            st.session_state.chat_history.append({"role": "agent", "text": f"Okay {uname}, let me check availability near {user_zip}. Which model are you interested in?"})
        else:
            # generic response using serper_fetch
            # try to detect model name word
            words = user_query.split()
            guessed_model = words[0] if words else "RAV4"
            info = serper_fetch(guessed_model)
            summary = info.get("summary")
            st.session_state.chat_history.append({"role": "agent", "text": f"Here’s a quick summary of {info.get('model')}: {summary}. Would you like to check availability or schedule a test drive?"})
        st.experimental_rerun()

with col2:
    st.header("Quick Actions")
    if st.button("Show nearby inventory"):
        zipcode = st.session_state.get("user_zip", "")
        if not zipcode:
            st.warning("Enter your ZIP code on the left first.")
        else:
            items = inventory_tool(zipcode)
            if not items:
                st.info("No inventory found near your ZIP code.")
            else:
                df = pd.DataFrame(items)
                # simplify features
                if "features" in df.columns:
                    df["features"] = df["features"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
                st.dataframe(df[["dealership_name", "model", "trim", "vin", "available_status", "address", "phone", "features"]])

    st.markdown("---")
    st.subheader("Schedule Test Drive (quick form)")
    with st.form("testdrive_form"):
        cname = st.text_input("Full name", value=st.session_state.get("user_name", ""))
        cemail = st.text_input("Email address")
        cphone = st.text_input("Phone number")
        zipcode = st.text_input("ZIP code", value=st.session_state.get("user_zip", ""))
        # Offer dropdown of nearby cars
        offers = inventory_tool(zipcode)
        options = [f"{o['model']} | {o['trim']} | {o['dealership_name']} | VIN:{o['vin']}" for o in offers]
        selected = st.selectbox("Select car", options if options else ["No cars found near ZIP"]) if options else None
        dt = st.date_input("Preferred date", value=datetime.now().date())
        tt = st.time_input("Preferred time", value=datetime.now().time().replace(microsecond=0))
        submitted = st.form_submit_button("Schedule")
        if submitted:
            if not (cname and cemail and cphone and zipcode and selected):
                st.warning("Please fill all fields and choose a car.")
            else:
                # parse selected
                # find inventory id
                chosen = None
                for o in offers:
                    label = f"{o['model']} | {o['trim']} | {o['dealership_name']} | VIN:{o['vin']}"
                    if label == selected:
                        chosen = o
                        break
                if not chosen:
                    st.error("Selected car not found in inventory list. Try again.")
                else:
                    # schedule
                    # we stored vehicle inventory_id as inventory_id in offers
                    # Need dealership_id and salesperson_id selection: choose first matching dealer
                    cur = conn.cursor()
                    cur.execute("SELECT dealership_id, dealership_name, address, email, phone FROM Dealership WHERE dealership_name = ? LIMIT 1", (chosen['dealership_name'],))
                    dealer = cur.fetchone()
                    dealership = {
                        "dealership_id": dealer[0] if dealer else None,
                        "dealership_name": dealer[1] if dealer else chosen.get('dealership_name'),
                        "address": dealer[2] if dealer else chosen.get('address'),
                        "email": dealer[3] if dealer else None,
                        "phone": dealer[4] if dealer else chosen.get('phone')
                    }
                    # salesperson simple pick
                    salesperson_id = None
                    salesperson_name = "Sales Team"
                    if dealership.get("dealership_id"):
                        cur.execute("SELECT salesperson_id, salesperson_name FROM Salesperson WHERE dealership_id = ? LIMIT 1", (dealership['dealership_id'],))
                        sp = cur.fetchone()
                        if sp:
                            salesperson_id = sp[0]
                            salesperson_name = sp[1]

                    dt_obj = datetime.combine(dt, tt)
                    result = schedule_test_drive(cname, cemail, cphone, zipcode, chosen['inventory_id'], dealership['dealership_id'], salesperson_id, dt_obj)

                    # fire background emails
                    generate_and_send_emails_bg(cname, cemail, cphone, chosen['model'], chosen['trim'], dealership, result['date'], result['time'], salesperson_name)

                    st.success(f"Test drive scheduled for {result['date']} at {result['time']}. Confirmation email will be sent shortly.")

# ---------------------- END ----------------------

st.markdown("---")
st.info("This is a prototype. Replace serper_fetch() with a real web tool and configure SMTP for real emails.")

