# Lab LIMS — Streamlit Prototype

A lightweight Laboratory Information Management System built with Python + Streamlit.

## Features (Phase 1)
- 🔐 User authentication with role-based access (technician / supervisor)
- 📥 Patient & specimen import via CSV
- 📝 Supplemental data entry (diagnosis, indication, second result)
- ✅ QC sign-off workflow with notes
- 📋 Immutable audit log of all actions

## Project Structure

```
lims_app/
├── app.py                  # Main entry point
├── requirements.txt
├── database/
│   ├── models.py           # SQLAlchemy models + DB init
│   └── seed.py             # Default user seeding
├── pages/
│   ├── dashboard.py        # KPI summary + recent specimens
│   ├── import_data.py      # CSV import
│   ├── supplemental_entry.py
│   ├── qc_signoff.py
│   └── audit_log.py
├── utils/
│   ├── auth.py             # Login / session management
│   └── audit.py            # Audit logging helpers
└── reports/                # (Phase 4) PDF report generation
```

## Quick Start

```bash
cd lims_app
pip install -r requirements.txt
streamlit run app.py
```

App opens at http://localhost:8501

**Default credentials** (change before sharing!):
| Username | Password | Role       |
|----------|----------|------------|
| admin    | admin123 | supervisor |
| tech1    | tech123  | technician |

## Deploying to Streamlit Cloud

1. Push this folder to a GitHub repo
2. Go to share.streamlit.io and connect the repo
3. Set the main file to `app.py`
4. Add a `DATABASE_URL` secret for persistent storage (e.g. Supabase PostgreSQL)
   - Without this, SQLite resets on each redeploy

## Roadmap

- **Phase 2:** Manual patient/specimen entry, demographic verification UI
- **Phase 3:** Advanced QC workflows, batch sign-off
- **Phase 4:** PDF report generation per patient
