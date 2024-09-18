import openai
import pandas as pd
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging to print both to the console and to a log file
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create file handler which logs even debug messages
fh = logging.FileHandler('debug_messages.log')
fh.setLevel(logging.INFO)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# Add the handlers to logger
logger.addHandler(fh)
logger.addHandler(ch)


OPEN_AI_API_KEY = os.environ.get("OPENAI_API_KEY", None)
if OPEN_AI_API_KEY is None:
    raise ValueError(f"""Please set the OPENAI_API_KEY environment variable:
            Copy the API key from the OpenAI dashboard and set it as an environment variable using the following command before running the script:
            Windows: set OPENAI_API_KEY=yourkey
            Mac/Linux: export OPENAI_API_KEY=yourkey
        """)

TOKEN_LIMIT = 200000
MAX_WORKERS = 10
REQUESTS_PER_MINUTE = 20

# Set the API key from the environment variable
openai.api_key = OPEN_AI_API_KEY

def analyze_title_abstract(title, abstract, topic):
    """Analyzes the title and abstract and classifies the study according to predefined criteria."""

    prompt_template = """
    Analyze the title and abstract of the following research paper for its relevance to the topic '{topic}'. Return the study's title. Assign a relevance score from 0 (completely unrelated) to 10 (highly relevant). Explicit inform the name of the article and provide a brief explanation for your score, referencing specific parts of the title and abstract that justify your rating.  If the topic is not mentioned or only indirectly related, explain why.
    Title: {title}
    Abstract: {abstract}
    The output should be formatted as a JSON object that conforms to the schema below.

    JSON Schema:
    {format_instructions}
    """

    format_instructions = json.dumps({
        "Title": "title",
        "RelevanceScore": "integer between 0-10",
        "Explanation": "string (brief explanation of the score)"
    }, indent=4)

    formatted_prompt = prompt_template.format(
        title=title,
        abstract=abstract,
        topic=topic,
        format_instructions=format_instructions
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert literature analyst specializing in assessing academic papers for relevance to specific topics. "
                "Your task is to evaluate the given Title and Abstract, return the title, assign a relevance score from 0 (not relevant) to 10 (highly relevant), "
                "and provide a brief explanation for your score. Explicit inform the name of the article in the beggining of your explanation."
            )
        },
        {"role": "user", "content": formatted_prompt},
    ]

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={
            "type": "json_object",
        }
    )

    # Extract the scores from the API response
    try:
        logging.info(f"Processing Title: {title}")
        logging.info(f"API response: {response.choices[0].message.content}")
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Error processing response for Title: {title}: {e}")
        result = {"RelevanceScore": "N/A (Error)", "Explanation": str(e)}

    logging.info(f"Tokens used: {response.usage.total_tokens}")

    return [result, response.usage.total_tokens]

def rate_limited_analyze_title_abstract(args):
    title, abstract, topic = args
    return analyze_title_abstract(title, abstract, topic)


def main(input_path, output_path, num_rows=None):
    total_tokens_used = 0
    token_usage = 0
    start_time = time.time()

    try:
        # Read input data
        input_data = pd.read_excel(input_path)
        if num_rows:
            # Randomly select the number of rows specified by the user
            input_data = input_data.sample(frac=1).reset_index(drop=True)
            input_data = input_data.head(num_rows)
    except Exception as e:
        logging.error(f"Error reading input file: {input_path}: {e}")
        raise

    # Check if 'Title' and 'Abstract' columns are present
    if not all(col in input_data.columns for col in ['Title', 'Abstract']):
        error_msg = "Input data must contain 'Title' and 'Abstract' columns."
        logging.error(error_msg)
        raise ValueError(error_msg)

    # Ask user for the topic to analyze
    topic = input("Enter the topic to analyze for relevance (e.g., 'product innovation'): ")

    # Columns to keep in the final output
    other_columns = [col for col in input_data.columns if col not in ["Title", "Abstract"]]

    # Prepare output data frame
    results = []
    rows_processed = 0
    total_rows = len(input_data)
 
    # Analyze titles and abstracts in batches with rate limiting
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i in range(0, total_rows, MAX_WORKERS):
            futures = []
            future_to_index = {} 
            for idx in range(i, min(i + MAX_WORKERS, total_rows)):
                logging.info(f"Submitting row {idx} for processing")
                title = input_data.iloc[idx]["Title"]
                abstract = input_data.iloc[idx]["Abstract"]
                future = executor.submit(rate_limited_analyze_title_abstract, (title, abstract, topic))
                future_to_index[future] = idx # Create a dictionary to index the future to the row index

            # Wait for all futures in the current batch to complete
            for future in as_completed(future_to_index):
                idx = future_to_index[future]  # Get the original row index from the dictionary
                logging.info(f"Processing row {idx}")
                result, token_used = future.result()
                total_tokens_used += token_used
                token_usage += token_used

                # Check if the token usage exceeds the limit
                if token_usage > TOKEN_LIMIT:
                    elapsed_time = time.time() - start_time
                    if elapsed_time < 60:
                        time_to_wait = 60 - elapsed_time
                        logging.info(f"Token limit exceeded. Waiting for {time_to_wait:.2f} seconds.")
                        time.sleep(time_to_wait)
                    start_time = time.time()
                    token_usage = token_used  # Reset token usage with the tokens used by the current request

                output_row = [input_data.iloc[idx][col] for col in other_columns]
                output_row += [
                    input_data.iloc[idx]["Title"],
                    input_data.iloc[idx]["Abstract"],
                    result.get("Title", "N/A"),
                    result.get("RelevanceScore", "N/A"),
                    result.get("Explanation", "N/A")
                ]

                results.append(output_row)
                rows_processed += 1

                # Write to CSV in batches
                if len(results) % MAX_WORKERS == 0:
                    output_df = pd.DataFrame(results, columns=other_columns + ["Title", "Abstract", "Title2", "RelevanceScore", "Explanation"])
                    if os.path.exists(output_path):
                        output_df.to_csv(output_path, mode='a', header=False, index=False)
                    else:
                        output_df.to_csv(output_path, index=False)
                    results = []  # Reset results for the next batch
                    logging.info(f"{rows_processed} rows processed, {total_rows - rows_processed} remaining")

        # Write any remaining rows to CSV
        if results:
            output_df = pd.DataFrame(results, columns=other_columns + ["Title", "Abstract", "Title2", "RelevanceScore", "Explanation"])
            if os.path.exists(output_path):
                output_df.to_csv(output_path, mode='a', header=False, index=False)
            else:
                output_df.to_csv(output_path, index=False)
            logging.info(f"{rows_processed} rows processed, {total_rows - rows_processed} remaining")

    logging.info(f"Output written to {output_path}")
    logging.info(f"Total Tokens Used: {total_tokens_used}")

if __name__ == "__main__":
    print("Welcome to the Literature Relevance Analysis Tool!")
    print("This tool uses OpenAI's GPT-4 model to analyze the relevance of academic papers to a specific topic.")
    print("Please ensure that your input file is in Excel format with 'Title' and 'Abstract' columns.")
    print("The output will be written to a CSV file with relevance scores and explanations.")
    print("Let's get started!\n")

    # Ask user for input and output file paths
    input_path = input("Enter the path to the input file - don't include quotation marks (e.g., input.xlsx): ")
    output_path = input("Enter the path to the output file - don't include quotation marks (e.g., output.csv): ")
    # Check if the input file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found at {input_path}")

    # Ask user if they want to run a sample test
    run_sample_test = input("Do you want to run a sample test? (y/n): ")
    if run_sample_test.lower() == "y":
        # Ask them how many rows they want to test
        num_rows = int(input("Enter the number of rows you want to test: "))
        # Run the sample test
        main(input_path, output_path, num_rows)
    else:
        main(input_path, output_path)
