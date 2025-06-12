import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, UnexpectedAlertPresentException
from urllib.parse import urlparse

class SeleniumHelper:
    timeout: float = 30
    logger: logging.Logger = None
    options: dict = {}
    util_scripts_directory: str = os.path.dirname(os.path.abspath(__file__)) + "\\util_scripts\\"

    @staticmethod
    def setup_logger(logger: logging.Logger):
        SeleniumHelper.logger = logger

    @staticmethod
    def set_options(options: dict):
        SeleniumHelper.options = options
    
    @staticmethod
    def is_plan_page_url(url: str) -> bool:
        return not ("planng" in url)
    
    @staticmethod
    def is_form_page_url(url: str) -> bool:
        parsed_url = urlparse(url)
        if "EventOverview" in parsed_url.path:
            return False
        return "Forms" in url or ("ViewEvent" in url and parsed_url.fragment)
    
    @staticmethod
    def get_build_version(driver: webdriver.Chrome) -> str:
        return driver.find_element(By.CSS_SELECTOR, "span.version").text.replace("Version ", "")
    
    @staticmethod
    def wait_for_form_page_load(driver: webdriver.Chrome) -> None:
        # Check if this is a form URL that doesn't exist
        if driver.current_url.endswith("planng/"):
            raise ValueError("Form does not exist")
        
        max_wait_time = SeleniumHelper.timeout
        start_time = time.time()
        
        # Wait for the main form container
        try:
            element = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "accelify-forms-details"))
            )
        except Exception:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".form-container, .main-content, body"))
                )
            except Exception as ex:
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.error(f"Form container not found: {str(ex)}")
                element = driver.find_element(By.TAG_NAME, "body")
        
        # Wait for AJAX requests to complete and form data to load
        stable_content_count = 0
        last_content_hash = None
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check for form content stability
                form_ready = driver.execute_script("""
                    var element = arguments[0];
                    var results = {};
                    
                    // Check for meaningful input elements (exclude navigation buttons)
                    var meaningfulInputs = element.querySelectorAll('input:not([type="button"]):not([type="submit"]):not([type="reset"]), select, textarea');
                    results.inputs_count = meaningfulInputs.length;
                    
                    // Get input types for debugging (exclude buttons)
                    var inputTypes = [];
                    meaningfulInputs.forEach(function(input) {
                        inputTypes.push(input.tagName.toLowerCase());
                    });
                    results.input_types = inputTypes;
                    
                    // Get content hash for stability check
                    var textContent = element.textContent.trim();
                    results.text_length = textContent.length;
                    results.content_hash = textContent.length + '_' + meaningfulInputs.length;
                    
                    // Form is ready only if we have meaningful inputs AND content
                    if (meaningfulInputs.length > 0) {
                        // Also check for loaded content
                        if (textContent.length > 100) {
                            results.ready_reason = 'inputs_and_content_found';
                            results.text_preview = textContent.substring(0, 50) + '...';
                            return results;
                        } else {
                            // If we have inputs but no content, wait more
                            results.ready_reason = null;
                            return results;
                        }
                    }
                    
                    // Check for Angular components
                    var angularComponents = element.querySelectorAll('[ng-app], [data-ng-app], .ng-scope, [ng-controller]');
                    results.angular_count = angularComponents.length;
                    if (angularComponents.length > 0) {
                        results.ready_reason = 'angular_ready';
                        return results;
                    }
                    
                    // Check for loaded content (non-empty text)
                    if (textContent.length > 100) {  // Increased threshold
                        results.ready_reason = 'content_loaded';
                        results.text_preview = textContent.substring(0, 50) + '...';
                        return results;
                    }
                    
                    // Check for specific form indicators
                    var formElements = element.querySelectorAll('form, .form-group, .field-validation-error');
                    results.form_elements_count = formElements.length;
                    if (formElements.length > 0 && textContent.length > 100) {
                        results.ready_reason = 'form_structure';
                        return results;
                    }
                    
                    results.ready_reason = null;
                    return results;
                """, element)
                
                # Check content stability - require only 1 stable check instead of 2
                current_hash = form_ready.get('content_hash', '')
                if current_hash == last_content_hash:
                    stable_content_count += 1
                else:
                    stable_content_count = 0
                    last_content_hash = current_hash
                
                # If content is stable and form is ready
                if form_ready and form_ready.get('ready_reason') and stable_content_count >= 1:
                    elapsed = time.time() - start_time
                    break
                    
            except Exception as e:
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.warning(f"Form readiness check failed, using fallback: {str(e)}")
                # Fallback: direct Selenium element search
                if element.find_elements(By.CSS_SELECTOR, "input, select, textarea, button, form"):
                    elapsed = time.time() - start_time
                    break
                    
        # Final check - if we still haven't found form elements, it might be a read-only page
        
        # Final check - if we still haven't found form elements, it might be a read-only page
        if time.time() - start_time >= max_wait_time:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.warning(f"Form load timeout after {max_wait_time}s, using fallback wait")
            time.sleep(1)  # Brief additional wait for stability
    
    @staticmethod
    def wait_for_standard_page_load(driver: webdriver.Chrome) -> None:                
        # Check if loading indicators exist before waiting for their absence
        loading_selectors = [".loading-wrapper", ".blockUI", ".blockMsg", ".blockPage"]
        loading_elements = []
        
        for selector in loading_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            loading_elements.extend(elements)
            
        print(f"🔍 Checking page readiness...")
        
        try:
            if loading_elements:
                # Wait for loading indicators to disappear
                WebDriverWait(driver, 10).until(
                    lambda d: not d.find_elements(By.CSS_SELECTOR, 
                        ".loading-wrapper, .blockUI, .blockMsg, .blockPage")
                )
                print("✅ Loading indicators cleared")
            else:
                # No loading indicators found - wait for document ready state
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print("✅ Document ready")
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Standard page load timeout: {str(ex)}")
            raise
    
    @staticmethod
    def wait_for_form_save_popup(driver: webdriver.Chrome) -> None:
        temp_start_time = time.time()
        
        while time.time() - temp_start_time < SeleniumHelper.timeout:
            try:
                # Modern approach without jQuery dependency
                if SeleniumHelper.is_plan_page_url(driver.current_url):
                    script_result = driver.execute_script("""
                        var alertDiv = document.querySelector('div[role="alert"]');
                        return alertDiv ? alertDiv.textContent : null;
                    """)
                else:
                    script_result = driver.execute_script("""
                        var notification = document.querySelector('kendo-notification');
                        return notification ? notification.textContent : null;
                    """)
                
                if script_result and "Form has been updated successfully" in script_result:
                    break
                    
            except UnexpectedAlertPresentException:
                try:
                    Alert(driver).accept()
                except:
                    pass
            except Exception:
                # Fallback: direct element search
                if SeleniumHelper.is_plan_page_url(driver.current_url):
                    alert_elem = driver.find_element(By.CSS_SELECTOR, 'div[role="alert"]')
                    if alert_elem and "Form has been updated successfully" in alert_elem.text:
                        break
                else:
                    notification_elem = driver.find_element(By.TAG_NAME, 'kendo-notification')
                    if notification_elem and "Form has been updated successfully" in notification_elem.text:
                        break
                    
            time.sleep(0.25)

        requests = SeleniumHelper.get_ajax_requests(driver)[::-1]
        error_occured = False
        form_save_endpoint = "plan/Events/UpdateForm" if SeleniumHelper.is_plan_page_url(driver.current_url) else "plan/api/forms/"
        for request in requests:
            if form_save_endpoint in request["url"]:
                if request["status"] != 200:
                    error_occured = True
                break

        if error_occured:
            raise ValueError("Exception occured while saving the form!")
        return time.time() - temp_start_time

    @staticmethod
    def login_user(url: str, driver: webdriver.Chrome, username: str, password: str) -> None:
        try:
            driver.get(url)
            if "AcceliTrack" in driver.current_url:
                return
            
            # Wait for login form elements to be present and clickable
            try:
                username_field = WebDriverWait(driver, SeleniumHelper.timeout).until(
                    EC.presence_of_element_located((By.ID, "UserName"))
                )
                password_field = WebDriverWait(driver, SeleniumHelper.timeout).until(
                    EC.presence_of_element_located((By.ID, "Password"))
                )
                submit_btn = WebDriverWait(driver, SeleniumHelper.timeout).until(
                    EC.element_to_be_clickable((By.ID, "lnkLogin"))
                )
            except Exception as ex:
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.error(f"Login form elements not found. Current URL: {driver.current_url}")
                    SeleniumHelper.logger.error(f"Page title: {driver.title}")
                    SeleniumHelper.logger.error(f"Error: {str(ex)}")
                raise
            
            username_field.send_keys(username)
            password_field.send_keys(password)
            submit_btn.click()
            
            # Wait for login to complete (URL should change)
            WebDriverWait(driver, SeleniumHelper.timeout).until(
                lambda d: "AcceliTrack" in d.current_url or d.current_url != url
            )
            
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Login failed: {str(ex)}")
            raise

    @staticmethod
    def measure_form_page_load_time(driver: webdriver.Chrome) -> float:
        start_time = time.time()
        # Force hard reload to measure real loading time
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_form_page_load(driver)
        return time.time() - start_time
    
    @staticmethod
    def measure_standard_page_load_time(driver: webdriver.Chrome) -> float:
        start_time = time.time()
        # Force hard reload to measure real loading time
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_standard_page_load(driver)
        elapsed = time.time() - start_time
        return elapsed
    
    @staticmethod
    def measure_form_save_time(driver: webdriver.Chrome) -> float:
        # Force hard reload to ensure clean state
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_form_page_load(driver)
        
        try:
            # Wait for form to be ready for interaction
            loader_locator = unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
            WebDriverWait(driver, SeleniumHelper.timeout).until(loader_locator)
            WebDriverWait(driver, SeleniumHelper.timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")))
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Form save preparation timeout: {str(ex)}")
            raise
        
        save_btns = driver.find_elements(By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")
        save_btn_elem = None
        for save_btn in save_btns:
            if "Save" in save_btn.text:
                save_btn_elem = save_btn
                break
                
        if save_btn_elem is None:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error("Save button not found on form")
            raise NoSuchElementException("'Save Form' was not found.")
            
        start_time = time.time()
        
        from frontline_selenium.page_filler import PageFormFiller
        try:
            if not SeleniumHelper.options.get("disable_filler", False):
                PageFormFiller.fill_form(driver)
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.exception(f"Form filler error: {str(ex)}")
            # Don't re-raise - form filler errors shouldn't stop save measurement
            
        # Retry logic for clicking save button
        attempts = 3
        start_time = time.time()
        while attempts > 0:
            attempts -= 1
            try:
                WebDriverWait(driver, SeleniumHelper.timeout).until(unpresence_of_element((By.CSS_SELECTOR, ".loader-circle")))
                driver.execute_script("window.scrollTo(0, 0);")
                save_btn_elem.click()
                break
            except ElementClickInterceptedException as ex:
                if attempts > 0:  # Only sleep if we have more attempts
                    if SeleniumHelper.logger:
                        SeleniumHelper.logger.warning(f"Save button click intercepted, retrying... ({attempts} attempts left)")
                    time.sleep(1)
                    start_time = time.time()  # Reset timer after sleep
                else:
                    if SeleniumHelper.logger:
                        SeleniumHelper.logger.error(f"Save button click failed after all retries: {str(ex)}")
                    raise  # Re-raise on final attempt
                    
        try:
            SeleniumHelper.wait_for_form_save_popup(driver)
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Form save popup timeout: {str(ex)}")
            raise
            
        elapsed = time.time() - start_time
        return elapsed
    
    @staticmethod
    def get_ajax_requests(driver: webdriver.Chrome) -> list[dict]:
        with open(SeleniumHelper.util_scripts_directory + "get_requests.js", "r") as script_file:
            script = script_file.read()
            return driver.execute_script(script)

    
class unpresence_of_element(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver: webdriver.Chrome):
        try:
            driver.find_element(*self.locator)
            return False
        except:
            return True