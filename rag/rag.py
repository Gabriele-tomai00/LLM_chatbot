from llama_index.core import Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from utils_rag import *
import asyncio
from llama_index.llms.openai_like import OpenAILike

os.environ["TOKENIZERS_PARALLELISM"] = "false" # avoid warning messages

Settings.llm = OpenAILike(
    model="llama3.1:70b",          # o il nome che ti ha restituito /v1/models
    api_base="http://172.30.42.129:8080/v1",
    api_key="not_necessary",
    context_window=4096,
    max_tokens=512,
    temperature=0,
    is_chat_model=True,
)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
# Settings.llm = Ollama(
#     model="mistral",
#     request_timeout=180.0,
#     context_window=2000,
#     generate_kwargs={"num_predict": 128},
#     temperature=0,
# )


# === TOOL: Search documents ===
async def search_documents(index, query: str) -> str:
    """Answer questions about the provided documents."""
    if index is None:
        return "The index does not exist yet. Please create it first using --create-index."
    query_engine = index.as_query_engine(llm=Settings.llm)
    response = await query_engine.aquery(query)
    return str(response)

async def search_documents_with_debug(index, query: str) -> str:
    retriever = index.as_retriever(similarity_top_k=3)
    print("Searching in documents...")
    nodes = await retriever.aretrieve(query)
    high_relevance = [n for n in nodes if n.score >= 0.7]
    medium_relevance = [n for n in nodes if 0.5 <= n.score < 0.7]
    print(f"Found: {len(high_relevance)} high relevance, {len(medium_relevance)} medium relevance")
    if high_relevance:
        best_score = max(n.score for n in high_relevance)
        print(f"Best match score: {best_score:.3f}")
    print("\nGenerating answer...")
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


    index = load_or_create_index("rag_index_con_teams_e_book")
    if index is None:
        print("Failed to load or create the index.")
        exit(1)
    else:
        print(f"Index loaded successfully.\n Current size: {get_index_size(index)}")

# COMMENTO PER NON RICREARE IL RAG INDEX CON TEAMS E BOOK
    # add_to_index_book(index, "units_book.json")

    # print(f"Index size after addition: {get_index_size(index)}")

    # add_to_index_teams_code(index, "teams_codes.json")

    # print(f"Index size after second addition: {get_index_size(index)}")


    # result = await search_documents(index, 
    #     "Qual è il codice teams di DOCUMENTAZIONE FOTOGRAFICA DEI CASI CLINICI?"
    # )
    result = await search_documents(index, 
        "Quali sono gli insegnamenti di SCIENZE INFERMIERISTICHE E OSTETRICHE (ME05) e i relativi codici teams?"
    )
    print("\nSearch Result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())