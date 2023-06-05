import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from urllib.parse import urlparse

class SeleniumHelper:
    timeout: float = 30
    logger: logging.Logger = None

    @staticmethod
    def setup_logger(logger: logging.Logger):
        SeleniumHelper.logger = logger
    
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
    def wait_for_form_save_popup(driver: webdriver.Chrome) -> None:
        script = ""
        if SeleniumHelper.is_plan_page_url(driver.current_url):
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

    @staticmethod
    def login_user(url: str, driver: webdriver.Chrome, username: str, password: str) -> None:
        driver.get(url)
        if "AcceliTrack" in driver.current_url:
            return
        username_field = driver.find_element("id", "UserName")
        password_field = driver.find_element("id", "Password")
        submit_btn = driver.find_element("id", "lnkLogin")
        username_field.send_keys(username)
        password_field.send_keys(password)
        submit_btn.click()

    @staticmethod
    def measure_form_page_load_time(driver: webdriver.Chrome) -> float:
        start_time = time.time()
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_form_page_load(driver)
        return time.time() - start_time
    
    @staticmethod
    def measure_standard_page_load_time(driver: webdriver.Chrome) -> float:
        start_time = time.time()
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_standard_page_load(driver)
        return time.time() - start_time
    
    @staticmethod
    def measure_form_save_time(driver: webdriver.Chrome) -> float:
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_form_page_load(driver)
        # TODO: Do we really need to wait until loader dissapear?
        loader_locator = unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
        WebDriverWait(driver, SeleniumHelper.timeout).until(loader_locator)
        WebDriverWait(driver, SeleniumHelper.timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")))
        save_btns = driver.find_elements(By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")
        save_btn_elem = None
        for save_btn in save_btns:
            if save_btn.text == "Save Form":
                save_btn_elem = save_btn
                break
        start_time = time.time()
        if save_btn_elem != None:
            from frontline_selenium.page_filler import PageFormFiller
            try:
                PageFormFiller.fill_form(driver)
            except Exception as ex:
                SeleniumHelper.logger.exception(ex)
            attempts = 3
            start_time = time.time()
            while attempts > 0:
                attempts -= 1
                try:
                    WebDriverWait(driver, SeleniumHelper.timeout).until( unpresence_of_element((By.CSS_SELECTOR, ".loader-circle")))
                    driver.execute_script("window.scrollTo(0, 0);")
                    save_btn_elem.click()
                    break
                except ElementClickInterceptedException as ex:
                    time.sleep(1)
                    start_time = time.time()
            if attempts == 0:
                save_btn_elem.click()

            SeleniumHelper.wait_for_form_save_popup(driver)
        else:
            raise NoSuchElementException("'Save Form' was not found.")
        return time.time() - start_time
    
    
class unpresence_of_element(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver: webdriver.Chrome):
        try:
            driver.find_element(*self.locator)
            return False
        except:
            return True