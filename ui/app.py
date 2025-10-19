import streamlit as st
from datetime import datetime
from agents.agent_tools import get_agent_executor, run_agent_with_streaming
from agents.nlu import classify_intent
from ui.app_helper import append_user_message, append_agent_message, display_chat_history, inventory_tool, schedule_test_drive, generate_and_send_emails_bg

def main():
    st.set_page_config(page_title="Toyota SmartDrive Agent", layout="wide")
    st.title("Toyota SmartDrive — Agentic Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ---------------- Sidebar: Scheduling Form ----------------
    with st.sidebar:
        st.header("Schedule a Test Drive")
        with st.form("schedule_form"):
            cname = st.text_input("Full Name", value=st.session_state.get("name",""))
            cemail = st.text_input("Email")
            cphone = st.text_input("Phone")
            zipc = st.text_input("ZIP Code", value=st.session_state.get("zipcode",""))

            offers = inventory_tool(zipc)
            opts = [f"{o['model']}|{o['trim']}|{o['dealership_name']}|{o['inventory_id']}" for o in offers]
            selected = st.selectbox("Select Car", opts if opts else ["No cars found"])

            date = st.date_input("Preferred Date")
            time = st.time_input("Preferred Time")

            submit = st.form_submit_button("Schedule Test Drive")
            if submit and selected != "No cars found":
                model, trim, dealership_name, inventory_id = selected.split('|')
                inventory_id = int(inventory_id)
                test_drive = schedule_test_drive(cname, cemail, cphone, zipc, inventory_id,
                                                 dealership_id=1, salesperson_id=1,
                                                 dt=datetime.combine(date, time))
                append_agent_message(f"Test drive scheduled on {test_drive['date']} at {test_drive['time']}. Confirmation email sent.")
                generate_and_send_emails_bg(cname, cemail, cphone, model, trim, inventory_id, test_drive['date'], test_drive['time'])

    # ---------------- Main Chat ----------------
    col1, col2 = st.columns([2,1])
    with col1:
        name = st.text_input("Your Name", value=st.session_state.get("name",""))
        zipcode = st.text_input("ZIP Code", value=st.session_state.get("zipcode",""))

        display_chat_history()

        user_input = st.text_input("Ask about cars, availability, or schedule a test drive:")
        if st.button("Send"):
            name = name.strip() or "Customer"
            st.session_state.name = name
            st.session_state.zipcode = zipcode
            append_user_message(user_input, name)

            # NLU classification
            intent, meta = classify_intent(user_input)

            if intent == "check_inventory":
                append_agent_message(f"Okay {name}, checking availability near {zipcode} for {meta.get('model','any model')}...")
                items = inventory_tool(zipcode, meta.get('model'))
                if not items:
                    append_agent_message("No inventory found nearby. Would you like me to suggest similar models?")
                else:
                    preview = "\n".join([f"{it['model']} {it['trim']} at {it['dealership_name']} (VIN:{it['vin']})" for it in items[:5]])
                    append_agent_message(preview)

            elif intent == "get_specs":
                append_agent_message(f"Looking up latest specs for {meta.get('model')}...")
                from tools.serper_client import serper_search_and_parse
                parsed = serper_search_and_parse(meta.get('model'))
                features = ', '.join(parsed.get('features',[]))
                trims = ', '.join(parsed.get('trims',[]))
                summary = parsed.get('summary','')
                append_agent_message(f"{summary}\nFeatures: {features}\nTrims: {trims}")

            elif intent == "schedule_test_drive":
                append_agent_message("Sure — I can schedule that. Please use the scheduling form on the right to provide your details and pick a car/date.")

            else:
                append_agent_message("Let me fetch that for you...")
                agent_executor = get_agent_executor()
                if agent_executor:
                    placeholder = st.empty()
                    full = run_agent_with_streaming(agent_executor, user_input, placeholder)
                    append_agent_message(full)
                else:
                    append_agent_message("LLM agent not configured. Please set OPENAI_API_KEY.")

            st.experimental_rerun()
