import requests
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any, Union

def get_hourly_energy_data(
    start_date: Optional[Union[datetime, date]] = None,
    end_date: Optional[Union[datetime, date]] = None,
    days: Optional[int] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieve hourly energy consumption and production from Tibber API.
    User can specify either start/end date (as datetime/date objects), or a number of days in history until yesterday.
    Returns a dict with 'consumption' and 'production' lists, each containing hourly data.
    """
    token = os.environ.get("TIBBER_API_TOKEN")
    if not token:
        raise ValueError("Tibber API token not found in environment variable 'TIBBER_API_TOKEN'.")

    if days is not None:
        end_dt = datetime.now().date() - timedelta(days=1)
        start_dt = end_dt - timedelta(days=days-1)
        start_date_str = start_dt.strftime('%Y-%m-%d')
        end_date_str = end_dt.strftime('%Y-%m-%d')
    elif start_date and end_date:
        # Accept datetime.date or datetime.datetime objects
        if hasattr(start_date, 'strftime') and hasattr(end_date, 'strftime'):
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            raise ValueError('start_date and end_date must be datetime/date objects')
    else:
        raise ValueError('Provide either start_date and end_date, or days')

    url = "https://api.tibber.com/v1-beta/gql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    consumption = []
    production = []
    after_cursor = None
    while True:
        after_str = f'"{after_cursor}"' if after_cursor else 'null'
        query = f"""
        {{
          viewer {{
            homes {{
              consumption(resolution: HOURLY, after: {after_str}, from: \"{start_date_str}\", to: \"{end_date_str}\") {{
                nodes {{
                  from
                  consumption
                  production
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
            consumption_data = data['data']['viewer']['homes'][0]['consumption']
            nodes = consumption_data['nodes']
            page_info = consumption_data['pageInfo']
        except (KeyError, IndexError, TypeError):
            raise RuntimeError('Unexpected response from Tibber API')

        for node in nodes:
            consumption.append({
                'from': node['from'],
                'consumption': node.get('consumption', 0)
            })
            production.append({
                'from': node['from'],
                'production': node.get('production', 0)
            })

        if page_info.get('hasNextPage'):
            after_cursor = page_info.get('endCursor')
            if not after_cursor:
                break
        else:
            break

    return {'consumption': consumption, 'production': production}
