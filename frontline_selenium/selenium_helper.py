import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse
class SeleniumHelper:
    timeout: float = 30

    @staticmethod
    def is_plan_page_url(url: str) -> bool:
        return not ("planng" in url)
    
    @staticmethod
    def is_form_page_url(url: str) -> bool:
        return "Forms" in url or ("ViewEvent" in url and urlparse(url).fragment)
    
    @staticmethod
    def get_build_version(driver: webdriver.Chrome) -> str:
        return driver.find_element(By.CSS_SELECTOR, "span.version").text.replace("Version ", "")
    
    @staticmethod
    def wait_for_form_page_load(driver: webdriver.Chrome) -> None:
        wait = WebDriverWait(driver, SeleniumHelper.timeout)
        element = wait.until(
            EC.any_of(
                EC.visibility_of_element_located((By.ID, "pnlForm")),
                EC.visibility_of_element_located((By.ID, "pnlEventContent")),
                EC.visibility_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                EC.visibility_of_element_located((By.TAG_NAME, "accelify-event-eligiblity-determination")),
                EC.visibility_of_element_located((By.TAG_NAME, "accelify-progress-report")),
                EC.visibility_of_element_located((By.TAG_NAME, "accelify-event-exceptionalities-view"))
            )
        )
        start_time = time.time()
        while time.time() - start_time < SeleniumHelper.timeout:
            if driver.execute_script("return $(arguments[0]).find('input').length > 0;", element):
                break
            time.sleep(1)
    
    @staticmethod
    def wait_for_standard_page_load(driver: webdriver.Chrome) -> None:
        WebDriverWait(driver, SeleniumHelper.timeout).until(
            EC.any_of(
                unpresence_of_element((By.CLASS_NAME, "loading-wrapper")),
                unpresence_of_element((By.CLASS_NAME, "blockUI")),
                unpresence_of_element((By.CLASS_NAME, "blockMsg")),
                unpresence_of_element((By.CLASS_NAME, "blockPage"))
            )
        )
    
    @staticmethod
    def wait_for_form_save_popup(url: str, driver: webdriver.Chrome) -> None:
        script = ""
        if SeleniumHelper.is_plan_page_url(url):
            script = "return $(\"div[role='alert']\").text()"
        else:
            script = "return $(\"kendo-notification\").text()"
        
        temp_start_time = time.time()
        while time.time() - temp_start_time < SeleniumHelper.timeout:
            script_result = driver.execute_script(script)
            if script_result != None and "Form has been updated successfully" in script_result:
                break
            time.sleep(1)
        return time.time() - temp_start_time


class unpresence_of_element(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver: webdriver.Chrome):
        try:
            driver.find_element(*self.locator)
            return False
        except:
            return True