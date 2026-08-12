import re
from typing import List

def check_trend_language(text: str) -> List[str]:
    """
    Scans the LLM output for forbidden temporal/trend language applied to ingredients/claims.
    Returns a list of flagged sentences for manual review in the run summary.
    """
    # Split text into rough sentences based on punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    flagged_sentences = []
    
    trend_patterns = [
        r'\brising\b', 
        r'\bdeclining\b', 
        r'\bincreasingly\b',
        r'\bgrowing\b', 
        r'\bdecreasing\b', 
        r'\bemerging trend\b',
        r'\bgaining popularity\b', 
        r'\blosing popularity\b'
    ]
    
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in trend_patterns]
    
    for sentence in sentences:
        if any(p.search(sentence) for p in compiled_patterns):
            # Clean up JSON formatting artifacts (quotes, brackets) for readability
            clean_sentence = sentence.replace('"', '').replace('{', '').replace('}', '').strip()
            flagged_sentences.append(clean_sentence)
            
    return flagged_sentences