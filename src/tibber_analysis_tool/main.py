import argparse
from datetime import datetime

import polars as pl

from tibber_analysis_tool.tibber_energy_summary import aggregate_by_peak_offpeak, get_hourly_energy_data


def main():
    parser = argparse.ArgumentParser(description="Query Tibber hourly energy data.")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Number of days in history until yesterday (default: 7)", default=7)

    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d") if args.start else None
    end_date = datetime.strptime(args.end, "%Y-%m-%d") if args.end else None
    days = args.days if not (args.start and args.end) else None

    consumption_data = get_hourly_energy_data("consumption", start_date=start_date, end_date=end_date, days=days)
    production_data = get_hourly_energy_data("production", start_date=start_date, end_date=end_date, days=days)

    agg_consumption = aggregate_by_peak_offpeak(consumption_data, "consumption")
    agg_production = aggregate_by_peak_offpeak(production_data, "production")

    merged = {**agg_consumption, **agg_production}
    merged["net-cost"] = agg_consumption["cost"] - agg_production["profit"]

    print(pl.DataFrame(consumption_data))
    print(pl.DataFrame(production_data))
    print(merged)


if __name__ == "__main__":
    main()
