import openai
import pandas as pd
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import base64
import re

# ========================== CONFIGURATION ===============================

# Define your dynamic questions here (you can change this block only!)
QUESTION_CONFIG = [
    {
        "name": "ESG_AND_INNOVATION",
        "prompt": "Did the paper studied the impact of  ESG or CSR or related topic on innovation? Return yes or no. If yes, explain the impact according to the authors.",
        "fields": ["Impact_ESG_on_innovation", "What_is_the_impact"]
    }
]

FOLDER_PATH = "C:/Users/rodri/Offline/LS-20250416"
OUTPUT_PATH = "C:/Users/rodri/Dropbox/Resources/Python/AI-Literature-Search/output/2025-04-16_ESG_CSR_Product_Innovation.csv"
GPT_MODEL = "gpt-4o"
MAX_WORKERS = 5
TOKEN_LIMIT = 4000000

# ======================== LOGGING SETUP ================================

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

# ======================== API KEY SETUP ================================

OPEN_AI_API_KEY = os.environ.get("OPENAI_API_KEY_AI-LITERATURE-SEARCH", None)
if OPEN_AI_API_KEY is None:
    raise ValueError("Please set the OPENAI_API_KEY_AI-LITERATURE-SEARCH environment variable.")
openai.api_key = OPEN_AI_API_KEY

# ======================== UTILITY FUNCTIONS =============================

def extract_json(response_text):
    match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start != -1 and end != -1:
        return response_text[start:end+1]
    return response_text

def analyze_pdf(pdf_name, base64_str):
    all_results = {"pdf_name": pdf_name}
    total_tokens = 0

    for q in QUESTION_CONFIG:
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
                        "text": f"{q['prompt']} Please respond with a JSON object using these keys: {q['fields']}."
                    }
                ]
            }
        ]

        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=messages
        )

        raw_response = response.choices[0].message.content
        total_tokens += response.usage.total_tokens
        logging.info(f"[{q['name']}] Response for {pdf_name}: {raw_response}")

        try:
            json_str = extract_json(raw_response)
            result = json.loads(json_str)
            for field in q["fields"]:
                all_results[f"{q['name']}_{field}"] = result.get(field, "N/A")
        except Exception as e:
            logging.error(f"Error parsing {q['name']} in {pdf_name}: {e}")
            for field in q["fields"]:
                all_results[f"{q['name']}_{field}"] = f"Error: {e}"

    return all_results, total_tokens

def process_pdf_file(file_path):
    pdf_name = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        logging.error(f"Could not read {file_path}: {e}")
        return {"pdf_name": pdf_name, "error": str(e)}, 0

    base64_str = base64.b64encode(file_bytes).decode('utf-8')
    result, tokens_used = analyze_pdf(pdf_name, base64_str)
    return result, tokens_used

# =========================== MAIN FUNCTION =============================

def main(folder_path, output_path):
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logging.error(f"No PDFs found in: {folder_path}")
        return

    total_tokens_used = 0
    token_usage = 0
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {executor.submit(process_pdf_file, file): file for file in pdf_files}
        for future in as_completed(future_to_file):
            try:
                result_dict, tokens_used = future.result()
                total_tokens_used += tokens_used
                token_usage += tokens_used

                if token_usage > TOKEN_LIMIT:
                    elapsed = time.time() - start_time
                    if elapsed < 60:
                        wait_time = 60 - elapsed
                        logging.info(f"Rate limit hit. Waiting {wait_time:.2f}s.")
                        time.sleep(wait_time)
                    start_time = time.time()
                    token_usage = tokens_used

                results.append(result_dict)
            except Exception as e:
                logging.error(f"Error during processing: {e}")

    output_df = pd.DataFrame(results)
    output_df.to_csv(output_path, index=False)
    logging.info(f"Done. Output saved to {output_path}. Total tokens used: {total_tokens_used}")

# ============================ EXECUTION ===============================

if __name__ == "__main__":
    main(FOLDER_PATH, OUTPUT_PATH)
