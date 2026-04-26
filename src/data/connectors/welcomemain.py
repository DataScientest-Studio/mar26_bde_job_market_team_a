from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapesearchpage import scrape_search_page_to_dict
from scrapejob import get_jobinfo
import yaml, json, pprint

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)
YAML_TAGS = "references/webscraping_tags.yml"
YAML_SEARCH_QUERIES = "references/collection_targets.yml" #TODO
JSON_PATH = "src/data/json_export/welcometothejungle.json"

def export_to_json(result_dict):
    with open(JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(result_dict, file, indent=4, ensure_ascii=False)

def parse_yaml_scraping_classes():
    try:
        with open(YAML_TAGS, "r") as f:
            scraping_dict=yaml.safe_load(f)
    except:
        print("Failed to load yaml tags file.")
    return scraping_dict

def main():
    try:
        scraping_dict = parse_yaml_scraping_classes()
        #TODO Lire la collection target pour cette fonction et l'appliquer avec les inputs donnés par le yaml
        jobs_dict = scrape_search_page_to_dict(driver, "ingenieur","paris", scraping_dict['search_page'])


        job_results_dict = {}
        for job_name, job_url in jobs_dict.items():
            details = get_jobinfo(driver, job_url, scraping_dict["job_page"])
            job_results_dict[job_name] = details

        for job, details in job_results_dict.items():
            print(f"\n{job}")
            for k, v in details.items():
                print(f"  {k}: {v}")


        pprint.pprint(job_results_dict)
        export_to_json(job_results_dict)


    finally:
        driver.quit()

if __name__ == "__main__":
    main()