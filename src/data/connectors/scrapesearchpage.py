from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pprint import pprint


def scrape_search_page_to_dict(driver, search_page, scraping_tags):
    jobs_dict = {}
    # url = search_page.format(page=page)
    driver.get(search_page)

    # Wait for job titles to appear or stop if none
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, scraping_tags['job_title']))
        )
    except:
        print("no jobs found here")

    soup = BeautifulSoup(driver.page_source, "html.parser")
    found_jobs = False

    #find job title h2 tag in search page
    for h2_tag in soup.select(scraping_tags['job_title']): #TODO remove [:3] if not testing
        title = h2_tag.get_text(strip=True)
        print(title)
        #get url in parent tag
        link_tag = h2_tag.find_parent("a", href=True)
        if link_tag:
            jobs_dict[title] = "https://www.welcometothejungle.com" + link_tag["href"]
            found_jobs = True
    print(jobs_dict)
    return jobs_dict



