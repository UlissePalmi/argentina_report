"""
Weekly diff engine — persists headline metrics from each pipeline run
and surfaces what changed vs the prior run.

Files:
  data/signals/history.jsonl  -- one JSON line per run (append-only)

Usage:
  from report.weekly_diff import snapshot, whats_changed, format_diff_md
  snapshot()              # call after signals are computed
  diff = whats_changed()  # call before report generation
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from utils import SIGNALS_DIR, get_logger

log = get_logger("report.weekly_diff")

HISTORY_FILE = SIGNALS_DIR / "history.jsonl"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _flatten(sig: dict, prefix: str) -> dict[str, Any]:
    """Flatten a signal dict into a dotted-key dict suitable for a history row."""
    out: dict[str, Any] = {}

    # Universal fields
    out[f"{prefix}.as_of_date"]  = sig.get("as_of_date")
    out[f"{prefix}.trend"]       = sig.get("trend")
    out[f"{prefix}.connection"]  = sig.get("connection_to_master_variable")
    out[f"{prefix}.data_quality"] = sig.get("data_quality")

    # All scalar metrics
    for k, v in (sig.get("metrics") or {}).items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[f"{prefix}.metrics.{k}"] = v

    # Master-specific sub-dicts
    if prefix == "signals_master":
        out[f"{prefix}.verdict"] = sig.get("verdict")
        for sub in ("master_variable", "enablers", "drivers", "accelerators"):
            for k, v in (sig.get(sub) or {}).items():
                if isinstance(v, (int, float, str, bool)) or v is None:
                    out[f"{prefix}.{sub}.{k}"] = v
        for metric_name, sc in (sig.get("scorecard") or {}).items():
            safe = (metric_name.lower()
                    .replace(" ", "_").replace("(", "").replace(")", "")
                    .replace("%", "pct").replace("$", "").replace("/", "_"))
            out[f"{prefix}.scorecard.{safe}.signal"] = sc.get("signal")
            out[f"{prefix}.scorecard.{safe}.value"]  = sc.get("value")

    return out


def _extract_row() -> dict[str, Any]:
    """Extract headline metrics from all current signal JSON files into a flat dict."""
    row: dict[str, Any] = {
        "run_date": date.today().isoformat(),
        "run_ts":   datetime.utcnow().isoformat(timespec="seconds"),
    }
    for path in sorted(SIGNALS_DIR.glob("signals_*.json")):
        try:
            sig = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not read %s: %s", path.name, e)
            continue
        row.update(_flatten(sig, path.stem))
    return row


def _load_history(n: int = 0) -> list[dict]:
    """Load last n rows from history.jsonl (0 = all)."""
    if not HISTORY_FILE.exists():
        return []
    rows = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows[-n:] if n else rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def snapshot() -> None:
    """Append a snapshot of today's headline metrics to history.jsonl."""
    row = _extract_row()
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log.info("Snapshot written to %s (run_date=%s)", HISTORY_FILE.name, row["run_date"])


def whats_changed() -> dict[str, Any]:
    """Compare the two most recent snapshots and return metric deltas.

    Returns {} if fewer than two snapshots exist.
    Returns:
        {
          "current_date": "2026-05-27",
          "prior_date":   "2026-05-20",
          "changes": {
            "signals_inflation.metrics.cpi_mom_latest": {
              "current": 3.38, "prior": 3.7, "delta": -0.32
            },
            ...
          }
        }
    """
    rows = _load_history(n=2)
    if len(rows) < 2:
        log.info("Fewer than 2 snapshots — no diff available yet.")
        return {}

    current, prior = rows[-1], rows[-2]
    changes: dict[str, Any] = {}

    import math

    def _is_nan(v: Any) -> bool:
        return isinstance(v, float) and math.isnan(v)

    all_keys = set(current.keys()) | set(prior.keys())
    for key in sorted(all_keys):
        if key in ("run_date", "run_ts"):
            continue
        c_val = current.get(key)
        p_val = prior.get(key)
        # Treat NaN == NaN as no change
        if _is_nan(c_val) and _is_nan(p_val):
            continue
        if c_val == p_val:
            continue
        delta = None
        if (isinstance(c_val, (int, float)) and not _is_nan(c_val)
                and isinstance(p_val, (int, float)) and not _is_nan(p_val)):
            delta = round(c_val - p_val, 4)
        changes[key] = {"current": c_val, "prior": p_val, "delta": delta}

    return {
        "current_date": current.get("run_date"),
        "prior_date":   prior.get("run_date"),
        "changes":      changes,
    }


def format_diff_md(diff: dict) -> str:
    """Render a whats_changed() dict as a markdown 'What Changed This Week' block."""
    if not diff or not diff.get("changes"):
        return ""

    current_date = diff.get("current_date", "?")
    prior_date   = diff.get("prior_date",   "?")
    changes      = diff["changes"]

    # Group by domain prefix
    groups: dict[str, list[str]] = {}
    for key, vals in changes.items():
        domain = key.split(".")[0].replace("signals_", "").capitalize()
        c = vals["current"]
        p = vals["prior"]
        d = vals["delta"]
        metric = ".".join(key.split(".")[1:])
        if d is not None:
            line = f"- **{metric}**: {p} -> {c} ({d:+.2f})"
        else:
            line = f"- **{metric}**: {p} -> {c}"
        groups.setdefault(domain, []).append(line)

    lines = [f"## What Changed ({prior_date} -> {current_date})\n"]
    for domain, items in sorted(groups.items()):
        lines.append(f"### {domain}")
        lines.extend(items)
        lines.append("")

    return "\n".join(lines)
