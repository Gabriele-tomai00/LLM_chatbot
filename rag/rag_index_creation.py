from llama_index.core import Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from utils_rag import *
import asyncio

os.environ["TOKENIZERS_PARALLELISM"] = "false" # avoid warning messages

scraper_dir = "results_custom_scrapers_october_teams_full"

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    device="cuda"
)

async def main():


    index = load_or_create_index("rag_index_con_teams_e_book")
    if index is None:
        print("Failed to load or create the index.")
        exit(1)
    else:
        print(f"Index loaded successfully.\n Current size: {get_index_size(index)}")

# COMMENTO PER NON RICREARE IL RAG INDEX CON TEAMS E BOOK
    add_to_index_staff_book(index, f"../{scraper_dir}/units_book.json")

    print(f"Index size after staff book addition: {get_index_size(index)}")

    add_to_index_teams_code(index,  f"../{scraper_dir}/teams_codes.json")

    print(f"Index size after teams code addition: {get_index_size(index)}")

    add_to_index_lesson_calendar(index, f"../{scraper_dir}/lessons_schedule_by_course")
    print(f"Index size after lessons calendar addition: {get_index_size(index)}")


    add_to_index_room_calendar(index, f"../{scraper_dir}/room_schedule_per_site")
    print(f"Index size after rooms calendar addition: {get_index_size(index)}")


if __name__ == "__main__":
    asyncio.run(main())