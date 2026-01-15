from llama_index.core import Settings
from llama_index.core import set_global_handler
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import asyncio
from utils_rag import *
from polito_llm_wrapper import *
from llama_index.core.prompts import PromptTemplate
import sys
import os

# Enable debug logging
set_global_handler("simple")

# Global settings
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")

try:
    #Settings.llm = PolitoLLMwrapper()
    Settings.llm = UuitsLLMWrapper(model_name="gpt-oss-120b", temperature=0.2)

except RuntimeError as e:
    print(e)
    sys.exit(1)

# --- Helper function to ensure index exists ---
def ensure_index(persist_dir: str, default_jsonl: str = "../results/filtered_items.jsonl"):
    index = get_index(persist_dir)
    if index is None:
        print(f"No index found in '{persist_dir}'.")
        while True:
            choice = input("Do you want to create it now? [y/n]: ").strip().lower()
            if choice in ["y", "yes"]:
                jsonl_path = input(f"Enter JSONL path to create index [{default_jsonl}]: ").strip()
                if not jsonl_path:
                    jsonl_path = default_jsonl
                if not os.path.exists(jsonl_path):
                    print(f"File '{jsonl_path}' does not exist. Please check the path.")
                    continue
                try:
                    create_index(persist_dir, jsonl_path)
                    print("Index created successfully.")
                    index = get_index(persist_dir)
                    break
                except Exception as e:
                    print(f"Error creating index: {e}")
            elif choice in ["n", "no"]:
                print("Exiting program. Index is required for RAG mode.")
                sys.exit(0)
            else:
                print("Please answer 'y' or 'n'.")
    return index

# --- Load or create index ---
index = ensure_index("chroma_db")

# --- Setup RAG prompt and query engine ---
RAG_PROMPT = PromptTemplate(
    """
CONTENUTO DISPONIBILE:
{context_str}

DOMANDA:
{query_str}

RISPOSTA:
"""
)

query_engine = index.as_query_engine(
    llm=Settings.llm,
    similarity_top_k=3,
    text_qa_template=RAG_PROMPT,
    verbose=False,
    use_async=True
)

retriever = index.as_retriever(similarity_top_k=3)

# --------------------------
# Async query functions
# --------------------------
async def search_documents_with_debug(query: str) -> str:
    print("Searching in documents...")
    nodes = await retriever.aretrieve(query)
    high_relevance = [n for n in nodes if n.score >= 0.7]
    medium_relevance = [n for n in nodes if 0.5 <= n.score < 0.7]
    print(f"Found: {len(high_relevance)} high relevance, {len(medium_relevance)} medium relevance")
    if high_relevance:
        best_score = max(n.score for n in high_relevance)
        print(f"Best match score: {best_score:.3f}")
    print("\nGenerating answer...")
    response = await query_engine.aquery(query)
    return str(response)

async def simple_query(query: str) -> str:
    try:
        response = await query_engine.aquery(query)
        return str(response)
    except Exception as e:
        return f"Errore: {e}"

async def test_document_sources():
    print("\nTESTING DOCUMENT CONTENT...")
    test_queries = [
        "Corsi di laurea in ingegneria informatica",
        "Programmi Erasmus mobilità internazionale", 
        "Requisiti test ammissione ingresso",
        "Tasse universitarie contributi",
        "Servizi biblioteche laboratori studenti"
    ]
    for query in test_queries:
        print(f"\nTesting: '{query}'")
        try:
            nodes = await retriever.aretrieve(query)
            if nodes:
                high_rel = len([n for n in nodes if n.score >= 0.7])
                medium_rel = len([n for n in nodes if 0.5 <= n.score < 0.7])
                best_score = max(n.score for n in nodes)
                print(f"   High: {high_rel}, Medium: {medium_rel}, Best: {best_score:.3f}")
            else:
                print("   No relevant chunks")
        except Exception as e:
            print(f"   Error: {e}")

async def test_llm_capabilities():
    print("\nTESTING LLM...")
    test_prompts = [
        "Rispondi semplicemente 'OK'",
        "Qual è la capitale d'Italia?",
    ]
    for prompt in test_prompts:
        try:
            response = await query_engine.aquery(prompt)
            print(f"'{prompt}' → {str(response)[:50]}...")
        except Exception as e:
            print(f"'{prompt}' → Error: {e}")

# --------------------------
# Command handlers
# --------------------------
async def handle_quit():
    print("Shutting down...")
    sys.exit(0)

async def handle_load_index():
    global index, query_engine, retriever
    index = ensure_index("chroma_db")
    query_engine = index.as_query_engine(
        llm=Settings.llm,
        similarity_top_k=3,
        text_qa_template=RAG_PROMPT,
        verbose=False,
        use_async=True
    )
    retriever = index.as_retriever(similarity_top_k=3)
    print("Index loaded successfully.")

async def handle_create_index(path: str):
    if not path:
        print("Please provide a path after 'create-index-from'.")
        return
    try:
        create_index("chroma_db", path)
        await handle_load_index()
        print("Index created successfully.")
    except Exception as e:
        print(f"Error creating index: {e}")

async def handle_test_llm():
    await test_llm_capabilities()

async def handle_test_sources():
    await test_document_sources()

async def handle_ask(query: str, debug: bool = True):
    if not query:
        print("Please provide a question.")
        return
    try:
        if debug:
            response = await search_documents_with_debug(query)
        else:
            response = await simple_query(query)
        print(f"\nANSWER:\n{response}\n")
    except Exception as e:
        print(f"Error: {e}")

# --------------------------
# Interactive loop
# --------------------------
async def interactive_loop():
    print("Assistant started (RAG Mode - CLEAN OUTPUT)")
    print("\nAvailable commands:")
    print("  create-index-from <file>")
    print("  load-index")
    print("  ask <question>")
    print("  quick <question>")
    print("  test_llm")
    print("  test_sources")
    print("  quit\n")

    command_map = {
        "quit": handle_quit,
        "load-index": handle_load_index,
        "test_llm": handle_test_llm,
        "test_sources": handle_test_sources,
    }

    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue

        parts = user_input.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "create-index-from":
            await handle_create_index(arg)
        elif cmd == "ask":
            await handle_ask(arg, debug=True)
        elif cmd == "quick":
            await handle_ask(arg, debug=False)
        elif cmd in command_map:
            await command_map[cmd]()
        else:
            print("Unknown command. Available commands: ask, quick, create-index-from, load-index, test_llm, test_sources, quit")

async def main():
    await interactive_loop()

if __name__ == "__main__":
    asyncio.run(main())