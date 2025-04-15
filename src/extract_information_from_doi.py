import requests
import time
import pandas as pd

# Load the Excel file
def extract_column_from_excel(file_path, column_name):
    df = pd.read_excel(file_path)
    if column_name in df.columns:
        column_data = df[column_name]
        return column_data
    else:
        return f"Column '{column_name}' not found in the Excel file."

# Extract metadata including citation count from CrossRef API
def get_metadata_from_doi(doi):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        title = data['message'].get('title', ['No title found'])[0]
        year = data['message'].get('issued', {}).get('date-parts', [[None]])[0][0]
        abstract = data['message'].get('abstract', 'No abstract found')
        citations = data['message'].get('is-referenced-by-count', 0)  # Number of citations
        return title, year, abstract, citations
    else:
        return 'No title found', 'No year found', 'No abstract found', 0

# Save metadata to Excel file including citation count
def save_metadata_to_excel(dois, output_file):
    data_list = []  # List to store data dictionaries

    i = 1
    total = len(dois)
    for doi in dois:
        title, year, abstract, citations = get_metadata_from_doi(doi)
        data_dict = {
            'DOI': doi,
            'Title': title,
            'Year': year,
            'Abstract': abstract,
            'Citations': citations
        }
        data_list.append(data_dict)
        print(f"{i} / {total}")
        i += 1
        # time.sleep(1)  # Uncomment if needed to avoid hitting the API rate limit

    # Create DataFrame and save to Excel
    df = pd.DataFrame(data_list)
    df.to_excel(output_file, index=False)

# Example usage
file_path = "C:/Users/rodri/Dropbox/Resources/Python/AI-Literature-Search/data/input/LS-20250414-Competitive_Intensity-2014_2025-JM_JMR_MS_JAMS.xlsx"  # Replace with your actual file path
column_name = 'DOI'  # The column you want to extract
column_data = extract_column_from_excel(file_path, column_name)

if isinstance(column_data, pd.Series):
    # File where the results will be saved
    output_file = "C:/Users/rodri/Dropbox/Resources/Python/AI-Literature-Search/data/interim/LS-20250414-Competitive_Intensity-2014_2025-JM_JMR_MS_JAMS_doi_metadata_with_citations.xlsx"

    # Call the function to process the DOIs and save to Excel
    save_metadata_to_excel(column_data, output_file)

    print(f"Metadata saved to {output_file}")
else:
    print(column_data)  # Print the error message
