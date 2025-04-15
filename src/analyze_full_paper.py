import openai
import pandas as pd
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import base64
import re

# Configure logging to print both to the console and to a log file
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fh = logging.FileHandler('debug_messages.log')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

# Get API key from environment variable
OPEN_AI_API_KEY = os.environ.get("OPENAI_API_KEY_AI-LITERATURE-SEARCH", None)
if OPEN_AI_API_KEY is None:
    raise ValueError(
        "Please set the OPENAI_API_KEY_AI-LITERATURE-SEARCH environment variable."
    )
openai.api_key = OPEN_AI_API_KEY

TOKEN_LIMIT = 4000000
MAX_WORKERS = 5  # Adjust the number of concurrent workers as needed
REQUESTS_PER_MINUTE = 5000

def extract_json(response_text):
    """
    Extracts a JSON string from the API response text.
    First, it looks for a JSON code block (```json ... ```). 
    If not found, it attempts to locate the first '{' and the last '}'.
    """
    # Try to extract from a markdown JSON block
    match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        return json_str
    # Fallback: extract based on the first and last curly brackets
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start != -1 and end != -1:
        json_str = response_text[start:end+1]
        return json_str
    # If no JSON structure is found, return the original text
    return response_text

def analyze_pdf(pdf_name, base64_str):
    """
    Build and send a request to the API using the base64-encoded PDF content.
    The request sends two message parts: one containing the file and a text prompt.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "file",
                    "file": {
                        "filename": pdf_name,
                        "file_data": f"data:application/pdf;base64,{base64_str}",
                    }
                },
                {
                    "type": "text",
                    "text": (
                        "Did the paper discuss competitive intensity? If yes, what does it say about competitive intensity? "
                        "Please provide your answer as a JSON object with the following keys: "
                        "'DiscussCompetitiveIntensity' (Yes/No) and 'WhatDoesItSay' (a brief explanation)."
                    )
                }
            ]
        }
    ]
    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    raw_response = response.choices[0].message.content
    logging.info(f"Processing PDF: {pdf_name}")
    logging.info(f"Raw API response: {raw_response}")
    
    try:
        json_str = extract_json(raw_response)
        result = json.loads(json_str)
    except Exception as e:
        logging.error(f"Error processing response for PDF {pdf_name}: {e}")
        result = {
            "DiscussCompetitiveIntensity": "N/A (Error)",
            "WhatDoesItSay": str(e)
        }
    
    logging.info(f"Tokens used: {response.usage.total_tokens}")
    return result, response.usage.total_tokens

def process_pdf_file(file_path):
    """
    Reads the PDF file, converts its contents to base64, queries the API, and
    returns the PDF name along with the two key answers.
    """
    pdf_name = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        logging.error(f"Could not read file {file_path}: {e}")
        return pdf_name, "N/A (File read error)", "N/A (File read error)", 0

    base64_str = base64.b64encode(file_bytes).decode('utf-8')
    result, tokens_used = analyze_pdf(pdf_name, base64_str)
    return (
        pdf_name,
        result.get("DiscussCompetitiveIntensity", "N/A"),
        result.get("WhatDoesItSay", "N/A"),
        tokens_used
    )

def main(folder_path, output_path):
    total_tokens_used = 0
    token_usage = 0
    start_time = time.time()

    # List all PDF files in the folder
    pdf_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith('.pdf')
    ]
    
    if not pdf_files:
        logging.error(f"No PDF files found in folder: {folder_path}")
        return
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {executor.submit(process_pdf_file, file_path): file_path for file_path in pdf_files}
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                pdf_name, dealt_with, how_it_dealt, tokens_used = future.result()
                total_tokens_used += tokens_used
                token_usage += tokens_used
                
                # Enforce token usage limit if necessary
                if token_usage > TOKEN_LIMIT:
                    elapsed_time = time.time() - start_time
                    if elapsed_time < 60:
                        time_to_wait = 60 - elapsed_time
                        logging.info(f"Token limit exceeded. Waiting for {time_to_wait:.2f} seconds.")
                        time.sleep(time_to_wait)
                    start_time = time.time()
                    token_usage = tokens_used
                    
                results.append([pdf_name, dealt_with, how_it_dealt])
            except Exception as exc:
                logging.error(f"Error processing file {file_path}: {exc}")
    
    # Save results to CSV with three columns
    output_df = pd.DataFrame(
        results,
        columns=["pdf NAME", "DISCUSS COMPETITIVE INTENSITY", "WHAT DOES IT SAY"]
    )
    output_df.to_csv(output_path, index=False)
    logging.info(f"Output written to {output_path}")
    logging.info(f"Total Tokens Used: {total_tokens_used}")

if __name__ == "__main__":
    folder_path = "C:/Users/rodri/Offline/competitive-intensity"
    output_path = "C:/Users/rodri/Dropbox/Resources/Python/AI-Literature-Search/output/2025-04-15_Competitive_Intensity_Review.csv  "
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    main(folder_path, output_path)
