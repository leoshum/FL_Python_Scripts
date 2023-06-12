import sys
import validators
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import json
from bs4 import BeautifulSoup

def replace_last_formId(url, new_formId):
    base_url, query_string = url.split('?')
    params = query_string.split('&')
    last_formId_index = -1
    for i in range(len(params) - 1, -1, -1):
        if params[i].startswith('formId='):
            last_formId_index = i
            break
    if last_formId_index != -1:
        params[last_formId_index] = 'formId=' + new_formId
    else:
        params.append('formId=' + new_formId)
    new_url = base_url + '?' + '&'.join(params)
    return new_url


def extract_tabs_from_plan(driver, url):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(url)
    tabs_list = []
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".k-tabstrip-items > li"))
        )
        tabs = driver.find_elements(By.CSS_SELECTOR, ".k-tabstrip-items > li")
        tabs_html = driver.find_element(By.CSS_SELECTOR, ".k-tabstrip-items").get_attribute('innerHTML')
        soup = BeautifulSoup(tabs_html, 'html.parser')
        tabs = soup.find_all('li')
        for tab in tabs:
            tabs_list.append([tab.find("span", class_='caption').text.strip(), replace_last_formId(driver.current_url, tab.get('data-id'))])
    except Exception as e:
        pass
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return tabs_list


def extract_tabs_from_planng(driver, url, section_name, base_url):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])
    tabs_info = []
    try:
        url_parts = urlparse(url)
        uri_splitted = url_parts.path.split("/")
        event_index = uri_splitted.index("ViewEvent")
        driver.get(f"{base_url}/plan/api/events/{uri_splitted[event_index + 1]}/details")
        event_details = json.loads(driver.find_element(By.CSS_SELECTOR, 'pre').text)
        event_id = event_details["eventModel"]["eventId"]
        common_student_id = event_details["eventModel"]["commonStudentModel"]["commonStudentId"]
        event_section = find_event_section(event_details, section_name)
        driver.get(f"{base_url}/plan/api/sections/?eventId={event_id}&eventSectionId={event_section['eventSectionId']}&commonStudentId={common_student_id}")
        tabs_api_info = json.loads(driver.find_element(By.CSS_SELECTOR, 'pre').text)["model"]
        for tab_info in tabs_api_info:
            link = f"{base_url}/planng/Events/ViewEvent/{event_id}/Forms/{event_section['nameHtmlText']}/{tab_info['formId']}"
            tabs_info.append([tab_info["formDefinitionNameFromResourcesFull"], link])
    except:
        pass
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return tabs_info


def find_event_section(event_details, section_name):
    for section_group in event_details["sectionGroups"]:
        for event_section in section_group["eventSections"]:
            if event_section["name"] == section_name:
                return event_section


def get_event_sections_list_with_tabs_extracted(event_sections, base_url, driver):
    new_event_sections_list = []
    for event_section in event_sections:
        tab_list = []
        if "planng" not in event_section[1]:
            tab_list = extract_tabs_from_plan(driver, event_section[1])
        else:
            tab_list = extract_tabs_from_planng(driver, event_section[1], event_section[0], base_url)

        if len(tab_list) > 1:
            for tab in tab_list:
                tab[0] = f"{event_section[0]} ({tab[0]})"
                new_event_sections_list.append(tab)
        else:
            new_event_sections_list.append(event_section)
    return new_event_sections_list


def login_user(driver, url, users):
    for user in users:
        driver.get(url)
        username_field = driver.find_element("id", "UserName")
        password_field = driver.find_element("id", "Password")
        submit_btn = driver.find_element("id", "lnkLogin")
        username_field.send_keys(user[0])
        password_field.send_keys(user[1])
        submit_btn.click()
        driver.get(f"{url}/plan")
        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(EC.presence_of_element_located((By.CLASS_NAME, "validator")))
            )
            if not driver.find_element(By.CLASS_NAME, "validator").text.strip() == "Access denied!":
                break
            else:
                for cookie in driver.get_cookies():    
                    driver.delete_cookie(cookie["name"])
        except:
            if "plan" in driver.current_url:
                return

def main():
    urls = open(sys.argv[1], 'r').readlines()
    users = [
        ("superlion", "CTAKAH613777"),
        ("PMGMT", "8Huds(3d")
    ]
    result_filename = "result.csv"
    prev_base_url = ""
    options = Options()
    #options.headless = True
    driver = webdriver.Chrome(options=options)
    with open(result_filename,'w') as file:
        pass

    for url in urls:
        if not validators.url(url):
            continue
        print(url)
        url_parts = urlparse(url)
        base_url = f"{url_parts.scheme}://{url_parts.netloc}"
        if base_url != prev_base_url:
            driver.get(base_url)
            login_user(driver, base_url, users)
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.any_of(
                EC.presence_of_element_located((By.ID, "pnlForm")),
                EC.presence_of_element_located((By.ID, "pnlEventContent")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-event-eligiblity-determination")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-progress-report")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-event-exceptionalities-view"))
            )
        )
        WebDriverWait(driver, 60).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page-title")),
            )
        )

        event_name = driver.find_element(By.CSS_SELECTOR, "h1.page-title").text
        event_sections = []
        if "planng" in url:
            uri_splitted = url_parts.path.split("/")
            event_index = uri_splitted.index("ViewEvent")
            driver.get(f"{base_url}/plan/api/events/{uri_splitted[event_index + 1]}/details")
            eventDetails = json.loads(driver.find_element(By.CSS_SELECTOR, 'pre').text)
            event_id = eventDetails["eventModel"]["eventId"]
            event_name = eventDetails["eventModel"]["name"]
            sectionGroups = eventDetails["sectionGroups"][1:-1]
            for sectionGroup in sectionGroups:
                for eventSection in sectionGroup["eventSections"]:
                    link = ""
                    if eventSection['isAngular']:
                        link = f"{base_url}/planng/Events/ViewEvent/{event_id}/Forms/{eventSection['nameHtmlText']}/{eventSection['eventSectionId']}"
                    else:
                        link = f"{base_url}/plan/Events/ViewEvent?eventId={event_id}#{eventSection['nameHtmlText']}"
                    name = eventSection['name']
                    event_sections.append([name, link])
        else:
            links = driver.find_elements(By.CSS_SELECTOR, "a.k-link")
            sections_to_exclude = ["#attachments", "#contactlognotes", "#eventoverview", "#distributionmanager", "#meetinginformation", "#studentinformation"]
            for link in links:
                exclude_section_not_exists = True 
                for exclude_section in sections_to_exclude:
                    if exclude_section in link.get_attribute("href"):
                        exclude_section_not_exists = False
                        break
                if exclude_section_not_exists:
                    event_sections.append([link.find_element(By.CSS_SELECTOR, "span").text, link.get_attribute("href")])
            
        event_sections = get_event_sections_list_with_tabs_extracted(event_sections, base_url, driver)
        prev_base_url = base_url
        
        with open(result_filename, "a+") as file:
            file.write(f"{event_name}\n")
        for event_section in event_sections:
            with open(result_filename, "a+") as file:
                file.write(f"{event_section[0]};{event_section[1]}\n")
        with open(result_filename, "a+") as file:
            file.write("\n")

if __name__ == "__main__":
    main()