"""
Supplemental Data Entry
Add diagnosis, indication, and second test result to imported specimens.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.models import get_session, Specimen, TestResult
from utils.auth import require_auth, current_user_id
from utils.audit import log_action


def show():
    require_auth()

    st.markdown("## 📝 Supplemental Data Entry")
    st.markdown("Select a specimen to add diagnosis, indication, and second result.")
    st.divider()

    session = get_session()

    # --- Filter controls ---
    col1, col2 = st.columns(2)
    with col1:
        show_incomplete = st.checkbox("Show only incomplete entries", value=True)
    with col2:
        search = st.text_input("Search by accession # or patient name", "")

    query = session.query(Specimen)
    if show_incomplete:
        query = query.filter(Specimen.supplemental_result == TestResult.PENDING)

    specimens = query.order_by(Specimen.created_at.desc()).all()

    # Filter by search term
    if search:
        s = search.lower()
        specimens = [
            sp for sp in specimens
            if s in sp.accession_number.lower()
            or (sp.patient and s in sp.patient.last_name.lower())
            or (sp.patient and s in sp.patient.first_name.lower())
        ]

    if not specimens:
        st.info("No specimens match the current filter.")
        session.close()
        return

    # --- Specimen selector ---
    options = {
        f"{sp.accession_number} — {sp.patient.last_name if sp.patient else '?'}, "
        f"{sp.patient.first_name if sp.patient else '?'}": sp.id
        for sp in specimens
    }
    selected_label = st.selectbox("Select specimen", list(options.keys()))
    selected_id = options[selected_label]
    specimen = session.query(Specimen).get(selected_id)

    st.divider()

    # --- Patient info (read-only) ---
    if specimen.patient:
        p = specimen.patient
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**Patient**\n\n{p.last_name}, {p.first_name}")
        c2.markdown(f"**DOB**\n\n{p.date_of_birth}")
        c3.markdown(f"**Sex**\n\n{p.sex.value}")
        c4.markdown(f"**Source Result**\n\n{specimen.source_result.value if specimen.source_result else '—'}")

    st.divider()

    # --- Editable supplemental fields ---
    with st.form("supplemental_form"):
        diagnosis = st.text_input(
            "Diagnosis / ICD Code",
            value=specimen.diagnosis or "",
            placeholder="e.g. J06.9, Z11.59"
        )
        indication = st.text_area(
            "Indication for Testing",
            value=specimen.indication_for_test or "",
            placeholder="Clinical reason for ordering the test..."
        )
        supp_result = st.selectbox(
            "Supplemental Test Result",
            options=[r.value for r in TestResult],
            index=[r.value for r in TestResult].index(
                specimen.supplemental_result.value if specimen.supplemental_result else TestResult.PENDING.value
            ),
        )
        notes = st.text_area(
            "Notes",
            value=specimen.supplemental_notes or "",
            placeholder="Any additional observations..."
        )

        submitted = st.form_submit_button("Save", type="primary")

    if submitted:
        old = {
            "diagnosis": specimen.diagnosis,
            "indication": specimen.indication_for_test,
            "supplemental_result": specimen.supplemental_result.value if specimen.supplemental_result else None,
        }
        specimen.diagnosis = diagnosis
        specimen.indication_for_test = indication
        specimen.supplemental_result = TestResult(supp_result)
        specimen.supplemental_notes = notes
        specimen.entered_by_id = current_user_id()
        specimen.entered_at = datetime.utcnow()
        specimen.updated_at = datetime.utcnow()
        session.commit()

        log_action(
            "specimen.supplement",
            specimen_id=specimen.id,
            detail={"before": old, "after": {
                "diagnosis": diagnosis,
                "indication": indication,
                "supplemental_result": supp_result,
            }}
        )
        st.success("Supplemental data saved.")

    session.close()
