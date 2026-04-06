"""
Shared helper: load a signal JSON and render its flags + analytical
summary as PDF body text or a markdown string.

Used by section builders (external, inflation, consumption, gdp) to
thread Layer-3 signal output into the PDF narrative.
"""

import json

from utils import SIGNALS_DIR, get_logger

log = get_logger("report.signal_text")


def load_signal(name: str) -> dict:
    """Return the signal dict for `name`, or {} if not available."""
    path = SIGNALS_DIR / f"signals_{name}.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Could not load signals_%s.json: %s", name, e)
        return {}


# ---------------------------------------------------------------------------
# Categorise flags by severity prefix
# ---------------------------------------------------------------------------

def _split_flags(flags: list[str]) -> tuple[list, list, list, list]:
    critical, warnings, positives, notes = [], [], [], []
    for f in flags:
        if f.startswith("CRITICAL:"):
            critical.append(f[len("CRITICAL:"):].strip())
        elif f.startswith("WARNING:"):
            warnings.append(f[len("WARNING:"):].strip())
        elif f.startswith("POSITIVE:"):
            positives.append(f[len("POSITIVE:"):].strip())
        else:
            notes.append(f.removeprefix("NOTE:").strip())
    return critical, warnings, positives, notes


# ---------------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------------

def render_signal_callout(pdf, sig: dict, label: str = "",
                          show_positive: bool = True,
                          max_flags: int = 4) -> None:
    """
    Append signal-derived analytical text to the current PDF section.

    Renders:
      • One-sentence signal summary
      • CRITICAL flags (always shown, styled as warnings)
      • WARNING flags (shown up to max_flags)
      • POSITIVE flags (shown when show_positive=True)
      • Connection to master variable (one line)
    """
    from report.build import _safe   # local import to avoid circular
    if not sig:
        return

    # Reset to left margin; compute explicit width to avoid fpdf2 zero-width edge case
    pdf.ln(0)
    pdf.set_x(pdf.l_margin)
    w = pdf.w - pdf.l_margin - pdf.r_margin

    summary   = sig.get("summary", "")
    flags     = sig.get("flags", [])
    conn      = sig.get("connection_to_master_variable", "")
    as_of     = sig.get("as_of_date", "")

    critical, warnings, positives, _ = _split_flags(flags)

    # Section sub-label
    if label:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(80, 80, 80)
        heading = f"Signal analysis{' -- ' + label if label else ''}"
        if as_of:
            heading += f" (as of {as_of})"
        pdf.set_x(pdf.l_margin)
        pdf.cell(w, 5, _safe(heading), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # Summary sentence
    if summary:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5, _safe(summary))
        pdf.ln(1)

    # CRITICAL + WARNING
    shown = 0
    for text in critical + warnings:
        if shown >= max_flags:
            break
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(160, 40, 40)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5, _safe(f"! {text}"))
        shown += 1

    # POSITIVE
    if show_positive:
        for text in positives:
            if shown >= max_flags:
                break
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(30, 120, 60)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(w, 5, _safe(f"+ {text}"))
            shown += 1

    # Master variable connection
    if conn and conn != "neutral":
        conn_text = {
            "positive": "Connection to master variable: POSITIVE -- supports real wage recovery.",
            "negative": "Connection to master variable: NEGATIVE -- constrains real wage recovery.",
        }.get(conn, "")
        if conn_text:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(w, 4.5, _safe(conn_text))

    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def render_signal_callout_md(sig: dict, label: str = "",
                             show_positive: bool = True,
                             max_flags: int = 4) -> str:
    """Return a markdown block with signal flags and summary."""
    if not sig:
        return ""

    summary  = sig.get("summary", "")
    flags    = sig.get("flags", [])
    conn     = sig.get("connection_to_master_variable", "")
    as_of    = sig.get("as_of_date", "")

    critical, warnings, positives, _ = _split_flags(flags)

    lines = []
    heading = f"**Signal{': ' + label if label else ''}**"
    if as_of:
        heading += f" *(as of {as_of})*"
    lines.append(heading)

    if summary:
        lines.append(f"*{summary}*")

    shown = 0
    for text in critical:
        if shown >= max_flags:
            break
        lines.append(f"- **CRITICAL:** {text}")
        shown += 1
    for text in warnings:
        if shown >= max_flags:
            break
        lines.append(f"- **WARNING:** {text}")
        shown += 1
    if show_positive:
        for text in positives:
            if shown >= max_flags:
                break
            lines.append(f"- POSITIVE: {text}")
            shown += 1

    if conn and conn != "neutral":
        conn_label = "POSITIVE" if conn == "positive" else "NEGATIVE"
        lines.append(f"- *Master variable connection: {conn_label}*")

    return "\n".join(lines) + "\n"
