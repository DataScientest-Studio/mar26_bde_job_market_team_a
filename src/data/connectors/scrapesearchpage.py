from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, WebDriverException

def scrape_search_page_to_dict(driver, search_page, scraping_tags):
    jobs_dict = {}

    try:
        driver.get(search_page)
    except WebDriverException as e:
        print(f"[Selenium error] Could not open page: {search_page}")
        print(e)
        return jobs_dict

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, scraping_tags['job_title']))
        )
    except TimeoutException:
        print(f"no jobs found here: {search_page}")
        return jobs_dict

    except WebDriverException as e:
        print(f"[Selenium error] Driver crashed or disconnected on: {search_page}")
        print(e)
        return jobs_dict

    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
    except WebDriverException as e:
        print(f"[Selenium error] Could not read page source: {search_page}")
        print(e)
        return jobs_dict

    for h2_tag in soup.select(scraping_tags['job_title']):
        title = h2_tag.get_text(strip=True)

        link_tag = h2_tag.find_parent("a", href=True)
        if link_tag:
            jobs_dict[title] = "https://www.welcometothejungle.com" + link_tag["href"]

    return jobs_dict


