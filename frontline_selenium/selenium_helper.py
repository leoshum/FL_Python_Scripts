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
    def get_logger():
        """Return a safe logger - either the configured one or a default logger"""
        return SeleniumHelper.logger if SeleniumHelper.logger is not None else logging.getLogger(__name__)

    @staticmethod
    def set_options(options: dict):
        SeleniumHelper.options = options
    
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
        
        while time.time() - start_time < timeout:
            try:
                api_errors = driver.execute_script("""
                    const errors = [];
                    try {
                        const entries = performance.getEntriesByType('resource');
                        const currentDomain = window.location.hostname.toLowerCase();
                        
                        entries.forEach(entry => {
                            const url = entry.name.toLowerCase();
                            let entryDomain = '';
                            
                            try {
                                entryDomain = new URL(entry.name).hostname.toLowerCase();
                            } catch(e) {
                                return; // Skip invalid URLs
                            }
                            
                            const isOurDomain = entryDomain.includes(currentDomain);                            
                            const isXmlHttpRequest = entry.initiatorType === 'xmlhttprequest';
                            const hasApiInUrl = url.includes('/api/');
                            
                            if (isOurDomain && isXmlHttpRequest && hasApiInUrl) {
                                if (entry.responseStatus >= 500) {
                                    errors.push({
                                        url: entry.name,
                                        fullUrl: entry.name,
                                        status: entry.responseStatus,
                                        type: 'http_error',
                                        duration: entry.duration,
                                        transferSize: entry.transferSize || 0
                                    });
                                }
                                // Check for failed requests, but exclude cancelled requests
                                else if (entry.responseStatus === 0 && entry.responseEnd > 0) {
                                    const isCancelledRequest = (
                                        entry.responseStart === 0 ||           // No response started
                                        entry.transferSize === 0 ||            // No data transferred
                                        (entry.duration > 0 && entry.duration < 1) // Very short duration suggests cancellation
                                    );                                    
                                    if (!isCancelledRequest) {
                                        errors.push({
                                            url: entry.name,
                                            fullUrl: entry.name,
                                            status: 0,
                                            type: 'network_error',
                                            duration: entry.duration,
                                            transferSize: entry.transferSize || 0
                                        });
                                    }
                                }
                            }
                        });
                    } catch(e) {
                        // Ignore performance API errors
                    }
                    return errors;
                """)
                
                #TODO: validate what we do not have duplicates of error 
                # example from logs
                # 08-19-25_15:36 - Starting save measurement
                # 08-19-25_15:37 - API Error Details: GET https://houston-tx-hotfix-acc.ss.frontlineeducation.com/plan/api/stateReporting/c0128922-3a86-4c0a-bc57-b32500f63687/RecalculateFields?consentReceivedDate=0002-08-02T00:00:00.000&studentAbsencesOverEvaluation=0&radioWasTheStudentAbsent=undefined&campusId=1362 - HTTP 500 (took 3129.0ms)
                # 08-19-25_15:37 - API Error Details: GET https://houston-tx-hotfix-acc.ss.frontlineeducation.com/plan/api/stateReporting/c0128922-3a86-4c0a-bc57-b32500f63687/RecalculateFields?consentReceivedDate=0020-08-02T00:00:00.000&studentAbsencesOverEvaluation=0&radioWasTheStudentAbsent=undefined&campusId=1362 - HTTP 500 (took 3064.8ms)
                # 08-19-25_15:37 - API Error Details: GET https://houston-tx-hotfix-acc.ss.frontlineeducation.com/plan/api/stateReporting/c0128922-3a86-4c0a-bc57-b32500f63687/RecalculateFields?consentReceivedDate=0202-08-02T00:00:00.000&studentAbsencesOverEvaluation=0&radioWasTheStudentAbsent=undefined&campusId=1362 - HTTP 500 (took 3003.7ms)

                if api_errors:
                    error_details = []
                    for error in api_errors:
                        full_url = error.get('fullUrl', error['url'])
                        status = error['status']
                        duration = error.get('duration', 0)
                        
                        if error['type'] == 'http_error':
                            error_details.append(f"{full_url} Status Code: {status} ({duration:.1f}ms)")
                        else:
                            error_details.append(f"{full_url} Network error ({duration:.1f}ms)")
                        
                        request_body = SeleniumHelper._get_network_request_body(driver, full_url, status)

                        method = "POST" if request_body else "GET"
                        
                        SeleniumHelper.logger.error(f"API Error Details: {method} {full_url} - HTTP {status} (took {duration:.1f}ms)")

                        if request_body:
                            SeleniumHelper.logger.error(f"Request body: {request_body}")
                    
                    error_msg = f"Save failed due to API error - {'; '.join(error_details)}"
                    raise ValueError(error_msg)
                
                success_found = driver.execute_script("""
                    const successTexts = [
                        'Form has been updated successfully',
                        'has been updated successfully',
                        'successfully updated',
                        'saved successfully',
                    ];
                    
                    const pageText = document.documentElement.innerText || document.documentElement.textContent || '';
                    const lowerPageText = pageText.toLowerCase();
                    
                    return successTexts.some(successText => 
                        lowerPageText.includes(successText.toLowerCase())
                    );
                """)
                
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
        
        elapsed = time.time() - start_time
        error_msg = f"Save message timeout after {elapsed:.0f}s"
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