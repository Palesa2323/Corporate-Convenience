
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def create_pdf_styles():
    """Create consistent styles for the business report."""

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#263238"),
        alignment=TA_CENTER,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#34495E"),
        spaceBefore=14,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    ))

    return styles

def create_report_table(headers, rows, column_widths=None):
    """Create a consistently styled table for the PDF report."""

    table_data = [headers] + rows

    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5D8DC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F2F4F4"),
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    return table


from xml.sax.saxutils import escape


def generate_pdf_report(report, output_directory="reports"):
    """Generate a PDF business report from the report data."""

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)

    department = report["department"]
    period = report["reporting_period"]

    start_date = period["start_date"]
    end_date = period["end_date"]

    safe_department = department.replace(" ", "_")

    filename = (
        f"business_report_{safe_department}_"
        f"{start_date}_to_{end_date}.pdf"
    )

    pdf_path = output_path / filename

    styles = create_pdf_styles()

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    content = []

    # 1. Report heading
    content.append(
        Paragraph(
            escape(report["report_title"]),
            styles["ReportTitle"],
        )
    )

    content.append(
        Paragraph(
            f"<b>Department:</b> {escape(department)}",
            styles["ReportBody"],
        )
    )

    content.append(
        Paragraph(
            f"<b>Reporting Period:</b> "
            f"{escape(start_date)} to {escape(end_date)}",
            styles["ReportBody"],
        )
    )

    content.append(Spacer(1, 12))

    # 2. Executive summary
    content.append(
        Paragraph("Executive Summary", styles["SectionHeading"])
    )

    content.append(
        Paragraph(
            escape(report["executive_summary"]),
            styles["ReportBody"],
        )
    )

    # 3. Ticket statistics
    statistics = report["statistics"]

    content.append(
        Paragraph("Ticket Statistics", styles["SectionHeading"])
    )

    statistics_rows = [
        ["Total Tickets", statistics["total_tickets"]],
        ["Resolved Tickets", statistics["resolved_tickets"]],
        ["Open Tickets", statistics["open_tickets"]],
        ["In Progress", statistics["in_progress_tickets"]],
        ["Outstanding Tickets", statistics["outstanding_tickets"]],
        ["Resolution Rate", f'{statistics["resolution_rate"]}%'],
    ]

    content.append(
        create_report_table(
            ["Metric", "Value"],
            statistics_rows,
            [110 * mm, 60 * mm],
        )
    )

    # 4. Department performance
    content.append(
        Paragraph("Department Performance", styles["SectionHeading"])
    )

    department_rows = []

    for item in report["department_performance"]:
        department_rows.append([
            item["department"],
            item["total_tickets"],
            item["resolved_tickets"],
            f'{item["resolution_rate"]}%',
        ])

    content.append(
        create_report_table(
            ["Department", "Total Tickets", "Resolved", "Resolution Rate"],
            department_rows,
            [45 * mm, 40 * mm, 35 * mm, 50 * mm],
        )
    )

    # 5. Historical comparison
    content.append(
        Paragraph("Historical Comparison", styles["SectionHeading"])
    )

    comparison = report["historical_comparison"]
    changes = comparison["changes"]

    historical_rows = []

    metric_labels = {
        "total_tickets": "Total Tickets",
        "resolved_tickets": "Resolved Tickets",
        "open_tickets": "Open Tickets",
        "in_progress_tickets": "In Progress",
        "resolution_rate": "Resolution Rate",
    }

    for metric, label in metric_labels.items():
        change = changes[metric]

        if metric == "resolution_rate":
            difference = f'{change["difference"]:+.2f} pp'
            percentage = "Not applicable"
        else:
            difference = f'{change["difference"]:+}'
            percentage = (
                f'{change["percentage_change"]:+.2f}%'
                if change["percentage_change"] is not None
                else "N/A"
            )

        historical_rows.append([
            label,
            change["current"],
            change["previous"],
            difference,
            percentage,
        ])

    content.append(
        Paragraph(
            f'Previous Period: {comparison["previous_period"]["start_date"]} '
            f'to {comparison["previous_period"]["end_date"]}',
            styles["ReportBody"],
        )
    )

    content.append(
        create_report_table(
            ["Metric", "Current", "Previous", "Difference", "Change"],
            historical_rows,
            [42 * mm, 28 * mm, 28 * mm, 32 * mm, 40 * mm],
        )
    )

    # 6. Daily ticket trends
    content.append(
        Paragraph("Daily Ticket Trends", styles["SectionHeading"])
    )

    daily_rows = [
        [item["ticket_date"], item["total_tickets"]]
        for item in report["daily_trends"]
    ]

    if daily_rows:
        content.append(
            create_report_table(
                ["Date", "Tickets Received"],
                daily_rows,
                [85 * mm, 85 * mm],
            )
        )
    else:
        content.append(
            Paragraph("No daily ticket data available.", styles["ReportBody"])
        )

    # 7. Insights
    content.append(
        Paragraph("Key Insights", styles["SectionHeading"])
    )

    for insight in report["insights"]:
        content.append(
            Paragraph(
                f"• {escape(str(insight))}",
                styles["ReportBody"],
            )
        )

    # 8. Recommendations
    content.append(
        Paragraph("Recommendations", styles["SectionHeading"])
    )

    for recommendation in report["recommendations"]:
        content.append(
            Paragraph(
                f"• {escape(str(recommendation))}",
                styles["ReportBody"],
            )
        )

    # Build the final PDF
    document.build(content)

    return pdf_path


