"""
SVAR pipeline orchestrator — Layer 3.5.

Runs the full SVAR pipeline:
  1. data_prep.py  — align panel, ADF tests, save svar_input.csv
  2. model.py      — fit VAR, Cholesky identification, IRF + FEVD, save JSON
  3. charts.py     — generate PNG charts

Call run_svar() from main.py after signals layer.
"""

from __future__ import annotations

from pathlib import Path

from utils import get_logger

log = get_logger("svar.run")

SVAR_DIR = Path(__file__).parent.parent / "data" / "svar"


def run_svar() -> bool:
    """
    Orchestrate the full SVAR pipeline.
    Returns True if completed successfully, False if skipped.
    """
    SVAR_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1 — data prep
    log.info("SVAR [1/3] Preparing data panel...")
    try:
        from svar.data_prep import prepare_data
        df = prepare_data()
    except Exception as exc:
        log.error("SVAR data_prep failed: %s", exc)
        return False

    if df is None or df.empty:
        log.warning("SVAR: no data available. Pipeline skipped.")
        return False

    # Step 2 — model estimation
    log.info("SVAR [2/3] Fitting VAR model...")
    try:
        from svar.model import fit_model
        result = fit_model(df)
    except Exception as exc:
        log.error("SVAR model fitting failed: %s", exc)
        return False

    if result is None:
        log.warning("SVAR: model fit returned None. Pipeline skipped.")
        return False

    # Step 3 — charts
    log.info("SVAR [3/3] Generating charts...")
    try:
        from svar.charts import build_charts
        paths = build_charts()
        log.info("SVAR: %d charts generated.", len(paths))
    except Exception as exc:
        log.error("SVAR chart generation failed: %s", exc)
        # Charts failing doesn't invalidate the model results

    log.info("SVAR pipeline complete. Outputs in data/svar/")
    return True
