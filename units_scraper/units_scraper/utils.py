
import datetime
import json

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
    
import json
from datetime import datetime
from pathlib import Path

def print_scraping_summary(stats: dict, log_file: str = "scraping_summary.log"):
    # Stampa raw dict per debug
    print(json.dumps(stats, indent=4, default=str))

    start_time = stats.get("start_time")
    if start_time is None:
        start_time = datetime.now()
    
    # finish_time preferibile da stats, altrimenti usa adesso
    end_time = stats.get("finish_time", datetime.now())
    request_depth_max = stats.get("request_depth_max", 0)

    elapsed = stats.get("elapsed_time_seconds")
    if elapsed is None:
        elapsed = (end_time - start_time).total_seconds()
    
    item_scraped_count = stats.get("item_scraped_count", 0)

    summary_lines = [
        f"\n====== SCRAPING SESSION {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======",
        f"🕒 elapsed time: {format_time(elapsed)}",
        f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"📄 Total items scraped: {item_scraped_count}",
        f"📊 Max request depth: {request_depth_max}",
        "==================================================="
    ]

    # Stampa a video
    for line in summary_lines:
        print(line)

    # Salva su file (append)
    log_path = Path(log_file)
    with log_path.open("a", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")


def remove_output_directory(dir_path = "output_bodies"):
    from shutil import rmtree
    from os import path

    if path.exists(dir_path) and path.isdir(dir_path):
        rmtree(dir_path)
        print(f"Output directory '{dir_path}' removed.")
    else:
        print(f"Output directory '{dir_path}' does not exist.")