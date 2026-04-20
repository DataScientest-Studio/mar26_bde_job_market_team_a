from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pprint import pprint
# options = webdriver.ChromeOptions()
# options.add_argument("--headless")
# driver = webdriver.Chrome(options=options)

def scrape_search_page_to_dict(driver,query, location):
    jobs_dict = {}

    # try:
    base_url = (
        "https://www.welcometothejungle.com/fr/jobs"
        "?page={page}"
        f"&query={query}"
        f"&aroundQuery={location}"
    )
    page = 1
    # while True:
    url = base_url.format(page=page)
    driver.get(url)

    # Wait for job titles to appear or stop if none
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/fr/companies/'] h2"))
        )
    except:
        print(f"No more jobs found on page {page}")
        # break

    soup = BeautifulSoup(driver.page_source, "html.parser")
    found_jobs = False

    for h2_tag in soup.select("a[href^='/fr/companies/'] h2"):
        title = h2_tag.get_text(strip=True)
        link_tag = h2_tag.find_parent("a", href=True)
        if link_tag:
            jobs_dict[title] = "https://www.welcometothejungle.com" + link_tag["href"]
            found_jobs = True

    # if not found_jobs:
        # break

    print(f"Page {page} scraped")
        # page += 1

    # finally:
    #     driver.quit()
    return jobs_dict



