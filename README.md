# RD_bot — Sunscreen Market Intelligence Pipeline

An end-to-end AI data pipeline that scrapes sunscreen product listings from Nykaa and Purplle, cleans and deduplicates them, performs statistical market aggregation, and runs a schema-enforced, grounding-verified LLM analysis layer to produce an executive-ready R&D white-space report.

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Core runtime |
| Scraping | Firecrawl API | Anti-bot-resilient extraction from Nykaa & Purplle |
| Data processing | Pandas, PyArrow | Cleaning, normalization, Parquet storage |
| Deduplication | RapidFuzz | Fuzzy matching on brand + product name + quantity → cross-platform product grouping |
| AI analysis | Google Gemini API | Schema-constrained JSON generation for market insights |
| Schema validation | Pydantic v2 | Response schema definition + custom flattener for Gemini's `$ref`/`allOf` constraints |
| Visualization | Matplotlib | Report charts |

---

## Architecture

```
[ Nykaa & Purplle listings ]
        │
        ▼
1. SCRAPER (scraper/)
        │ Firecrawl adapter → raw product records
        ▼  scraped_sunscreens.csv
2. CLEAN & DEDUP (processing/clean.py)
        │ Ingredient canonicalization, claims normalization, price tiering,
        │ RapidFuzz cross-platform dedup (threshold ≥90) → canonical_product_group_id
        ▼  clean_products.parquet
3. AGGREGATION (processing/aggregate.py)
        │ Ingredient frequency, pigmentation-ingredient tagging, rare/differentiation
        │ ingredients, claim frequency & saturation, price-tier × pigmentation crosstab
        ▼  stats_summary.json
4. AI ANALYSIS (analysis/)
        │ Gemini + flattened Pydantic schema → structured insights
        ├─ grounding_check.py  (blocking: every number must match stats_summary.json, ±0.5% tolerance)
        ├─ trend_check.py      (non-blocking: flags temporal language for human review)
        │       fail → 1 retry with failure detail appended to prompt
        ▼  insights.json
5. REPORT ASSEMBLY (report/)
        │ Charts + templated markdown — no LLM call, pure templating
        ▼  final_report.md
```

### Stage notes

1. **Scraping** — Nykaa + Purplle chosen; Amazon/Myntra excluded (anti-bot cost outweighed benefit for this scope). Built on Firecrawl rather than a hand-rolled Playwright scraper, trading some raw-JSON traceability for build speed and resilience to anti-bot measures.
2. **Cleaning & dedup** — ingredient and claims vocabularies are normalized against hand-built config dictionaries (`processing/config/`), not inferred automatically, since the ingredient/claims vocabulary in this dataset is small enough to curate directly. Price tiers (Budget/Mid/Premium) are computed per-run from the actual `selling_price` distribution (33rd/66th percentile), not hardcoded cutoffs.
3. **Aggregation** — every countable statistic (frequencies, crosstabs, rare-ingredient/brand lists) is computed deterministically in pandas here, not left for the LLM to estimate. All ingredient-based stats are scoped to the subset of products with ingredient data, kept separate from platform-wide stats. The dataset is a single-snapshot scrape, so trend directionality (rising/declining ingredients) is explicitly marked not computable rather than inferred.
4. **AI analysis** — the LLM's role is interpretation and synthesis only, never counting. Every claim it produces is checked against the numbers actually present in `stats_summary.json`; any number that doesn't trace back to the source data fails the run and triggers a bounded retry. No vector database or retrieval is used — the input is small enough to inject directly into the prompt.
5. **Report assembly** — deterministic templating over `insights.json` + `stats_summary.json`, no further LLM calls.

---

## Repository Structure

```
RD_bot/
├── scraper/
│   ├── adapters/
│   │   ├── base.py
│   │   └── firecrawl_adapter.py
│   ├── models.py
│   ├── orchestrator.py
│   └── cli.py
├── processing/
│   ├── config/
│   │   ├── ingredient_synonyms.json
│   │   ├── pigmentation_ingredients.json
│   │   └── claims_denylist.json
│   ├── clean.py
│   ├── aggregate.py
│   └── quality_gates.py
├── analysis/
│   ├── schema.py            # Pydantic response schema + Gemini-compatible flattener
│   ├── prompt_builder.py
│   ├── llm_client.py
│   ├── grounding_check.py
│   ├── trend_check.py
│   └── run.py
├── report/
│   ├── charts/
│   ├── builder.py
│   └── final_report.md
├── data/
│   ├── scraped_sunscreens.csv
│   ├── clean_products.parquet
│   ├── stats_summary.json
│   └── insights.json
├── docs/
│   ├── prd.md / architecture.md                  # Stage 1
│   ├── prd_stage2_3.md / architecture_stage2_3.md # Stage 2–3
│   └── prd_stage4.md / architecture_stage4.md     # Stage 4
├── METHODOLOGY.md
├── requirements.txt
└── Assignment_Report.pdf
```

---

## Getting Started

**Prerequisites:** Python 3.11+, a Google Gemini API key. A Firecrawl API key is only required to re-scrape live data — sample scraped data is included, so re-scraping is optional.

```bash
git clone https://github.com/your-username/RD_bot.git
cd RD_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export GEMINI_API_KEY="your-gemini-api-key"
export FIRECRAWL_API_KEY="your-firecrawl-api-key"   # optional — only needed to re-scrape
```

## Running the Pipeline

```bash
# Step 1 — scrape (optional; scraped_sunscreens.csv is already included)
python -m scraper.cli --platform nykaa --platform purplle

# Step 2 — clean, dedup, aggregate
python processing/clean.py
python processing/aggregate.py

# Step 3 — AI analysis + grounding validation
python analysis/run.py

# Step 4 — charts + final report
python report/builder.py
```

Each stage writes its output to `data/` before the next stage runs, so any stage can be re-run independently against the previous stage's saved output without re-running the whole pipeline.

---

## Quality Control

- **Grounding gate** (`analysis/grounding_check.py`, blocking): extracts every number stated in the LLM's output and verifies it matches a number present in `stats_summary.json`, within ±0.5% tolerance for rounding. An unmatched number fails the run and triggers one bounded retry with the specific discrepancy appended to the prompt; a second failure halts the pipeline rather than shipping an ungrounded report.
- **Temporal-language guard** (`analysis/trend_check.py`, non-blocking): flags rising/declining/growing-style phrasing for human review, since this is a single-snapshot dataset that cannot support trend claims — flagged rather than hard-failed, since distinguishing "emerging, low-competition ingredient" from an actual (unsupportable) trend claim is a judgment call, not a keyword match.
- **Deterministic aggregation**: every frequency, crosstab, and rare-ingredient count in `stats_summary.json` is computed in pandas, not by the LLM — the LLM never counts, only interprets.
- **Traceability**: every number in the final report traces back through `insights.json` → `stats_summary.json` → `clean_products.parquet` → the original scraped listing.

See `METHODOLOGY.md` for the full account of data-quality issues found during the build (scraper 403s, a price-crosstab bug, a raw-vs-deduplicated count mismatch) and how each was resolved — kept separate from this README so the two documents serve different readers.
