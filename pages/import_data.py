"""
Patient & Specimen Import
Accepts CSV uploads from the source system.
Expected columns: external_id, first_name, last_name, date_of_birth, sex,
                  accession_number, source_result
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.models import get_session, Patient, Specimen, Sex, TestResult
from utils.auth import require_auth
from utils.audit import log_action


REQUIRED_COLUMNS = {
    "external_id", "first_name", "last_name",
    "date_of_birth", "sex", "accession_number", "source_result"
}


def show():
    require_auth()

    st.markdown("## 📥 Import Patient Data")
    st.markdown(
        "Upload a CSV exported from your source system. "
        "Existing patients are matched on `external_id`; "
        "existing accession numbers are skipped."
    )
    st.divider()

    # --- CSV template download ---
    template_df = pd.DataFrame(columns=list(REQUIRED_COLUMNS))
    st.download_button(
        "⬇️ Download CSV template",
        template_df.to_csv(index=False),
        file_name="lims_import_template.csv",
        mime="text/csv",
    )

    st.divider()
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded is None:
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.markdown(f"**{len(df)} rows found.** Preview:")
    st.dataframe(df.head(5), use_container_width=True)

    if st.button("Import", type="primary"):
        session = get_session()
        created_patients = 0
        created_specimens = 0
        skipped = 0

        for _, row in df.iterrows():
            # Upsert patient
            patient = session.query(Patient).filter_by(
                external_id=str(row["external_id"])
            ).first()

            if not patient:
                patient = Patient(
                    external_id=str(row["external_id"]),
                    first_name=str(row["first_name"]),
                    last_name=str(row["last_name"]),
                    date_of_birth=str(row["date_of_birth"]),
                    sex=_parse_sex(row["sex"]),
                )
                session.add(patient)
                session.flush()
                created_patients += 1

            # Skip duplicate accessions
            existing = session.query(Specimen).filter_by(
                accession_number=str(row["accession_number"])
            ).first()

            if existing:
                skipped += 1
                continue

            specimen = Specimen(
                accession_number=str(row["accession_number"]),
                patient_id=patient.id,
                source_result=_parse_result(row["source_result"]),
                received_at=datetime.utcnow(),
            )
            session.add(specimen)
            session.flush()
            log_action("specimen.import", specimen_id=specimen.id, detail={"accession": str(row["accession_number"])})
            created_specimens += 1

        session.commit()
        session.close()

        st.success(
            f"Import complete — "
            f"{created_patients} new patients, "
            f"{created_specimens} new specimens, "
            f"{skipped} skipped (duplicate accession)."
        )


def _parse_sex(val) -> Sex:
    v = str(val).strip().lower()
    if v in ("m", "male"):    return Sex.MALE
    if v in ("f", "female"):  return Sex.FEMALE
    return Sex.UNKNOWN


def _parse_result(val) -> TestResult:
    v = str(val).strip().lower()
    if "not" in v:            return TestResult.NOT_DETECTED
    if "detected" in v:       return TestResult.DETECTED
    if "inconclusive" in v:   return TestResult.INCONCLUSIVE
    return TestResult.PENDING
