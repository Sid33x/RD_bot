import pandas as pd
import re
import json
import uuid
import os
import sys
from rapidfuzz import fuzz, process

# Import resilience regardless of execution entrypoint
try:
    from quality_gates import check_stage2_gates
except ImportError:
    from processing.quality_gates import check_stage2_gates

def load_configs():
    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, "config/pigmentation_ingredients.json"), "r") as f:
        pigmentation_list = set(json.load(f))
    with open(os.path.join(base_dir, "config/ingredient_synonyms.json"), "r") as f:
        synonyms = json.load(f)
    with open(os.path.join(base_dir, "config/claims_denylist.json"), "r") as f:
        denylist = json.load(f)
    return pigmentation_list, synonyms, denylist

def canonicalize_ingredients(df: pd.DataFrame, synonyms: dict, pigmentation_list: set) -> pd.DataFrame:
    def process_ingredients(row):
        if pd.isna(row) or not str(row).strip():
            return [], []
            
        raw_tokens = re.split(r'[,;+]', str(row))
        canon_list = []
        pigmentation_flags = []
        
        for token in raw_tokens:
            token = token.strip().lower()
            token = re.sub(r'\s*\d+(\.\d+)?%$', '', token).strip()
            
            if re.search(r'spf\s*\d+', token) or re.search(r'pa\++', token):
                continue
                
            if not token:
                continue
                
            mapped_token = synonyms.get(token, token.title())
            if mapped_token not in canon_list:
                canon_list.append(mapped_token)
            
            if mapped_token in pigmentation_list and mapped_token not in pigmentation_flags:
                pigmentation_flags.append(mapped_token)
                
        return canon_list, pigmentation_flags

    res = df['key_ingredients'].apply(process_ingredients)
    df['ingredients_canonical'] = res.apply(lambda x: x[0])
    df['ingredients_pigmentation'] = res.apply(lambda x: x[1])
    return df

def clean_claims(df: pd.DataFrame, denylist_patterns: list) -> pd.DataFrame:
    compiled = [re.compile(p, re.IGNORECASE) for p in denylist_patterns]
    
    # Manual synonym map for genuine variants not fixed by regex
    claim_synonyms = {
        "waterproof": "water resistant",
        "water light": "waterlight",
        "broad spectrum protection": "broad spectrum"
    }
    
    def process_claims(row):
        if pd.isna(row) or not str(row).strip():
            return []
            
        raw_tokens = re.split(r',', str(row))
        clean_list = []
        
        for token in raw_tokens:
            token = token.strip()
            
            # Drop empty or denylisted tokens
            if not token or any(p.search(token) for p in compiled):
                continue
                
            # 1. Normalize format: convert hyphens/slashes to spaces
            token = re.sub(r'[-/]', ' ', token)
            
            # 2. Standardize whitespace and lowercase for matching
            token = re.sub(r'\s+', ' ', token).strip().lower()
            
            # 3. Apply synonym map to catch "waterproof" -> "water resistant"
            token = claim_synonyms.get(token, token)
            
            # 4. Title case for final standard output
            clean_list.append(token.title())
            
        return list(dict.fromkeys(clean_list))
        
    df['claims_clean'] = df['claims'].apply(process_claims)
    return df

def segment_price(df: pd.DataFrame) -> pd.DataFrame:
    # Dynamically compute cutoffs from the actual dataset
    p33 = df['selling_price'].astype(float).quantile(0.33)
    p66 = df['selling_price'].astype(float).quantile(0.66)
    
    bins = [0, p33, p66, float('inf')]
    labels = ['Budget', 'Mid', 'Premium']
    
    df['price_tier'] = pd.cut(df['selling_price'].astype(float), bins=bins, labels=labels, right=False)
    return df

def detect_cross_platform_duplicates(df: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:
    df['dedup_key'] = df['brand'].astype(str) + " " + df['product_name'].astype(str) + " " + df['quantity_value'].astype(str)
    df['canonical_product_group_id'] = None
    
    existing_keys = []
    key_to_group = {}
    group_platforms = {}
    
    for idx, row in df.iterrows():
        key = row['dedup_key']
        plat = row['platform']
        
        if not existing_keys:
            new_id = str(uuid.uuid4())
            existing_keys.append(key)
            key_to_group[key] = new_id
            group_platforms[new_id] = {plat}
            df.at[idx, 'canonical_product_group_id'] = new_id
            continue
            
        match = process.extractOne(key, existing_keys, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= threshold:
            matched_group_id = key_to_group[match[0]]
            
            # PRD Requirement: DO NOT collapse distinct products from the same platform
            if plat in group_platforms[matched_group_id]:
                new_id = str(uuid.uuid4())
                existing_keys.append(key)
                key_to_group[key] = new_id
                group_platforms[new_id] = {plat}
                df.at[idx, 'canonical_product_group_id'] = new_id
            else:
                # Safe to group across platforms
                df.at[idx, 'canonical_product_group_id'] = matched_group_id
                group_platforms[matched_group_id].add(plat)
                existing_keys.append(key)
                key_to_group[key] = matched_group_id
        else:
            new_id = str(uuid.uuid4())
            existing_keys.append(key)
            key_to_group[key] = new_id
            group_platforms[new_id] = {plat}
            df.at[idx, 'canonical_product_group_id'] = new_id
            
    return df.drop(columns=['dedup_key'])
    
def finalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    expected_cols = [
        "platform", "platform_product_id", "product_url", "product_name", "brand",
        "mrp", "selling_price", "discount_pct", "price_tier",
        "quantity_value", "quantity_unit",
        "ingredients_canonical", "ingredients_pigmentation", "claims_clean",
        "spf", "pa_rating", "rating", "review_count",
        "canonical_product_group_id", "has_ingredient_data", "scraped_at", "run_id"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    return df[expected_cols]

def main():
    print("Starting Stage 2: Cleaning and Normalization")
    
    # Path resolution fallback (checks data/ folder first, then root directory)
    input_path = "data/scraped_sunscreens.csv"
    if not os.path.exists(input_path):
        input_path = "scraped_sunscreens.csv"
        
    if not os.path.exists(input_path):
        raise FileNotFoundError("Could not find 'scraped_sunscreens.csv' in 'data/' or in root directory.")
        
    print(f"Reading input data from: {input_path}")
    df = pd.read_csv(input_path)
    pigmentation_list, synonyms, denylist = load_configs()
    
    df['has_ingredient_data'] = df['key_ingredients'].notna()
    expected_ingredient_rows = int(df['has_ingredient_data'].sum())
    
    df = canonicalize_ingredients(df, synonyms, pigmentation_list)
    df = clean_claims(df, denylist)
    df = segment_price(df)
    df = detect_cross_platform_duplicates(df)
    df = finalize_schema(df)
        
    passed, details = check_stage2_gates(df, expected_ingredient_rows)
    
    # Guarantee output directory exists
    os.makedirs("data", exist_ok=True)
    
    if not passed:
        print(f"Quality Gates Failed! Details: {details}")
        df.to_parquet("data/clean_products.FAILED.parquet", index=False)
        return
        
    df.to_parquet("data/clean_products.parquet", index=False)
    print("Stage 2 Complete. Parquet saved successfully to data/clean_products.parquet.")

if __name__ == "__main__":
    main()