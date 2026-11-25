from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from fpdf import FPDF

from utils.analytics import add_area_label


def _pdf_text(value: Any, max_length: int = 100) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text.encode("latin-1", errors="replace").decode("latin-1")[:max_length]


def _display(value: Any, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "Unavailable"
    if isinstance(value, float):
        return f"{value:,.1f}{suffix}"
    if isinstance(value, (int,)):
        return f"{value:,}{suffix}"
    return f"{value}{suffix}"


def build_pdf_report(
    households: pd.DataFrame,
    residents: pd.DataFrame,
    *,
    summary: dict[str, Any],
    insights: list[str],
    generated_on: date | None = None,
) -> bytes:
    """Create an in-memory PDF that keeps household and resident totals distinct."""
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_margins(15, 14, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_title("Barangay Household Dashboard Report")
    pdf.set_author("Barangay Household Dashboard")

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(
        0,
        10,
        "Barangay Household Dashboard",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", size=10)
    pdf.cell(
        0,
        7,
        f"Report generated: {(generated_on or date.today()).isoformat()}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        7,
        "Household population is the sum of recorded household member counts.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        7,
        f"Individual resident records included: {len(residents):,}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Household statistics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    metrics = (
        ("Household records", summary.get("total_households")),
        ("Recorded household members", summary.get("total_population")),
        ("Average recorded household size", summary.get("average_household_size")),
    )
    for label, value in metrics:
        pdf.cell(
            0,
            7,
            f"{label}: {_display(value)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(
        0,
        8,
        "Individual registry and source aggregate counts",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", size=10)
    resident_metrics = (
        ("Male residents in individual registry", summary.get("male_residents")),
        ("Female residents in individual registry", summary.get("female_residents")),
        ("Children in individual registry", summary.get("children")),
        (
            "Senior citizens (source household aggregates)",
            summary.get("senior_citizens"),
        ),
        ("PWD members (source household aggregates)", summary.get("pwd_residents")),
        ("Registered families", summary.get("registered_families")),
    )
    for label, value in resident_metrics:
        pdf.cell(
            0,
            7,
            f"{label}: {_display(value)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    if residents.empty:
        pdf.multi_cell(
            0,
            6,
            "The supplied dataset has no individual resident records. "
            "Resident demographic totals are unavailable and were not estimated.",
        )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Households by Purok / zone", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    if households.empty or not (
        "purok" in households.columns or "barangay" in households.columns
    ):
        pdf.cell(0, 6, "No household records match the selected filters.", new_x="LMARGIN", new_y="NEXT")
    else:
        area_data = add_area_label(households)
        household_counts = area_data.groupby("area_label", dropna=False).size()
        member_counts = area_data.groupby("area_label", dropna=False)[
            "household_members"
        ].sum(min_count=1)
        for area, count in household_counts.items():
            members = member_counts.get(area)
            member_text = _display(members)
            pdf.cell(
                0,
                6,
                f"{_pdf_text(area)}: {int(count):,} household(s), "
                f"{member_text} recorded members",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary of findings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    if insights:
        for insight in insights:
            pdf.multi_cell(0, 6, f"- {_pdf_text(insight)}")
    else:
        pdf.multi_cell(
            0,
            6,
            "No findings could be calculated for the selected filters.",
        )
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0,
        5,
        "Descriptive report only. The source project labels its bundled dataset as "
        "fictional demonstration data. Verify records and apply official criteria "
        "before making decisions.",
    )
    return bytes(pdf.output())
