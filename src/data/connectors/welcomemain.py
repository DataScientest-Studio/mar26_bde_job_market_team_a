import json
import pprint

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.data.connectors.scrapejob import get_jobinfo
from src.data.connectors.scrapesearchpage import scrape_search_page_to_dict

YAML_TAGS = "references/webscraping_tags.yml"
YAML_SEARCH_QUERIES = "references/collection_targets.yml"  # TODO
JSON_PATH = "src/data/json_export/welcometothejungle.json"


def export_to_json(result_dict):
    with open(JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(result_dict, file, indent=4, ensure_ascii=False)


def parse_yaml_scraping_classes():
    with open(YAML_TAGS, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_welcome_to_the_jungle():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    try:
        scraping_dict = parse_yaml_scraping_classes()
        # TODO: read collection targets and apply all configured welcome searches.
        jobs_dict = scrape_search_page_to_dict(
            driver,
            "ingenieur",
            "paris",
            scraping_dict["search_page"],
        )

        job_results_dict = {}
        for job_name, job_url in jobs_dict.items():
            details = get_jobinfo(driver, job_url, scraping_dict["job_page"])
            details["source_url"] = job_url
            job_results_dict[job_name] = details

        for job, details in job_results_dict.items():
            print(f"\n{job}")
            for key, value in details.items():
                print(f"  {key}: {value}")

        pprint.pprint(job_results_dict)
        export_to_json(job_results_dict)
        return JSON_PATH
    finally:
        driver.quit()


def main():
    collect_welcome_to_the_jungle()


if __name__ == "__main__":
    main()
