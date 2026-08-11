import logging
import json
import os
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        return json.dumps(log_record)

def setup_logger(run_id: str):
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(run_id)
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(f"logs/scraper_{run_id}.jsonl")
    file_handler.setFormatter(JSONFormatter())
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger