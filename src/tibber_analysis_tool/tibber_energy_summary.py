import os
from datetime import date, datetime, timedelta
from typing import Any

import requests


def _resolve_date_range(start_date, end_date, days):
    """
    Helper to resolve start and end date strings from either start/end or days.
    Returns (start_date_str, end_date_str)
    """
    if days is not None:
        end_dt = datetime.now().date() - timedelta(days=1)
        start_dt = end_dt - timedelta(days=days - 1)
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")
    elif start_date and end_date:
        if hasattr(start_date, "strftime") and hasattr(end_date, "strftime"):
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
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
) -> dict[str, list[dict[str, Any]]]:
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
    after_cursor = None
    while True:
        after_str = f'"{after_cursor}"' if after_cursor else "null"
        query = f"""
        {{
          viewer {{
            homes {{
              {data_type}(resolution: HOURLY, after: {after_str}, from: \"{start_date_str}\", to: \"{end_date_str}\") {{
                nodes {{
                  from
                  {data_type}
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
        response = requests.post(url, headers=headers, json={"query": query})
        response.raise_for_status()
        data = response.json()
        try:
            home = data["data"]["viewer"]["homes"][0]
            table = home[data_type]
            nodes = table["nodes"]
            page_info = table["pageInfo"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Unexpected response from Tibber API") from None

        for node in nodes:
            results.append({"from": node["from"], data_type: node.get(data_type, 0)})

        if page_info.get("hasNextPage"):
            after_cursor = page_info.get("endCursor")
            if not after_cursor:
                break
        else:
            break

    return {data_type: results}
