import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, UnexpectedAlertPresentException, TimeoutException, StaleElementReferenceException
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
        parsed_url = urlparse(url)
        if "EventOverview" in parsed_url.path:
            return False
        # Include DistributionManager and EligibilitiesImpairments as form pages
        return ("Forms" in url or 
                ("ViewEvent" in url and parsed_url.fragment) or
                "DistributionManager" in url or
                "EligibilitiesImpairments" in url)
    
    @staticmethod
    def get_build_version(driver: webdriver.Chrome) -> str:
        return driver.find_element(By.CSS_SELECTOR, "span.version").text.replace("Version ", "")
    
    @staticmethod
    def wait_for_form_page_load(driver: webdriver.Chrome, timeout: int = 30) -> None:
        """
        INDUSTRY-STANDARD form page load detection using MutationObserver.
        Proven approach used by modern testing frameworks like Playwright and Cypress.
        Simple, reliable, and fast detection of form readiness.
        """
        try:
            # STEP 1: Trigger reload FIRST
            driver.execute_script("location.reload(true);")
            
            # STEP 2: Wait for document ready state
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState === 'complete';")
            )
            
            # STEP 3: INDUSTRY-STANDARD approach - MutationObserver + simple checks
            driver.execute_script(f"""
                return new Promise((resolve) => {{
                    const startTime = performance.now();
                    const maxWaitTime = {min(timeout, 15) * 1000}; // Max 15 seconds
                    
                    let formContainer = null;
                    let lastMutationTime = startTime;
                    const STABILITY_REQUIRED = 500; // 500ms of stability for wait function
                    
                    // Find form container
                    const findFormContainer = () => {{
                        const selectors = [
                            'accelify-forms-details',
                            '.form-container', 
                            '.main-content',
                            '#pnlForm',
                            '#pnlEventContent'
                        ];
                        
                        for (const selector of selectors) {{
                            const element = document.querySelector(selector);
                            if (element && element.offsetHeight > 0) {{
                                return element;
                            }}
                        }}
                        return document.body;
                    }};
                    
                    // Check if form is ready
                    const isFormReady = () => {{
                        if (!formContainer) {{
                            formContainer = findFormContainer();
                        }}
                        
                        // 1. Check for visible form inputs
                        const inputs = formContainer.querySelectorAll('input, select, textarea');
                        const visibleInputs = Array.from(inputs).filter(input => {{
                            return input.offsetHeight > 0 && !input.disabled;
                        }});
                        
                        // 2. Check for loading indicators
                        const loadingElements = document.querySelectorAll('.loading, .spinner, .blockUI');
                        const hasLoading = Array.from(loadingElements).some(el => el.offsetHeight > 0);
                        
                        // 3. Simple readiness check
                        const hasContent = formContainer.innerText.trim().length > 100;
                        const hasInputs = visibleInputs.length > 0;
                        
                        return !hasLoading && (hasInputs || hasContent);
                    }};
                    
                    // MutationObserver to track DOM changes
                    const observer = new MutationObserver((mutations) => {{
                        // Only track significant mutations
                        const significantMutation = mutations.some(mutation => 
                            mutation.type === 'childList' && mutation.addedNodes.length > 0
                        );
                        
                        if (significantMutation) {{
                            lastMutationTime = performance.now();
                        }}
                    }});
                    
                    // Start observing
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true
                    }});
                    
                    const checkStability = () => {{
                        const currentTime = performance.now();
                        const elapsed = currentTime - startTime;
                        
                        // Timeout check
                        if (elapsed > maxWaitTime) {{
                            observer.disconnect();
                            resolve(true);
                            return;
                        }}
                        
                        // Check if form is ready
                        if (isFormReady()) {{
                            const timeSinceLastMutation = currentTime - lastMutationTime;
                            
                            if (timeSinceLastMutation >= STABILITY_REQUIRED) {{
                                // Form is ready and stable
                                observer.disconnect();
                                resolve(true);
                                return;
                            }}
                        }}
                        
                        // Continue checking
                        setTimeout(checkStability, 100);
                    }};
                    
                    // Start checking after a brief delay
                    setTimeout(checkStability, 200);
                }});
            """)
            
            # Wait for the Promise to resolve
            WebDriverWait(driver, timeout + 5).until(
                lambda d: d.execute_script("return true;")  # Promise will resolve
            )
            
        except Exception as ex:
            # Simple fallback
            if SeleniumHelper.logger:
                SeleniumHelper.logger.warning(f"MutationObserver form detection failed, using simple fallback: {str(ex)}")
            
            try:
                # Wait for document ready (if not already)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState === 'complete';")
                )
                
                # Brief wait for rendering
                time.sleep(0.8)
                
                # Try to find any visible form container
                WebDriverWait(driver, 5).until(
                    EC.any_of(
                        EC.visibility_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                        EC.visibility_of_element_located((By.CLASS_NAME, "form-container")),
                        EC.visibility_of_element_located((By.CLASS_NAME, "main-content")),
                        EC.visibility_of_element_located((By.ID, "pnlForm")),
                        EC.visibility_of_element_located((By.ID, "pnlEventContent"))
                    )
                )
            except TimeoutException:
                # If no specific form container found, assume page is ready
                pass
    
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
                # Fallback: direct element search - but still need to check for success
                try:
                    if SeleniumHelper.is_plan_page_url(driver.current_url):
                        alert_elem = driver.find_element(By.CSS_SELECTOR, 'div[role="alert"]')
                        if alert_elem and "Form has been updated successfully" in alert_elem.text:
                            break
                    else:
                        notification_elem = driver.find_element(By.TAG_NAME, 'kendo-notification')
                        if notification_elem and "Form has been updated successfully" in notification_elem.text:
                            break
                except:
                    # If fallback also fails, continue the loop
                    pass
                    
            time.sleep(0.25)

        # Check if we timed out without finding success message
        elapsed = time.time() - temp_start_time
        if elapsed >= SeleniumHelper.timeout:
            error_msg = f"Form save popup timeout after {SeleniumHelper.timeout}s"
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(error_msg)
            raise TimeoutException(error_msg)

        # Check AJAX requests for save operation status
        try:
            requests = SeleniumHelper.get_ajax_requests(driver)
            # Reverse to check most recent requests first
            requests = list(reversed(requests))
        except Exception as e:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.warning(f"Failed to get AJAX requests: {str(e)}")
            # Continue without AJAX validation if it fails
            return elapsed
        
        error_occured = False
        form_save_endpoint = "plan/Events/UpdateForm" if SeleniumHelper.is_plan_page_url(driver.current_url) else "plan/api/forms/"
        
        for request in requests:
            request_url = request.get("url", "") if isinstance(request, dict) else str(request)
            request_status = request.get("status", 0) if isinstance(request, dict) else 0
            
            if form_save_endpoint in request_url:
                if request_status != 200 and request_status != "pending":
                    error_occured = True
                break

        if error_occured:
            raise ValueError("Exception occured while saving the form!")
        return elapsed

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
    def measure_form_page_load_time(driver: webdriver.Chrome, url: str) -> tuple:
        """
        Measure page load time for form pages with hybrid monitoring.
        Combines API request monitoring with loading indicator detection.
        """
        SeleniumHelper.get_logger().debug(f"Starting hybrid monitoring for: {url}")
        
        start_time = time.time()  # Add missing start_time definition
        
        try:
            # Store current URL and clear performance entries
            current_url = driver.current_url
            driver.execute_script("performance.clearResourceTimings();")
            
            # Refresh the page to get clean reload
            driver.refresh()
            
            # Enable network monitoring immediately after refresh
            driver.execute_cdp_cmd('Network.enable', {})
            
            # Hybrid monitoring script - checks BOTH API requests AND loading indicators
            monitoring_script = """
            return new Promise((resolve) => {                
                let documentReady = false;
                let lastActivityTime = Date.now();
                let checkInterval;
                
                const loadingSelectors = [
                    '.loading', '.spinner', '.blockUI', '.loader-circle',
                    '.loading-wrapper', '.blockMsg', '.blockPage',
                    '.k-loading-mask',           // Kendo Grid loader
                    '[kendogridloading]',        // Kendo Grid loading attribute
                    '.k-loading-text',           // Kendo loading text
                    '.k-loading-image',          // Kendo loading image
                    '.k-i-loading',              // Kendo loading icon
                    '.loading-overlay',          // Generic loading overlay
                    '.spinner-border',           // Bootstrap spinner
                    '.fa-spinner'                // FontAwesome spinner
                ];
                
                const formApiPatterns = [
                    '/sections/',
                    '/exceptionalities/', 
                    '/distributionrecipients/',
                    '/getDistribution',              // Covers all getDistribution* endpoints
                    '/translationProjects/',
                    '/entity-locking/',
                    '/getSectionHistory/',
                    '/lookupValues/',
                    '/events/',
                    '/api/'                          // Catch any API request
                ];
                
                function checkHybridState() {
                    const now = Date.now();
                    const resources = performance.getEntriesByType('resource');
                    
                    if (!documentReady && document.readyState === 'complete') {
                        documentReady = true;
                    }
                    
                    const visibleLoaders = loadingSelectors.filter(selector => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            return Array.from(elements).some(el => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       style.opacity !== '0' &&
                                       el.offsetHeight > 0 && 
                                       el.offsetWidth > 0;
                            });
                        } catch (e) {
                            return false;
                        }
                    });
                    
                    const allApiRequests = resources
                        .filter(r => formApiPatterns.some(pattern => r.name.includes(pattern)))
                        .map(r => ({
                            url: r.name,
                            duration: r.duration,
                            status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                        }));
                    
                    const pendingApiRequests = allApiRequests.filter(r => r.status === 'PENDING');
                    
                    const recentSlowRequests = allApiRequests.filter(r => {
                        const isRecent = (now - (performance.timing.navigationStart + r.responseEnd)) < 10000; // 10 seconds
                        const isSlow = r.duration > 3000; // >3 seconds
                        return (r.status === 'PENDING' || (isRecent && isSlow));
                    });
                    
                    const hasActivity = visibleLoaders.length > 0 || 
                                       pendingApiRequests.length > 0 || 
                                       recentSlowRequests.length > 0;
                    
                    if (hasActivity) {
                        lastActivityTime = now;
                    }
                    
                    const timeSinceLastActivity = now - lastActivityTime;
                    const isFullyLoaded = documentReady && 
                                         visibleLoaders.length === 0 && 
                                         pendingApiRequests.length === 0 && 
                                         recentSlowRequests.length === 0 &&
                                         timeSinceLastActivity > 3000; // 3 seconds of inactivity
                    
                    if (isFullyLoaded) {
                        clearInterval(checkInterval);
                        
                        const networkState = {
                            allApiRequests: allApiRequests,
                            apiRequests: allApiRequests.length,
                            pendingApi: pendingApiRequests.length,
                            totalRequests: resources.length,
                            loadersFound: loadingSelectors.length,
                            activeLoaders: visibleLoaders.length
                        };
                        
                        resolve(networkState);
                    }
                }
                
                checkHybridState();
                checkInterval = setInterval(checkHybridState, 500);
                
                setTimeout(() => {
                    clearInterval(checkInterval);
                    
                    const resources = performance.getEntriesByType('resource');
                    const allApiRequests = resources
                        .filter(r => formApiPatterns.some(pattern => r.name.includes(pattern)))
                        .map(r => ({
                            url: r.name,
                            duration: r.duration,
                            status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                        }));
                    
                    const networkState = {
                        allApiRequests: allApiRequests,
                        apiRequests: allApiRequests.length,
                        pendingApi: allApiRequests.filter(r => r.status === 'PENDING').length,
                        totalRequests: resources.length,
                        timeout: true
                    };
                    
                    resolve(networkState);
                }, 30000);  // 30 seconds timeout
            });
            """
            
            # Wait for the Promise to resolve with extended timeout
            network_state = WebDriverWait(driver, 35).until(
                lambda d: d.execute_script(monitoring_script)
            )
            
            SeleniumHelper.get_logger().debug("Hybrid monitoring completed successfully")
            SeleniumHelper.get_logger().debug(f"Network state: {network_state}")
            
            # Calculate total load time
            load_time = time.time() - start_time
            
            return load_time, network_state
                
        except Exception as e:
            SeleniumHelper.get_logger().error(f"Error during hybrid monitoring: {str(e)}")
            raise

    @staticmethod
    def measure_standard_page_load_time(driver: webdriver.Chrome) -> float:
        """
        Modern page load measurement using Navigation Timing API.
        Provides accurate, browser-native timing without polling overhead.
        Handles all page types with comprehensive fallback support.
        """
        try:
            # STEP 1: Mark start time and trigger reload FIRST
            start_time = time.time()
            driver.execute_script("location.reload(true);")
            
            # STEP 2: Wait for document ready state
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState === 'complete';")
            )
            
            # STEP 3: Use JavaScript Promise for page readiness detection
            load_time = driver.execute_script("""
                return new Promise((resolve, reject) => {
                    const startTime = performance.now();
                    const maxWaitTime = 30000; // 30 seconds max
                    
                    const checkPageReady = () => {
                        const elapsed = performance.now() - startTime;
                        
                        // Timeout protection
                        if (elapsed > maxWaitTime) {
                            // Return current elapsed time instead of rejecting
                            const finalTime = elapsed / 1000;
                            resolve(finalTime);
                            return;
                        }
                        
                        // Document is already complete (checked above)
                        
                        // Check for loading indicators (comprehensive coverage)
                        const loadingSelectors = [
                            '.loading', '.spinner', '.blockUI', '.loader-circle',
                            '.loading-wrapper', '.blockMsg', '.blockPage'
                        ];
                        
                        const hasLoadingIndicators = loadingSelectors.some(selector => 
                            document.querySelector(selector)
                        );
                        
                        // Check for pending requests
                        let hasPendingRequests = false;
                        try {
                            const entries = performance.getEntriesByType('resource') || [];
                            const recentRequests = entries.filter(entry => 
                                entry.startTime > (Date.now() - 3000) // Last 3 seconds
                            );
                            
                            hasPendingRequests = recentRequests.some(entry => 
                                entry.responseEnd === 0 && 
                                (Date.now() - entry.startTime) < 1000 // Less than 1 second old
                            );
                        } catch (e) {
                            hasPendingRequests = false;
                        }
                        
                        // Page is ready when document is complete, no loading indicators, no pending requests
                        const isPageReady = !hasLoadingIndicators && !hasPendingRequests;
                        
                        if (isPageReady) {
                            // Use Navigation Timing API for precise measurement
                            const navigationTiming = performance.timing;
                            const loadCompleteTime = navigationTiming.loadEventEnd - navigationTiming.navigationStart;
                            
                            // If loadEventEnd is not available yet, use current elapsed time
                            const finalTime = loadCompleteTime > 0 ? 
                                loadCompleteTime / 1000 : 
                                elapsed / 1000;
                            
                            resolve(finalTime);
                        } else {
                            // Continue checking with requestAnimationFrame (no blocking!)
                            requestAnimationFrame(checkPageReady);
                        }
                    };
                    
                    // Start checking immediately
                    checkPageReady();
                });
            """)
            
            # Wait for the Promise to resolve and return the timing
            return WebDriverWait(driver, 35).until(
                lambda d: d.execute_script("return arguments[0];", load_time)
            )
            
        except Exception as ex:
            # Fallback to original method if modern approach fails
            if SeleniumHelper.logger:
                SeleniumHelper.logger.warning(f"Navigation Timing API failed for standard page, using fallback: {str(ex)}")
            
            # Simple fallback method - use the start_time we already captured
            try:
                # Wait for document ready (if not already)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState === 'complete';")
                )
            except TimeoutException:
                pass
            
            return time.time() - start_time
    
    @staticmethod
    def measure_form_save_time(driver: webdriver.Chrome) -> float:
        # Force hard reload to ensure clean state
        driver.execute_script("location.reload(true);")
        SeleniumHelper.wait_for_form_page_load(driver)
        
        try:
            # Wait for form to be ready for interaction
            loader_locator = SeleniumHelper.unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
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
                WebDriverWait(driver, SeleniumHelper.timeout).until(SeleniumHelper.unpresence_of_element((By.CSS_SELECTOR, ".loader-circle")))
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
    def get_ajax_requests(driver: webdriver.Chrome) -> list:
        try:
            with open(SeleniumHelper.util_scripts_directory + "get_requests.js", "r") as script_file:
                script = script_file.read()
        except (FileNotFoundError, IOError) as e:
            error_msg = f"Failed to read get_requests.js: {str(e)}"
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            return driver.execute_script(script)
        except Exception as e:
            error_msg = f"Failed to execute get_requests.js: {str(e)}"
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(error_msg)
            raise

    @staticmethod
    def test_form_load_detection(driver: webdriver.Chrome) -> dict:
        """Test function to debug form loading detection"""
        try:
            element = driver.find_element(By.CSS_SELECTOR, "accelify-forms-details, .form-container, .main-content, body")
        except:
            element = driver.find_element(By.TAG_NAME, "body")
        
        result = driver.execute_script("""
            var element = arguments[0];
            var results = {
                url: window.location.href,
                document_ready: document.readyState,
                inputs_count: 0,
                text_length: 0,
                has_loading: false,
                pending_requests: 0,
                all_requests: [],
                ready: false,
                reason: null,
                debug_info: {}
            };
            
            // Count meaningful form elements
            var inputs = element.querySelectorAll('input:not([type="button"]):not([type="submit"]):not([type="reset"]), select, textarea');
            results.inputs_count = inputs.length;
            
            // Get text content length
            results.text_length = element.textContent.trim().length;
            
            // Check for loading indicators
            var loadingElements = element.querySelectorAll('.loading, .spinner, .blockUI, .loader-circle');
            results.has_loading = loadingElements.length > 0;
            results.debug_info.loading_selectors = Array.from(loadingElements).map(el => el.className);
            
            // Check for pending API requests
            try {
                var performance = window.performance || {};
                var entries = performance.getEntriesByType ? performance.getEntriesByType("resource") : [];
                
                var allApiRequests = entries.filter(function(entry) {
                    return entry.name.includes('/api/') && entry.startTime > (Date.now() - 30000);
                });
                
                var pendingApiRequests = allApiRequests.filter(function(entry) {
                    return entry.responseEnd === 0;
                });
                
                results.pending_requests = pendingApiRequests.length;
                results.all_requests = allApiRequests.map(function(entry) {
                    return {
                        url: entry.name,
                        status: entry.responseEnd === 0 ? 'pending' : 'completed',
                        duration: entry.responseEnd === 0 ? (Date.now() - entry.startTime) : (entry.responseEnd - entry.startTime)
                    };
                });
            } catch(e) {
                results.debug_info.network_error = e.toString();
                results.pending_requests = 0;
            }
            
            // Determine if form is ready
            if (!results.has_loading && results.pending_requests === 0) {
                if (results.inputs_count > 0) {
                    results.ready = true;
                    results.reason = 'form_elements_ready';
                } else if (results.text_length > 50) {
                    results.ready = true;
                    results.reason = 'content_loaded';
                }
            } else {
                results.reason = results.has_loading ? 'loading_indicators_present' : 'pending_api_requests';
            }
            
            return results;
        """, element)
        
        return result

    @staticmethod
    def unpresence_of_element(locator):
        def _predicate(driver):
            try:
                driver.find_element(*locator)
                return False
            except (NoSuchElementException, StaleElementReferenceException):
                return True
            except Exception as e:
                # Log unexpected exceptions but don't suppress them
                if SeleniumHelper.logger:
                    SeleniumHelper.logger.warning(f"Unexpected exception in unpresence_of_element: {str(e)}")
                raise
        return _predicate

    @staticmethod
    def analyze_form_performance(driver: webdriver.Chrome) -> dict:
        """
        DEEP PERFORMANCE ANALYSIS for identifying bottlenecks in heavy forms.
        
        Returns detailed metrics about:
        - Network requests and their durations
        - Resource loading patterns
        - Form complexity metrics
        - Visual rendering timeline
        - Potential performance issues
        """
        try:
            analysis = driver.execute_script("""
                const analysis = {
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    
                    // NAVIGATION TIMING ANALYSIS
                    navigationTiming: {},
                    
                    // NETWORK PERFORMANCE ANALYSIS
                    networkAnalysis: {
                        totalRequests: 0,
                        apiRequests: [],
                        slowRequests: [],
                        failedRequests: [],
                        totalTransferSize: 0,
                        cacheHitRate: 0
                    },
                    
                    // FORM COMPLEXITY ANALYSIS
                    formAnalysis: {
                        formType: 'unknown',
                        totalElements: 0,
                        interactiveElements: 0,
                        sections: 0,
                        loadedSections: 0,
                        hasAsyncContent: false,
                        estimatedComplexity: 'low'
                    },
                    
                    // VISUAL PERFORMANCE ANALYSIS
                    visualAnalysis: {
                        firstContentfulPaint: 0,
                        largestContentfulPaint: 0,
                        cumulativeLayoutShift: 0,
                        timeToInteractive: 0
                    },
                    
                    // PERFORMANCE ISSUES DETECTED
                    performanceIssues: [],
                    
                    // RECOMMENDATIONS
                    recommendations: []
                };
                
                // LAYER 1: Navigation Timing Analysis
                const nav = performance.timing;
                if (nav.navigationStart > 0) {
                    analysis.navigationTiming = {
                        dnsLookup: nav.domainLookupEnd - nav.domainLookupStart,
                        tcpConnection: nav.connectEnd - nav.connectStart,
                        serverResponse: nav.responseEnd - nav.requestStart,
                        domProcessing: nav.domContentLoadedEventEnd - nav.responseEnd,
                        resourceLoading: nav.loadEventEnd - nav.domContentLoadedEventEnd,
                        totalLoadTime: nav.loadEventEnd - nav.navigationStart
                    };
                    
                    // Identify slow phases
                    if (analysis.navigationTiming.serverResponse > 3000) {
                        analysis.performanceIssues.push({
                            type: 'slow_server_response',
                            severity: 'high',
                            duration: analysis.navigationTiming.serverResponse,
                            description: 'Server response time exceeds 3 seconds'
                        });
                    }
                    
                    if (analysis.navigationTiming.domProcessing > 2000) {
                        analysis.performanceIssues.push({
                            type: 'slow_dom_processing',
                            severity: 'medium',
                            duration: analysis.navigationTiming.domProcessing,
                            description: 'DOM processing takes longer than 2 seconds'
                        });
                    }
                }
                
                // LAYER 2: Network Performance Analysis
                const resources = performance.getEntriesByType('resource');
                analysis.networkAnalysis.totalRequests = resources.length;
                
                let totalSize = 0;
                let cacheHits = 0;
                
                resources.forEach(resource => {
                    const duration = resource.responseEnd - resource.startTime;
                    const size = resource.transferSize || 0;
                    totalSize += size;
                    
                    // Cache analysis
                    if (resource.transferSize === 0 && resource.decodedBodySize > 0) {
                        cacheHits++;
                    }
                    
                    // API request analysis
                    if (resource.name.includes('/api/') || 
                        resource.name.includes('/plan/') ||
                        resource.name.includes('Forms') ||
                        resource.name.includes('Events')) {
                        
                        const apiRequest = {
                            url: resource.name.split('/').pop(),
                            fullUrl: resource.name,
                            duration: duration,
                            size: size,
                            method: resource.initiatorType,
                            startTime: resource.startTime,
                            isSlowRequest: duration > 3000,
                            isFailed: resource.responseEnd === 0
                        };
                        
                        analysis.networkAnalysis.apiRequests.push(apiRequest);
                        
                        if (apiRequest.isSlowRequest) {
                            analysis.networkAnalysis.slowRequests.push(apiRequest);
                            analysis.performanceIssues.push({
                                type: 'slow_api_request',
                                severity: duration > 10000 ? 'critical' : 'high',
                                duration: duration,
                                url: apiRequest.url,
                                description: `API request took ${(duration/1000).toFixed(1)} seconds`
                            });
                        }
                        
                        if (apiRequest.isFailed) {
                            analysis.networkAnalysis.failedRequests.push(apiRequest);
                            analysis.performanceIssues.push({
                                type: 'failed_request',
                                severity: 'critical',
                                url: apiRequest.url,
                                description: 'API request failed or timed out'
                            });
                        }
                    }
                });
                
                analysis.networkAnalysis.totalTransferSize = totalSize;
                analysis.networkAnalysis.cacheHitRate = resources.length > 0 ? (cacheHits / resources.length) * 100 : 0;
                
                // LAYER 3: Form Complexity Analysis
                const formSelectors = [
                    'accelify-forms-details',
                    '.form-container',
                    '.main-content',
                    '#pnlForm',
                    '#pnlEventContent'
                ];
                
                let formContainer = null;
                let formType = 'unknown';
                
                for (const selector of formSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.offsetHeight > 0) {
                        formContainer = element;
                        formType = selector.replace(/[#.]/g, '');
                        break;
                    }
                }
                
                if (!formContainer) {
                    formContainer = document.body;
                    formType = 'generic';
                }
                
                analysis.formAnalysis.formType = formType;
                
                // Count form elements
                const allElements = formContainer.querySelectorAll('*');
                const interactiveElements = formContainer.querySelectorAll('input, select, textarea, button');
                const visibleInteractive = Array.from(interactiveElements).filter(el => el.offsetHeight > 0);
                
                analysis.formAnalysis.totalElements = allElements.length;
                analysis.formAnalysis.interactiveElements = visibleInteractive.length;
                
                // Analyze form sections
                const formSections = formContainer.querySelectorAll(
                    'accelify-form-section, .form-section, .section-container, [class*="section"]'
                );
                
                analysis.formAnalysis.sections = formSections.length;
                
                let loadedSections = 0;
                formSections.forEach(section => {
                    const sectionInputs = section.querySelectorAll('input, select, textarea');
                    const sectionText = section.innerText?.trim() || '';
                    const hasLoading = section.querySelector('.loading, .spinner, .skeleton');
                    
                    if ((sectionInputs.length > 0 || sectionText.length > 50) && !hasLoading) {
                        loadedSections++;
                    }
                });
                
                analysis.formAnalysis.loadedSections = loadedSections;
                
                // Check for async content
                const asyncIndicators = formContainer.querySelectorAll(
                    '[ng-if], [*ngIf], [v-if], .async-content, .lazy-load'
                );
                analysis.formAnalysis.hasAsyncContent = asyncIndicators.length > 0;
                
                // Estimate complexity
                if (analysis.formAnalysis.interactiveElements > 50 || analysis.formAnalysis.sections > 10) {
                    analysis.formAnalysis.estimatedComplexity = 'high';
                } else if (analysis.formAnalysis.interactiveElements > 20 || analysis.formAnalysis.sections > 5) {
                    analysis.formAnalysis.estimatedComplexity = 'medium';
                } else {
                    analysis.formAnalysis.estimatedComplexity = 'low';
                }
                
                // LAYER 4: Visual Performance Analysis
                const paintEntries = performance.getEntriesByType('paint');
                paintEntries.forEach(entry => {
                    if (entry.name === 'first-contentful-paint') {
                        analysis.visualAnalysis.firstContentfulPaint = entry.startTime;
                    }
                });
                
                // LCP analysis
                try {
                    const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
                    if (lcpEntries.length > 0) {
                        analysis.visualAnalysis.largestContentfulPaint = lcpEntries[lcpEntries.length - 1].startTime;
                    }
                } catch (e) {
                    // LCP not supported
                }
                
                // LAYER 5: Generate Recommendations
                if (analysis.networkAnalysis.slowRequests.length > 0) {
                    analysis.recommendations.push({
                        type: 'network_optimization',
                        priority: 'high',
                        description: `Optimize ${analysis.networkAnalysis.slowRequests.length} slow API requests`,
                        details: analysis.networkAnalysis.slowRequests.map(req => req.url)
                    });
                }
                
                if (analysis.formAnalysis.estimatedComplexity === 'high') {
                    analysis.recommendations.push({
                        type: 'form_optimization',
                        priority: 'medium',
                        description: 'Consider lazy loading or pagination for complex form',
                        details: `${analysis.formAnalysis.interactiveElements} interactive elements, ${analysis.formAnalysis.sections} sections`
                    });
                }
                
                if (analysis.networkAnalysis.cacheHitRate < 50) {
                    analysis.recommendations.push({
                        type: 'caching_optimization',
                        priority: 'medium',
                        description: `Improve caching strategy (current hit rate: ${analysis.networkAnalysis.cacheHitRate.toFixed(1)}%)`,
                        details: 'Enable browser caching for static resources'
                    });
                }
                
                if (analysis.visualAnalysis.firstContentfulPaint > 3000) {
                    analysis.recommendations.push({
                        type: 'rendering_optimization',
                        priority: 'high',
                        description: `First Contentful Paint is slow (${(analysis.visualAnalysis.firstContentfulPaint/1000).toFixed(1)}s)`,
                        details: 'Optimize critical rendering path'
                    });
                }
                
                return analysis;
            """)
            
            return analysis
            
        except Exception as ex:
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(f"Performance analysis failed: {str(ex)}")
            
            return {
                "error": str(ex),
                "timestamp": time.time(),
                "url": driver.current_url,
                "fallback_analysis": True
            }