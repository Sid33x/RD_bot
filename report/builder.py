import json
import os
import re
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Ensure directories exist
os.makedirs("report/charts", exist_ok=True)

def load_data():
    with open("data/stats_summary.json", "r") as f:
        stats = json.load(f)
    with open("data/insights.json", "r") as f:
        insights = json.load(f)
    return stats, insights

def fix_decimals(text):
    """Intercepts decimal errors (e.g., 0.615%) and formats them to 61.5%."""
    if not isinstance(text, str):
        return text
    def replacer(match):
        val = float(match.group(1))
        # If the value is less than 1, it's a raw fraction that needs * 100
        if val < 1.0: 
            return f"{val * 100:.1f}%"
        return match.group(0)
    return re.sub(r'([0-9]*\.[0-9]+)%', replacer, text)

def generate_charts(stats):
    """Generates standard R&D charts from the stats summary."""
    sns.set_theme(style="whitegrid")
    
    # Dynamic subset count
    subset_n = stats.get("dataset_meta", {}).get("products_with_ingredient_data", "N/A")
    
    # Chart 1: Price Tier Crosstab
    crosstab = stats.get("price_segment_crosstab", [])
    if crosstab:
        tiers = [item["price_tier"] for item in crosstab]
        pcts = [item["pct_with_pigmentation_ingredient"] * 100 for item in crosstab]
        
        plt.figure(figsize=(8, 5))
        ax = sns.barplot(x=tiers, y=pcts, palette="Blues_d")
        plt.title(f"Pigmentation Actives by Price Tier (Subset n={subset_n})", pad=15, fontweight='bold')
        plt.ylabel("% of Products Containing Actives")
        plt.ylim(0, 110)
        
        for i, p in enumerate(ax.patches):
            ax.annotate(f"{pcts[i]:.1f}%", 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='bottom', xytext=(0, 5), textcoords='offset points')
        
        plt.tight_layout()
        plt.savefig("report/charts/price_crosstab.png", dpi=300)
        plt.close()

    # Chart 2: Top Ingredients (Top 20)
    top_ing = stats.get("top_ingredients", [])[:20]
    if top_ing:
        ings = [item["ingredient"] for item in top_ing]
        counts = [item["count"] for item in top_ing]
        
        plt.figure(figsize=(10, 8))
        sns.barplot(x=counts, y=ings, palette="crest")
        plt.title("Top 20 Pigmentation Ingredients by Frequency", pad=15, fontweight='bold')
        plt.xlabel("Number of Products")
        plt.tight_layout()
        plt.savefig("report/charts/top_ingredients.png", dpi=300)
        plt.close()

    # Chart 3 (NEW): Top Claims Frequency
    top_claims = stats.get("top_claims", [])[:15]
    if top_claims:
        claims_labels = [item["claim"] for item in top_claims]
        claims_pcts = [item["pct"] * 100 for item in top_claims]

        plt.figure(figsize=(9, 7))
        ax = sns.barplot(x=claims_pcts, y=claims_labels, palette="flare")
        plt.title("Top Product Claims by Frequency", pad=15, fontweight='bold')
        plt.xlabel("% of Products")
        for i, p in enumerate(ax.patches):
            ax.annotate(f"{claims_pcts[i]:.1f}%",
                        (p.get_width(), p.get_y() + p.get_height() / 2.),
                        ha='left', va='center', xytext=(5, 0), textcoords='offset points')
        plt.tight_layout()
        plt.savefig("report/charts/top_claims.png", dpi=300)
        plt.close()

    # Chart 4 (NEW): Brand Positioning Scatter (Pigmentation vs Basic SPF claims)
    positioning = stats.get("brand_positioning", [])
    if positioning:
        df_pos = pd.DataFrame(positioning)
        plt.figure(figsize=(8, 7))
        ax = sns.scatterplot(
            data=df_pos, x="pigmentation_claim_count", y="basic_spf_claim_count",
            s=120, color="#2C6E91", edgecolor="black"
        )
        for _, row in df_pos.iterrows():
            ax.annotate(row["brand"], (row["pigmentation_claim_count"], row["basic_spf_claim_count"]),
                        xytext=(6, 4), textcoords='offset points', fontsize=8)
        plt.title("Brand Positioning: Pigmentation vs. Basic SPF Claims", pad=15, fontweight='bold')
        plt.xlabel("Pigmentation Claim Count")
        plt.ylabel("Basic SPF Claim Count")
        plt.tight_layout()
        plt.savefig("report/charts/brand_positioning.png", dpi=300)
        plt.close()

    # Chart 5 (NEW): Ingredient x Claim Heatmap
    combos = stats.get("ingredient_claim_combinations", [])
    if combos:
        df_combo = pd.DataFrame(combos)
        pivot = df_combo.pivot_table(index="ingredient", columns="claim", values="count", fill_value=0)
        plt.figure(figsize=(10, 6))
        sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGnBu", cbar_kws={"label": "Product Count"})
        plt.title("Ingredient x Claim Co-occurrence", pad=15, fontweight='bold')
        plt.ylabel("")
        plt.xlabel("")
        plt.xticks(rotation=40, ha="right")
        plt.tight_layout()
        plt.savefig("report/charts/ingredient_claim_heatmap.png", dpi=300)
        plt.close()

    # Chart 6 (NEW, conditional): Pigmentation Ingredient Adoption by Price Tier
    # Requires aggregate.py to emit "price_tier_ingredient_breakdown":
    # [{"price_tier": "Budget", "ingredient": "Niacinamide", "pct": 0.7}, ...]
    tier_ing = stats.get("price_tier_ingredient_breakdown", [])
    if tier_ing:
        df_ti = pd.DataFrame(tier_ing)
        df_ti["pct"] = df_ti["pct"] * 100
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_ti, x="ingredient", y="pct", hue="price_tier", palette="viridis")
        plt.title("Pigmentation Ingredient Adoption by Price Tier", pad=15, fontweight='bold')
        plt.ylabel("% of Products in Tier")
        plt.xlabel("")
        plt.xticks(rotation=30, ha="right")
        plt.legend(title="Price Tier")
        plt.tight_layout()
        plt.savefig("report/charts/tier_ingredient_breakdown.png", dpi=300)
        plt.close()


def build_ingredient_roster_table(stats):
    """Markdown table: full pigmentation-ingredient roster with brands."""
    rows = stats.get("pigmentation_ingredients", [])
    if not rows:
        return ""
    lines = ["| Ingredient | Count | % of Products | Brands |", "|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["count"]):
        brands = ", ".join(r.get("brands", []))
        lines.append(f"| {r['ingredient']} | {r['count']} | {r['pct']*100:.1f}% | {brands} |")
    return "\n".join(lines)


def build_rare_ingredients_table(stats, max_brand_count=2, limit=25):
    """Markdown table: rare/emerging ingredients (brand_count <= threshold)."""
    rows = [r for r in stats.get("rare_ingredients", []) if r.get("brand_count", 0) <= max_brand_count]
    if not rows:
        return ""
    rows = rows[:limit]
    lines = ["| Ingredient | Brand Count | Brand(s) |", "|---|---|---|"]
    for r in rows:
        brands = ", ".join(r.get("brands", []))
        lines.append(f"| {r['ingredient']} | {r['brand_count']} | {brands} |")
    return "\n".join(lines)


def build_markdown_report(stats, insights):
    """Assembles the final markdown report shell."""
    
    meta = stats.get("dataset_meta", {})
    md = [
        "# R&D Market Intelligence: Pigmentation Sunscreens",
        f"**Dataset Snapshot:** {meta.get('total_products', 87)} total products deduplicated across {', '.join(meta.get('platforms', {}).keys()).title()}.",
        f"**Analyzed Subset:** {meta.get('products_with_ingredient_data', 52)} products with verified ingredient data.\n",
        "---\n"
    ]
    
    # 1. Executive Summary
    md.append("## 1. Executive Summary\n")
    for item in insights.get("executive_summary", []):
        finding = fix_decimals(item.get('finding', ''))
        stat = fix_decimals(item.get('supporting_stat', ''))
        md.append(f"* **{finding}**")
        md.append(f"  * *Data:* {stat}\n")
        
    md.append("---\n")
    
    # 2. Market Data Visualizations
    md.append("## 2. Market Data & Distributions\n")
    md.append("### Formulation Penetration by Price Tier")
    md.append("![Price Crosstab](charts/price_crosstab.png)\n")
    md.append("### Ingredient Frequency (Top 20)")
    md.append("![Top Ingredients](charts/top_ingredients.png)\n")
    md.append("### Claim Frequency (Top 15)")
    md.append("![Top Claims](charts/top_claims.png)\n")
    md.append("### Ingredient x Claim Co-occurrence")
    md.append("![Ingredient Claim Heatmap](charts/ingredient_claim_heatmap.png)\n")
    if stats.get("price_tier_ingredient_breakdown"):
        md.append("### Pigmentation Ingredient Adoption by Price Tier")
        md.append("![Tier Ingredient Breakdown](charts/tier_ingredient_breakdown.png)\n")
    md.append("---\n")
    
    # 3. Ingredient Landscape
    land = insights.get("ingredient_landscape", {})
    md.append("## 3. Ingredient Landscape\n")
    md.append(f"{fix_decimals(land.get('narrative', ''))}\n")
    md.append(f"**Top Actives Commentary:** {fix_decimals(land.get('top_ingredients_commentary', ''))}\n")

    trend_note = stats.get("trend_note")
    if trend_note:
        md.append(f"**Rising / Declining Ingredients:** {trend_note.capitalize()}. "
                   f"This requires two or more scrape snapshots over time; the current dataset "
                   f"is a single time-point capture, so trend direction cannot be reported.\n")

    if land.get("emerging_low_competition"):
        md.append("### Emerging / Low-Competition Actives (Summary)")
        for item in land["emerging_low_competition"]:
            md.append(f"* **{item.get('ingredient', '')}** (Used by {item.get('brand_count', 0)} brands): {fix_decimals(item.get('note', ''))}")
        md.append("")

    rare_table = build_rare_ingredients_table(stats)
    if rare_table:
        md.append("### Full Rare / Emerging Ingredients Table (<=2 brands)")
        md.append(rare_table)
    md.append("\n---\n")

    # NEW: Full Pigmentation Ingredient Roster (appendix-style table)
    roster_table = build_ingredient_roster_table(stats)
    if roster_table:
        md.append("## 3a. Full Pigmentation-Ingredient Roster\n")
        md.append(roster_table)
        md.append("\n---\n")

    # NEW: Brand Positioning Section (chart + narrative)
    pos_analysis = insights.get("brand_positioning_analysis", [])
    if pos_analysis or stats.get("brand_positioning"):
        md.append("## 4. Brand Positioning (Pigmentation vs Basic SPF)\n")
        if stats.get("brand_positioning"):
            md.append("![Brand Positioning](charts/brand_positioning.png)\n")
        for item in pos_analysis:
            md.append(f"* **{item.get('brand', '')}**: {fix_decimals(item.get('positioning_strategy', ''))}")
        md.append("\n---\n")
        
    # NEW: Ingredient + Claim Combinations Section
    combo_analysis = insights.get("ingredient_claim_analysis", [])
    if combo_analysis:
        md.append("## 5. Ingredient & Claim Combinations\n")
        for item in combo_analysis:
            md.append(f"* **{item.get('combination', '')}**: {fix_decimals(item.get('analysis', ''))}")
        md.append("\n---\n")
        
    # 6. Claims Analysis
    claims = insights.get("claims_analysis", {})
    md.append("## 6. Claims Analysis\n")

    md.append("### Saturated Individual Claims")
    for c in claims.get("saturated", []):
        md.append(f"* **{c.get('claim_or_pair', '')}** ({c.get('pct', 0):.1f}%): {fix_decimals(c.get('commentary', ''))}")

    if not stats.get("saturated_claim_pairs"):
        md.append("\n**Saturated Claim Combinations:** None. No two-claim combination "
                   "(e.g. 'SPF50 + Niacinamide') appears in \u226515% of products at this sample size — "
                   "the market has not converged on a standard claim pairing yet.")

    md.append("\n### Underrepresented Pigmentation Claims")
    for c in claims.get("underrepresented", []):
        md.append(f"* **{c.get('claim', '')}** ({c.get('pct', 0):.1f}%): {fix_decimals(c.get('commentary', ''))}")
    md.append("\n---\n")
    
    # 7. Strategic White Space Opportunities
    md.append("## 7. Strategic White Space Opportunities\n")
    for idx, gap in enumerate(insights.get("white_space_opportunities", []), 1):
        md.append(f"### Opportunity {idx}: {fix_decimals(gap.get('gap', ''))}")
        md.append(f"* **The Gap:** {fix_decimals(gap.get('why_it_is_a_gap', ''))}")
        md.append(f"* **Supporting Evidence:** {fix_decimals(gap.get('supporting_data', ''))}")
        md.append(f"* **Proposed Product Direction:** {fix_decimals(gap.get('proposed_product_direction', ''))}\n")
        
    md.append("---\n")
    
    # 8. Limitations / Methodology
    md.append("## 8. Limitations & Methodology\n")
    for limitation in insights.get("limitations", []):
        md.append(f"* {fix_decimals(limitation)}")

    # NEW: static data-quality caveats (not LLM-generated, always included)
    md.append("* Ingredient extraction can be title-derived and occasionally noisy for products "
               "with sparse listing pages; treat single-product ingredient counts as directional.")
    md.append("* The `claims` field mixes genuine product claims with promotional/marketing phrasing "
               "from listing pages; claim-frequency figures should be read as approximate.")
    md.append(f"* Rising/declining ingredient trends are not reported: {fix_decimals(str(trend_note)) if trend_note else 'not computable from a single time-point scrape'}.")

    # Write to file
    with open("report/final_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

if __name__ == "__main__":
    print("Starting Stage 5: Report Assembly")
    stats_data, insights_data = load_data()
    
    print("Generating charts...")
    generate_charts(stats_data)
    
    print("Building Markdown document...")
    build_markdown_report(stats_data, insights_data)
    
    print("SUCCESS: Final report generated at report/final_report.md")