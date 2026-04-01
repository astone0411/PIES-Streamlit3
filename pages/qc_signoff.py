"""
QC Sign-off
Review specimens and approve or reject QC checks.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.models import get_session, Specimen, QCRecord, QCStatus, TestResult
from utils.auth import require_auth, current_user_id, is_supervisor
from utils.audit import log_action


def show():
    require_auth()

    st.markdown("## ✅ QC Sign-off")
    st.markdown("Review and approve specimens before report generation.")
    st.divider()

    session = get_session()

    # Specimens that have supplemental data but are not yet verified
    specimens = (
        session.query(Specimen)
        .filter(Specimen.supplemental_result != TestResult.PENDING)
        .filter(Specimen.is_verified == False)
        .order_by(Specimen.entered_at.desc())
        .all()
    )

    if not specimens:
        st.success("🎉 No specimens pending QC sign-off.")
        # Show recently approved
        recent = (
            session.query(QCRecord)
            .filter_by(status=QCStatus.APPROVED)
            .order_by(QCRecord.signed_at.desc())
            .limit(10)
            .all()
        )
        if recent:
            st.markdown("### Recently Approved")
            data = [
                {
                    "Accession #": r.specimen.accession_number,
                    "Signed By":   r.signed_by_user.display_name,
                    "Signed At":   r.signed_at.strftime("%Y-%m-%d %H:%M"),
                    "Notes":       r.notes or "—",
                }
                for r in recent
            ]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        session.close()
        return

    st.markdown(f"**{len(specimens)} specimen(s) awaiting QC sign-off**")

    for specimen in specimens:
        with st.expander(
            f"🔬 {specimen.accession_number} — "
            f"{specimen.patient.last_name if specimen.patient else '?'}, "
            f"{specimen.patient.first_name if specimen.patient else '?'}",
            expanded=False,
        ):
            p = specimen.patient
            if p:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**DOB:** {p.date_of_birth}")
                c2.markdown(f"**Sex:** {p.sex.value}")
                c3.markdown(f"**External ID:** {p.external_id}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Source Result:** {specimen.source_result.value if specimen.source_result else '—'}")
            c2.markdown(f"**Supplemental Result:** {specimen.supplemental_result.value if specimen.supplemental_result else '—'}")
            st.markdown(f"**Diagnosis:** {specimen.diagnosis or '—'}")
            st.markdown(f"**Indication:** {specimen.indication_for_test or '—'}")
            if specimen.entered_by:
                st.caption(f"Data entered by {specimen.entered_by.display_name} at {specimen.entered_at.strftime('%Y-%m-%d %H:%M') if specimen.entered_at else '?'}")

            st.markdown("---")
            notes = st.text_area("QC Notes (optional)", key=f"notes_{specimen.id}", placeholder="Any observations...")

            col_approve, col_reject = st.columns(2)
            if col_approve.button("✅ Approve", key=f"approve_{specimen.id}", type="primary"):
                _sign_off(session, specimen, QCStatus.APPROVED, notes)
                st.success("Approved.")
                st.rerun()

            if col_reject.button("❌ Reject", key=f"reject_{specimen.id}"):
                _sign_off(session, specimen, QCStatus.REJECTED, notes)
                st.warning("Rejected.")
                st.rerun()

    session.close()


def _sign_off(session, specimen: Specimen, status: QCStatus, notes: str):
    record = QCRecord(
        specimen_id=specimen.id,
        signed_by_id=current_user_id(),
        status=status,
        notes=notes or None,
        signed_at=datetime.utcnow(),
    )
    session.add(record)

    if status == QCStatus.APPROVED:
        specimen.is_verified = True
        specimen.updated_at = datetime.utcnow()

    session.commit()
    log_action(
        f"qc.{status.value.lower()}",
        specimen_id=specimen.id,
        detail={"notes": notes},
    )
