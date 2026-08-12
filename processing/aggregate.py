import pandas as pd
import json
import os
from collections import Counter
from itertools import combinations
import itertools

def compute_top_ingredients(df_ing: pd.DataFrame, top_n: int = 20) -> list:
    deduped = df_ing.drop_duplicates(subset=['canonical_product_group_id'])
    total = len(deduped)
    exploded = deduped.explode('ingredients_canonical').dropna(subset=['ingredients_canonical'])
    counts = exploded['ingredients_canonical'].value_counts().head(top_n)
    return [{"ingredient": k, "count": int(v), "pct": round(v / total, 3)} for k, v in counts.items()]

def compute_pigmentation_ingredients(df_ing: pd.DataFrame) -> list:
    deduped = df_ing.drop_duplicates(subset=['canonical_product_group_id'])
    total = len(deduped)
    exploded = deduped.explode('ingredients_pigmentation').dropna(subset=['ingredients_pigmentation'])
    counts = exploded['ingredients_pigmentation'].value_counts()
    
    res = []
    for ing, count in counts.items():
        brands = exploded[exploded['ingredients_pigmentation'] == ing]['brand'].unique().tolist()
        res.append({
            "ingredient": ing, "count": int(count), "pct": round(count / total, 3), "brands": sorted(brands)
        })
    return res

def compute_rare_ingredients(df_ing: pd.DataFrame, max_brands: int = 3) -> list:
    deduped = df_ing.drop_duplicates(subset=['canonical_product_group_id'])
    exploded = deduped.explode('ingredients_canonical').dropna(subset=['ingredients_canonical'])
    brand_ing_map = exploded.groupby('ingredients_canonical')['brand'].unique()
    rare = brand_ing_map[brand_ing_map.apply(len) <= max_brands]
    return [{"ingredient": k, "brand_count": len(v), "brands": sorted(list(v))} for k, v in rare.items()]

def compute_top_claims(df: pd.DataFrame, top_n: int = 20) -> list:
    deduped = df.drop_duplicates(subset=['canonical_product_group_id'])
    total = len(deduped)
    exploded = deduped.explode('claims_clean').dropna(subset=['claims_clean'])
    counts = exploded['claims_clean'].value_counts().head(top_n)
    return [{"claim": k, "count": int(v), "pct": round(v / total, 3)} for k, v in counts.items()]

def compute_claim_saturation(df: pd.DataFrame, min_pct: float = 0.4) -> list:
    deduped = df.drop_duplicates(subset=['canonical_product_group_id'])
    total_rows = len(deduped)
    pair_counts = Counter()
    
    for _, row in deduped.dropna(subset=['claims_clean']).iterrows():
        claims = row['claims_clean']
        if isinstance(claims, list) and len(claims) > 1:
            pair_counts.update(combinations(sorted(claims), 2))
            
    saturated = [{"pair": list(pair), "joint_pct": round(count / total_rows, 3)} 
                 for pair, count in pair_counts.items() if (count / total_rows) > min_pct]
    return saturated

def compute_underrepresented_pigmentation_claims(df: pd.DataFrame, floor_pct: float = 0.10) -> list:
    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, "config/pigmentation_ingredients.json"), "r") as f:
        pig_vocab = set(json.load(f))
        
    deduped = df.drop_duplicates(subset=['canonical_product_group_id'])
    total_rows = len(deduped)
    exploded = deduped.explode('claims_clean')['claims_clean'].dropna()
    
    underrepresented = []
    for claim in exploded.unique():
        if any(p.lower() in claim.lower() for p in pig_vocab):
            count = (exploded == claim).sum()
            pct = count / total_rows
            if pct < floor_pct:
                underrepresented.append({"claim": claim, "pct": round(pct, 3)})
    return underrepresented

def compute_price_ingredient_crosstab(df: pd.DataFrame) -> list:
    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, "config/pigmentation_ingredients.json"), "r") as f:
        # Load reference list as lowercase for bulletproof matching
        pig_vocab = set([p.lower() for p in json.load(f)])
        
    deduped = df.drop_duplicates(subset=['canonical_product_group_id']).copy()
    
    # Fix: Make the type check resilient to numpy arrays loaded from Parquet
    def has_pigmentation_ingredient(ing_iterable):
        # Check if it's iterable and not a standard float (like NaN)
        if pd.isna(ing_iterable).all() if hasattr(ing_iterable, 'all') else pd.isna(ing_iterable):
            return False
            
        try:
            return any(str(ing).lower() in pig_vocab for ing in ing_iterable)
        except TypeError:
            # If it's somehow not iterable, return False
            return False
        
    deduped['has_pigmentation'] = deduped['ingredients_canonical'].apply(has_pigmentation_ingredient)
    
    crosstab = []
    for tier in ['Budget', 'Mid', 'Premium']:
        tier_df = deduped[deduped['price_tier'] == tier]
        total = len(tier_df)
        if total == 0:
            crosstab.append({"price_tier": tier, "product_count": 0, "pct_with_pigmentation_ingredient": 0.0})
        else:
            with_pig = tier_df['has_pigmentation'].sum()
            crosstab.append({
                "price_tier": tier, 
                "product_count": total, 
                "pct_with_pigmentation_ingredient": round(with_pig / total, 3)
            })
    return crosstab

def compute_ingredient_claim_combinations(df_ing: pd.DataFrame, top_n: int = 15) -> list:
    """Calculates the co-occurrence of specific ingredients with specific claims (Step 5)."""
    deduped = df_ing.drop_duplicates(subset=['canonical_product_group_id'])
    total = len(deduped)
    
    # Explode ingredients first, drop nulls
    exploded_ing = deduped.explode('ingredients_canonical').dropna(subset=['ingredients_canonical'])
    # Explode claims on the already-exploded ingredients dataframe
    exploded_both = exploded_ing.explode('claims_clean').dropna(subset=['claims_clean'])
    
    # Group by the pair and count
    combo_counts = exploded_both.groupby(['ingredients_canonical', 'claims_clean']).size().reset_index(name='count')
    combo_counts = combo_counts.sort_values(by='count', ascending=False).head(top_n)
    
    res = []
    for _, row in combo_counts.iterrows():
        res.append({
            "ingredient": row['ingredients_canonical'],
            "claim": row['claims_clean'],
            "count": int(row['count']),
            "pct": round(row['count'] / total, 3)
        })
    return res

def compute_brand_positioning(df: pd.DataFrame) -> list:
    """Analyzes brands positioning purely on pigmentation vs basic sun protection (Step 4)."""
    deduped = df.drop_duplicates(subset=['canonical_product_group_id']).dropna(subset=['claims_clean', 'brand'])
    exploded = deduped.explode('claims_clean')
    
    # Define basic vocabularies for classification
    pigmentation_keywords = ['pigmentation', 'dark spot', 'brightening', 'even tone', 'melasma', 'glow', 'radiance']
    spf_keywords = ['spf', 'uva', 'uvb', 'sun protection', 'broad spectrum', 'sunburn', 'sun block', 'pa+++']
    
    def is_pig(claim):
        return any(k in str(claim).lower() for k in pigmentation_keywords)
    def is_spf(claim):
        return any(k in str(claim).lower() for k in spf_keywords)
    
    exploded['is_pig'] = exploded['claims_clean'].apply(is_pig)
    exploded['is_spf'] = exploded['claims_clean'].apply(is_spf)
    
    brand_agg = exploded.groupby('brand').agg(
        total_pig_claims=('is_pig', 'sum'),
        total_spf_claims=('is_spf', 'sum')
    ).reset_index()
    
    res = []
    # Filter to brands that actually make claims to avoid noise
    for _, row in brand_agg[(brand_agg['total_pig_claims'] > 0) | (brand_agg['total_spf_claims'] > 0)].iterrows():
        res.append({
            "brand": row['brand'],
            "pigmentation_claim_count": int(row['total_pig_claims']),
            "basic_spf_claim_count": int(row['total_spf_claims'])
        })
    
    # Sort by pigmentation focus to highlight the pure pigmentation brands
    res = sorted(res, key=lambda x: x['pigmentation_claim_count'], reverse=True)
    return res[:15]

def main():
    print("Starting Stage 3: Statistical Aggregation")
    parquet_path = "data/clean_products.parquet"
    if not os.path.exists(parquet_path):
        raise FileNotFoundError("data/clean_products.parquet does not exist. Run 'python processing/clean.py' first.")
        
    df = pd.read_parquet(parquet_path)
    df_ing = df[df['has_ingredient_data'] == True]
    
    stats_summary = {
        "dataset_meta": {
            "total_products": df['canonical_product_group_id'].nunique(),
            "products_with_ingredient_data": df_ing['canonical_product_group_id'].nunique(),
            "platforms": {str(k): int(v) for k, v in df.drop_duplicates(subset=['canonical_product_group_id'])['platform'].value_counts().items()} if 'platform' in df.columns else {},
            "raw_scraped_rows": len(df)
        },
        "top_ingredients": compute_top_ingredients(df_ing),
        "pigmentation_ingredients": compute_pigmentation_ingredients(df_ing),
        "rare_ingredients": compute_rare_ingredients(df_ing),
        "trend_note": "not computable: single time-point scrape",
        "top_claims": compute_top_claims(df),
        "saturated_claim_pairs": compute_claim_saturation(df, min_pct=0.15), 
        "underrepresented_pigmentation_claims": compute_underrepresented_pigmentation_claims(df, floor_pct=0.10),
        "price_segment_crosstab": compute_price_ingredient_crosstab(df_ing),
        # NEW FIELDS ADDED HERE:
        "ingredient_claim_combinations": compute_ingredient_claim_combinations(df_ing),
        "brand_positioning": compute_brand_positioning(df)
    }

    os.makedirs("data", exist_ok=True)
    with open("data/stats_summary.json", "w") as f:
        json.dump(stats_summary, f, indent=2)
        
    print("Stage 3 Complete. Output saved to data/stats_summary.json.")

if __name__ == "__main__":
    main()