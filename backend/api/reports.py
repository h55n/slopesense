"""PDF report generation for district-level landslide risk briefings."""

from datetime import datetime, timezone
from io import BytesIO
from typing import List


async def generate_district_report(
    district_code: str,
    district_name: str,
    alerts: List[dict],
    run_timestamp: datetime,
) -> bytes:
    """Generate a compact NDMA-style district PDF report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=f"SlopeSense {district_code} Report",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("National Disaster Management Authority", styles["Title"]))
    story.append(Paragraph("SlopeSense District Landslide Risk Intelligence Report", styles["Heading2"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"District: <b>{district_name}</b> ({district_code.upper()})", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    story.append(Paragraph(f"Model run: {run_timestamp.isoformat()}", styles["Normal"]))
    story.append(Paragraph("Model version: v0.1", styles["Normal"]))
    story.append(Spacer(1, 12))

    max_fpi = max((float(alert.get("fpi_score", 0)) for alert in alerts), default=0)
    story.append(
        Paragraph(
            f"Overview: {len(alerts)} active block alerts. Maximum FPI: {max_fpi:.0%}.",
            styles["Heading3"],
        )
    )

    rows = [["Block", "Tier", "FPI", "95% CI", "Dominant Signal"]]
    for alert in sorted(alerts, key=lambda item: item.get("fpi_score", 0), reverse=True)[:20]:
        rows.append(
            [
                alert.get("block_name") or alert.get("block_code") or "Unknown",
                alert.get("tier") or alert.get("alert_tier") or "NORMAL",
                f"{float(alert.get('fpi_score', 0)):.0%}",
                f"{float(alert.get('fpi_ci_lower', 0)):.0%}-{float(alert.get('fpi_ci_upper', 0)):.0%}",
                _dominant_signal(alert),
            ]
        )

    table = Table(rows, repeatRows=1, colWidths=[120, 82, 50, 70, 170])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Recommended Actions", styles["Heading3"]))
    story.append(
        Paragraph(
            "WATCH: monitor rainfall and vulnerable slopes. WARNING: alert DDMA, "
            "prepare shelters and field teams. EMERGENCY: initiate evacuation planning "
            "for exposed settlements and coordinate SDRF/NDRF support.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph("Confidence and Data Sources", styles["Heading3"]))
    story.append(
        Paragraph(
            "FPI combines NASA GPM rainfall, SMAP soil moisture, Copernicus DEM, "
            "Sentinel-2 vegetation change, NDMA susceptibility priors, and forecast rainfall. "
            "Alerts with wide confidence intervals are suppressed to reduce false positives.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 24))
    story.append(Paragraph("Digital signature: ______________________________", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def _dominant_signal(alert: dict) -> str:
    signals = alert.get("dominant_signals") or []
    if signals and isinstance(signals, list):
        return str(signals[0].get("signal", "unknown")).replace("_", " ")
    return str(alert.get("dominant_signal", "unknown")).replace("_", " ")
