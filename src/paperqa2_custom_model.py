from paperqa import Settings, ask

answer = ask(
    "What's the percentage of products that are radical innovations?",
    settings=Settings(
        llm="gpt-4o-mini", summary_llm="gpt-4o-mini", paper_directory="C:/Users/rodri/Offline Folder/pdf"
    ),
)