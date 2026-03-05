import os
import json
from datetime import datetime
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    Settings,
    StorageContext,
    Document,
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb


def print_indexing_summary(start_time, persist_dir, num_docs, log_file: str = "indexing_summary.log"):
    elapsed = (datetime.now() - start_time).total_seconds()
    summary_lines = [
        f"\n====== INDEX CREATION SESSION {start_time.strftime('%d-%m-%Y %H:%M')} ======",
        f"Time taken: {format_time(elapsed)}",
        f"Index created and saved to: {persist_dir}",
        f"Total documents indexed: {num_docs}",
        f"📄 TIME of end: {datetime.now().strftime('%H:%M:%S')}",
        "====================================================="
    ]
    for line in summary_lines:
        print(line)
    log_path = Path(log_file)
    with log_path.open("a", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")


def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

    
def add_to_index_book(index, json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])

    documents = []

    for item in entries:
        doc = Document(
            text=item.get("page_content"),
            metadata={
                "type": "course",
                "course_name": item.get("nome insegnamento"),
                "professor": item.get("docente"),
                "teams_code": item.get("codice teams")
            }
        )

        documents.append(doc)

    for doc in documents:
        index.insert(doc)

    return len(documents)



def add_to_index_teams_code(index, json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("codes", [])

    documents = []

    for item in entries:
        doc = Document(
            text=item.get("page_content"),
            metadata={
                "type": "course",
                "course_name": item.get("nome_insegnamento"),
                "course_name_eng": item.get("nome_insegnamento_eng"),
                "course_code": item.get("codice_insegnamento")
            }
        )

        documents.append(doc)

    for doc in documents:
        index.insert(doc)

    return len(documents)







def load_or_create_index(persist_dir):

    db = chromadb.PersistentClient(path=persist_dir)

    chroma_collection = db.get_or_create_collection("quickstart")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=Settings.embed_model
    )

    return index


def get_index_size(index):
    collection = index.vector_store._collection
    return collection.count()