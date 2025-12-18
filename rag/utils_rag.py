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
    
def create_index(persist_dir, jsonl_path):
    """Create a new vector index from a JSONL file."""
    start_time = datetime.now()

    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"File not found: {jsonl_path}")

    if os.path.exists(persist_dir):
        delete_index(persist_dir)

    print(f"Creating a new index from file: {jsonl_path} starting at {start_time.strftime('%H:%M:%S')}")

    documents = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            doc = Document(
                text=f"Title: {item.get('title', '')}\n"
                     f"URL: {item.get('url', '')}\n"
                     f"Timestamp: {item.get('timestamp', '')}\n\n"
                     f"{item.get('content', '')}",
                metadata={
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "timestamp": item.get("timestamp")
                },
            )
            documents.append(doc)

    # index = VectorStoreIndex.from_documents(
    #     documents,
    #     embed_model=Settings.embed_model,
    # )

    # index.storage_context.persist(persist_dir=persist_dir)
    # print_indexing_summary(start_time, persist_dir, len(documents))
    # return index


    db = chromadb.PersistentClient(persist_dir)
    chroma_collection = db.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents, 
        storage_context=storage_context, 
        embed_model=Settings.embed_model
    )
    return index

def get_index(persist_dir: str, jsonl_path: str = "../items.jsonl") -> VectorStoreIndex:
    """Load an existing index. If directory missing or incomplete, return None."""

    if not os.path.exists(persist_dir):
        print(f"Index directory '{persist_dir}' does not exist.")
        return None

    print("Loading existing index from:", persist_dir)
    # storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    # index = load_index_from_storage(
    #     storage_context,
    #     embed_model=Settings.embed_model,
    # )
    # return index

    db2 = chromadb.PersistentClient(persist_dir)
    chroma_collection = db2.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=Settings.embed_model,
    )
    return index



def delete_index(persist_dir: str):
    if os.path.exists(persist_dir):
        import shutil
        shutil.rmtree(persist_dir)
        print("Deleted index directory:", persist_dir)
    else:
        print("Index directory does not exist:", persist_dir)