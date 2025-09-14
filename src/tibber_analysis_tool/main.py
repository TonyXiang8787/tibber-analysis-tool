import argparse
from datetime import datetime

import polars as pl

from tibber_analysis_tool.tibber_energy_summary import get_hourly_energy_data


def main():
    parser = argparse.ArgumentParser(description="Query Tibber hourly energy data.")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Number of days in history until yesterday (default: 31)", default=31)

    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d") if args.start else None
    end_date = datetime.strptime(args.end, "%Y-%m-%d") if args.end else None
    days = args.days if not (args.start and args.end) else None

    result = {}
    result["consumption"] = get_hourly_energy_data("consumption", start_date=start_date, end_date=end_date, days=days)
    result["production"] = get_hourly_energy_data("production", start_date=start_date, end_date=end_date, days=days)
    
    pl.Config.set_tbl_rows(100)
    print(pl.DataFrame(result["consumption"]))
    print(pl.DataFrame(result["production"]))


if __name__ == "__main__":
    main()
