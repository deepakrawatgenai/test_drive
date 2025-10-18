# ui/ui.py
import streamlit as st
import json
from datetime import datetime, date, time
from agent import ToyotaAgentManager
from database_setup import query_db, get_inventory_by_zipcode, get_vehicle_types, get_models_by_type, get_all_models, get_trims_by_model

# Note: Page config and CSS are injected inside main() to avoid import-time Streamlit calls


def initialize_session_state():
    """Initialize session state variables"""
    if 'agent_manager' not in st.session_state:
        st.session_state.agent_manager = ToyotaAgentManager()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'customer_info' not in st.session_state:
        st.session_state.customer_info = {}
    
    if 'show_booking_form' not in st.session_state:
        st.session_state.show_booking_form = False
    
    if 'selected_vehicle' not in st.session_state:
        st.session_state.selected_vehicle = None
    
    if 'inventory_results' not in st.session_state:
        st.session_state.inventory_results = []
    
    if 'vehicle_preferences' not in st.session_state:
        st.session_state.vehicle_preferences = {
            'preferred_type': '',
            'preferred_model': '',
            'preferred_trim': ''
        }


def display_customer_info_form():
    """Display customer information collection form"""
    st.sidebar.header("👤 Customer Information")
    
    with st.sidebar.form("customer_info_form"):
        # Basic customer information
        name = st.text_input("Full Name", value=st.session_state.customer_info.get('name', ''))
        email = st.text_input("Email", value=st.session_state.customer_info.get('email', ''))
        phone = st.text_input("Phone", value=st.session_state.customer_info.get('phone', ''))
        zipcode = st.text_input("ZIP Code", value=st.session_state.customer_info.get('zipcode', ''))
        city = st.text_input("City", value=st.session_state.customer_info.get('city', ''))
        
        # Vehicle preferences section
        st.subheader("🚗 Vehicle Preferences")
        
        # Get vehicle types and models
        vehicle_types = get_vehicle_types()
        type_options = [""] + list(vehicle_types.keys())
        
        # Vehicle type dropdown
        current_type = st.session_state.vehicle_preferences.get('preferred_type', '')
        preferred_type = st.selectbox(
            "Preferred Vehicle Type",
            options=type_options,
            index=type_options.index(current_type) if current_type in type_options else 0,
            help="Select the type of vehicle you're interested in"
        )
        
        # Model dropdown (filtered by type)
        model_options = [""]
        if preferred_type:
            model_options.extend(get_models_by_type(preferred_type))
        else:
            model_options.extend(get_all_models())
        
        current_model = st.session_state.vehicle_preferences.get('preferred_model', '')
        preferred_model = st.selectbox(
            "Preferred Model",
            options=model_options,
            index=model_options.index(current_model) if current_model in model_options else 0,
            help="Select a specific Toyota model"
        )
        
        # Trim dropdown (filtered by model)
        trim_options = [""]
        if preferred_model:
            trim_options.extend(get_trims_by_model(preferred_model))
        
        current_trim = st.session_state.vehicle_preferences.get('preferred_trim', '')
        preferred_trim = st.selectbox(
            "Preferred Trim Level",
            options=trim_options,
            index=trim_options.index(current_trim) if current_trim in trim_options else 0,
            help="Select a specific trim level (optional)"
        )
        
        submitted = st.form_submit_button("Update Info")
        
        if submitted:
            st.session_state.customer_info = {
                'name': name,
                'email': email,
                'phone': phone,
                'zipcode': zipcode,
                'city': city
            }
            
            st.session_state.vehicle_preferences = {
                'preferred_type': preferred_type,
                'preferred_model': preferred_model,
                'preferred_trim': preferred_trim
            }
            
            # Update agent context with customer info and preferences
            st.session_state.agent_manager.set_customer_context(
                name=name, email=email, phone=phone, zipcode=zipcode, city=city,
                preferred_type=preferred_type, preferred_model=preferred_model, preferred_trim=preferred_trim
            )
            
            st.sidebar.success("✅ Information updated!")
            
            # Auto-search inventory if preferences are set
            if zipcode and preferred_model:
                inventory = get_inventory_by_zipcode(zipcode, preferred_model)
                st.session_state.inventory_results = inventory
    
    # Show current info
    if st.session_state.customer_info:
        st.sidebar.write("**Current Information:**")
        for key, value in st.session_state.customer_info.items():
            if value:
                st.sidebar.write(f"- {key.title()}: {value}")
    
    # Show vehicle preferences
    if any(st.session_state.vehicle_preferences.values()):
        st.sidebar.write("**Vehicle Preferences:**")
        for key, value in st.session_state.vehicle_preferences.items():
            if value:
                display_key = key.replace('preferred_', '').replace('_', ' ').title()
                st.sidebar.write(f"- {display_key}: {value}")


def display_vehicle_card(vehicle_data):
    """Display a vehicle card with booking option"""
    vid, model, trim, color, rate, features_json, dealer_name, city, zipcode, address, phone, inventory_id, vin = vehicle_data
    
    # Parse features
    try:
        features = json.loads(features_json) if features_json else {}
    except:
        features = {}
    
    with st.container():
        st.markdown(f"""
        <div class="vehicle-card">
            <h3>🚗 {model} {trim}</h3>
            <p><strong>Color:</strong> {color}</p>
            <p class="price-tag">${rate:,.2f}</p>
            <p><strong>Available at:</strong> {dealer_name}, {city} {zipcode}</p>
            <p><strong>Address:</strong> {address}</p>
            <p><strong>Phone:</strong> {phone}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show features if available
        if features:
            with st.expander("🔧 Vehicle Features"):
                feature_text = ""
                for key, value in features.items():
                    feature_text += f"• **{key.title()}:** {value}\n"
                st.markdown(feature_text)
        
        # Test drive button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"📅 Schedule Test Drive", key=f"book_{inventory_id}"):
                st.session_state.selected_vehicle = {
                    'id': vid,
                    'model': model,
                    'trim': trim,
                    'color': color,
                    'rate': rate,
                    'dealer_name': dealer_name,
                    'dealer_address': address,
                    'dealer_city': city,
                    'dealer_zipcode': zipcode,
                    'dealer_phone': phone,
                    'inventory_id': inventory_id,
                    'vin': vin
                }
                st.session_state.show_booking_form = True
                st.rerun()
        
        with col2:
            if st.button(f"ℹ️ More Details", key=f"details_{inventory_id}"):
                # Get more details using the agent
                response = st.session_state.agent_manager.get_response(f"Tell me more about the {model} {trim}")
                st.session_state.chat_history.append(("You", f"Tell me more about the {model} {trim}"))
                st.session_state.chat_history.append(("Toyota AI", response))
                st.rerun()


def display_booking_form():
    """Display test drive booking form"""
    if not st.session_state.selected_vehicle:
        return
    
    vehicle = st.session_state.selected_vehicle
    
    st.header(f"📅 Schedule Test Drive - {vehicle['model']} {vehicle['trim']}")
    
    with st.form("booking_form"):
        st.subheader("Vehicle Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Model:** {vehicle['model']} {vehicle['trim']}")
            st.write(f"**Color:** {vehicle['color']}")
            st.write(f"**Price:** ${vehicle['rate']:,.2f}")
        with col2:
            st.write(f"**Dealership:** {vehicle['dealer_name']}")
            st.write(f"**Location:** {vehicle['dealer_city']}, {vehicle['dealer_zipcode']}")
            st.write(f"**Phone:** {vehicle['dealer_phone']}")
        
        st.subheader("Customer Information")
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("Full Name*", value=st.session_state.customer_info.get('name', ''))
            customer_email = st.text_input("Email*", value=st.session_state.customer_info.get('email', ''))
        with col2:
            customer_phone = st.text_input("Phone*", value=st.session_state.customer_info.get('phone', ''))
            customer_zipcode = st.text_input("ZIP Code*", value=st.session_state.customer_info.get('zipcode', ''))
        
        st.subheader("Appointment Details")
        col1, col2 = st.columns(2)
        with col1:
            test_date = st.date_input("Preferred Date*", min_value=date.today())
        with col2:
            test_time = st.time_input("Preferred Time*", value=time(14, 0))  # Default 2:00 PM
        
        special_request = st.text_area("Special Requests or Questions", placeholder="Any specific features you'd like to focus on, accessibility needs, or questions?")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submitted = st.form_submit_button("🚗 Book Test Drive", width='stretch')
        
        if submitted:
            # Validate required fields
            if not all([customer_name, customer_email, customer_phone, customer_zipcode]):
                st.error("❌ Please fill in all required fields marked with *")
            else:
                # Prepare booking data
                booking_data = {
                    'customer_name': customer_name,
                    'email': customer_email,
                    'phone': customer_phone,
                    'zipcode': customer_zipcode,
                    'city': st.session_state.customer_info.get('city', ''),
                    'vehicle_id': vehicle['id'],
                    'date': str(test_date),
                    'time': str(test_time),
                    'special_request': special_request
                }
                
                # Save booking using clean tools module
                try:
                    from tools import save_booking_tool
                    payload = {
                        'customer': {
                            'name': booking_data['customer_name'],
                            'email': booking_data['email'],
                            'phone': booking_data['phone'],
                            'zipcode': booking_data['zipcode'],
                            'city': booking_data.get('city', '')
                        },
                        'vehicle': {
                            'vehicle_id': booking_data['vehicle_id']
                        },
                        # Prefer inventory_id; tool will resolve dealership_id
                        'inventory_id': vehicle.get('inventory_id'),
                        'date': booking_data['date'],
                        'time': booking_data['time'],
                        'special_request': booking_data.get('special_request', '')
                    }
                    raw = save_booking_tool(json.dumps(payload))
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except Exception as e:
                    parsed = { 'ok': False, 'error': 'booking_call_failed', 'detail': str(e) }

                if parsed and parsed.get('ok'):
                    success_msg = (
                        f"✅ Successfully booked a test drive for {vehicle['model']} {vehicle['trim']} "
                        f"on {test_date} at {test_time}. Your confirmation ID is #{parsed.get('testdrive_id')}."
                    )
                    st.success(success_msg)
                    st.session_state.show_booking_form = False
                    st.session_state.selected_vehicle = None
                    
                    # Update customer info
                    st.session_state.customer_info.update({
                        'name': customer_name,
                        'email': customer_email,
                        'phone': customer_phone,
                        'zipcode': customer_zipcode
                    })
                    
                    # Add to chat history
                    st.session_state.chat_history.append(("System", success_msg))
                    
                    st.balloons()
                    st.rerun()
                else:
                    err_detail = parsed.get('detail') or parsed.get('error') or 'Unknown error'
                    st.error(f"❌ Booking failed: {err_detail}")
    
    # Cancel button
    if st.button("❌ Cancel Booking"):
        st.session_state.show_booking_form = False
        st.session_state.selected_vehicle = None
        st.rerun()


def display_chat_interface():
    """Display the main chat interface"""
    st.header("🚗 Toyota AI Sales Assistant")
    
    # Chat history container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for role, message in st.session_state.chat_history:
            if role == "You":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong><br>
                    {message}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message agent-message">
                    <strong>🤖 Toyota AI:</strong><br>
                    {message}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    with st.container():
        user_input = st.chat_input("Ask about Toyota vehicles, check inventory, or schedule a test drive...")
        
        if user_input:
            # Add user message to history
            st.session_state.chat_history.append(("You", user_input))
            
            # Get agent response
            with st.spinner("🤔 Let me help you with that..."):
                response = st.session_state.agent_manager.get_response(user_input)
            
            # Add agent response to history
            st.session_state.chat_history.append(("Toyota AI", response))
            
            # Check if response mentions inventory and update display
            if "Available Toyota Vehicles" in response and st.session_state.customer_info.get('zipcode'):
                zipcode = st.session_state.customer_info['zipcode']
                inventory = get_inventory_by_zipcode(zipcode)
                st.session_state.inventory_results = inventory
            
            st.rerun()


def display_inventory_cards():
    """Display inventory as cards if available"""
    if st.session_state.inventory_results:
        st.header("🚗 Available Vehicles")
        
        # Group by dealership for better organization
        dealership_groups = {}
        for vehicle in st.session_state.inventory_results:
            dealer_name = vehicle[6]  # dealership_name
            if dealer_name not in dealership_groups:
                dealership_groups[dealer_name] = []
            dealership_groups[dealer_name].append(vehicle)
        
        for dealer_name, vehicles in dealership_groups.items():
            st.subheader(f"📍 {dealer_name}")
            
            # Display vehicles in columns
            cols = st.columns(min(len(vehicles), 2))
            for idx, vehicle in enumerate(vehicles):
                with cols[idx % 2]:
                    display_vehicle_card(vehicle)


def main():
    """Main UI function"""
    # Custom CSS for better styling (inject at runtime, not import time)
    st.markdown(
        """
        <style>
        .vehicle-card {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            background-color: #f9f9f9;
        }
        .price-tag {
            color: #d63384;
            font-size: 1.5rem;
            font-weight: bold;
        }
        .feature-list {
            background-color: #e9ecef;
            padding: 0.5rem;
            border-radius: 5px;
            margin: 0.5rem 0;
        }
        .chat-message {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 10px;
        }
        .user-message {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        .agent-message {
            background-color: #f3e5f5;
            border-left: 4px solid #9c27b0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    initialize_session_state()
    
    # Sidebar
    display_customer_info_form()
    
    # Main content area
    if st.session_state.show_booking_form:
        display_booking_form()
    else:
        # Chat interface
        display_chat_interface()
        
        # Inventory cards (if available)
        display_inventory_cards()
        
        # Quick action buttons
        st.sidebar.header("🚀 Quick Actions")
        
        if st.sidebar.button("🔍 Search Inventory Near Me"):
            if st.session_state.customer_info.get('zipcode'):
                zipcode = st.session_state.customer_info['zipcode']
                user_input = f"Show me available Toyota vehicles near {zipcode}"
                st.session_state.chat_history.append(("You", user_input))
                response = st.session_state.agent_manager.get_response(user_input)
                st.session_state.chat_history.append(("Toyota AI", response))
                st.rerun()
            else:
                st.sidebar.error("Please enter your ZIP code first!")
        
        if st.sidebar.button("🚗 Popular Toyota Models"):
            user_input = "Tell me about popular Toyota models and their key features"
            st.session_state.chat_history.append(("You", user_input))
            response = st.session_state.agent_manager.get_response(user_input)
            st.session_state.chat_history.append(("Toyota AI", response))
            st.rerun()
        
        if st.sidebar.button("⚡ Hybrid Vehicles"):
            user_input = "Show me Toyota hybrid vehicles and their benefits"
            st.session_state.chat_history.append(("You", user_input))
            response = st.session_state.agent_manager.get_response(user_input)
            st.session_state.chat_history.append(("Toyota AI", response))
            st.rerun()
        
        if st.sidebar.button("🔄 Reset Chat"):
            st.session_state.chat_history = []
            st.session_state.agent_manager.reset_conversation()
            st.session_state.inventory_results = []
            st.rerun()


def run_ui():
    """Function to run the UI (called from main.py)"""
    main()


if __name__ == "__main__":
    main()