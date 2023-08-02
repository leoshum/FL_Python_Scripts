import os
import sys
import time
import argparse
import validators
from urllib.parse import urlparse
from openpyxl import load_workbook
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException

package_path = os.path.abspath('..')
sys.path.append(package_path)
from frontline_selenium.selenium_helper import SeleniumHelper
from frontline_selenium.support_tech_helper import SupportTech

def extract_base_url(url):
	url_parts = urlparse(url)
	return f"{url_parts.scheme}://{url_parts.netloc}"

def find_distribute_button(driver):
    distribute_button = None
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for button in buttons:
        if "Distribute" in button.text:
            distribute_button = button
            break
    if not distribute_button:
        # distribute button is not found
        pass
    return distribute_button

def wait_dm(driver):
    wait = WebDriverWait(driver, 20)
    wait.until(
        EC.all_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#pnlEventFormsPackages table tr")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "#pnlDistributeTo table tr")),
        )
    )
    time.sleep(4)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    my_namespace = parser.parse_args()
    input_file = my_namespace.input_file

    wb = load_workbook(input_file, data_only=True)
    wb_sheet = wb.active

    options = Options()
    options.add_argument('--disable-cache')
    options.add_argument('--disable-features=NetworkService')
    options.add_argument('--disable-session-storage')
    driver = webdriver.Chrome(options=options)

    prev_base_url = ""
    base_url = ""
    for row in wb_sheet.iter_rows(min_row=5):
        url = row[1].value
        if not url or not validators.url(url): continue
        
        base_url = extract_base_url(url)
        if base_url != prev_base_url:
             SeleniumHelper.login_user(base_url, driver, "SFTDVTester", "ht2jGMM2GnC3bwX7")
        prev_base_url = base_url

        prev_tab = driver.window_handles[0]
        driver.execute_script("window.open('');")
        driver.switch_to.window(prev_tab)
        curr_tab = driver.window_handles[1]
        driver.close()
        driver.switch_to.window(curr_tab)

        driver.get(url)

        if "planng" in driver.current_url:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "accelify-distribution-manager")))
            find_distribute_button(driver)

            table = driver.find_element(By.CSS_SELECTOR, "#pnlDistributeTo table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            if rows and len(rows) > 1: rows = rows[1:]
            for row in rows:
                print(row.find_elements(By.CSS_SELECTOR, "td"))
        else:
            wait_dm(driver)
            packages_count = driver.execute_script("return $('#pnlEventFormsPackages table tr:gt(0)').length")
            for i in range(packages_count):
                wait_dm(driver)
                driver.execute_script("""
                    var first_elem = $("#pnlDistributeTo table tr:gt(0)").first();
                    var lastColumnValue = first_elem.find("td:last").find("input[type='checkbox']").click();
                    var dropdownlist = first_elem.find("td:last-of-type").prev().find("input[data-role='dropdownlist']").data("kendoDropDownList");
                    for (var i = 0; i < dropdownlist.dataItems().length; ++i) {
                        if (dropdownlist.dataItems()[i].Name != "Collaboration Portal") {
                            dropdownlist.value(dropdownlist.dataItems()[i].LookupValueId);
                            dropdownlist.trigger("change");
                            break;
                        }
                    }
                """)
                packages = driver.find_elements(By.CSS_SELECTOR, "#pnlEventFormsPackages table tr")
                print(packages)
                packages[i + 1].find_element(By.CSS_SELECTOR, "td div").click()
                time.sleep(1)
                driver.execute_script("$('#btnDistribute').click()")
                time.sleep(3)
                driver.get(url)

if __name__ == "__main__":
    main()