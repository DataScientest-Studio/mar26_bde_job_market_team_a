from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import yaml

def scrape_job_title(soup, scraping_classes, result_dict):
    # Get job name from class
    jobtitle_element = soup.select_one(f"h2.{scraping_classes['job_title_class']}")
    job_name = str(jobtitle_element.get_text(strip=True)) if jobtitle_element else None
    result_dict['title'] = job_name
    return result_dict

def scrape_job_tags(soup, scraping_classes, result_dict):
    #================================ Job tags
    # initializing empty jobtags dictionary to dynamically fill with  scraped tags
    #finding first header of tags in page
    main_div = soup.select_one(f"div.{scraping_classes['job_tags_class']}")
    if main_div is None:
        return result_dict
    #gathering all tags in this header
    subdiv_elements = main_div.select(f"div.{scraping_classes['job_sub_tags_class']}")
    #getting all new keys and values for the dictionary based on whats displayed on site
    for div in subdiv_elements:
        icon = div.find(lambda tag: tag.name in ["svg", "img"] and tag.get("alt"))
        if icon:
            alt_name = icon.get("alt").strip()
            # Get all text in the div, remove the icon's label if present
            text_value = div.get_text(" ", strip=True)
            # Remove the alt label text if it appears in the text
            text_value = text_value.replace(alt_name, "", 1).strip()

            result_dict[alt_name] = text_value
    return result_dict

def scrape_company_name(soup, scraping_classes, result_dict):
    # Get company full text
    company_name_element = soup.select_one(f"span.{scraping_classes['company_name_class']}")
    company_name_str = company_name_element.get_text(strip=True)
    result_dict['company'] = company_name_str
    return result_dict

def scrape_company_industry(soup, scraping_classes, result_dict):
    #============================== Industry
    # industry element is a specific div with the alt="Tag" on the page
    #finding first header of company details
    company_tags_main_elem = soup.select_one(f"div.{scraping_classes['company_tags_class']}")
    if company_tags_main_elem is None:
        return result_dict
    #gathering all tags in this header
    company_tags_elements = company_tags_main_elem.select(f"div.{scraping_classes['company_sub_tag_class']}")
    #getting all new keys and values for the dictionary based on whats displayed on site
    for div in company_tags_elements:
        icon = div.find(lambda tag: tag.name in ["svg", "img"] and tag.get("alt"))
        if icon:
            alt_name = icon.get("alt").strip()
            if alt_name == "Tag":
                span = div.find("span")
                if span:
                    industry_name = span.get_text(strip=True)
                if industry_name:
                    result_dict['industry']=industry_name
                    break
    return result_dict

def scrape_skills(soup, scraping_classes, result_dict):
    #================================ Skills
    #
    skills_lst = []
    skills_elements = soup.select(f"div.{scraping_classes['skills_class']}")
    for skill in skills_elements:
        span = skill.find('span')
        if span:
            skill_text = span.get_text(strip=True)
            if skill_text not in skills_lst:
                skills_lst.append(skill_text)
    if skills_lst != []:
        result_dict['skills'] = skills_lst

def get_description_snippet(soup, scraping_classes, result_dict, char_limit=240):
    description_element = soup.select_one(f"div.{scraping_classes['description_class']}")
    if description_element is None:
        return result_dict
    description_text = description_element.get_text(strip=True)
    description_snippet = description_text[:char_limit]
    result_dict['description'] = description_snippet
    return result_dict

def reformat_job_tags(result_dict):
    result_dict_keys_lst = list(result_dict.keys())
    if 'Contract' in result_dict_keys_lst:
        result_dict['contract_type']=result_dict.pop('Contract')
    if 'Location' in result_dict_keys_lst:
        result_dict['location']=result_dict.pop('Location')
    if 'Remote' in result_dict_keys_lst:
        result_dict['remote']=result_dict.pop('Remote')
    if 'Salary' in result_dict_keys_lst:
        result_dict['salary']=result_dict.pop('Salary')
    if 'Clock' in result_dict_keys_lst:
        result_dict['starting_date']=result_dict.pop('Clock')
    if 'Suitcase' in result_dict_keys_lst:
        result_dict['experience']=result_dict.pop('Suitcase')
    if 'EducationLevel' in result_dict_keys_lst:
        result_dict['education']=result_dict.pop('EducationLevel')

def scrape_publication_datetime(soup, scraping_classes, result_dict,):
    publication_date_element = soup.select_one(f"p.{scraping_classes['publication_date_class']}")
    if publication_date_element is None:
        return result_dict
    time_element=publication_date_element.find("time")
    if time_element and time_element.has_attr('datetime'):
        publication_datetime = time_element['datetime']
        result_dict['published_at'] = publication_datetime
    return result_dict

def accept_cookies_once(driver):
    if getattr(accept_cookies_once, "done", False):
        return

    try:
        cookie_button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'OK pour moi')]"))
        )
        cookie_button.click()
        time.sleep(0.2)
    except:
        pass
    finally:
        accept_cookies_once.done = True

def get_jobinfo(driver,url, scraping_classes):

    driver.get(url)

    # Accept cookies if present
    accept_cookies_once(driver)

    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "h2"))
    )

    # Parse HTML
    soup = BeautifulSoup(driver.page_source, "html.parser")
    result_dict = {}
    scrape_job_title(soup, scraping_classes, result_dict)
    scrape_publication_datetime(soup,scraping_classes,result_dict)
    scrape_company_name(soup, scraping_classes, result_dict)
    scrape_company_industry(soup, scraping_classes, result_dict)
    scrape_job_tags(soup, scraping_classes, result_dict)
    reformat_job_tags(result_dict)
    scrape_skills(soup, scraping_classes, result_dict)
    get_description_snippet(soup,scraping_classes,result_dict)
    result_dict['id']=url
    #=================
    return result_dict
    
