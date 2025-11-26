import os
import json
import argparse
import logging
import time
from typing import Dict, Any, List
from dotenv import load_dotenv
from mistralai import Mistral
from therapy_models import TherapyReport
from rad_models import RadiationTherapyReport
from langsmith import traceable

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global client instance to reuse across calls
_mistral_client = None

def get_mistral_client():
    """Get or create a global Mistral client instance."""
    global _mistral_client
    if _mistral_client is None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set.")
        _mistral_client = Mistral(api_key=api_key)
    return _mistral_client

@traceable(
    run_type="llm",
    name="therapy_extraction",
    tags=["therapy", "medical_report", "mistral"],
    metadata={"model": "mistral-medium-latest", "report_type": "therapy"}
)
def get_therapy_json(markdown_text: str) -> dict:
    """
    Converts markdown text from a therapy (chemotherapy/biological) report to a structured JSON object.
    
    Args:
        markdown_text: The markdown content of the therapy report.
    
    Returns:
        A dictionary with the structured therapy data.
    """
    client = get_mistral_client()
    model = "mistral-medium-latest"
    
    schema = TherapyReport.model_json_schema()
    
    prompt = f"""Extract structured therapy report data from this markdown text. This could be a chemotherapy, biological therapy, or hormonal therapy report. Return only a JSON object conforming to this schema:

{json.dumps(schema, indent=2)}

Important notes:
- therapy_type should be one of: 'Chemotherapy', 'Biological Therapy', 'Targeted Therapy', 'Hormonal Therapy', 'Immunotherapy'
- administration_route examples: 'Intravenous', 'Oral', 'Subcutaneous', 'Intramuscular'
- Extract all drugs mentioned for cancer treatment only with their dosages and units
- Convert dates to YYYY-MM-DD format
- Set adverse_event_observed to true if any side effects or adverse events are mentioned

Report:
{markdown_text}"""

    messages: List[Dict[str, str]] = [
        {"role": "user", "content": prompt}
    ]

    start_time = time.time()
    try:
        print(f"[🔄] Starting therapy JSON extraction with {model}...")
        
        chat_response = client.chat.complete(
            model=model,
            messages=messages,  # type: ignore
            response_format={"type": "json_object"},
            max_tokens=4000,
            temperature=0.1
        )
        
        response_content = chat_response.choices[0].message.content  # type: ignore
        if response_content:
            result = json.loads(response_content)  # type: ignore
            elapsed_time = time.time() - start_time
            print(f"[✅] Therapy JSON extraction completed in {elapsed_time:.2f} seconds")
            return result
        else:
            logging.error("Empty response from Mistral API")
            return {}
    except Exception as e:
        elapsed_time = time.time() - start_time
        logging.error(f"Failed to get therapy data from Mistral API after {elapsed_time:.2f}s: {e}")
        return {}

@traceable(
    run_type="llm",
    name="radiation_extraction",
    tags=["radiation", "medical_report", "mistral"],
    metadata={"model": "mistral-medium-latest", "report_type": "radiation"}
)
def get_radiation_json(markdown_text: str) -> dict:
    """
    Converts markdown text from a radiation therapy report to a structured JSON object.
    
    Args:
        markdown_text: The markdown content of the radiation therapy report.
    
    Returns:
        A dictionary with the structured radiation therapy data.
    """
    client = get_mistral_client()
    model = "mistral-medium-latest"
    
    schema = RadiationTherapyReport.model_json_schema()
    
    prompt = f"""Extract structured radiation therapy report data from this markdown text. Return only a JSON object conforming to this schema:

{json.dumps(schema, indent=2)}

Important notes:
- radiation_type examples: 'EBRT' (External Beam Radiation Therapy), 'IMRT', 'IGRT', 'Stereotactic', 'Brachytherapy'
- test_therapy should typically be 'therapy' for radiation therapy reports
- Convert dates to YYYY-MM-DD format
- Extract total dosage and unit (commonly 'Gy' for Gray)
- area_treated should specify the anatomical region (e.g., 'Spine', 'Brain', 'Chest', 'Pelvis')
- Include any adverse events or side effects mentioned
- Extract number of fractions (treatment sessions)

Report:
{markdown_text}"""

    messages: List[Dict[str, str]] = [
        {"role": "user", "content": prompt}
    ]

    start_time = time.time()
    try:
        print(f"[🔄] Starting radiation therapy JSON extraction with {model}...")
        
        chat_response = client.chat.complete(
            model=model,
            messages=messages,  # type: ignore
            response_format={"type": "json_object"},
            max_tokens=4000,
            temperature=0.1
        )
        
        response_content = chat_response.choices[0].message.content  # type: ignore
        if response_content:
            result = json.loads(response_content)  # type: ignore
            elapsed_time = time.time() - start_time
            print(f"[✅] Radiation therapy JSON extraction completed in {elapsed_time:.2f} seconds")
            return result
        else:
            logging.error("Empty response from Mistral API")
            return {}
    except Exception as e:
        elapsed_time = time.time() - start_time
        logging.error(f"Failed to get radiation therapy data from Mistral API after {elapsed_time:.2f}s: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Convert a medical report from markdown to JSON.")
    parser.add_argument("input_file", type=str, help="Path to the input markdown file.")
    parser.add_argument("--output_file", type=str, help="Optional path to the output JSON file.")
    parser.add_argument("--report_type", type=str, default="therapy", 
                       choices=["therapy", "radiation"], 
                       help="Type of report to process (default: therapy)")
    args = parser.parse_args()

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input_file}")
        return

    # Process based on report type
    if args.report_type == "therapy":
        json_output = get_therapy_json(markdown_content)
    elif args.report_type == "radiation":
        json_output = get_radiation_json(markdown_content)
    else:
        logging.error(f"Unsupported report type: {args.report_type}")
        return

    if json_output:
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(json_output, f, indent=4)
            logging.info(f"Successfully created JSON output at {args.output_file}")
        else:
            print(json.dumps(json_output, indent=4))

if __name__ == "__main__":
    main() 