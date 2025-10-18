# main.py
import streamlit as st
from ui.ui import run_ui
from ui.admin_dashboard import run_admin_dashboard
from database_setup import init_database
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Toyota AI Sales Platform",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main application function"""
    # Environment checks and diagnostics
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['OPENAI_MODEL', 'SERPER_API_KEY', 'SENDER_EMAIL', 'SENDER_PASSWORD']

    missing_required = [v for v in required_vars if not os.getenv(v)]
    missing_optional = [v for v in optional_vars if not os.getenv(v)]

    st.sidebar.caption("Environment")
    if missing_required:
        st.sidebar.warning(f"Missing required: {', '.join(missing_required)}")
    if missing_optional:
        st.sidebar.info(f"Optional missing: {', '.join(missing_optional)}")

    with st.sidebar.expander("🔧 Connectivity diagnostics"):
        def mask(val: Optional[str]):
            return "set" if val else "missing"
        st.write(f"OPENAI_API_KEY: {mask(os.getenv('OPENAI_API_KEY'))}")
        st.write(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL') or 'gpt-4o-mini (default)'}")
        st.write(f"SERPER_API_KEY: {mask(os.getenv('SERPER_API_KEY'))}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Test OpenAI", key="diag_llm"):
                try:
                    from langchain_openai import ChatOpenAI
                    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
                    llm = ChatOpenAI(model=model, temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'), timeout=15)
                    out = llm.invoke("Say 'pong' if you can hear me.")
                    st.success(f"LLM OK: {getattr(out, 'content', out)}")
                except Exception as e:
                    st.error(f"LLM test failed: {e}")
        with c2:
            if st.button("Test Serper", key="diag_serper"):
                try:
                    from langchain_community.utilities import GoogleSerperAPIWrapper
                    serper = GoogleSerperAPIWrapper()
                    res = serper.run("Toyota USA site:toyota.com")
                    st.success("Serper OK: received results")
                except Exception as e:
                    st.error(f"Serper test failed: {e}")

        st.caption(".env example")
        st.code(
            """
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
SERPER_API_KEY=your-serper-key
SENDER_EMAIL=optional@domain.com
SENDER_PASSWORD=app-password-or-token
            """.strip(),
            language="bash",
        )

    # Sidebar navigation
    st.sidebar.title("🚗 Toyota AI Platform")
    
    # Mode selection
    page = st.sidebar.radio(
        "Select Mode",
        ["🤖 Customer Chat", "🏢 Admin Dashboard"],
        help="Choose between customer interface or admin management"
    )
    
    # Display selected page
    if page == "🤖 Customer Chat":
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Customer Interface**")
        st.sidebar.markdown("• Chat with Toyota AI Assistant")
        st.sidebar.markdown("• Browse available vehicles")
        st.sidebar.markdown("• Schedule test drives")
        st.sidebar.markdown("• Get vehicle information")
        
        run_ui()
        
    elif page == "🏢 Admin Dashboard":
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Admin Interface**")
        st.sidebar.markdown("• Manage inventory")
        st.sidebar.markdown("• View test drive bookings")
        st.sidebar.markdown("• Update appointment status")
        st.sidebar.markdown("• Analytics dashboard")
        
        run_admin_dashboard()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Toyota AI Sales Assistant**")
    st.sidebar.markdown("Powered by LangChain & OpenAI")
    st.sidebar.markdown("© 2025 Toyota North America")

if __name__ == "__main__":
    main()