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

    # Calculate all consumption and all production as sum of peak and off-peak
    all_consumption = agg_consumption["peak_consumption"] + agg_consumption["off_peak_consumption"]
    all_production = agg_production["peak_production"] + agg_production["off_peak_production"]
    net_energy = all_consumption - all_production
    if net_energy != 0:
        merged["average_price"] = merged["net-cost"] / net_energy
    else:
        merged["average_price"] = float("nan")

    df_consumption = pl.DataFrame(consumption_data)
    df_production = pl.DataFrame(production_data)

    # Merge on 'from', suffix columns, and rename 'from' to 'timestamp'
    df_merged = df_consumption.join(
        df_production,
        on="from",
        how="outer",
        suffix="_production",
    )
    df_merged = df_merged.rename({"from": "timestamp"})
    # Drop the duplicate 'from_production' column if it exists
    if "from_production" in df_merged.columns:
        df_merged = df_merged.drop("from_production")
    # Fill missing values with 0.0
    df_merged = df_merged.fill_null(0.0)
    df_merged = df_merged.sort("timestamp")
    df_merged = df_merged.set_sorted("timestamp")

    print(df_merged)
    print("Summary:")
    summary_df = pl.DataFrame([merged]).transpose(include_header=True)
    summary_df.columns = ["key", "value"]
    print(summary_df)


if __name__ == "__main__":
    main()
