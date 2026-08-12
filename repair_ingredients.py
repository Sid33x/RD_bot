import sqlite3
import pandas as pd
import os
from google import genai
from dotenv import load_dotenv


def repair_missing_ingredients():
    load_dotenv()

    # Ensure your GEMINI_API_KEY is in your .env file
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY not found in environment variables.")
        return

    client = genai.Client(api_key=api_key)

    db_path = "data/scraper.db"

    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)

    # 1. Fetch only products that successfully scraped
    #    but are missing ingredients
    query = """
        SELECT 
            p.platform_product_id,
            p.product_name,
            p.brand,
            r.raw_markdown
        FROM products p
        JOIN raw_evidence r
            ON p.platform_product_id = r.platform_product_id
        WHERE (p.key_ingredients IS NULL OR p.key_ingredients = '')
          AND p.scrape_status = 'success'
    """

    missing_df = pd.read_sql_query(query, conn)

    print(
        f"Found {len(missing_df)} products missing ingredients. "
        "Commencing repair..."
    )

    cursor = conn.cursor()
    repaired_count = 0

    # 2. Iterate through missing products
    #    and use Gemini to extract ingredients
    for index, row in missing_df.iterrows():

        product_name = row["product_name"] or "Unknown Product"

        print(f"Repairing: {product_name[:40]}...")

        # Take the first 8000 characters of markdown
        markdown_text = (
            row["raw_markdown"][:8000]
            if row["raw_markdown"]
            else ""
        )

        if not markdown_text.strip():
            print("  -> No raw markdown available")
            continue

        prompt = f"""
You are an expert cosmetic product data extractor.

Product name:
{product_name}

Brand:
{row["brand"] or "Unknown"}

Below is raw markdown scraped directly from the product page.

Task:
Extract the key/active ingredients that are EXPLICITLY mentioned
in the supplied text.

Examples include:
- Niacinamide
- Vitamin C
- Zinc Oxide
- Salicylic Acid
- Hyaluronic Acid

Important rules:
1. Only extract ingredients explicitly present in the text.
2. Never guess, infer, or assume an ingredient.
3. Do not invent ingredients based on the product name or brand.
4. Return the top 3-5 key/active ingredients if they are explicitly stated.
5. Return ONLY a comma-separated list.
6. If no ingredients can be confidently identified, return exactly:
UNKNOWN

Raw Markdown:
{markdown_text}
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0
                }
            )

            result = response.text.strip()

            if result.upper() != "UNKNOWN" and result != "":
                print(f"  -> Found: {result}")

                # Update SQLite database in-place
                cursor.execute(
                    """
                    UPDATE products
                    SET key_ingredients = ?
                    WHERE platform_product_id = ?
                    """,
                    (
                        result,
                        row["platform_product_id"]
                    )
                )

                conn.commit()
                repaired_count += 1

            else:
                print(
                    "  -> Still missing "
                    "(ingredients not found in raw markdown)"
                )

        except Exception as e:
            print(f"  -> API Error: {e}")

    # 3. Re-export the fully repaired dataset
    print("\nRe-exporting repaired dataset to Parquet and CSV...")

    df_final = pd.read_sql_query(
        """
        SELECT *
        FROM products
        WHERE scrape_status = 'success'
        """,
        conn
    )

    df_final.to_parquet(
        "clean_products_raw.parquet",
        index=False
    )

    df_final.to_csv(
        "scraped_sunscreens.csv",
        index=False
    )

    conn.close()

    print(
        f"Repair Complete! Successfully recovered ingredients "
        f"for {repaired_count} products."
    )


if __name__ == "__main__":
    repair_missing_ingredients()