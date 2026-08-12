from pydantic import BaseModel, Field
from typing import List
import json

# =====================================================================
# 1. Pydantic Models (Defines the exact structure & LLM instructions)
# =====================================================================

class ExecutiveSummaryItem(BaseModel):
    finding: str = Field(
        ..., 
        description="A clear, plain-language R&D finding based on the data."
    )
    supporting_stat: str = Field(
        ..., 
        description="Must explicitly quote/reference an actual numeric field and value present in stats_summary.json."
    )

class EmergingIngredient(BaseModel):
    ingredient: str
    brand_count: int
    note: str

class IngredientLandscape(BaseModel):
    narrative: str
    top_ingredients_commentary: str
    emerging_low_competition: List[EmergingIngredient]

class ClaimSaturated(BaseModel):
    claim_or_pair: str
    pct: float
    commentary: str

class ClaimUnderrepresented(BaseModel):
    claim: str
    pct: float
    commentary: str

class ClaimsAnalysis(BaseModel):
    saturated: List[ClaimSaturated]
    underrepresented: List[ClaimUnderrepresented]

class BrandPositioningInsight(BaseModel):
    brand: str
    positioning_strategy: str = Field(
        ..., 
        description="Analyze if this brand positions its sunscreens purely as a pigmentation treatment vs basic sun protection based on the data."
    )

class ComboAnalysis(BaseModel):
    combination: str
    analysis: str = Field(
        ..., 
        description="Analyze if this specific ingredient + claim combination is saturated, rare, or a missing opportunity."
    )

class WhiteSpaceOpportunity(BaseModel):
    gap: str = Field(
        ..., 
        description="The specific market white space or formulation gap identified."
    )
    supporting_data: str = Field(
        ..., 
        description="Must cite specific numbers (percentages, counts) from stats_summary.json that prove this gap exists."
    )
    why_it_is_a_gap: str
    proposed_product_direction: str = Field(
        ..., 
        description="Actionable R&D concept utilizing the identified gap."
    )

class InsightsOutput(BaseModel):
    executive_summary: List[ExecutiveSummaryItem] = Field(
        ...,
        description="3 to 5 key findings summarizing the dataset."
    )
    ingredient_landscape: IngredientLandscape
    claims_analysis: ClaimsAnalysis
    brand_positioning_analysis: List[BrandPositioningInsight] = Field(
        ...,
        description="Analysis of how specific brands balance pigmentation vs basic sun protection."
    )
    ingredient_claim_analysis: List[ComboAnalysis] = Field(
        ...,
        description="Analysis of the top ingredient + claim combinations."
    )
    white_space_opportunities: List[WhiteSpaceOpportunity] = Field(
        ...,
        description="A minimum of 3 specific, data-backed product opportunities."
    )
    limitations: List[str] = Field(
        ...,
        description="Must explicitly state the known constraints: single time-point snapshot, limited platforms, and sample size restrictions."
    )


# =====================================================================
# 2. Schema Flattener (Prepares the schema for the Gemini API)
# =====================================================================

def get_groq_schema(model: type[BaseModel]) -> dict:
    """
    Extracts the Pydantic schema, recursively resolves all $refs (including 
    those wrapped in allOf by Pydantic v2 field descriptions), and strips 
    Groq-incompatible keys like $defs, default, and title.
    """
    raw_schema = model.model_json_schema()
    defs = raw_schema.pop("$defs", {})

    def resolve(obj):
        if isinstance(obj, dict):
            # Case 1: Bare $ref (No Pydantic Field metadata attached)
            if "$ref" in obj:
                ref_key = obj["$ref"].split("/")[-1]
                return resolve(defs[ref_key].copy())
            
            # Case 2: allOf wrapper (Triggered when Field(description=...) is used on a nested model)
            if "allOf" in obj and isinstance(obj["allOf"], list) and len(obj["allOf"]) == 1:
                inner = obj["allOf"][0]
                if "$ref" in inner:
                    ref_key = inner["$ref"].split("/")[-1]
                    resolved_ref = resolve(defs[ref_key].copy())
                    
                    # Merge the resolved reference object with its sibling keys (like "description")
                    merged = {}
                    for k, v in resolved_ref.items():
                        merged[k] = v
                    for k, v in obj.items():
                        # Skip allOf (since we resolved it) and Gemini-incompatible keys
                        if k not in ["allOf", "default", "title"]:
                            merged[k] = resolve(v)
                    return merged

            # Case 3: Standard dictionary recursion
            resolved_dict = {}
            for k, v in obj.items():
                if k not in ["default", "title"]:
                    resolved_dict[k] = resolve(v)
            return resolved_dict
            
        elif isinstance(obj, list):
            return [resolve(item) for item in obj]
            
        return obj

    return resolve(raw_schema)


if __name__ == "__main__":
    # Test execution: ensure it compiles a clean, flat dictionary without crashing.
    groq_ready_schema = get_groq_schema(InsightsOutput)
    
    # Assertions to mathematically guarantee no $defs or $refs survived
    schema_str = json.dumps(groq_ready_schema)
    assert "$defs" not in schema_str, "Schema still contains $defs!"
    assert "$ref" not in schema_str, "Schema still contains $ref!"
    assert "allOf" not in schema_str, "Schema still contains allOf wrappers!"
    
    print("Schema flattened successfully! Ready for Groq API.")
    print(json.dumps(groq_ready_schema, indent=2))
