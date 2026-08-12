import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure directories exist
os.makedirs("report/charts", exist_ok=True)

def load_data():
    with open("data/stats_summary.json", "r") as f:
        stats = json.load(f)
    with open("data/insights.json", "r") as f:
        insights = json.load(f)
    return stats, insights

def generate_charts(stats):
    """Generates standard R&D charts from the stats summary."""
    sns.set_theme(style="whitegrid")
    
    # Chart 1: Price Tier Crosstab
    crosstab = stats.get("price_segment_crosstab", [])
    if crosstab:
        tiers = [item["price_tier"] for item in crosstab]
        pcts = [item["pct_with_pigmentation_ingredient"] * 100 for item in crosstab]
        
        plt.figure(figsize=(8, 5))
        ax = sns.barplot(x=tiers, y=pcts, palette="Blues_d")
        plt.title("Pigmentation Actives by Price Tier (Subset n=52)", pad=15, fontweight='bold')
        plt.ylabel("% of Products Containing Actives")
        plt.ylim(0, 110)
        
        # Add data labels
        for i, p in enumerate(ax.patches):
            ax.annotate(f"{pcts[i]:.1f}%", 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='bottom', xytext=(0, 5), textcoords='offset points')
        
        plt.tight_layout()
        plt.savefig("report/charts/price_crosstab.png", dpi=300)
        plt.close()

    # Chart 2: Top Ingredients
    top_ing = stats.get("top_ingredients", [])[:10] # Top 10
    if top_ing:
        ings = [item["ingredient"] for item in top_ing]
        counts = [item["count"] for item in top_ing]
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x=counts, y=ings, palette="crest")
        plt.title("Top 10 Pigmentation Ingredients by Frequency", pad=15, fontweight='bold')
        plt.xlabel("Number of Products")
        plt.tight_layout()
        plt.savefig("report/charts/top_ingredients.png", dpi=300)
        plt.close()

def build_markdown_report(stats, insights):
    """Assembles the final markdown report shell."""
    
    # 1. Header & Meta
    meta = stats.get("dataset_meta", {})
    md = [
        "# R&D Market Intelligence: Pigmentation Sunscreens",
        f"**Dataset Snapshot:** {meta.get('total_products', 87)} total products deduplicated across {', '.join(meta.get('platforms', {}).keys()).title()}.",
        f"**Analyzed Subset:** {meta.get('products_with_ingredient_data', 52)} products with verified ingredient data.\n",
        "---\n"
    ]
    
    # 2. Executive Summary
    md.append("## 1. Executive Summary\n")
    for item in insights.get("executive_summary", []):
        md.append(f"* **{item['finding']}**")
        md.append(f"  * *Data:* {item['supporting_stat']}\n")
        
    md.append("---\n")
    
    # 3. Market Data Visualizations
    md.append("## 2. Market Data & Distributions\n")
    md.append("### Formulation Penetration by Price Tier")
    md.append("![Price Crosstab](charts/price_crosstab.png)\n")
    md.append("### Ingredient Frequency (Top 10)")
    md.append("![Top Ingredients](charts/top_ingredients.png)\n")
    md.append("---\n")
    
    # 4. Ingredient Landscape
    land = insights.get("ingredient_landscape", {})
    md.append("## 3. Ingredient Landscape\n")
    md.append(f"{land.get('narrative', '')}\n")
    md.append(f"**Top Actives Commentary:** {land.get('top_ingredients_commentary', '')}\n")
    
    if land.get("emerging_low_competition"):
        md.append("### Emerging / Low-Competition Actives")
        for item in land["emerging_low_competition"]:
            md.append(f"* **{item['ingredient']}** (Used by {item['brand_count']} brands): {item['note']}")
        md.append("\n---\n")
        
    # 5. Claims Analysis
    claims = insights.get("claims_analysis", {})
    md.append("## 4. Claims Analysis\n")
    
    md.append("### Saturated Claims")
    for c in claims.get("saturated", []):
        md.append(f"* **{c['claim_or_pair']}** ({c['pct']*100:.1f}%): {c['commentary']}")
        
    md.append("\n### Underrepresented Pigmentation Claims")
    for c in claims.get("underrepresented", []):
        md.append(f"* **{c['claim']}** ({c['pct']*100:.1f}%): {c['commentary']}")
    md.append("\n---\n")
    
    # 6. Strategic White Space Opportunities
    md.append("## 5. Strategic White Space Opportunities\n")
    for idx, gap in enumerate(insights.get("white_space_opportunities", []), 1):
        md.append(f"### Opportunity {idx}: {gap['gap']}")
        md.append(f"* **The Gap:** {gap['why_it_is_a_gap']}")
        md.append(f"* **Supporting Evidence:** {gap['supporting_data']}")
        md.append(f"* **Proposed Product Direction:** {gap['proposed_product_direction']}\n")
        
    md.append("---\n")
    
    # 7. Limitations / Methodology
    md.append("## 6. Limitations & Methodology\n")
    for limitation in insights.get("limitations", []):
        md.append(f"* {limitation}")
        
    # Write to file
    with open("report/final_report.md", "w") as f:
        f.write("\n".join(md))

if __name__ == "__main__":
    print("Starting Stage 5: Report Assembly")
    stats_data, insights_data = load_data()
    
    print("Generating charts...")
    generate_charts(stats_data)
    
    print("Building Markdown document...")
    build_markdown_report(stats_data, insights_data)
    
    print("SUCCESS: Final report generated at report/final_report.md")