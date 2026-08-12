import pandas as pd

def check_stage2_gates(df: pd.DataFrame, expected_ingredient_rows: int) -> tuple[bool, dict]:
    """Validates the cleaned dataset before Parquet export."""
    passed = True
    details = {}
    
    # Gate 1: Price sanity - Every row must have a non-null price_tier
    if df["price_tier"].isnull().any():
        passed = False
        details["price_sanity"] = "Failed: Missing price_tier on some rows"
        
    # Gate 2: Dedup sanity - Prevent collapsing genuinely distinct same-platform products
    if "canonical_product_group_id" in df.columns:
        dupes = df.groupby(["canonical_product_group_id", "platform"])["platform_product_id"].nunique()
        if (dupes > 1).any():
            passed = False
            details["dedup_sanity"] = "Failed: Collapsed distinct same-platform products"
            
    # Gate 3: Ingredient sample size - Must match the exact number going in to ensure no silent drops
    actual_rows = df["has_ingredient_data"].sum()
    if actual_rows != expected_ingredient_rows:
        passed = False
        details["ingredient_sample_size"] = f"Failed: Expected {expected_ingredient_rows} rows, got {actual_rows}"

    return passed, details