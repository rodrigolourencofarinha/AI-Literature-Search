# Literature-Search

## Objecive

The Literature-Search project aims to create an automated tool that helps researchers review multiple research articles efficiently, reducing the manual effort involved in finding and prioritizing relevant studies.

## Problem

Researchers (specially PhD students) often struggle to stay updated with the vast number of publications in their fields, particularly when exploring unfamiliar topics. While search engines can retrieve thousands of articles based on keywords, they do not effectively help prioritize or filter the most relevant works. This inefficiency becomes a barrier, especially when quick understanding of a new topic is required. 

## Solution

Leveraging the power of AI, Literature-Search streamlines the process of reviewing and prioritizing hundreds of studies. The tool helps researchers focus on the most relevant articles, improving both productivity and depth of insight.

This repo has two files: 
- `extract_information_from_doi.py`: This script extracts the title and abstract of multiple DOIs using CrossRef api
- `analyze_abstracts.py`: This script analyzes abstracts and titles using ChatGPT, assigning a relevance score based on how well the study aligns with the desired topic.

## Analysis Process

The `analyze_abstracts.py` script follows a structured prompt to evaluate each article:

``` Python
prompt_template = """
Analyze the title and abstract of the following research paper for its relevance to the topic '{topic}'. Return the study's title. Assign a relevance score from 0 (completely unrelated) to 10 (highly relevant). Explicitly state the name of the article and provide a brief explanation for your score, referencing specific parts of the title and abstract that justify your rating. If the topic is not mentioned or only indirectly related, explain why.
Title: {title}
Abstract: {abstract}
The output should be formatted as a JSON object that conforms to the schema below.
"""
```

This helps automate the process of scoring and categorizing articles based on relevance to a specific research area.

