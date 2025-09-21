import base64
import os
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import holidays
import requests


def aggregate_by_peak_offpeak(hourly_data: list[dict[str, Any]], data_type: str) -> dict[str, Any]:
    """
    Aggregates hourly consumption/production and cost/profit by Dutch peak and off-peak hours.
    Dutch regulation (2025):
      - Peak: Mon-Fri, 07:00-23:00 (Amsterdam time)
      - Off-peak: All other times (including weekends, holidays, and 23:00-07:00)
    Returns a dict with keys:
      - 'peak': sum of consumption/production during peak hours
      - 'offpeak': sum of consumption/production during off-peak hours
      - 'total_cost_or_profit': sum of cost (for consumption) or profit (for production) for all hours
    """
    AMSTERDAM = ZoneInfo("Europe/Amsterdam")
    PEAK_START_HOUR = 7
    PEAK_END_HOUR = 23
    PEAK_END_WEEKDAY = 4
    nl_holidays = holidays.country_holidays("NL")
    peak_total = 0.0
    offpeak_total = 0.0
    total_cost_or_profit = 0.0
    for entry in hourly_data:
        dt = datetime.fromisoformat(entry["from"]).astimezone(AMSTERDAM)
        hour = dt.hour
        weekday = dt.weekday()
        is_holiday = dt.date() in nl_holidays
        is_peak = (not is_holiday) and (0 <= weekday <= PEAK_END_WEEKDAY) and (PEAK_START_HOUR <= hour < PEAK_END_HOUR)
        value = entry.get(data_type, 0.0) or 0.0
        if is_peak:
            peak_total += value
        else:
            offpeak_total += value
        # cost for consumption, profit for production
        if data_type == "consumption":
            total_cost_or_profit += entry.get("cost", 0.0) or 0.0
        else:
            total_cost_or_profit += entry.get("profit", 0.0) or 0.0
    if data_type == "consumption":
        return {
            "peak_consumption": peak_total,
            "off_peak_consumption": offpeak_total,
            "cost": total_cost_or_profit,
        }
    else:
        return {
            "peak_production": peak_total,
            "off_peak_production": offpeak_total,
            "profit": total_cost_or_profit,
        }


def _resolve_date_range(start_date, end_date, days):
    """
    Helper to resolve start and end date strings from either start/end or days.
    Returns (start_date_str, end_date_str)
    """
    AMSTERDAM = ZoneInfo("Europe/Amsterdam")

    def to_iso8601(dt):
        # Convert to Amsterdam timezone and return ISO8601 with offset
        if isinstance(dt, datetime):
            dt = dt.replace(tzinfo=AMSTERDAM) if dt.tzinfo is None else dt.astimezone(AMSTERDAM)
            return dt.replace(microsecond=0).isoformat()
        elif isinstance(dt, date):
            dt = datetime(dt.year, dt.month, dt.day, tzinfo=AMSTERDAM)
            return dt.isoformat()
        else:
            raise ValueError("Date must be datetime or date object")

    if days is not None:
        end_dt = datetime.now().date() - timedelta(days=1)
        start_dt = end_dt - timedelta(days=days)
        start_date_str = to_iso8601(start_dt)
        end_date_str = to_iso8601(end_dt)
    elif start_date and end_date:
        if hasattr(start_date, "isoformat") and hasattr(end_date, "isoformat"):
            start_date_str = to_iso8601(start_date)
            end_date_str = to_iso8601(end_date)
        else:
            raise ValueError("start_date and end_date must be datetime/date objects")
    else:
        raise ValueError("Provide either start_date and end_date, or days")
    return start_date_str, end_date_str


def get_hourly_energy_data(
    data_type: str,
    start_date: datetime | date | None = None,
    end_date: datetime | date | None = None,
    days: int | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve hourly energy consumption or production from Tibber API.
    data_type: 'consumption' or 'production'.
    User can specify either start/end date (as datetime/date objects), or a number of days in history until yesterday.
    Returns a dict with the requested data type as a list of hourly data.
    """
    if data_type not in {"consumption", "production"}:
        raise ValueError("data_type must be 'consumption' or 'production'")

    token = os.environ.get("TIBBER_API_TOKEN")
    if not token:
        raise ValueError("Tibber API token not found in environment variable 'TIBBER_API_TOKEN'.")

    start_date_str, end_date_str = _resolve_date_range(start_date, end_date, days)

    url = "https://api.tibber.com/v1-beta/gql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    results = []
    after_cursor = base64.b64encode(start_date_str.encode()).decode()
    cost_profit = "cost" if data_type == "consumption" else "profit"
    first = True
    while True:
        after_str = f'"{after_cursor}"'
        query = f"""
        {{
          viewer {{
            homes {{
              {data_type}(resolution: HOURLY, after: {after_str}, first: 744) {{
                nodes {{
                  from
                  {data_type}
                  {cost_profit}
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
            }}
          }}
        }}
        """
        try:
            response = requests.post(url, headers=headers, json={"query": query})
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            raise
        data = response.json()
        try:
            home = data["data"]["viewer"]["homes"][0]
            table = home[data_type]
            nodes = table["nodes"]
            page_info = table["pageInfo"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Unexpected response from Tibber API: {data['errors']}") from None

        if first:
            first = False
        else:
            nodes = nodes[1:]  # Skip the first node to avoid overlap
        for node in nodes:
            node_from_dt = datetime.fromisoformat(node["from"])
            end_dt = datetime.fromisoformat(end_date_str)
            if node_from_dt >= end_dt:
                return results  # Break both inner and outer loop
            results.append(node)

        if page_info.get("hasNextPage"):
            after_cursor = page_info.get("endCursor")
            if not after_cursor:
                break
        else:
            break

    return results
