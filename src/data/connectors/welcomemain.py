# main.py  (combined runner)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapesearchpage import scrape_search_page_to_dict
from scrapejob import get_jobinfo

options = Options()
# options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

try:

    jobs_dict = scrape_search_page_to_dict(driver, "ingenieur","paris")

    all_results = {}
    for job_name, job_url in jobs_dict.items():
        details = get_jobinfo(driver, job_url)
        all_results[job_name] = details

    for job, details in all_results.items():
        print(f"\n{job}")
        for k, v in details.items():
            print(f"  {k}: {v}")

finally:
    driver.quit()