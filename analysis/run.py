import json
import os
import sys
import uuid
from pydantic import ValidationError
from dotenv import load_dotenv
load_dotenv()

# Force Python to recognize the 'analysis' directory for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from schema import InsightsOutput, get_groq_schema
from prompt_builder import build_system_instruction, build_user_prompt
from llm_client import call_groq_analysis
from grounding_check import check_grounding
from trend_check import check_trend_language

def main():
    print("Starting Stage 4: AI Analysis Layer")
    
    input_path = "data/stats_summary.json"
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Missing input file: {input_path}. Please run Stage 3 first.")
        
    with open(input_path, "r") as f:
        stats_summary_dict = json.load(f)
        stats_summary_text = json.dumps(stats_summary_dict, indent=2)

    api_schema = get_groq_schema(InsightsOutput)
    run_id = str(uuid.uuid4())[:8] # Generate a short run_id for the log file
    os.makedirs("logs", exist_ok=True)
    jsonl_log_path = f"logs/stage4_{run_id}.jsonl"
    
    run_summary = {
        "status": "failed",
        "attempts": 0,
        "schema_valid": False,
        "grounding_passed": False,
        "trend_language_flags": [],
        "failure_reason": None
    }
    
    max_attempts = 2
    retry_feedback = None
    final_insights_dict = None

    for attempt in range(1, max_attempts + 1):
        run_summary["attempts"] = attempt
        print(f"\n--- Attempt {attempt} of {max_attempts} ---")
        
        # Per-attempt observability log
        attempt_log = {
            "attempt": attempt,
            "schema_valid": False,
            "grounding_passed": False,
            "unmatched_numbers": [],
            "raw_response": None,
            "prompt": None
        }
        
        try:
            print("Calling Groq API...")
            system_instruction = build_system_instruction()
            user_prompt = build_user_prompt(stats_summary_text, retry_feedback)
            
            attempt_log["prompt"] = f"SYSTEM: {system_instruction}\nUSER: {user_prompt}"
            
            raw_response = call_groq_analysis(system_instruction, user_prompt, api_schema)
            attempt_log["raw_response"] = raw_response
            response_dict = json.loads(raw_response)
            
            # Gate 1: Schema Validation (Pydantic)
            insights_model = InsightsOutput(**response_dict)
            run_summary["schema_valid"] = True
            attempt_log["schema_valid"] = True
            
            # Gate 2: Numeric Grounding Validation
            grounding_passed, unmatched_numbers = check_grounding(raw_response, stats_summary_dict)
            run_summary["grounding_passed"] = grounding_passed
            attempt_log["grounding_passed"] = grounding_passed
            attempt_log["unmatched_numbers"] = unmatched_numbers
            
            if not grounding_passed:
                error_msg = f"Grounding Failure: The following numbers were generated but do not exist in the source data: {unmatched_numbers}. Only use numbers from the provided JSON."
                print(error_msg)
                retry_feedback = error_msg
                
                # Write attempt log before continuing to retry
                with open(jsonl_log_path, "a") as log_file:
                    log_file.write(json.dumps(attempt_log) + "\n")
                continue 
                
            # Both hard gates passed
            final_insights_dict = insights_model.model_dump()
            
            # Write successful attempt log
            with open(jsonl_log_path, "a") as log_file:
                log_file.write(json.dumps(attempt_log) + "\n")
            break
            
        except json.JSONDecodeError:
            error_msg = "Schema Failure: The response was not valid JSON."
            print(error_msg)
            retry_feedback = error_msg
            with open(jsonl_log_path, "a") as log_file:
                log_file.write(json.dumps(attempt_log) + "\n")
            
        except ValidationError as e:
            error_msg = f"Schema Failure: The generated JSON did not match the required structure.\nDetails:\n{e}"
            print(error_msg)
            retry_feedback = error_msg
            with open(jsonl_log_path, "a") as log_file:
                log_file.write(json.dumps(attempt_log) + "\n")
            
        except Exception as e:
            raise e

    # Post-Execution Routing
    if final_insights_dict:
        run_summary["status"] = "success"
        
        print("Running semantic trend check...")
        trend_flags = check_trend_language(json.dumps(final_insights_dict))
        run_summary["trend_language_flags"] = trend_flags
        
        if trend_flags:
            print(f"Warning: Found {len(trend_flags)} sentences with potential trend language. Logged for review.")
            
        with open("data/insights.json", "w") as f:
            json.dump(final_insights_dict, f, indent=2)
        print("SUCCESS: Stage 4 complete. Insights saved to data/insights.json.")
    else:
        run_summary["failure_reason"] = retry_feedback
        print(f"FAILURE: Pipeline halted after {max_attempts} attempts. Insights NOT saved.")

    # Write final run summary
    with open("logs/stage4_run_summary.json", "w") as f:
        json.dump(run_summary, f, indent=2)

if __name__ == "__main__":
    main()