import time
import uuid
import json
from typing import List
from scraper.adapters.firecrawl_adapter import FirecrawlAdapter
from scraper.storage import SQLiteStorage
from scraper.logging_setup import setup_logger

class ScrapeOrchestrator:
    def __init__(self, target_platforms: List[str]):
        self.platforms = target_platforms
        self.run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.db = SQLiteStorage()
        self.logger = setup_logger(self.run_id)
        self.target_count = 60
        
        # Unified Discovery Configurations - Using distinct queries to bypass lazy-loading
        self.discovery_urls = {
            "nykaa": [
                "https://www.nykaa.com/search/result/?q=sunscreen+pigmentation",
                "https://www.nykaa.com/search/result/?q=niacinamide+sunscreen",
                "https://www.nykaa.com/search/result/?q=vitamin+c+sunscreen",
                "https://www.nykaa.com/search/result/?q=dark+spot+sunscreen",
                "https://www.nykaa.com/search/result/?q=alpha+arbutin+sunscreen"
            ],
            "purplle": [
                "https://www.purplle.com/search?q=pigmentation%20sunscreen",
                "https://www.purplle.com/search?q=niacinamide%20sunscreen",
                "https://www.purplle.com/search?q=vitamin%20c%20sunscreen",
                "https://www.purplle.com/search?q=brightening%20sunscreen",
                "https://www.purplle.com/search?q=dark%20spot%20sunscreen"
            ],
            "maccaron": [
                "https://maccaron.in/en/products/search/?q=sunscreen",
                "https://maccaron.in/en/products/search/?q=spf+50",
                "https://maccaron.in/en/products/search/?q=sun+cream",
                "https://maccaron.in/en/products/search/?q=brightening+sunscreen"
            ]
        }

    def run(self):
        self.logger.info("Starting orchestration run", extra={"extra_info": {"run_id": self.run_id, "event_type": "run_start"}})
        metrics = {"total_discovered": 0, "total_success": 0, "total_error": 0}

        for platform in self.platforms:
            self.logger.info(f"Starting platform phase", extra={"extra_info": {"platform": platform}})
            adapter = FirecrawlAdapter(platform_name=platform)
            product_urls = []

            # Automated Discovery Strategy for all platforms
            print(f"Discovering {platform.capitalize()} URLs across multiple pages...")
            for search_url in self.discovery_urls.get(platform, []):
                discovered = adapter.discover(search_url)
                product_urls.extend(discovered)
                
                # Stop discovering if we hit our target (adding a buffer just in case of fetch failures)
                if len(product_urls) >= (self.target_count + 10):
                    break

            # Deduplicate URLs
            product_urls = list(set(product_urls))
            metrics["total_discovered"] += len(product_urls)
            self.logger.info("Discovery complete", extra={"extra_info": {"platform": platform, "url_count": len(product_urls)}})

            # Fetching Phase
            print(f"Beginning fetch for up to {self.target_count} {platform} products...")
            for url in product_urls[:self.target_count]:  
                product_id = adapter._extract_product_id(url)
                
                if self.db.is_already_scraped(product_id):
                    self.logger.info("Skipping already scraped", extra={"extra_info": {"product_url": url}})
                    print(f"⏩ Skipping (already scraped): {product_id}")
                    continue

                start_time = time.time()
                raw_result = adapter.fetch_product(url)
                record = adapter.parse(raw_result, self.run_id)
                latency_ms = int((time.time() - start_time) * 1000)

                self.db.save_product(record)
                
                if record.scrape_status == "success":
                    self.db.save_raw_evidence(record.platform_product_id, self.run_id, raw_result.raw_markdown)
                    metrics["total_success"] += 1
                    self.logger.info("Fetch success", extra={"extra_info": {"product_url": url, "latency_ms": latency_ms}})
                    print(f"✅ Extracted: {record.product_name}")
                else:
                    metrics["total_error"] += 1
                    self.logger.error("Fetch error", extra={"extra_info": {"product_url": url, "error": raw_result.error_message}})
                    print(f"❌ Failed: {url}")
                
                time.sleep(2.5) # Rate limiting buffer

        self.db.export_to_parquet()
        self.logger.info("Run complete. Parquet exported.", extra={"extra_info": metrics})
        
        with open("run_summary.json", "w") as f:
            json.dump(metrics, f, indent=2)
        print("\n🎉 Run Complete. Check clean_products_raw.parquet for the output.")