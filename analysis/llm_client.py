import os
import json
from groq import Groq

def call_groq_analysis(system_instruction: str, user_prompt: str, api_schema: dict) -> str:
    """
    Calls the Groq API, enforcing JSON output. 
    Prompt construction is handled externally by prompt_builder.py.
    """
    # Ensure the API key is present
    if not os.environ.get("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY environment variable is not set. Please add it to your .env file.")

    client = Groq()
    
    # We use Llama 3.3 70B Versatile, the flagship reasoning model on Groq's free tier.
    model_name = "llama-3.3-70b-versatile"

    # Inject the schema constraint directly into the system instruction
    json_instruction = (
        "\n\nYou MUST respond ONLY with a valid JSON object that strictly adheres to the following JSON schema. "
        "Do not include markdown formatting, explanations, or any text outside the JSON object.\n"
        f"SCHEMA:\n{json.dumps(api_schema, indent=2)}"
    )
    
    full_system_instruction = system_instruction + json_instruction

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": full_system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2, # Low temperature to prioritize strict adherence to data over creativity
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content