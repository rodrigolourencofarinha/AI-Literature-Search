from paperqa import Settings, ask


answer = ask(
    "What are the different definition of radical innovation?",
    settings=Settings(
        llm="gpt-4o-mini", summary_llm="gpt-4o-mini", paper_directory="C:/Users/rodri/Offline Folder/pdf"
    ),
)