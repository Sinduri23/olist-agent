"""Load the Olist CSVs (Kaggle: 'Brazilian E-Commerce Public Dataset by Olist') into a database.

    python -m agent.load_data --csv-dir ./olist_csvs --url postgresql+psycopg2://postgres:pw@localhost/olist
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from . import config

DATE_COLUMNS = {
    "olist_orders_dataset": [
        "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "olist_order_items_dataset": ["shipping_limit_date"],
    "olist_order_reviews_dataset": ["review_creation_date", "review_answer_timestamp"],
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv-dir", required=True)
    p.add_argument("--url", default=config.DATABASE_URL, help="use an ADMIN connection here, not the read-only agent role")
    args = p.parse_args()

    engine = create_engine(args.url)
    for table in sorted(config.ALLOWED_TABLES):
        path = Path(args.csv_dir) / f"{table}.csv"
        if not path.exists():
            print(f"missing {path}, skipping")
            continue
        df = pd.read_csv(path, parse_dates=DATE_COLUMNS.get(table, []))
        df.to_sql(table, engine, if_exists="replace", index=False, chunksize=10_000)
        print(f"loaded {table}: {len(df):,} rows")


if __name__ == "__main__":
    main()
