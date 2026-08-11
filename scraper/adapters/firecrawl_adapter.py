import os
import datetime
import requests
from urllib.parse import urlparse
from typing import List
from scraper.adapters.base import MarketplaceAdapter
from scraper.models import (
    FirecrawlProductSchema, 
    ProductRecord, 
    RawFetchResult
)

class FirecrawlAdapter(MarketplaceAdapter):
    def __init__(self, platform_name: str):
        self.platform = platform_name
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY is missing from environment variables!")
        
        self.api_url = "https://api.firecrawl.dev/v1/scrape"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _extract_product_id(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.path.strip("/").split("/")[-1]

    def discover(self, search_url: str) -> List[str]:
        try:
            # FIX: Use native 'links' format and force a 3-second render delay for SPAs
            payload = {
                "url": search_url,
                "formats": ["links"],
                "waitFor": 3000  # Gives Purplle/Maccaron time to load the product grid
            }
            
            response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()
            
            res_data = response.json()
            # Extract raw links directly from the payload
            all_links = res_data.get("data", {}).get("links", [])
            
            valid_urls = []
            for link in all_links:
                link_lower = link.lower()
                
                # Platform-specific URL filtering to ensure we only get Product Pages
                if self.platform == "nykaa" and ("/p/" in link_lower or "productid=" in link_lower):
                    valid_urls.append(link)
                elif self.platform == "purplle" and "/product/" in link_lower:
                    valid_urls.append(link)
                elif self.platform == "maccaron" and "/products/" in link_lower:
                    valid_urls.append(link)
                    
            return valid_urls
            
        except Exception as e:
            print(f"❌ DISCOVERY ERROR on {self.platform}: {type(e).__name__} - {str(e)}")
            return []

    def fetch_product(self, url: str) -> RawFetchResult:
        try:
            payload = {
                "url": url,
                "formats": ["markdown", "json"],
                "jsonOptions": {
                    "schema": FirecrawlProductSchema.model_json_schema()
                }
            }
            response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()
            
            res_data = response.json()
            data_payload = res_data.get("data", {})
            
            extracted_json = data_payload.get("json", {})
            raw_markdown = data_payload.get("markdown", "")
            
            if not extracted_json:
                raise ValueError("Firecrawl returned empty JSON.")
                
            extracted_data = FirecrawlProductSchema(**extracted_json)
            
            return RawFetchResult(
                product_url=url,
                raw_markdown=raw_markdown,
                extracted_data=extracted_data
            )
        except Exception as e:
            print(f"❌ FETCH ERROR on {url}: {type(e).__name__} - {str(e)}")
            return RawFetchResult(
                product_url=url,
                raw_markdown="",
                extracted_data=None,
                error_message=str(e)
            )

    def parse(self, raw: RawFetchResult, run_id: str) -> ProductRecord:
        platform_id = self._extract_product_id(raw.product_url)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if raw.error_message or not raw.extracted_data:
            return ProductRecord(
                platform=self.platform,
                platform_product_id=platform_id,
                product_url=raw.product_url,
                product_name="ERROR",
                scraped_at=now,
                scrape_status="error",
                source_response_type="firecrawl_error",
                run_id=run_id
            )

        data = raw.extracted_data
        
        return ProductRecord(
            platform=self.platform,
            platform_product_id=platform_id,
            product_url=raw.product_url,
            product_name=data.product_name,
            brand=data.brand,
            mrp=data.mrp,
            selling_price=data.selling_price,
            discount_pct=data.discount_pct,
            quantity_value=data.quantity_value,
            quantity_unit=data.quantity_unit,
            ingredients_raw=data.ingredients_raw,
            key_ingredients=data.key_ingredients,
            
            ingredient_concentrations=data.ingredient_concentrations,
            finish=data.finish,
            skin_types=data.skin_types,
            free_from=data.free_from,
            pregnancy_safe=data.pregnancy_safe,
            
            claims_raw=data.claims_raw,
            claims=data.claims,
            spf=data.spf,
            pa_rating=data.pa_rating,
            rating=data.rating,
            review_count=data.review_count,
            description=data.description,
            availability=data.availability,
            scraped_at=now,
            scrape_status="success",
            source_response_type="firecrawl_schema_json",
            run_id=run_id
        )