
from datetime import date, timedelta

from backend.database import get_connection, DEPARTMENTS


def get_ticket_statistics(start_date, end_date, department="All"):
    """Retrieve and calculate ticket statistics for a reporting period."""

    query = """
        SELECT
            COUNT(*) AS total_tickets,

            SUM(CASE
                WHEN status = 'Resolved' THEN 1
                ELSE 0
            END) AS resolved_tickets,

            SUM(CASE
                WHEN status = 'Open' THEN 1
                ELSE 0
            END) AS open_tickets,

            SUM(CASE
                WHEN status = 'In Progress' THEN 1
                ELSE 0
            END) AS in_progress_tickets

        FROM tickets

        WHERE date(created_at) BETWEEN ? AND ?
    """

    parameters = [start_date, end_date]

    if department != "All":
        if department not in DEPARTMENTS:
            raise ValueError("Invalid department selected.")

        query += " AND department = ?"
        parameters.append(department)

    with get_connection() as connection:
        result = connection.execute(
            query, parameters
        ).fetchone()

    total = result["total_tickets"] or 0
    resolved = result["resolved_tickets"] or 0
    opened = result["open_tickets"] or 0
    in_progress = result["in_progress_tickets"] or 0

    resolution_rate = (
        (resolved / total) * 100 if total else 0
    )

    return {
        "total_tickets": total,
        "resolved_tickets": resolved,
        "open_tickets": opened,
        "in_progress_tickets": in_progress,
        "outstanding_tickets": opened + in_progress,
        "resolution_rate": round(resolution_rate, 2)
    }


def get_department_performance(start_date, end_date):
    """Calculate ticket performance across all departments."""

    performance = []

    with get_connection() as connection:
        for department in DEPARTMENTS:

            result = connection.execute("""
                SELECT
                    COUNT(*) AS total,

                    SUM(CASE
                        WHEN status = 'Resolved' THEN 1
                        ELSE 0
                    END) AS resolved

                FROM tickets

                WHERE department = ?
                AND date(created_at) BETWEEN ? AND ?

            """, (department, start_date, end_date)).fetchone()

            total = result["total"] or 0
            resolved = result["resolved"] or 0

            rate = (
                (resolved / total) * 100
                if total else 0
            )

            performance.append({
                "department": department,
                "total_tickets": total,
                "resolved_tickets": resolved,
                "resolution_rate": round(rate, 2)
            })

    return performance


def get_daily_trends(start_date, end_date, department="All"):
    """Retrieve daily ticket volumes for trend analysis."""

    query = """
        SELECT
            date(created_at) AS ticket_date,
            COUNT(*) AS total_tickets

        FROM tickets

        WHERE date(created_at) BETWEEN ? AND ?
    """

    parameters = [start_date, end_date]

    if department != "All":
        if department not in DEPARTMENTS:
            raise ValueError("Invalid department selected.")

        query += " AND department = ?"
        parameters.append(department)

    query += """
        GROUP BY date(created_at)
        ORDER BY ticket_date
    """

    with get_connection() as connection:
        rows = connection.execute(
            query, parameters
        ).fetchall()

    return [dict(row) for row in rows]


def generate_executive_summary(statistics, department="All"):
    """Convert business statistics into a readable summary."""

    total = statistics["total_tickets"]
    resolved = statistics["resolved_tickets"]
    outstanding = statistics["outstanding_tickets"]
    rate = statistics["resolution_rate"]

    if total == 0:
        return (
            f"No tickets were recorded for {department} "
            "during the selected reporting period. "
            "There is insufficient data to assess performance."
        )

    summary = (
        f"During the reporting period, {department} received "
        f"{total} tickets. The organisation resolved "
        f"{resolved} tickets, achieving a resolution rate "
        f"of {rate}%. There are currently {outstanding} "
        "tickets remaining outstanding."
    )

    return summary


def generate_recommendations(statistics, performance):
    """Generate recommendations based on actual business data."""

    recommendations = []

    if statistics["total_tickets"] == 0:
        return ["Collect more ticket data before assessing performance."]

    if statistics["outstanding_tickets"] > 0:
        recommendations.append(
            "Review outstanding tickets and prioritise older "
            "or urgent requests."
        )

    if statistics["resolution_rate"] < 70:
        recommendations.append(
            "Investigate factors affecting ticket resolution "
            "and consider allocating additional support resources."
        )

    if statistics["resolution_rate"] >= 90:
        recommendations.append(
            "Maintain current support processes and identify "
            "practices that can be replicated across departments."
        )

    busiest = max(
        performance,
        key=lambda item: item["total_tickets"]
    )

    if busiest["total_tickets"] > 0:
        recommendations.append(
            f"{busiest['department']} received the highest "
            "number of tickets. Monitor its workload and "
            "resource requirements."
        )

    return recommendations


def compare_reporting_periods(start_date, end_date, department="All"):
    """Compare the selected reporting period with the previous equivalent period."""

    current_start = date.fromisoformat(start_date)
    current_end = date.fromisoformat(end_date)

    if current_start > current_end:
        raise ValueError("Start date cannot be after end date.")

    # Calculate the length of the reporting period.
    period_length = (current_end - current_start).days + 1

    # Calculate the previous equivalent period.
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    # Retrieve statistics for both periods.
    current_statistics = get_ticket_statistics(
        start_date,
        end_date,
        department
    )

    previous_statistics = get_ticket_statistics(
        previous_start.isoformat(),
        previous_end.isoformat(),
        department
    )

    # Compare important business metrics.
    metrics = [
        "total_tickets",
        "resolved_tickets",
        "open_tickets",
        "in_progress_tickets",
        "resolution_rate"
    ]

    changes = {}

    for metric in metrics:
        current_value = current_statistics[metric]
        previous_value = previous_statistics[metric]

        difference = current_value - previous_value

        percentage_change = (
            round((difference / previous_value) * 100, 2)
            if previous_value != 0
            else None
        )

        changes[metric] = {
            "current": current_value,
            "previous": previous_value,
            "difference": difference,
            "percentage_change": percentage_change
        }

    return {
        "current_period": {
            "start_date": start_date,
            "end_date": end_date,
            "statistics": current_statistics
        },
        "previous_period": {
            "start_date": previous_start.isoformat(),
            "end_date": previous_end.isoformat(),
            "statistics": previous_statistics
        },
        "changes": changes
    }


def generate_historical_insights(comparison):
    """Identify important changes between reporting periods."""

    current = comparison["current_period"]["statistics"]
    previous = comparison["previous_period"]["statistics"]

    insights = []

    # Ticket volume analysis
    ticket_difference = (
        current["total_tickets"] - previous["total_tickets"]
    )

    if ticket_difference > 0:
        insights.append(
            f"Ticket volume increased by {ticket_difference} "
            "compared with the previous reporting period."
        )
    elif ticket_difference < 0:
        insights.append(
            f"Ticket volume decreased by {abs(ticket_difference)} "
            "compared with the previous reporting period."
        )
    else:
        insights.append(
            "Ticket volume remained unchanged compared "
            "with the previous reporting period."
        )

    # Resolution performance analysis
    rate_difference = (
        current["resolution_rate"] - previous["resolution_rate"]
    )

    if rate_difference > 0:
        insights.append(
            f"The resolution rate improved by "
            f"{rate_difference:.2f} percentage points."
        )
    elif rate_difference < 0:
        insights.append(
            f"The resolution rate declined by "
            f"{abs(rate_difference):.2f} percentage points."
        )
    else:
        insights.append(
            "The resolution rate remained unchanged."
        )

    # Outstanding ticket analysis
    outstanding_difference = (
        current["outstanding_tickets"]
        - previous["outstanding_tickets"]
    )

    if outstanding_difference > 0:
        insights.append(
            f"Outstanding tickets increased by "
            f"{outstanding_difference}."
        )
    elif outstanding_difference < 0:
        insights.append(
            f"Outstanding tickets decreased by "
            f"{abs(outstanding_difference)}."
        )
    else:
        insights.append(
            "The number of outstanding tickets remained unchanged."
        )

    # Resolved ticket analysis
    resolved_difference = (
        current["resolved_tickets"]
        - previous["resolved_tickets"]
    )

    if resolved_difference > 0:
        insights.append(
            f"The organisation resolved "
            f"{resolved_difference} more tickets."
        )
    elif resolved_difference < 0:
        insights.append(
            f"The organisation resolved "
            f"{abs(resolved_difference)} fewer tickets."
        )
    else:
        insights.append(
            "The number of resolved tickets remained unchanged."
        )

    return insights


def generate_historical_recommendations(comparison):
    """Generate recommendations using historical performance."""

    current = comparison["current_period"]["statistics"]
    previous = comparison["previous_period"]["statistics"]

    recommendations = []

    if current["total_tickets"] == 0:
        return [
            "Collect additional ticket records before making "
            "business performance recommendations."
        ]

    if current["outstanding_tickets"] > previous["outstanding_tickets"]:
        recommendations.append(
            "Investigate the increase in outstanding tickets "
            "and prioritise unresolved requests."
        )

    if current["resolution_rate"] < previous["resolution_rate"]:
        recommendations.append(
            "Review the factors contributing to the decline "
            "in resolution performance."
        )

    if current["resolved_tickets"] < previous["resolved_tickets"]:
        recommendations.append(
            "Evaluate staffing levels and ticket handling "
            "processes to improve resolution output."
        )

    if current["total_tickets"] > previous["total_tickets"]:
        recommendations.append(
            "Monitor the increase in ticket demand and ensure "
            "support resources are sufficient."
        )

    if not recommendations:
        recommendations.append(
            "Maintain current support processes and continue "
            "monitoring business performance."
        )

    return recommendations


def generate_business_report(start_date, end_date, department="All"):
    """Assemble all reporting data into one business report."""

    # Validate the reporting dates.
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if start > end:
        raise ValueError("Start date cannot be after end date.")

    # Retrieve current reporting statistics.
    statistics = get_ticket_statistics(
        start_date,
        end_date,
        department
    )

    # Retrieve historical comparison.
    comparison = compare_reporting_periods(
        start_date,
        end_date,
        department
    )

    # Retrieve department performance.
    department_performance = get_department_performance(
        start_date,
        end_date
    )

    # Only show the selected department when filtering.
    if department != "All":
        department_performance = [
            item for item in department_performance
            if item["department"] == department
        ]

    # Retrieve daily ticket trends.
    daily_trends = get_daily_trends(
        start_date,
        end_date,
        department
    )

    # Generate executive summary.
    executive_summary = generate_executive_summary(
        statistics,
        department
    )

    # Generate historical insights.
    insights = generate_historical_insights(comparison)

    # Generate business recommendations.
    recommendations = generate_recommendations(
        statistics,
        department_performance
    )

    historical_recommendations = generate_historical_recommendations(
        comparison
    )

    # Combine recommendations without duplicates.
    all_recommendations = list(dict.fromkeys(
        recommendations + historical_recommendations
    ))

    # Assemble the complete report.
    return {
        "report_title": "Corporate Convenience Weekly Business Report",
        "department": department,
        "reporting_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "statistics": statistics,
        "historical_comparison": comparison,
        "department_performance": department_performance,
        "daily_trends": daily_trends,
        "executive_summary": executive_summary,
        "insights": insights,
        "recommendations": all_recommendations
    }



