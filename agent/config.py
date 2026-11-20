import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://olist_agent:change_me@localhost:5432/olist")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_ROWS = int(os.getenv("MAX_ROWS", "100"))
MAX_STEPS = int(os.getenv("MAX_STEPS", "6"))
STATEMENT_TIMEOUT_MS = int(os.getenv("STATEMENT_TIMEOUT_MS", "10000"))

ALLOWED_TABLES = {
    "olist_customers_dataset",
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "product_category_name_translation",
}
