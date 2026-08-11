import pandas as pd

# 1. Load the dataset (change to .csv if you prefer)
df = pd.read_parquet("clean_products_raw.parquet")

# 2. Force Pandas to display ALL columns without hiding any
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# 3. Print the total size of the dataset
print(f"Total Products: {df.shape[0]}")
print(f"Total Columns: {df.shape[1]}")
print("-" * 50)

# 4. Print a list of every single column name
print("All Column Names:")
print(df.columns.tolist())
print("-" * 50)

# 5. Print the first 3 rows showing ALL data
print(df.head(3).to_string(index=False))

# Optional: To save it to a CSV so you can open it in Excel/Google Sheets:
df.to_csv("scraped_sunscreens.csv", index=False)
print("\n✅ Saved a copy to scraped_sunscreens.csv for easy viewing!")