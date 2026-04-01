"""
Audit Log — read-only view of all data changes.
"""

import streamlit as st
import pandas as pd
from database.models import get_session, AuditLog
from utils.auth import require_auth


def show():
    require_auth()

    st.markdown("## 📋 Audit Log")
    st.markdown("Immutable record of all data entry and sign-off actions.")
    st.divider()

    session = get_session()

    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("Show last", [50, 100, 250, 500], index=0)
    with col2:
        search = st.text_input("Filter by action or username", "")

    logs = (
        session.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    if search:
        s = search.lower()
        logs = [
            l for l in logs
            if s in (l.action or "").lower()
            or (l.user and s in l.user.username.lower())
            or (l.user and s in l.user.display_name.lower())
        ]

    if not logs:
        st.info("No audit log entries found.")
        session.close()
        return

    data = [
        {
            "Timestamp":    l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "User":         l.user.display_name if l.user else "—",
            "Action":       l.action,
            "Accession #":  l.specimen.accession_number if l.specimen else "—",
            "Detail":       l.detail or "—",
        }
        for l in logs
    ]

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    session.close()
