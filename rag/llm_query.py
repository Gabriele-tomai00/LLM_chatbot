from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import asyncio
from utils_rag import *
from polito_llm_wrapper import *


# Global settings
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = PolitoLLMwrapper()   # your custom wrapper


# Load RAG index
index = get_index("rag_index")
if index is None:
    print("No index found. Please create it first using --create-index.")
    exit(1)

query_engine = index.as_query_engine(llm=Settings.llm)


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


async def search_documents(query: str) -> str:
    """Query the RAG index asynchronously."""
    response = await query_engine.aquery(query)
    return str(response)


# Agent definition
agent = AgentWorkflow.from_tools_or_functions(
    [multiply, search_documents],
    llm=Settings.llm,
    system_prompt="""
    Rispondi sempre e solo in italiano.
    Quando è necessaria un'operazione matematica, usa gli strumenti disponibili.
    Quando la domanda riguarda documenti, usa 'search_documents'.
    Non mescolare inglese e italiano.
    """,
)


# --------------------------
# Interactive loop
# --------------------------
async def interactive_loop(agent):
    print("🟢 Assistant started.")
    print("Available commands:")
    print("  ask <question>  → ask a question")
    print("  quit            → exit the program\n")

    while True:
        user_input = input("> ").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("🔴 Shutting down...")
            break

        if user_input.lower().startswith("ask "):
            query = user_input[4:].strip()
            if not query:
                print("Please provide a question after 'ask'.")
                continue

            print("⏳ In progress...\n")

            try:
                response = await agent.run(query)
                print(f"Answer:\n{response}\n")
            except Exception as e:
                print(f"Error while processing: {e}\n")

        else:
            print("Unknown command. Use:")
            print("  ask <question>")
            print("  quit\n")


async def main():
    await interactive_loop(agent)


if __name__ == "__main__":
    asyncio.run(main())
