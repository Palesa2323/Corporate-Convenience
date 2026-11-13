
from datetime import datetime, timedelta, timezone

from backend.database import get_connection


def get_daily_ticket_counts(days=30, department=None):
    """
    Retrieve the number of tickets created per day
    over the selected historical period.
    """

    if not isinstance(days, int) or days < 1:
        raise ValueError("Days must be a positive integer.")

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)

    query = """
        SELECT DATE(created_at) AS ticket_date,
               COUNT(*) AS ticket_count
        FROM tickets
        WHERE DATE(created_at) >= ?
          AND DATE(created_at) <= ?
    """

    params = [start_date.isoformat(), end_date.isoformat()]

    if department:
        query += " AND department = ?"
        params.append(department)

    query += " GROUP BY DATE(created_at) ORDER BY ticket_date"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    daily_counts = {
        row["ticket_date"]: row["ticket_count"]
        for row in rows
    }

    # Include dates with zero tickets.
    results = []

    for day in range(days):
        current_date = start_date + timedelta(days=day)

        results.append({
            "date": current_date.isoformat(),
            "tickets": daily_counts.get(current_date.isoformat(), 0)
        })

    return results


def forecast_ticket_workload(days=30, forecast_days=7, department=None):
    """
    Forecast future ticket workload using a simple
    linear regression trend.
    """

    if not isinstance(forecast_days, int) or forecast_days < 1:
        raise ValueError("Forecast days must be a positive integer.")

    history = get_daily_ticket_counts(days, department)

    values = [item["tickets"] for item in history]
    count = len(values)

    if count == 0:
        return {
            "history": [],
            "forecast": [],
            "message": "No historical ticket data available."
        }
    if not any(values):
        return {
            "history": history,
            "forecast": [],
            "average_daily_tickets": 0,
            "trend": "No activity",
            "daily_change": 0,
            "message": "No tickets were recorded during the selected period."
        }
    # Calculate the average daily ticket volume.
    average = sum(values) / count

    # Calculate the linear regression trend.
    x_mean = (count - 1) / 2
    y_mean = average

    denominator = sum(
        (x - x_mean) ** 2 for x in range(count)
    )

    if denominator == 0:
        slope = 0
    else:
        slope = sum(
            (x - x_mean) * (values[x] - y_mean)
            for x in range(count)
        ) / denominator

    # Generate future workload predictions.
    last_date = datetime.fromisoformat(history[-1]["date"]).date()

    forecast = []

    for day in range(1, forecast_days + 1):
        predicted = max(0, round(average + slope * (count - 1 + day - x_mean)))

        forecast_date = last_date + timedelta(days=day)

        forecast.append({
            "date": forecast_date.isoformat(),
            "predicted_tickets": predicted
        })

    return {
        "history": history,
        "forecast": forecast,
        "average_daily_tickets": round(average, 2),
        "trend": (
            "Increasing" if slope > 0.1
            else "Decreasing" if slope < -0.1
            else "Stable"
        ),
        "daily_change": round(slope, 2),
        "message": "Workload forecast generated successfully."
    }
