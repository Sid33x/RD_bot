import argparse
from dotenv import load_dotenv
from scraper.orchestrator import ScrapeOrchestrator

if __name__ == "__main__":
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Skincare Scraper Execution (Task 1)")
    parser.add_argument("--platforms", type=str, default="nykaa,purplle", help="Comma-separated list of platforms to scrape")
    args = parser.parse_args()
    
    platforms = [p.strip() for p in args.platforms.split(",")]
    
    orchestrator = ScrapeOrchestrator(target_platforms=platforms)
    orchestrator.run()