from llama_index.core import Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from utils_rag import *
import asyncio
import argparse

# === GLOBAL SETTINGS ===
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = Ollama(
    model="mistral",
    request_timeout=180.0,
    context_window=2000,
    generate_kwargs={"num_predict": 128},
    temperature=0,
)


# === TOOL: Search documents ===
async def search_documents(query: str) -> str:
    """Answer questions about the provided documents."""
    index = get_index("rag_index")
    if index is None:
        return "The index does not exist yet. Please create it first using --create-index."
    query_engine = index.as_query_engine(llm=Settings.llm)
    response = await query_engine.aquery(query)
    return str(response)


# === AGENT ===
agent = AgentWorkflow.from_tools_or_functions(
    [search_documents],
    llm=Settings.llm,
    system_prompt=(
        "Sei un assistente utile che risponde sempre in italiano. "
        "Puoi rispondere a domande sui documenti forniti."
    ),
)


# === MAIN ===
async def main():
    parser = argparse.ArgumentParser(description="RAG chatbot CLI")

    parser.add_argument(
        "-m", "--message",
        type=str,
        help="Send a message to the AI agent."
    )
    parser.add_argument(
        "-s", "--search",
        type=str,
        help="Perform a direct semantic search in the index (bypasses the agent)."
    )
    parser.add_argument(
        "-r", "--delete-index",
        action="store_true",
        help="Delete the existing RAG index and exit."
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Create the index from items.jsonl and exit."
    )

    args = parser.parse_args()

    # === Option 1: Delete index ===
    if args.delete_index:
        print("Deleting the existing index...")
        delete_index("rag_index")
        print("Index deleted successfully.")
        return

    # === Option 2: Create index ===
    if args.create_index:
        print("Creating a new index from items.jsonl...")
        create_index("rag_index", "../items.jsonl")
        return

    # === Option 3: Direct search ===
    if args.search:
        print(f"Searching the index for: '{args.search}'")
        result = await search_documents(args.search)
        print("\nSearch Result:")
        print(result)
        return

    # === Option 4: Chat with the agent ===
    if args.message:
        index = get_index("rag_index")
        if index is None:
            print("No index found. Please create the index first using --create-index.")
            return
        query_engine = index.as_query_engine(llm=Settings.llm)
        agent.query_engine = query_engine
        response = await agent.run(args.message)
        print("\nAnswer:")
        print(response)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
