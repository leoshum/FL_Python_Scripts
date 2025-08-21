import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
    def _load_script(script_name: str, params: dict = {}) -> str:
        script_path = os.path.join(SeleniumHelper.util_scripts_directory, script_name)
        with open(script_path, "r", encoding="utf-8") as script_file:
            script = script_file.read()
            for key, value in params.items():
                script = script.replace(key, str(value))
            return script
    
    @staticmethod
    def is_plan_page_url(url: str) -> bool:
        return not ("planng" in url)
    
    @staticmethod
    def is_form_page_url(url: str) -> bool:
        # EventOverview is the only ViewEvent page that's NOT a form
        if "EventOverview" in url:
            return False
        
        # Any ViewEvent URL (except EventOverview) is a form page
        if "ViewEvent" in url:
            return True
            
        # Include other form types
        return ("Forms" in url or "DistributionManager" in url)
    
    
    @staticmethod
    def get_build_version(driver: webdriver.Chrome) -> str:
        return driver.find_element(By.CSS_SELECTOR, "span.version").text.replace("Version ", "")
    
    @staticmethod
    def wait_for_standard_page_load(driver: webdriver.Chrome) -> None:                
        # Check if loading indicators exist before waiting for their absence
        loading_selectors = [".loading-wrapper", ".blockUI", ".blockMsg", ".blockPage"]
        loading_elements = []
        
        for selector in loading_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            loading_elements.extend(elements)
        
        try:
            if loading_elements:
                # TODO: move magic number to config 
                WebDriverWait(driver, 10).until(
                    lambda d: not d.find_elements(By.CSS_SELECTOR, 
                        ".loading-wrapper, .blockUI, .blockMsg, .blockPage")
                )
                print("Loading indicators cleared")
            else:
                # No loading indicators found - wait for document ready state
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print("Document ready")
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Standard page load timeout: {str(ex)}")
            raise
    
    @staticmethod
    def wait_for_form_save_popup(driver: webdriver.Chrome) -> float:
        start_time = time.time()
        timeout = 20  # sec
        interval = 0.1  # sec
        
        try:
            driver.execute_cdp_cmd('Network.enable', {})
        except:
            SeleniumHelper.logger.error("Network.enable failed")

        api_errors_script = SeleniumHelper._load_script("get_api_error_request.js")
        success_script = SeleniumHelper._load_script("get_saved_notification.js")
        
        while time.time() - start_time < timeout:
            try:
                api_errors = driver.execute_script(api_errors_script)

                if api_errors:
                    error_details = []
                    for error in api_errors:
                        full_url = error['url']
                        status = error['status']
                        duration = error['duration']
                        
                        error_details.append(f"{full_url} Status Code: {status} ({duration:.1f}ms)")
                        
                        request_body = SeleniumHelper._get_network_request_body(driver, full_url, status)

                        method = "POST" if request_body else "GET"
                        
                        SeleniumHelper.logger.error(f"API Error Details: {method} {full_url} - HTTP {status} (took {duration:.1f}ms)")

                        if request_body:
                            SeleniumHelper.logger.error(f"Request body: {request_body}")
                    
                    error_msg = f"Save failed due to API error - {'; '.join(error_details)}"
                    raise ValueError(error_msg)
                
                success_found = driver.execute_script(success_script)
                
                if success_found:
                    elapsed = time.time() - start_time
                    if SeleniumHelper.logger:
                        SeleniumHelper.logger.info(f"Save success message found after {elapsed:.1f}s")
                    return elapsed
                
            except ValueError:
                raise
            except Exception as e:
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.warning(f"Error during save popup check: {str(e)}")
            
            time.sleep(interval)
        
        error_msg = f"Save message timeout after {timeout:.0f}s"
        SeleniumHelper.logger.error(error_msg)
        raise TimeoutException(error_msg)

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
    def handle_warning_popup(driver: webdriver.Chrome) -> bool:
        """
        handle warning popup whick appears after Save button click if it exists
        """
        try:
            popup_wait = WebDriverWait(driver, 1)
            warning_dialog = popup_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'][aria-modal='true'].k-window.k-dialog"))
            )
            
            ok_button = warning_dialog.find_element(By.CSS_SELECTOR, "button#btnSave")
            if ok_button and "Ok" in ok_button.text:
                ok_button.click()
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.info("Warning popup detected and OK button clicked")
                
                WebDriverWait(driver, 2).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog'][aria-modal='true'].k-window.k-dialog"))
                )
                return True
                
        except:
            pass
        
        return False

    # TODO: add loger for exeption handling after test
    @staticmethod
    def _get_network_request_body(driver, failed_url, status_code):
        try:
            import json
            logs = driver.get_log('performance')
            
            for log in logs:
                message = json.loads(log['message'])
                
                if message['message']['method'] == 'Network.requestWillBeSent':
                    params = message['message']['params']
                    request = params['request']
                    
                    if (request['url'] == failed_url and 
                        request['method'] == 'POST' and 
                        'postData' in request):
                        return request['postData']
            
            return None
            
        except Exception:
            return None