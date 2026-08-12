import re
from typing import Tuple, List, Set

def extract_numbers_from_string(text: str) -> Set[float]:
    """Regex-extracts all standalone numbers (integers and decimals) from a string."""
    matches = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    return {float(m) for m in matches}

def extract_source_numbers(data) -> Set[float]:
    """Recursively walks the source JSON to build the authorized truth set of numbers."""
    numbers = set()
    
    if isinstance(data, dict):
        for v in data.values():
            numbers.update(extract_source_numbers(v))
    elif isinstance(data, list):
        for item in data:
            numbers.update(extract_source_numbers(item))
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        numbers.add(float(data))
        # If it's a percentage ratio, authorize its human-readable * 100 format
        if 0.0 <= data <= 1.0:
            numbers.add(float(data) * 100.0)
    elif isinstance(data, str):
        # Extract numbers embedded in strings (e.g., "SPF 50" -> 50.0)
        numbers.update(extract_numbers_from_string(data))
        
    return numbers

def check_grounding(insights_text: str, stats_summary: dict, tolerance: float = 0.6) -> Tuple[bool, List[float]]:
    """
    Validates that every number in the LLM output exists in the source data.
    Tolerance is set to 0.6 to safely handle standard LLM rounding (e.g., 63.5% -> 64%).
    """
    source_numbers = extract_source_numbers(stats_summary)
    
    # Authorize structural and common rhetorical numbers required by the prompt
    structural_numbers = {1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0, 100.0}
    allowed_numbers = source_numbers.union(structural_numbers)
    
    output_numbers = extract_numbers_from_string(insights_text)
    
    unmatched = []
    for num in output_numbers:
        # Check if the generated number is within `tolerance` of any allowed number
        if not any(abs(num - allowed) <= tolerance for allowed in allowed_numbers):
            unmatched.append(num)
            
    # Deduplicate unmatched numbers for cleaner error reporting during retries
    unmatched = sorted(list(set(unmatched)))
    
    passed = len(unmatched) == 0
    return passed, unmatched