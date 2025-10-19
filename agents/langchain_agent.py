import streamlit as st
import pandas as pd
from datetime import datetime
from agents.langchain_agent import ToyotaAgent
from tools.agent_tools import AgentTools

from ui.app_helper import inventory_tool, schedule_test_drive, generate_and_send_emails_bg
st.set_page_config(page_title="Toyota SmartDrive Agent", layout="wide")
st.title("Toyota SmartDrive — Agentic Chat & Test Drive")
# ---------------------- SERPER ADVANCED PARSING ----------------------

def parse_serper_response(raw_text: str) -> dict:
    """
    Parses Serper search output to extract key information like features and trims.
    Returns dict: {summary: str, features: List[str], trims: List[str]}
    """
    import re

    summary = raw_text[:500]  # take first 500 chars as summary
    features = re.findall(r'\b(Hybrid|AWD|FWD|Heated Seats|Panoramic Roof|Infotainment|Sunroof|Navigation|Leather|Bluetooth)\b', raw_text, re.IGNORECASE)
    features = list(set([f.title() for f in features]))
    trims = re.findall(r'\b(Base|XLE|XSE|Limited|LE|SE|Platinum)\b', raw_text, re.IGNORECASE)
    trims = list(set([t.upper() for t in trims]))

    return {"summary": summary, "features": features, "trims": trims}

# Example usage inside agent_tools.py for Serper wrapper

def serper_search_advanced(query: str) -> str:
    raw = tools.serper_search(query)  # original Serper fetch
    parsed = parse_serper_response(raw)
    out = f"Summary: {parsed['summary']}\nFeatures: {', '.join(parsed['features'])}\nTrims: {', '.join(parsed['trims'])}"
    return out
agent = ToyotaAgent()
tools = AgentTools()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

col1, col2 = st.columns([2, 1])

with col1:
    for item in st.session_state.chat_history:
        if item["role"] == "agent":
            st.markdown(f"**Agent:** {item['text']}")
        else:
            st.markdown(f"**{item['name']} (you):** {item['text']}")

    user_name = st.text_input("Your name", value=st.session_state.get("user_name", ""))
    user_zip = st.text_input("Your ZIP code", value=st.session_state.get("user_zip", ""))
    user_query = st.text_input("Ask me about Toyota cars, availability, or schedule a test drive:")

    if st.button("Send") and user_query.strip():
        uname = user_name.strip() or "Customer"
        st.session_state.user_name = uname
        st.session_state.user_zip = user_zip
        st.session_state.chat_history.append({"role": "user", "name": uname, "text": user_query})

        # Use NLU parser to determine intent
        parsed = tools.parse_intent(user_query)
        intent = parsed.get("intent", "general")
        entities = parsed.get("entities", {})

        if intent == "schedule_test_drive":
            st.session_state.chat_history.append({"role": "agent", "text": f"Sure {uname}! Would you like to schedule a test drive for a particular model, or are you looking to explore other cars as well?"})
            # Optionally, show quick test drive form automatically
        elif intent == "check_inventory":
            zipcode = entities.get("zipcode", user_zip)
            model = entities.get("model")
            items_summary = tools.inventory_lookup(f"zipcode={zipcode};model={model if model else ''}")
            st.session_state.chat_history.append({"role": "agent", "text": items_summary})
        elif intent == "compare_models":
            st.session_state.chat_history.append({"role": "agent", "text": f"I can compare models for you. Tell me two model names separated by 'vs' or comma."})
        else:
            # Fallback to agent
            response_text = agent.run(user_query)
            st.session_state.chat_history.append({"role": "agent", "text": response_text})

        st.experimental_rerun()

with col2:
    st.header("Quick Actions")
    if st.button("Show nearby inventory"):
        zipcode = st.session_state.get("user_zip", "")
        if not zipcode:
            st.warning("Enter your ZIP code on the left first.")
        else:
            items = tools.inventory_lookup(f"zipcode={zipcode}")
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
        offers = tools.inventory_lookup(f"zipcode={zipcode}")
        options = [f"{o['model']} | {o['trim']} | {o['dealership_name']} | VIN:{o['vin']}" for o in offers]
        selected = st.selectbox("Select car", options if options else ["No cars found near ZIP"]) if options else None
        dt = st.date_input("Preferred date", value=datetime.now().date())
        tt = st.time_input("Preferred time", value=datetime.now().time().replace(microsecond=0))
        submitted = st.form_submit_button("Schedule")
        if submitted:
            if not (cname and cemail and cphone and zipcode and selected):
                st.warning("Please fill all fields and choose a car.")
            else:
                chosen = next((o for o in offers if f"{o['model']} | {o['trim']} | {o['dealership_name']} | VIN:{o['vin']}" == selected), None)
                if not chosen:
                    st.error("Selected car not found in inventory list. Try again.")
                else:
                    result = schedule_test_drive(cname, cemail, cphone, zipcode, chosen['inventory_id'], chosen['dealership_id'], None, datetime.combine(dt, tt))
                    generate_and_send_emails_bg(cname, cemail, cphone, chosen['model'], chosen['trim'], chosen, result['date'], result['time'])
                    st.success(f"Test drive scheduled for {result['date']} at {result['time']}. Confirmation email will be sent shortly.")

