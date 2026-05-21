from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def scrape_searchpages(driver, scraping_classes):
    WELCOME_URL_BASE = "https://www.welcometothejungle.com"
    jobsearches_per_regionblock_dict = {}
    url = scraping_classes['entry_page_link']
    driver.get(url)

    # Wait for job titles to appear or stop if none
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, scraping_classes['link_presence']))
        )
    except:
        print(f"No search tags found on entry page.")
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    jobregion_block_elements = soup.select(f"div.{scraping_classes['entry_page_region_block_class']}")
   
    for searchregion_block in jobregion_block_elements:## TODO à modifier pour réduire le temps de test
            
            searchregion_name_elem = searchregion_block.previous_element
            searchregion_text = searchregion_name_elem.text.strip()
            if searchregion_text == 'Métiers par lettres':
                continue
            region_name = searchregion_text.replace("Offres d'emploi en ", "")
            searchtag_elements = searchregion_block.select(f'a.{scraping_classes["search_tags_class"]}')
            jobsearches_per_regionblock_dict[region_name] = {}
            for searchtag in searchtag_elements: #TODO à modifier pour réduire le sco^p de recherche
                search_link = searchtag.get('href')
                span = searchtag.find('span')
                search_text=span.text
                # Construction du dict à partir des différentes valeurs trouvées sur la page
                jobsearches_per_regionblock_dict[region_name][search_text] = WELCOME_URL_BASE+search_link

    return jobsearches_per_regionblock_dict
