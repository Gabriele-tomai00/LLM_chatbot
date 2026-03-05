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

    
def add_to_index_staff_book(index, json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])

    documents = []
    for item in entries:
        metadata = item.get("metadata", {})
        doc = Document(
            text=item.get("page_content"),
            metadata={
                "type": metadata.get("doc_type"),
                "nome": metadata.get("nome"),
                "role": metadata.get("role"),
                "department": metadata.get("department"),
                "department_staff_url": metadata.get("department_staff_url"),
                "phone": metadata.get("phone"),
                "email": metadata.get("email"),
                "last_updated": metadata.get("last_updated")
            }
        )
        documents.append(doc)

    for doc in documents:
        index.insert(doc)

    return len(documents)



def add_to_index_teams_code(index, json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for item in data:
        metadata = item.get("metadata", {})
        doc = Document(
            text=item.get("page_content"),
            metadata={
                "type": metadata.get("doc_type"),
                "course_name": metadata.get("course_name"),
                "course_code": metadata.get("course_code"),
                "teams_code": metadata.get("teams_code"),
                "degree_program_code": metadata.get("degree_program_code"),
                "degree_program": metadata.get("degree_program"),
                "degree_program_eng": metadata.get("degree_program_eng"),
                "academic_year": metadata.get("academic_year"),
                "teacher_name": metadata.get("teacher_name"),
                "teacher_id": metadata.get("teacher_id"),
                "period": metadata.get("period"),
                "last_update": metadata.get("last_update")
            }
        )
        documents.append(doc)

    for doc in documents:
        index.insert(doc)

    return len(documents)


def add_to_index_lesson_calendar(index, folder_path):

    json_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith(".json")
    ]

    total_documents = 0

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        for item in data:
            metadata = item.get("metadata", {})
            doc = Document(
                text=item.get("page_content"),
                metadata={
                    "type": metadata.get("doc_type"),
                    "department": metadata.get("department"),
                    "course_code": metadata.get("course_code"),
                    "study_course": metadata.get("study_course"),
                    "subject_code": metadata.get("subject_code"),
                    "subject_name": metadata.get("subject_name"),
                    "study_year_code": metadata.get("study_year_code"),
                    "curriculum": metadata.get("curriculum"),
                    "date_iso": metadata.get("date_iso"),
                    "read_time": metadata.get("read_time"),
                    "start_time": metadata.get("start_time"),
                    "end_time": metadata.get("end_time"),
                    "full_location": metadata.get("full_location"),
                    "professor": metadata.get("professor"),
                    "lesson_type": metadata.get("lesson_type"),
                    "cancelled": metadata.get("cancelled"),
                    "url": metadata.get("url")
                }
            )
            documents.append(doc)

        for doc in documents:
            index.insert(doc)

        total_documents += len(documents)

    return total_documents



def add_to_index_room_calendar(index, folder_path):

    json_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith(".json")
    ]

    total_documents = 0

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        for item in data:
            metadata = item.get("metadata", {})
            doc = Document(
                text=item.get("page_content"),
                metadata={
                    "type": metadata.get("doc_type", "room_calendar"),
                    "event_type": metadata.get("event_type"),
                    "site_code": metadata.get("site_code"),
                    "room_code": metadata.get("room_code"),
                    "full_location": metadata.get("full_location"),
                    "date_iso": metadata.get("date_iso"),
                    "readable_date": metadata.get("readable_date"),
                    "time_start": metadata.get("time_start"),
                    "time_end": metadata.get("time_end"),
                    "event": metadata.get("event"),
                    "teacher": metadata.get("teacher"),
                    "last_update": metadata.get("last_update")
                }
            )
            documents.append(doc)

        for doc in documents:
            index.insert(doc)

        total_documents += len(documents)

    return total_documents



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