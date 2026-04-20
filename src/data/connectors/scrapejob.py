from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")
# options.add_argument("--disable-gpu")
# options.add_argument("--no-sandbox")
# driver = webdriver.Chrome(options=options)

def get_jobinfo(driver,url):
    driver.get(url)

    # Accept cookies if present
    try:
        cookie_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter')]"))
        )
        cookie_button.click()
        time.sleep(1)
    except:
        pass

    # Wait for company link and h2 to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/fr/companies/']"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "h2"))
    )

    # Parse HTML
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Get company full text
    company_tag = soup.select_one("a[href^='/fr/companies/']")
    company = str(company_tag.get_text(strip=True)) if company_tag else None

    # Get first h2 job name
    h2_tag = soup.find("h2")
    job_name = str(h2_tag.get_text(strip=True)) if h2_tag else None

    metadata = {
        "Contract": "",
        "Location": "",
        "Remote": "",
        "Salary": "",
        "Clock": "",
        "Suitcase": "",
        "EducationLevel": ""
    }

    for div in soup.select("div.sc-fibHhp.iyXUgN"):
        icon = div.find(lambda tag: tag.name in ["svg", "img"] and tag.get("alt"))
        if icon:
            alt_name = icon.get("alt").strip()
            if alt_name in metadata:
                # Get all text in the div, remove the icon's label if present
                text_value = div.get_text(" ", strip=True)
                # Remove the alt label text if it appears in the text
                text_value = text_value.replace(alt_name, "", 1).strip()
                metadata[alt_name] = text_value
    return {
        "company": company,
        "job_name": job_name,
        **metadata
    }
