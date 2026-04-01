"""
VCF Annotation Page
Upload a VCF file → annotate with Ensembl VEP, CancerVar, and ClinVar → 
display interactive results table with CSV download.
"""

import streamlit as st
import pandas as pd
import tempfile
import json
import os
from pathlib import Path

from utils.auth import require_auth, current_user_id
from utils.audit import log_action

# ClinVar local file — place your clinvar.vcf.gz here
CLINVAR_PATH = Path(__file__).parent.parent / "assets" / "clinvar.vcf.gz"


def show():
    require_auth()

    st.markdown("## 🧬 VCF Annotation")
    st.markdown(
        "Upload a `.vcf` file to annotate variants with "
        "**Ensembl VEP**, **CancerVar**, and **ClinVar**."
    )
    st.divider()

    # --- ClinVar availability notice ---
    clinvar_available = CLINVAR_PATH.exists()
    if clinvar_available:
        st.success(f"✅ ClinVar database loaded ({CLINVAR_PATH.name})")
    else:
        st.warning(
            "⚠️ ClinVar database not found at `assets/clinvar.vcf.gz`. "
            "VEP + CancerVar annotations will still run. "
            "Add the file to enable ClinVar lookups."
        )

    st.divider()

    # --- File upload ---
    uploaded_vcf = st.file_uploader(
        "Upload VCF file",
        type=["vcf"],
        help="Standard VCF format. Multi-allelic lines will be split automatically."
    )

    if uploaded_vcf is None:
        _render_format_guide()
        return

    st.markdown(f"**File:** `{uploaded_vcf.name}` ({uploaded_vcf.size / 1024:.1f} KB)")

    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.number_input(
            "VEP batch size", min_value=10, max_value=200, value=50,
            help="Variants sent per API request. Reduce if you hit timeouts."
        )
    with col2:
        genome_build = st.selectbox("Genome build", ["GRCh38", "GRCh37"])

    st.divider()

    if st.button("▶️ Run Annotation", type="primary", use_container_width=True):
        _run_annotation(uploaded_vcf, batch_size, genome_build, clinvar_available)


def _run_annotation(uploaded_vcf, batch_size, genome_build, clinvar_available):
    """Write VCF to temp file, run annotation, display results."""

    from utils.vcfAnnotateCloud import annotate_vcf_to_json
    from utils.clinvar_lookup import get_clinsig_pure_python

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="wb") as tmp_vcf:
        tmp_vcf.write(uploaded_vcf.read())
        tmp_vcf_path = tmp_vcf.name

    tmp_json_path = tmp_vcf_path.replace(".vcf", "_annotated.json")

    # --- Progress UI ---
    st.markdown("### ⏳ Annotation in Progress")
    status_box  = st.empty()
    progress_bar = st.progress(0)
    log_box     = st.empty()

    try:
        # Count variants first for progress tracking
        status_box.info("Parsing VCF...")
        from utils.vcfAnnotateCloud import parse_vcf
        variants = list(parse_vcf(tmp_vcf_path))
        total = len(variants)

        if total == 0:
            st.error("No variants found in the uploaded VCF. Check the file format.")
            return

        status_box.info(f"Found **{total}** variant(s). Starting VEP annotation...")
        progress_bar.progress(10)

        # Run annotation
        annotate_vcf_to_json(
            tmp_vcf_path,
            tmp_json_path,
            batch_size=batch_size,
            genome_build=genome_build,
        )
        progress_bar.progress(70)

        # Load results
        with open(tmp_json_path) as f:
            records = json.load(f)

        progress_bar.progress(80)
        status_box.info("Running ClinVar lookups...")

        # ClinVar enrichment
        if clinvar_available:
            enriched = []
            for i, rec in enumerate(records):
                clinsig = get_clinsig_pure_python(
                    rec["chrom"], rec["pos"], rec["ref"], rec["alt"],
                    vcf_path=str(CLINVAR_PATH)
                )
                rec["clinsig"]      = clinsig["clinical_significance"] if clinsig else None
                rec["review_status"] = clinsig["review_status"]         if clinsig else None
                rec["clinvar_id"]   = clinsig["variation_id"]           if clinsig else None
                enriched.append(rec)
                progress_bar.progress(80 + int(18 * (i + 1) / max(len(records), 1)))
            records = enriched
        else:
            for rec in records:
                rec["clinsig"]       = "N/A (no ClinVar DB)"
                rec["review_status"] = None
                rec["clinvar_id"]    = None

        progress_bar.progress(100)
        status_box.success(f"✅ Annotation complete — {len(records)} variant(s) annotated.")
        log_box.empty()

        log_action(
            "vcf.annotate",
            detail={
                "filename": uploaded_vcf.name,
                "variants": total,
                "clinvar": clinvar_available,
                "build": genome_build,
            }
        )

        _render_results(records, uploaded_vcf.name)

    except Exception as e:
        status_box.error(f"Annotation failed: {e}")
        st.exception(e)

    finally:
        for p in [tmp_vcf_path, tmp_json_path]:
            try:
                os.unlink(p)
            except Exception:
                pass


def _render_results(records: list, source_filename: str):
    """Display results as an interactive filterable table with CSV download."""

    st.divider()
    st.markdown("### 📊 Annotation Results")

    df = pd.DataFrame(records)

    # Friendly column rename
    col_map = {
        "chrom":          "Chr",
        "pos":            "Position",
        "ref":            "Ref",
        "alt":            "Alt",
        "gene_symbol":    "Gene",
        "transcript_id":  "Transcript",
        "hgvsc":          "HGVSc",
        "hgvsp":          "HGVSp",
        "consequence":    "Consequence",
        "cancervar":      "CancerVar",
        "opai":           "OPAI",
        "clinsig":        "ClinVar Significance",
        "review_status":  "ClinVar Review Status",
        "clinvar_id":     "ClinVar ID",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # --- Filters ---
    with st.expander("🔍 Filter results", expanded=False):
        fc1, fc2, fc3 = st.columns(3)

        genes = ["All"] + sorted(df["Gene"].dropna().unique().tolist()) if "Gene" in df.columns else ["All"]
        sel_gene = fc1.selectbox("Gene", genes)

        consequences = ["All"] + sorted(df["Consequence"].dropna().unique().tolist()) if "Consequence" in df.columns else ["All"]
        sel_consequence = fc2.selectbox("Consequence", consequences)

        if "ClinVar Significance" in df.columns:
            clinsigs = ["All"] + sorted(df["ClinVar Significance"].dropna().unique().tolist())
            sel_clinsig = fc3.selectbox("ClinVar Significance", clinsigs)
        else:
            sel_clinsig = "All"

    filtered = df.copy()
    if sel_gene != "All":
        filtered = filtered[filtered["Gene"] == sel_gene]
    if sel_consequence != "All":
        filtered = filtered[filtered["Consequence"] == sel_consequence]
    if sel_clinsig != "All" and "ClinVar Significance" in filtered.columns:
        filtered = filtered[filtered["ClinVar Significance"] == sel_clinsig]

    st.markdown(f"Showing **{len(filtered)}** of **{len(df)}** variant(s)")

    # Colour-code ClinVar significance
    def highlight_clinsig(val):
        if not isinstance(val, str):
            return ""
        v = val.lower()
        if "pathogenic" in v and "likely" not in v:
            return "background-color: #f8d7da; color: #842029;"
        if "likely_pathogenic" in v or "likely pathogenic" in v:
            return "background-color: #fde8d8; color: #7d3c10;"
        if "benign" in v:
            return "background-color: #d1e7dd; color: #0a3622;"
        if "uncertain" in v or "vus" in v:
            return "background-color: #fff3cd; color: #664d03;"
        return ""

    styled = filtered.style.applymap(
        highlight_clinsig,
        subset=["ClinVar Significance"] if "ClinVar Significance" in filtered.columns else []
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # --- CSV download ---
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    out_name  = source_filename.replace(".vcf", "_annotated.csv")

    st.download_button(
        label="⬇️ Download results as CSV",
        data=csv_bytes,
        file_name=out_name,
        mime="text/csv",
        use_container_width=True,
    )


def _render_format_guide():
    """Show expected VCF format when no file is uploaded."""
    with st.expander("ℹ️ Expected VCF format", expanded=False):
        st.markdown("""
Standard VCF v4.x format. The file must have at least these columns:

| #CHROM | POS | ID | REF | ALT | QUAL | FILTER | INFO |
|--------|-----|----|-----|-----|------|--------|------|
| 1 | 45331556 | . | C | T | . | . | . |
| 17 | 7674220 | . | G | A | . | . | . |

- `chr` prefix is optional (both `chr1` and `1` are accepted)
- Multi-allelic ALT values (e.g. `A,T`) are split automatically
- Header lines starting with `#` are ignored
        """)
