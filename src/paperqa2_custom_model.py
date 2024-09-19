import os
from datetime import datetime
from paperqa import Settings, ask

def ask_and_log(question, settings, log_file='C:/Users/rodri/OneDrive/Documents/Python/Literature-Search/output/qa_history.txt'):
    """
    Asks a question using the paperqa module and logs the interaction to a text file.

    Args:
        question (str): The question to ask.
        settings (Settings): Configuration settings for the ask function.
        log_file (str, optional): Path to the log file. Defaults to 'qa_history.txt'.

    Returns:
        str: The answer returned by the ask function.
    """
    try:
        # Ask the question using the provided settings
        answer = ask(question, settings=settings)
        
        # Prepare the log entry with a timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = (
            f"Timestamp: {timestamp}/n"
            f"Q: {question}/n"
            f"A: {answer}/n"
            f"{'-'*50}/n"
        )
        
        # Append the log entry to the log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print("Question and answer logged successfully.")
        return answer

    except Exception as e:
        print(f"An error occurred while processing the question: {e}")
        return None

def main():
    # Define the settings for the paperqa module
    settings = Settings(
        llm="gpt-4o-mini",
        summary_llm="gpt-4o-mini",
        paper_directory="C:/Users/rodri/Offline Folder/pdf"
    )
    
    # Ensure the paper directory exists
    if not os.path.isdir(settings.paper_directory):
        print(f"Error: The directory {settings.paper_directory} does not exist.")
        return
    
    # Example questions
    questions = [
        "What are the different definitions of radical innovation?",
        "How does radical innovation differ from incremental innovation?",
        "Can you provide examples of radical innovation in technology?"
    ]
    
    # Ask each question and log the interaction
    for idx, question in enumerate(questions, start=1):
        print(f"/nQuestion {idx}: {question}")
        answer = ask_and_log(question, settings)
        if answer:
            print(f"Answer {idx}: {answer}")
        else:
            print(f"Failed to retrieve answer for question {idx}.")

if __name__ == "__main__":
    main()
