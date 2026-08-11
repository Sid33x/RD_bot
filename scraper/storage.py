import sqlite3
import pandas as pd
import os
import json
from scraper.models import ProductRecord

class SQLiteStorage:
    def __init__(self, db_path: str = "data/scraper.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Added back mrp, rating, review_count, discount, quantity, description, availability
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    platform TEXT,
                    platform_product_id TEXT,
                    product_url TEXT,
                    product_name TEXT,
                    brand TEXT,
                    mrp REAL,
                    selling_price REAL,
                    discount_pct REAL,
                    quantity_value REAL,
                    quantity_unit TEXT,
                    key_ingredients TEXT,
                    ingredient_concentrations TEXT,
                    finish TEXT,
                    skin_types TEXT,
                    free_from TEXT,
                    pregnancy_safe BOOLEAN,
                    claims TEXT,
                    spf TEXT,
                    pa_rating TEXT,
                    rating REAL,
                    review_count INTEGER,
                    description TEXT,
                    availability TEXT,
                    scrape_status TEXT,
                    scraped_at TIMESTAMP,
                    run_id TEXT,
                    PRIMARY KEY (platform, platform_product_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_evidence (
                    platform_product_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    raw_markdown TEXT
                )
            """)
            conn.commit()

    def save_product(self, record: ProductRecord):
        safe_concentrations = json.dumps(record.ingredient_concentrations) if record.ingredient_concentrations else "{}"
        safe_key_ingredients = ", ".join(record.key_ingredients) if record.key_ingredients else ""
        safe_skin_types = ", ".join(record.skin_types) if record.skin_types else ""
        safe_free_from = ", ".join(record.free_from) if record.free_from else ""
        safe_claims = ", ".join(record.claims) if record.claims else ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    platform, platform_product_id, product_url, product_name, 
                    brand, mrp, selling_price, discount_pct, quantity_value, quantity_unit,
                    key_ingredients, ingredient_concentrations,
                    finish, skin_types, free_from, pregnancy_safe, claims, spf, pa_rating,
                    rating, review_count, description, availability,
                    scrape_status, scraped_at, run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.platform, record.platform_product_id, record.product_url, 
                record.product_name, record.brand, record.mrp, record.selling_price, 
                record.discount_pct, record.quantity_value, record.quantity_unit,
                safe_key_ingredients, safe_concentrations, record.finish, 
                safe_skin_types, safe_free_from, record.pregnancy_safe, 
                safe_claims, record.spf, record.pa_rating,
                record.rating, record.review_count, record.description, record.availability,
                record.scrape_status, record.scraped_at.isoformat(), record.run_id
            ))
            conn.commit()

    def save_raw_evidence(self, product_id: str, run_id: str, markdown: str):
        if not markdown:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO raw_evidence (platform_product_id, run_id, raw_markdown)
                VALUES (?, ?, ?)
            """, (product_id, run_id, markdown))
            conn.commit()

    def is_already_scraped(self, product_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM products WHERE platform_product_id = ? AND scrape_status = 'success'", (product_id,))
            return cursor.fetchone() is not None

    def export_to_parquet(self, output_path: str = "clean_products_raw.parquet"):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM products WHERE scrape_status = 'success'", conn)
            df.to_parquet(output_path, index=False)
            df.to_csv("scraped_sunscreens.csv", index=False)