"""Shared PDF base class and Latin-1 sanitiser used by all report modules."""

from pathlib import Path

import pandas as pd
from fpdf import FPDF, XPos, YPos


def _safe(text: str) -> str:
    """Replace characters outside Latin-1 with safe ASCII equivalents."""
    return (text
            .replace("—", "--")
            .replace("–", "-")
            .replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("→", "->")
            .replace("•", "*")
            .encode("latin-1", errors="replace").decode("latin-1"))


class ArgentinaPDF(FPDF):
    MARGIN = 15
    PAGE_W = 210

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Argentina Macro Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 80, 160)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(20, 80, 160)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, _safe(text))
        self.ln(2)

    def add_chart(self, img_path: str | None, caption: str = ""):
        if not img_path or not Path(img_path).exists():
            self.body_text("[Chart unavailable]")
            return
        avail_w = self.PAGE_W - 2 * self.MARGIN
        img_h = avail_w * 0.45
        if self.get_y() + img_h + 10 > self.h - 20:
            self.add_page()
        self.image(img_path, x=self.MARGIN, w=avail_w)
        if caption:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, caption, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            self.set_text_color(0, 0, 0)
        self.ln(3)

    def add_table(self, df: pd.DataFrame, cols: list[str], fmt: dict | None = None,
                  title: str = ""):
        fmt = fmt or {}
        subset = df[cols].dropna().tail(12).reset_index(drop=True)
        if subset.empty:
            return
        if title:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(60, 60, 60)
            self.cell(0, 6, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)
        avail_w = self.PAGE_W - 2 * self.MARGIN
        col_w = avail_w / len(cols)
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = c.replace("_", " ").replace("usd bn", "(USD bn)").replace("pct", "%").title()
            self.cell(col_w, 6, label, border=0, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8.5)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or (hasattr(v, "strftime")):
                    try:    cell_str = pd.to_datetime(v).strftime("%Y-%m-%d")
                    except: cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:    cell_str = f.format(v)
                    except: cell_str = str(v)
                self.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
            self.ln()
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def add_table_n(self, df: pd.DataFrame, cols: list[str],
                    fmt: dict | None = None, title: str = "", limit: int = 24):
        fmt = fmt or {}
        subset = df[cols].dropna(how="all").tail(limit).reset_index(drop=True)
        if subset.empty:
            return
        if title:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(60, 60, 60)
            self.cell(0, 6, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)
        avail_w = self.PAGE_W - 2 * self.MARGIN
        col_w = avail_w / len(cols)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = (c.replace("_", " ").replace("usd bn", "(USD bn)")
                      .replace("pct", "%").replace("yoy", "YoY").title())
            self.cell(col_w, 6, _safe(label), border=0, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or hasattr(v, "strftime"):
                    try:    cell_str = pd.to_datetime(v).strftime("%b %Y")
                    except: cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:    cell_str = f.format(v)
                    except: cell_str = str(v)
                if c != "date":
                    try:
                        num = float(v)
                        self.set_text_color(0, 110, 50) if num > 0 else \
                            (self.set_text_color(180, 0, 0) if num < 0 else
                             self.set_text_color(80, 80, 80))
                    except (TypeError, ValueError):
                        self.set_text_color(40, 40, 40)
                self.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
                self.set_text_color(40, 40, 40)
            self.ln()
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def subsection(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 140)
        self.cell(0, 7, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def note(self, text: str):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.set_x(self.l_margin)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4.5, _safe(text))
        self.set_text_color(0, 0, 0)
        self.ln(2)
