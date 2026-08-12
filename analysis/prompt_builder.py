def build_system_instruction() -> str:
    """
    Encodes the strict constraints from PRD Section 6 into the system prompt.
    """
    return (
        "You are an expert cosmetic R&D analyst. Your task is to interpret a precomputed dataset "
        "and identify market white-space opportunities for sunscreens targeting pigmentation.\n\n"
        "STRICT CONSTRAINTS:\n"
        "1. NO HALLUCINATED NUMBERS: Every percentage, count, and metric you state MUST exist exactly in the provided data. Do not estimate or invent numbers.\n"
        "2. NO TREND HALLUCINATIONS: This dataset is a single snapshot in time. Do not state or imply that any ingredient or claim is 'rising', 'growing', or 'declining'.\n"
        "3. CITATIONS REQUIRED: Every white space opportunity must cite specific supporting numbers from the data.\n"
        "4. CAVEATS REQUIRED: You must explicitly mention in the limitations that this is a single-time-point scrape with a restricted sample size.\n\n"
        "WHITE SPACE OPPORTUNITY RULES:\n"
        "5. DIVERSITY REQUIRED: Produce at least 3 opportunities, and each must be grounded in a DIFFERENT data section — "
        "do not generate all 3 from 'rare_ingredients' alone. Draw from distinct sections such as: "
        "price_segment_crosstab (e.g. a price tier under-indexing on pigmentation ingredients), "
        "underrepresented_pigmentation_claims (a claim rarely made despite relevant ingredients existing), "
        "saturated_claim_pairs vs. rare_ingredients (a common claim with no premium/differentiated ingredient backing it), "
        "and rare_ingredients (low-competition actives).\n"
        "6. NO TEMPLATE REPETITION: Do not reuse the same sentence structure or reasoning pattern across opportunities — "
        "each 'why_it_is_a_gap' must reflect the specific data pattern that motivates it, not a generic 'few brands use X' justification applied interchangeably.\n"
        "7. price_segment_crosstab MUST be used as supporting_data for at least one opportunity if it shows a meaningful spread across tiers."
    )

def build_user_prompt(stats_summary_text: str, retry_feedback: str = None) -> str:
    """
    Injects the full stats_summary.json verbatim and handles retry feedback.
    """
    prompt = f"Here is the precomputed statistical summary of the market:\n\n{stats_summary_text}"
    
    if retry_feedback:
        prompt += (
            "\n\n=======================================================\n"
            "YOUR PREVIOUS ATTEMPT FAILED THE PIPELINE GATES.\n"
            "FIX THE FOLLOWING ISSUES:\n"
            f"{retry_feedback}\n"
            "=======================================================\n"
            "Regenerate your response ensuring all numbers used exist in the original data."
        )
        
    return prompt