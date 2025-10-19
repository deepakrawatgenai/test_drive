
import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
from jinja2 import Template

# LangChain & provider imports
try:
    from langchain_openai import ChatOpenAI
    from langchain.agents import Tool, initialize_agent
    from langchain.agents.agent_types import AgentType
    from langchain.memory import ConversationBufferMemory
    from langchain_community.utilities import GoogleSerperAPIWrapper
except Exception as e:
    # If imports fail, allow the app to still show prototype UI and fall back to simple functions
    ChatOpenAI = None
    Tool = None
    initialize_agent = None
    AgentType = None
    ConversationBufferMemory = None
    GoogleSerperAPIWrapper = None
    print("LangChain/OpenAI/Serper imports failed:", e)

DB_PATH = "toyota_sales.db"

# ---------------------- DB ----------------------

def get_db_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()

# ---------------------- SERPER (web search) ----------------------

def serper_fetch(query: str) -> Dict[str, Any]:
    """Use LangChain GoogleSerperAPIWrapper if available, otherwise fallback to static placeholder."""
    api_key = os.getenv("SERPER_API_KEY")
    if GoogleSerperAPIWrapper and api_key:
        os.environ["SERPER_API_KEY"] = api_key
        try:
            wrapper = GoogleSerperAPIWrapper()
            docs = wrapper.run(query)
            # wrapper.run returns a string summary; wrap into dict
            return {"model": query, "summary": docs, "features": [], "raw": docs}
        except Exception as e:
            print("Serper wrapper error:", e)
    # Fallback static
    return {
        "model": query,
        "summary": f"{query} — summary (placeholder). Replace serper_fetch with real Serper API in production.",
        "features": ["Hybrid", "AWD", "Panoramic Roof", "Heated Seats", "12.3in Infotainment"],
        "trims": ["Base", "XLE", "XSE", "Limited"]
    }

# ---------------------- INVENTORY & FEATURE MATCH ----------------------

def inventory_tool(zipcode: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT dealership_id FROM Dealership WHERE zipcode = ? LIMIT 50", (zipcode,))
    dealers = cur.fetchall()
    dealer_ids = [d[0] for d in dealers]
    if not dealer_ids:
        return []
    seq = ",".join(["?"] * len(dealer_ids))
    q = f"SELECT Inventory.id as inventory_id, Inventory.vin, Inventory.available_status, Vehicle.id as vehicle_id, Vehicle.make, Vehicle.model, Vehicle.trim, Vehicle.features, Vehicle.rate, Dealership.dealership_id, Dealership.dealership_name, Dealership.address, Dealership.email, Dealership.phone FROM Inventory JOIN Vehicle ON Inventory.vehicle_id = Vehicle.id JOIN Dealership ON Inventory.dealership_id = Dealership.dealership_id WHERE Inventory.dealership_id IN ({seq})"
    params = dealer_ids
    if model:
        q += " AND Vehicle.model LIKE ?"
        params = dealer_ids + [f"%{model}%"]
    cur.execute(q, params)
    rows = cur.fetchall()
    results = []
    for r in rows:
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
            "dealership_id": r[9],
            "dealership_name": r[10],
            "address": r[11],
            "dealership_email": r[12],
            "phone": r[13]
        })
    return results


def feature_match_tool(target_features: List[str], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    target_set = set([f.lower() for f in target_features])
    scored = []
    for c in candidates:
        cand_set = set([f.lower() for f in c.get("features", [])])
        overlap = len(target_set.intersection(cand_set))
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored]

# ---------------------- SCHEDULING & EMAIL ----------------------

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
    customer_id = create_or_get_customer(customer_name, customer_email, customer_phone, zipcode)
    cur = conn.cursor()
    date_str = dt.date().isoformat()
    time_str = dt.time().isoformat()
    cur.execute("INSERT INTO TestDrive (customer_id, dealership_id, salesperson_id, vehicle_id, date, time, special_request) VALUES (?, ?, ?, ?, ?, ?, ?)", (customer_id, dealership_id, salesperson_id, inventory_id, date_str, time_str, special_request))
    conn.commit()
    return {"testdrive_id": cur.lastrowid, "customer_id": customer_id, "dealership_id": dealership_id, "vehicle_inventory_id": inventory_id, "date": date_str, "time": time_str}


def render_email_customer(customer_name: str, model: str, trim: str, dealership_name: str, address: str, date: str, time: str, salesperson_name: str = "Sales Team") -> str:
    tpl = Template("""
Subject: Test Drive Confirmation  {{ model }} {{ trim }}

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
Subject: New Test Drive Scheduled  {{ model }} {{ trim }}

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
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not (host and user and password):
        print("SMTP not configured. Email content below:", content)
        return False
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(content)
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
    cust_email = render_email_customer(customer_name, model, trim, dealership.get("dealership_name"), dealership.get("address"), date, time, salesperson_name)
    dealer_email = render_email_dealer(customer_name, customer_email, customer_phone, model, trim, date, time)
    def job():
        send_email_smtp(customer_email, cust_email)
        if dealership.get("dealership_email"):
            send_email_smtp(dealership.get("dealership_email"), dealer_email)
        else:
            print("Dealer email not found; dealer email content:", dealer_email)
    t = threading.Thread(target=job, daemon=True)
    t.start()

# ---------------------- LANGCHAIN AGENT SETUP ----------------------

def build_langchain_agent():
    """Constructs a LangChain agent with tools. Returns (agent_executor, llm)."""
    # LLM
    llm = None
    if ChatOpenAI:
        llm = ChatOpenAI(temperature=0.3)
    else:
        print("ChatOpenAI unavailable; agent will not be initialized.")

    tools = []

    # Serper search tool wrapper
    def serper_tool_fn(query: str) -> str:
        info = serper_fetch(query)
        return info.get("summary") or info.get("raw") or "No results"

    if Tool:
        tools.append(Tool(name="serper_search", func=serper_tool_fn, description="Use to fetch latest car info and web results for the given model or query."))

    # Inventory tool wrapper
    def inventory_tool_fn(payload: str) -> str:
        # payload expected: 'zipcode=xxxxx;model=RAV4'
        parts = dict([p.split("=") for p in payload.split(";") if "=" in p])
        zipcode = parts.get("zipcode", "")
        model = parts.get("model")
        items = inventory_tool(zipcode, model)
        if not items:
            return "No inventory found near the provided ZIP code."
        brief = []
        for it in items[:10]:
            brief.append(f"{it['model']} {it['trim']} at {it['dealership_name']} (VIN:{it['vin']}) - {it['available_status']}")
        return "".join(brief)

    if Tool:
        tools.append(Tool(name="inventory_lookup", func=inventory_tool_fn, description="Check vehicle availability near a zipcode. Input: 'zipcode=XXXXX;model=ModelName'"))

    # Feature match tool
    def feature_match_fn(payload: str) -> str:
        # payload: JSON string with keys 'features' and 'zipcode'
        try:
            p = json.loads(payload)
            feats = p.get("features", [])
            zipcode = p.get("zipcode", "")
        except Exception:
            return "Invalid payload for feature_match"
        candidates = inventory_tool(zipcode)
        matched = feature_match_tool(feats, candidates)
        if not matched:
            return "No similar models found nearby."
        out = []
        for m in matched[:8]:
            out.append(f"{m['model']} {m['trim']} @ {m['dealership_name']} (VIN:{m['vin']}) — features: {', '.join(m.get('features',[]))}")
        return "".join(out)

    if Tool:
        tools.append(Tool(name="feature_match", func=feature_match_fn, description="Find similar models by feature list. Input JSON string with features and zipcode."))

    # Schedule test drive tool (agent can ask to call it — but actual scheduling via UI form is preferred)
    def schedule_tool(payload: str) -> str:
        # payload expected JSON with keys: name,email,phone,zipcode,inventory_id,dealership_id,date,time
        try:
            p = json.loads(payload)
            dt = datetime.fromisoformat(p['date'] + 'T' + p['time'])
            res = schedule_test_drive(p['name'], p['email'], p['phone'], p['zipcode'], int(p['inventory_id']), int(p['dealership_id']), p.get('salesperson_id'), dt, p.get('special_request',''))
            # fire emails
            dealership = {"dealership_name": p.get('dealership_name',''), "address": p.get('dealership_address',''), "dealership_email": p.get('dealership_email')}
            generate_and_send_emails_bg(p['name'], p['email'], p['phone'], p.get('model','Unknown'), p.get('trim',''), dealership, res['date'], res['time'], p.get('salesperson_name','Sales Team'))
            return f"Scheduled test drive on {res['date']} at {res['time']} (id: {res['testdrive_id']}). Confirmation emails sent."
        except Exception as e:
            return f"Error scheduling test drive: {e}"

    if Tool:
        tools.append(Tool(name="schedule_test_drive", func=schedule_tool, description="Schedule a test drive. Input JSON with schedule details."))

    # Initialize agent
    if initialize_agent and llm and tools:
        memory = None
        if ConversationBufferMemory:
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        agent = initialize_agent(tools, llm, agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION, verbose=False, memory=memory)
        return agent, llm
    return None, None

agent_executor, llm = build_langchain_agent()

# ---------------------- STREAMLIT UI ----------------------

st.set_page_config(page_title="Toyota SmartDrive Agent", layout="wide")
st.title("Toyota SmartDrive — Agentic Chat & Test Drive")

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
        uname = user_name.strip() or "Customer"
        st.session_state.user_name = uname
        st.session_state.user_zip = user_zip
        st.session_state.chat_history.append({"role": "user", "name": uname, "text": user_query})

        # Intent parsing (simple rules + LLM fallback)
        qlower = user_query.lower()
        intent = "general"
        if any(k in qlower for k in ["test drive", "schedule", "book", "drive"]):
            intent = "schedule_test_drive"
        elif any(k in qlower for k in ["available", "stock", "inventory", "near", "zip"]):
            intent = "check_inventory"
        elif any(k in qlower for k in ["compare", "vs", "difference"]):
            intent = "compare_models"

        # Rule-based responses
        if intent == "schedule_test_drive":
            st.session_state.chat_history.append({"role": "agent", "text": f"Sure {uname}! Would you like to schedule a test drive for a particular model, or are you looking to explore other cars as well?"})
        elif intent == "check_inventory":
            st.session_state.chat_history.append({"role": "agent", "text": f"Okay {uname}, let me check availability near {user_zip}. Which model are you interested in?"})
        elif intent == "compare_models":
            st.session_state.chat_history.append({"role": "agent", "text": f"I can compare models for you. Tell me two model names separated by 'vs' or comma."})
        else:
            # Fallback to LLM agent if available, otherwise serper_fetch
            if agent_executor:
                try:
                    resp = agent_executor.run(user_query)
                except Exception as e:
                    print("Agent run error:", e)
                    resp = serper_fetch(user_query).get("summary")
            else:
                resp = serper_fetch(user_query).get("summary")
            st.session_state.chat_history.append({"role": "agent", "text": resp})
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
                chosen = None
                for o in offers:
                    label = f"{o['model']} | {o['trim']} | {o['dealership_name']} | VIN:{o['vin']}"
                    if label == selected:
                        chosen = o
                        break
                if not chosen:
                    st.error("Selected car not found in inventory list. Try again.")
                else:
                    cur = conn.cursor()
                    cur.execute("SELECT dealership_id, dealership_name, address, email, phone FROM Dealership WHERE dealership_name = ? LIMIT 1", (chosen['dealership_name'],))
                    dealer = cur.fetchone()
                    dealership = {"dealership_id": dealer[0] if dealer else None, "dealership_name": dealer[1] if dealer else chosen.get('dealership_name'), "address": dealer[2] if dealer else chosen.get('address'), "dealership_email": dealer[3] if dealer else None, "phone": dealer[4] if dealer else chosen.get('phone')}
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
                    generate_and_send_emails_bg(cname, cemail, cphone, chosen['model'], chosen['trim'], dealership, result['date'], result['time'], salesperson_name)
                    st.success(f"Test drive scheduled for {result['date']} at {result['time']}. Confirmation email will be sent shortly.")

st.markdown("---")
st.info("This prototype integrates Serper via LangChain's GoogleSerperAPIWrapper and OpenAI via langchain-openai when available. Docs: Serper (serper.dev) and LangChain OpenAI integration.")

# End of file