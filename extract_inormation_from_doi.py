import requests
import csv
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

# Save metadata to CSV file including citation count
def save_metadata_to_csv(dois, output_file):
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['DOI', 'Title', 'Year', 'Abstract', 'Citations'])  # Add 'Citations' to the header

        i = 1
        for doi in dois:
            title, year, abstract, citations = get_metadata_from_doi(doi)
            writer.writerow([doi, title, year, abstract, citations])  # Write citation count as well
            print(i, "/", len(dois))
            i = i + 1
            #time.sleep(1)  # Uncomment this if needed to avoid hitting the API rate limit

# Example usage
file_path = "C:/Users/rodri/Offline Folder/LS_20240916_Innovation_1990-2024.xlsx"  # Replace with your actual file path
column_name = 'DOI'  # The column you want to extract
column_data = extract_column_from_excel(file_path, column_name)

# File where the results will be saved
output_file = "doi_metadata_with_citations.csv"

# Call the function to process the DOIs and save to CSV
save_metadata_to_csv(column_data, output_file)

print(f"Metadata saved to {output_file}")
