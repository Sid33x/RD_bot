import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

# 1. Extraction Schema for Firecrawl
class FirecrawlProductSchema(BaseModel):
    product_name: str = Field(description="The full name of the sunscreen product")
    brand: Optional[str] = Field(default=None, description="The brand of the product")
    mrp: Optional[float] = Field(default=None, description="Maximum Retail Price before discounts")
    selling_price: Optional[float] = Field(default=None, description="Current discounted selling price")
    discount_pct: Optional[float] = Field(default=None, description="Discount percentage if available")
    quantity_value: Optional[float] = Field(default=None, description="Numeric value of quantity (e.g., 50)")
    quantity_unit: Optional[str] = Field(default=None, description="Unit of quantity (e.g., 'g', 'ml')")
    ingredients_raw: Optional[str] = Field(default=None, description="Verbatim scraped text of ingredients")
    key_ingredients: List[str] = Field(default_factory=list, description="List of key active ingredients mentioned (e.g., Niacinamide)")
    
    # --- NEW R&D WHITESPACE FIELDS ---
    ingredient_concentrations: Optional[Dict[str, str]] = Field(default=None, description="Extracted percentages of active ingredients, e.g., {'Niacinamide': '5%', 'Vitamin C': '10%'}")
    finish: Optional[str] = Field(default=None, description="Cosmetic finish or texture (e.g., Matte, Dewy, Invisible, Tinted, Gel)")
    skin_types: List[str] = Field(default_factory=list, description="Targeted skin types (e.g., Oily, Dry, Sensitive, All)")
    free_from: List[str] = Field(default_factory=list, description="Explicitly excluded ingredients (e.g., Fragrance-Free, Silicone-Free)")
    pregnancy_safe: Optional[bool] = Field(default=None, description="True if explicitly marketed as safe for pregnancy/lactation")
    # ---------------------------------
    
    claims_raw: Optional[str] = Field(default=None, description="Verbatim text of product claims/benefits")
    claims: List[str] = Field(default_factory=list, description="List of claims like 'SPF 50', 'Sulfate-Free', 'Anti-aging'")
    spf: Optional[str] = Field(default=None, description="SPF value if mentioned (e.g., '50', '30')")
    pa_rating: Optional[str] = Field(default=None, description="PA rating if mentioned (e.g., 'PA++++')")
    rating: Optional[float] = Field(default=None, description="Product rating out of 5")
    review_count: Optional[int] = Field(default=None, description="Total number of reviews")
    description: Optional[str] = Field(default=None, description="Product description")
    availability: Optional[str] = Field(default=None, description="'In Stock' or 'Out of Stock'")

class FirecrawlDiscoverySchema(BaseModel):
    product_urls: List[str] = Field(description="List of exact product detail page URLs found on the page")

class RawFetchResult(BaseModel):
    product_url: str
    raw_markdown: str
    extracted_data: Optional[FirecrawlProductSchema]
    error_message: Optional[str] = None

# 2. Canonical Database Record
class ProductRecord(BaseModel):
    platform: str
    platform_product_id: str
    product_url: str
    product_name: str
    brand: Optional[str] = None
    mrp: Optional[float] = None
    selling_price: Optional[float] = None
    discount_pct: Optional[float] = None
    currency: str = "INR"
    quantity_value: Optional[float] = None
    quantity_unit: Optional[str] = None
    ingredients_raw: Optional[str] = None
    key_ingredients: List[str] = Field(default_factory=list)
    
    # --- NEW R&D WHITESPACE FIELDS ---
    ingredient_concentrations: Optional[Dict[str, str]] = None
    finish: Optional[str] = None
    skin_types: List[str] = Field(default_factory=list)
    free_from: List[str] = Field(default_factory=list)
    pregnancy_safe: Optional[bool] = None
    # ---------------------------------
    
    claims_raw: Optional[str] = None
    claims: List[str] = Field(default_factory=list)
    spf: Optional[str] = None
    pa_rating: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    description: Optional[str] = None
    availability: Optional[str] = None
    scraped_at: datetime.datetime
    source_response_type: str = "firecrawl_schema_json"
    scrape_status: str
    parser_version: str = "firecrawl-2.0"
    run_id: str