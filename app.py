"""
LIMS Application — Main Entry Point
Run with: streamlit run app.py
"""

import streamlit as st
from database.models import init_db
from utils.auth import is_authenticated, login, logout

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Lab LIMS",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Sidebar nav styling */
    [data-testid="stSidebarNav"] { display: none; }

    /* Clean metric cards */
    [data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Status badges */
    .badge-approved { color: #198754; font-weight: 600; }
    .badge-pending  { color: #fd7e14; font-weight: 600; }
    .badge-rejected { color: #dc3545; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Database initialisation (runs once per session/cold start)
# ---------------------------------------------------------------------------
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True

# ---------------------------------------------------------------------------
# Login screen
# ---------------------------------------------------------------------------
def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🧪 Lab LIMS")
        st.markdown("Please sign in to continue.")
        st.divider()

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            if login(username, password):
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.caption("Default accounts: **admin** / admin123 · **tech1** / tech123")
        st.caption("⚠️ Change default passwords before sharing with your team.")

# ---------------------------------------------------------------------------
# Authenticated app shell
# ---------------------------------------------------------------------------
def render_app():
    # Import pages lazily to avoid circular imports
    from pages import dashboard, import_data, supplemental_entry, qc_signoff, audit_log, vcf_annotate

    # Sidebar
    with st.sidebar:
        st.markdown("### 🧪 Lab LIMS")
        st.caption(f"Signed in as **{st.session_state['display_name']}** ({st.session_state['role']})")
        st.divider()

        pages = {
            "Dashboard":            ("🏠", dashboard),
            "Import Patient Data":  ("📥", import_data),
            "Supplemental Entry":   ("📝", supplemental_entry),
            "QC Sign-off":          ("✅", qc_signoff),
            "VCF Annotation":       ("🧬", vcf_annotate),
            "Audit Log":            ("📋", audit_log),
        }

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "Dashboard"

        for label, (icon, _) in pages.items():
            if st.button(f"{icon}  {label}", use_container_width=True,
                         type="primary" if st.session_state["current_page"] == label else "secondary"):
                st.session_state["current_page"] = label
                st.rerun()

        st.divider()
        if st.button("🚪  Sign Out", use_container_width=True):
            logout()
            st.rerun()

    # Page renderer
    _, module = pages[st.session_state["current_page"]]
    module.show()

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if is_authenticated():
    render_app()
else:
    render_login()
