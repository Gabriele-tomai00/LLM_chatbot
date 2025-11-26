from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import asyncio
import os
import os
import json
from datetime import datetime
from pathlib import Path
from utils_rag import *
from polito_llm_wrapper import *



# Settings control global defaults
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = PolitoLLMwrapper()

# Create a RAG tool using LlamaIndex
index = get_index("rag_index")
if index is None:
    print("No index found. Please create the index first using --create-index.")
    exit(1)
query_engine = index.as_query_engine(# we can optionally override the llm here
    llm=Settings.llm,
)


def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""
    return a * b


async def search_documents(query: str) -> str:
    """Useful for answering natural language questions about an personal essay written by Paul Graham."""
    response = await query_engine.aquery(query)
    return str(response)


# Create an enhanced workflow with both tools
agent = AgentWorkflow.from_tools_or_functions(
    [multiply, search_documents],
    llm=Settings.llm,
    system_prompt="""You are a helpful assistant that can perform calculations
    and search through documents to answer questions. Answer in Italian.""",
)


# Now we can ask questions about the documents or do calculations
async def main():
    response = await agent.run(
        "What do you know about università di Trieste?"
    )
    print(response)


# Run the agent
if __name__ == "__main__":
    asyncio.run(main())