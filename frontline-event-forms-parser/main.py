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

urls = open(sys.argv[1], 'r').readlines()
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
        username_field = driver.find_element("id", "UserName")
        password_field = driver.find_element("id", "Password")
        submit_btn = driver.find_element("id", "lnkLogin")
        username_field.send_keys("PMGMT")
        password_field.send_keys("8Huds(3d")
        submit_btn.click()
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

    prev_base_url = base_url
    
    with open(result_filename, "a+") as file:
        file.write(f"{event_name}\n")
    for event_section in event_sections:
        with open(result_filename, "a+") as file:
            file.write(f"{event_section[0]};{event_section[1]}\n")
    with open(result_filename, "a+") as file:
        file.write("\n")
