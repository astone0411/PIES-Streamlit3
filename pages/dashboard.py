"""
Dashboard — summary stats and recent activity.
"""

import streamlit as st
import pandas as pd
from database.models import get_session, Specimen, QCRecord, QCStatus, TestResult
from utils.auth import require_auth


def show():
    require_auth()

    st.markdown("## 🧪 Dashboard")
    st.markdown(f"Welcome back, **{st.session_state['display_name']}**")
    st.divider()

    session = get_session()

    # --- KPI cards ---
    total       = session.query(Specimen).count()
    pending_qc  = session.query(Specimen).filter_by(is_verified=False).count()
    approved_qc = session.query(QCRecord).filter_by(status=QCStatus.APPROVED).count()
    detected    = session.query(Specimen).filter_by(source_result=TestResult.DETECTED).count()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Specimens",   total)
    c2.metric("Pending QC",        pending_qc,  delta=f"-{pending_qc}" if pending_qc else None, delta_color="inverse")
    c3.metric("QC Approved",       approved_qc)
    c4.metric("Detected Results",  detected)

    st.divider()

    # --- Recent specimens ---
    st.markdown("### Recent Specimens")
    rows = (
        session.query(Specimen)
        .order_by(Specimen.created_at.desc())
        .limit(10)
        .all()
    )

    if rows:
        data = [
            {
                "Accession #":      s.accession_number,
                "Patient":          f"{s.patient.last_name}, {s.patient.first_name}" if s.patient else "—",
                "Source Result":    s.source_result.value if s.source_result else "—",
                "Supp. Result":     s.supplemental_result.value if s.supplemental_result else "—",
                "Verified":         "✅" if s.is_verified else "⏳",
                "Created":          s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "—",
            }
            for s in rows
        ]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info("No specimens yet. Import or add one to get started.")

    session.close()
