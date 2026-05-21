import json
import pprint

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from src.data.connectors.scrapesearchpage import scrape_search_page_to_dict
from src.data.connectors.scrapejob import get_jobinfo
from src.data.connectors.scrape_entrypage import scrape_searchpages
import yaml, json, pprint, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env")

SCRAPING_TAGS_YAML = os.getenv("SCRAPING_TAGS")

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-extensions")
options.add_argument("--disable-notifications")
options.add_argument("--blink-settings=imagesEnabled=false")

prefs = {
    "profile.managed_default_content_settings.images": 2,
}
options.add_experimental_option("prefs", prefs)


def create_driver():
    return webdriver.Chrome(options=options)

def export_to_json(result_dict):
    
    connectors_dir = Path(__file__).parent
    src_data_dir = connectors_dir.parent
    src_dir = src_data_dir.parent
    project_root= src_dir.parent

    data_dump_folder = project_root.joinpath("data/raw/welcome_to_the_jungle")
    data_dump_folder.mkdir(parents=True, exist_ok=True)

    collection_date = datetime.now().strftime("%Y-%m-%d")
    json_path = data_dump_folder / f"welcome_to_the_jungle_{collection_date}.json"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(result_dict, file, indent=4, ensure_ascii=False)

def parse_yaml_scraping_classes():
    try:
        with open(SCRAPING_TAGS_YAML, "r") as f:
            scraping_dict=yaml.safe_load(f)
    except:
        print("Failed to load yaml tags file.")
    return scraping_dict

def parse_iso_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_already_scraped(published_at, latest_wttj):
    published_dt = parse_iso_datetime(published_at)
    latest_dt = parse_iso_datetime(latest_wttj)

    if not published_dt or not latest_dt:
        return False

    return published_dt <= latest_dt

def initialize():
    driver = create_driver()
    try:
        scraping_dict = parse_yaml_scraping_classes()
        search_pages_dict = scrape_searchpages(driver, scraping_dict['entry_page'])

        keys_list = list(search_pages_dict.keys())
        seen_search_urls = set()
        unique_jobs_dict = {}

        for counter, region in enumerate(keys_list):
            print(f"{region} : {counter+1} / {len(keys_list)}")

            for search_text in list(search_pages_dict[region].keys()):
                search_url = search_pages_dict[region][search_text]

                if search_url in seen_search_urls:
                    continue

                seen_search_urls.add(search_url)

                jobs_dict = scrape_search_page_to_dict(
                    driver,
                    search_url,
                    scraping_dict['search_page']
                )

                for job_title, job_url in jobs_dict.items():
                    if job_url not in unique_jobs_dict:
                        unique_jobs_dict[job_url] = {
                            "title": job_title,
                            "region": region,
                        }

        job_results_dict = {}
        total_unique_jobs = len(unique_jobs_dict)

        for counter, (job_url, job_meta) in enumerate(unique_jobs_dict.items(), start=1):
            job_title = job_meta["title"]
            job_region = job_meta["region"]

            print(f"[Job details] {counter} / {total_unique_jobs} - {job_title}")

            details = get_jobinfo(driver, job_url, scraping_dict["job_page"])
            details["region"] = job_region
            job_results_dict[job_url] = details

        print(f"[WelcomeToTheJungle] Scraped {len(job_results_dict)} jobs.")
        return export_to_json(job_results_dict)

    finally:
        driver.quit()


if __name__ == "__main__":
    initialize()
