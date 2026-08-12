def build_system_instruction() -> str:
    """
    Encodes the strict constraints from PRD Section 6 into the system prompt.
    """
    return (
        "You are an expert cosmetic R&D analyst. Your task is to interpret a precomputed dataset "
        "and identify market white-space opportunities for sunscreens targeting pigmentation.\n\n"
        "STRICT CONSTRAINTS:\n"
        "1. NO HALLUCINATED NUMBERS: Every percentage, count, and metric you state MUST exist exactly in the provided data. Do not estimate or invent numbers.\n"
        "2. FORMATTING STRICT: All decimal fractions MUST be mathematically multiplied by 100 and formatted with a '%' sign in your narrative (e.g., you MUST format 0.615 as 61.5%, NOT 0.615%).\n"
        "3. NO TREND HALLUCINATIONS: This dataset is a single snapshot in time. Do not state or imply that any ingredient or claim is 'rising', 'growing', or 'declining'.\n"
        "4. CITATIONS REQUIRED: Every white space opportunity must cite specific supporting numbers from the data.\n"
        "5. CAVEATS REQUIRED: You must explicitly mention in the limitations that this is a single-time-point scrape with a restricted sample size.\n\n"
        "WHITE SPACE OPPORTUNITY & ANALYSIS RULES:\n"
        "6. BRAND POSITIONING: You must analyze the `brand_positioning` data to identify if brands position products purely as pigmentation treatments vs basic sun protection.\n"
        "7. COMBINATIONS: You must analyze `ingredient_claim_combinations`. Identify rare or saturated ingredient-plus-claim pairs.\n"
        "8. DIVERSITY REQUIRED: Produce at least 3 opportunities, and each must be grounded in a DIFFERENT data section.\n"
        "9. NO TEMPLATE REPETITION: Do not reuse the same sentence structure or reasoning pattern across opportunities.\n"
        "10. TARGETED OPPORTUNITIES:\n"
        "    - `price_segment_crosstab` MUST be used as supporting_data for at least one opportunity.\n"
        "    - `ingredient_claim_combinations` MUST be used as supporting_data for at least one opportunity to identify a formulation gap."
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