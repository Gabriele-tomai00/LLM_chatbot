from llama_index.core import Settings
from llama_index.core import set_global_handler
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import asyncio
from utils_rag import *
from polito_llm_wrapper import *
from llama_index.core.prompts import PromptTemplate


# Enable debug logging
set_global_handler("simple")

# Global settings
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = PolitoLLMwrapper()

# Load RAG index
index = get_index("rag_index")
if index is None:
    print("No index found. Please create it first using --create-index.")
    exit(1)

RAG_PROMPT = PromptTemplate(
"""
{system_prompt}

CONTESTO (informazioni recuperate):
{context_str}

DOMANDA:
{query_str}

"""
)


# Create query engine
query_engine = index.as_query_engine(
    llm=Settings.llm,
    similarity_top_k=3,
    text_qa_template=RAG_PROMPT,
    verbose=False,  # Disabilitato per meno output
    use_async=True
)

# Create retriever for debug
retriever = index.as_retriever(similarity_top_k=3)


async def search_documents_with_debug(query: str) -> str:
    """Search the indexed university documents and return relevant information with minimal debug info."""
    print("Searching in documents...")
    
    # Retrieve chunks quietly
    nodes = await retriever.aretrieve(query)
    
    # Show only summary of found chunks
    high_relevance = [n for n in nodes if n.score >= 0.7]
    medium_relevance = [n for n in nodes if 0.5 <= n.score < 0.7]
    
    print(f"Found: {len(high_relevance)} high relevance, {len(medium_relevance)} medium relevance")
    
    if high_relevance:
        best_score = max(n.score for n in high_relevance)
        print(f"Best match score: {best_score:.3f}")
    
    print("\nGenerating answer...")
    
    try:
        response = await query_engine.aquery(query)
        return str(response)
    except Exception as e:
        print(f"LLM error, using fallback...")
        return "Non ho trovato informazioni sufficienti per rispondere."


async def simple_query(query: str) -> str:
    """Simple query without any debug info."""
    try:
        response = await query_engine.aquery(query)
        return str(response)
    except Exception as e:
        return f"Errore: {e}"


async def test_document_sources():
    """Test function with clean output."""
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
                best_score = max(n.score for n in nodes) if nodes else 0
                print(f"   High: {high_rel}, Medium: {medium_rel}, Best: {best_score:.3f}")
            else:
                print("   No relevant chunks")
        except Exception as e:
            print(f"   Error: {e}")


async def test_llm_capabilities():
    """Test if the LLM is working properly with clean output."""
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
# Interactive loop
# --------------------------
async def interactive_loop():
    print("Assistant started (RAG Mode - CLEAN OUTPUT)")
    print("\nAvailable commands:")
    print("  ask <question>    → ask with minimal debug info")
    print("  quick <question>  → ask without any debug info") 
    print("  test_llm          → test if LLM is working")
    print("  test_sources      → test document content")
    print("  quit              → exit the program")
    print("\n")

    while True:
        user_input = input("> ").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("Shutting down...")
            break

        elif user_input.lower() == "test_llm":
            await test_llm_capabilities()

        elif user_input.lower() == "test_sources":
            await test_document_sources()

        elif user_input.lower().startswith("ask "):
            query = user_input[4:].strip()
            if not query:
                print("Please provide a question after 'ask'.")
                continue

            try:
                response = await search_documents_with_debug(query)
                print(f"\nANSWER:\n{response}\n")
            except Exception as e:
                print(f"Error: {e}")

        elif user_input.lower().startswith("quick "):
            query = user_input[6:].strip()
            if not query:
                print("Please provide a question after 'quick'.")
                continue

            print("Processing...")
            try:
                response = await simple_query(query)
                print(f"\nANSWER:\n{response}\n")
            except Exception as e:
                print(f"Error: {e}")

        else:
            print("Unknown command. Use: ask, quick, test_llm, test_sources, quit")


async def main():
    await interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())