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
driver = webdriver.Chrome(options=options)


def export_to_json(result_dict):
    
    connectors_dir = Path(__file__).parent
    src_data_dir = connectors_dir.parent
    src_dir = src_data_dir.parent
    project_root= src_dir.parent

    data_dump_folder = project_root.joinpath("data/raw/welcometothejungle")
    data_dump_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = data_dump_folder / f"welcometothejungle_{timestamp}.json"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(result_dict, file, indent=4, ensure_ascii=False)

def parse_yaml_scraping_classes():
    try:
        with open(SCRAPING_TAGS_YAML, "r") as f:
            scraping_dict=yaml.safe_load(f)
    except:
        print("Failed to load yaml tags file.")
    return scraping_dict

def initialize():
    try:
        
        scraping_dict = parse_yaml_scraping_classes()
        job_dicts_list=[]
        search_pages_dict = scrape_searchpages(driver,scraping_dict['entry_page'])
        
        for region in list(search_pages_dict.keys()):
            for search_text in list(search_pages_dict[region].keys()):
                jobs_dict={}
                search_url = search_pages_dict[region][search_text]
                jobs_dict[region] = scrape_search_page_to_dict(driver, search_url, scraping_dict['search_page'])
                job_dicts_list.append(jobs_dict) # append a dict

        job_results_dict = {}

        for jobs_dict in job_dicts_list:
            for job_region, job_dict in jobs_dict.items():#TODO ranger la région en clé type région: job1:url1 là c'est pas le cas
                for job_title, job_url in job_dict.items():
                
                    details = get_jobinfo(driver, job_url, scraping_dict["job_page"])
                    details['region'] = job_region
                    # Ajout de 'url en tant que clé de job (ID)
                    job_results_dict[job_url] = details
                

        for job, details in job_results_dict.items():
            print(f"\n{job}")
            for k, v in details.items():
                print(f"  {k}: {v}")


        pprint.pprint(job_results_dict)
        export_to_json(job_results_dict)


    finally:
        driver.quit()

if __name__ == "__main__":
    initialize()