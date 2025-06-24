"""
Performance Manager - Unified Interface
Main entry point for all performance measurements with backward compatibility
"""

import logging
import time
from typing import Union, Tuple, List, Dict, Optional
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from .performance_config import get_config
from .performance_types import MeasurementResult, MeasurementStatus, NetworkState, ApiRequest, create_network_state, create_measurement_result
from .performance_measurer import create_measurer
from .selenium_helper import SeleniumHelper

# Array of ignored APIs (third-party services that should not trigger errors)
IGNORED_APIS = [
    'api.userway.org',
    'userway.org',
    # Add more third-party APIs here as needed
    # 'google-analytics.com',
    # 'googletagmanager.com'
]

def is_ignored_api_url(url):
    """Check if URL should be ignored (third-party service)"""
    if not url:
        return False
    url_lower = url.lower()
    return any(ignored_api in url_lower for ignored_api in IGNORED_APIS)

class PerformanceManager:
    """
    Unified performance measurement manager.
    Provides both new unified interface and backward compatibility.
    """
    
    def __init__(self, driver: webdriver.Chrome, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)
        self.config = get_config()
        
        # Initialize measurers
        self.save_measurer = create_measurer(self.driver, "form_save", self.logger)
        
    def measure_form_page_load_time(self, url: str) -> Union[Tuple[float, dict], MeasurementResult]:
        """
        Measure form page load time with hybrid monitoring.
        
        Returns:
            Tuple[float, dict]: (load_time, network_state) for backward compatibility
            OR MeasurementResult: Full measurement result object (new interface)
        """
        try:
            measurer = create_measurer(self.driver, "form_load", self.logger)
            result = measurer.measure(url)
            
            form_load_errors = self._check_form_load_errors()
            if form_load_errors:
                error_message = "; ".join(form_load_errors)
                self.logger.error(f"Form load errors detected: {error_message}")
                
                raise Exception(f"Form load failed: {error_message}")
            
            if self.config.log_measurement_details:
                self.logger.info(f"Form load measurement: {result.to_dict()}")
            
            # Return tuple for backward compatibility
            network_state_dict = {
                'allApiRequests': [
                    {
                        'url': req.url,
                        'duration': req.duration,
                        'status': req.status.value
                    }
                    for req in result.network_state.all_api_requests
                ],
                'apiRequests': result.network_state.api_request_count,
                'pendingApi': result.network_state.pending_api_count,
                'totalRequests': result.network_state.total_requests,
                'timeout': result.network_state.has_timeout,
                'reliability_metrics': {
                    'load_time': result.load_time,
                    'total_requests': result.network_state.total_requests,
                    'api_requests': result.network_state.api_request_count,
                    'pending_requests': result.network_state.pending_api_count,
                    'reliability_score': result.reliability_score,
                    'quality_grade': result.quality_grade
                }
            }
            
            return result.load_time, network_state_dict
            
        except Exception as e:
            self.logger.error(f"Form page load measurement failed: {e}")
            # Return fallback tuple for backward compatibility
            fallback_network_state = {
                'allApiRequests': [],
                'apiRequests': 0,
                'pendingApi': 0,
                'totalRequests': 0,
                'timeout': True,
                'reliability_metrics': {
                    'load_time': self.config.fallback_timeout,
                    'total_requests': 0,
                    'api_requests': 0,
                    'pending_requests': 0,
                    'reliability_score': 0.0,
                    'quality_grade': 'F'
                }
            }
            return self.config.fallback_timeout, fallback_network_state
    
    def measure_standard_page_load_time(self) -> Union[float, MeasurementResult]:
        """
        Measure standard page load time using Navigation Timing API.
        
        Returns:
            float: Load time in seconds (backward compatibility)
            OR MeasurementResult: Full measurement result object (new interface)
        """
        try:
            measurer = create_measurer(self.driver, "standard_load", self.logger)
            result = measurer.measure()
            
            if self.config.log_measurement_details:
                self.logger.info(f"Standard load measurement: {result.to_dict()}")
            
            # Return float for backward compatibility
            return result.load_time
            
        except Exception as e:
            self.logger.error(f"Standard page load measurement failed: {e}")
            return self.config.fallback_timeout
    
    def measure_form_save_time(self, url: str = None) -> float:
        """
        Measure form save time
        Returns: float (save time in seconds)
        Raises: Specific exceptions for different error types
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
        import time
        
        try:
            self.logger.info("Starting form save time measurement...")
            
            # Set Save button detection timeout to 15 seconds
            SAVE_BUTTON_TIMEOUT = 15
            
            try:
                # Wait for form to be ready for interaction (without reload)
                # Check if page is already loaded and form is ready
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.execute_script("return document.readyState === 'complete';")
                )
                
                # Wait for any loading indicators to disappear
                loader_locator = self._unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
                WebDriverWait(self.driver, SAVE_BUTTON_TIMEOUT).until(loader_locator)
                
                # Ensure basic form elements are clickable
                WebDriverWait(self.driver, SAVE_BUTTON_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")))
                
            except Exception as ex:
                self.logger.warning(f"Form not immediately ready, trying with reload: {str(ex)}")
                
                # Fallback: reload if form is not ready
                self.driver.execute_script("location.reload(true);")
                self._wait_for_form_page_load()
            
                # Retry readiness check after reload
                try:
                    loader_locator = self._unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
                    WebDriverWait(self.driver, SAVE_BUTTON_TIMEOUT).until(loader_locator)
                    WebDriverWait(self.driver, SAVE_BUTTON_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnUpdateForm, button[type='submit']")))
                except Exception as retry_ex:
                    self.logger.error(f"Form save preparation timeout after reload: {str(retry_ex)}")
                    # 🚨 THIS IS A FORM LOAD ERROR, NOT A SAVE ERROR!
                    raise Exception(f"Form could not be prepared for save operation: {str(retry_ex)}")
            
            # Hide interfering elements that can intercept clicks
            self._hide_interfering_elements_simple()
            
            # Comprehensive Save button detection for different form types
            save_btn_elem = None
            
            # Strategy 1: Enhanced selectors for Kendo UI buttons and modern forms
            enhanced_selectors = [
                # Kendo UI buttons with specific structure
                "button[kendobutton][type='submit']",                    # Kendo submit buttons
                "button[kendobutton] span.k-button-text",                # Kendo button spans
                "button.k-button.k-button-solid span.k-button-text",    # Kendo solid buttons
                "button[role='button'] span.k-button-text",             # ARIA role buttons
                
                # Traditional selectors
                "#btnUpdateForm",                                        # Standard form save button ID
                "button[type='submit']",                                # Generic submit buttons  
                "input[type='submit']",                                 # Submit inputs
                ".k-button",                                            # Kendo button class
                "button"                                                # All buttons as fallback
            ]
            
            for selector in enhanced_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        # For span elements, get the parent button
                        if element.tag_name == "span":
                            button = element.find_element(By.XPATH, "./..")
                            button_text = element.text.strip()
                        else:
                            button = element
                            button_text = button.text.strip()
                            
                            # If button text is empty, try to get text from child span
                            if not button_text:
                                try:
                                    span_elem = button.find_element(By.CSS_SELECTOR, "span.k-button-text, .k-button-text, span")
                                    button_text = span_elem.text.strip()
                                except:
                                    continue
                        
                        # Check if this is a Save button
                        if "Save" in button_text and button.is_enabled() and button.is_displayed():
                            save_btn_elem = button
                            self.logger.debug(f"Found Save button using selector: {selector}, text: '{button_text}'")
                            break
                    
                    if save_btn_elem:
                        break
                        
                except Exception as ex:
                    self.logger.debug(f"Selector '{selector}' failed: {str(ex)}")
                    continue
            
            # Strategy 2: Enhanced XPath search for Save buttons
            if save_btn_elem is None:
                try:
                    enhanced_xpath_selectors = [
                        # Look for buttons containing "Save" in text or child elements
                        "//button[contains(text(), 'Save') or .//span[contains(text(), 'Save')]]",
                        "//button[@kendobutton and (.//span[contains(text(), 'Save')] or contains(text(), 'Save'))]",
                        "//button[@role='button' and (.//span[contains(text(), 'Save')] or contains(text(), 'Save'))]",
                        "//input[@type='submit' and contains(@value, 'Save')]", 
                        "//*[contains(@class, 'k-button') and (.//span[contains(text(), 'Save')] or contains(text(), 'Save'))]"
                    ]
                    
                    for xpath in enhanced_xpath_selectors:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, xpath)
                            for button in buttons:
                                if button.is_enabled() and button.is_displayed():
                                    save_btn_elem = button
                                    self.logger.debug(f"Found Save button using XPath: {xpath}")
                                    break
                            
                            if save_btn_elem:
                                break
                                
                        except Exception as ex:
                            self.logger.debug(f"XPath '{xpath}' failed: {str(ex)}")
                            continue
                            
                except Exception as ex:
                    self.logger.debug(f"XPath strategy failed: {str(ex)}")
                    pass
            
            # If no Save button found - just raise the error
            if save_btn_elem is None:
                current_url = self.driver.current_url
                self.logger.error(f"Save button not found: {current_url}")
                # Log available buttons for debugging
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    button_texts = [btn.text.strip() for btn in all_buttons if btn.text.strip()]
                    self.logger.debug(f"Available buttons on page: {button_texts}")
                except:
                    pass
                
                raise NoSuchElementException("Save button not found")
            
            # Get initial network requests BEFORE clicking Save
            try:
                initial_requests = self._get_network_requests_simple()
            except:
                initial_requests = []
                
            start_time = time.time()
            
            # Fill form if needed - TEMPORARILY DISABLED
            # try:
            #     from frontline_selenium.page_filler import PageFormFiller
            #     if not getattr(self, 'options', {}).get("disable_filler", False):
            #         PageFormFiller.fill_form(self.driver)
            #         self.logger.debug("Form filled successfully")
            # except Exception as ex:
            #     self.logger.warning(f"Form filler failed (continuing anyway): {str(ex)}")
            #     # Don't re-raise - form filler errors shouldn't stop save measurement
            #     pass
            
            self.logger.info("FORM FILLER DISABLED - PROCEEDING TO SAVE BUTTON CLICK")
                
            # Enhanced retry logic for clicking save button with JavaScript fallback
            attempts = 3
            start_time = time.time()
            save_button_clicked = False
            
            while attempts > 0:
                attempts -= 1
                try:
                    WebDriverWait(self.driver, SAVE_BUTTON_TIMEOUT).until(self._unpresence_of_element((By.CSS_SELECTOR, ".loader-circle")))
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    
                    # Hide interfering elements again before clicking (they might reappear)
                    self._hide_interfering_elements_simple()
                    
                    # Try regular click first
                    save_btn_elem.click()
                    save_button_clicked = True
                    break
                    
                except ElementClickInterceptedException as ex:
                    if attempts > 0:  # Only try JavaScript click if we have more attempts
                        self.logger.warning(f"Save button click intercepted, trying JavaScript click... ({attempts} attempts left)")
                        
                        try:
                            # Force JavaScript click as fallback
                            self.driver.execute_script("arguments[0].click();", save_btn_elem)
                            save_button_clicked = True
                            break
                        except Exception as js_ex:
                            self.logger.warning(f"JavaScript click also failed: {str(js_ex)}")
                        time.sleep(1)
                        start_time = time.time()  # Reset timer after sleep
                    else:
                        self.logger.error(f"Save button click failed after all retries: {str(ex)}")
                        raise  # Re-raise on final attempt
            
            if not save_button_clicked:
                self.logger.error("SAVE BUTTON WAS NEVER CLICKED!")
                raise Exception("Save button click failed - button was never clicked")
            
            # 🚨 SETUP NETWORK ERROR MONITORING IMMEDIATELY AFTER CLICK
            self.driver.execute_script("""
                // Setup network error monitoring
                window._networkErrors = window._networkErrors || [];
                
                // Helper function to check if URL is from frontlineeducation
                function isFrontlineEducationAPI(url) {
                    if (!url) return false;
                    return url.includes('frontlineeducation') || 
                           url.includes('frontlineed');
                }
                
                // Monitor fetch requests
                if (!window._fetchMonitorSetup) {
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        return originalFetch.apply(this, args)
                            .then(response => {
                                // 🚨 ONLY TRACK FRONTLINE EDUCATION API ERRORS
                                if (response.status >= 400 && isFrontlineEducationAPI(response.url)) {
                                    window._networkErrors.push({
                                        type: 'HTTP_ERROR',
                                        status: response.status,
                                        url: response.url,
                                        message: `HTTP ${response.status} ${response.statusText}`,
                                        timestamp: Date.now()
                                    });
                                }
                                return response;
                            })
                            .catch(error => {
                                // Only log network errors for frontline education APIs
                                const url = args[0] && typeof args[0] === 'string' ? args[0] : 'Unknown URL';
                                if (isFrontlineEducationAPI(url)) {
                                    window._networkErrors.push({
                                        type: 'FETCH_ERROR',
                                        message: error.message,
                                        url: url,
                                        timestamp: Date.now()
                                    });
                                }
                                throw error;
                            });
                    };
                    window._fetchMonitorSetup = true;
                }
                
                // Monitor XMLHttpRequest
                if (!window._xhrMonitorSetup) {
                    const originalXHR = window.XMLHttpRequest;
                    window.XMLHttpRequest = function() {
                        const xhr = new originalXHR();
                        const originalSend = xhr.send;
                        
                        xhr.addEventListener('load', function() {
                            if (xhr.status >= 400 && isFrontlineEducationAPI(xhr.responseURL)) {
                                window._networkErrors.push({
                                    type: 'XHR_ERROR',
                                    status: xhr.status,
                                    url: xhr.responseURL || 'Unknown URL',
                                    message: `HTTP ${xhr.status} ${xhr.statusText}`,
                                    timestamp: Date.now()
                                });
                            }
                        });
                        
                        xhr.addEventListener('error', function() {
                            // Only log XHR errors for frontline education APIs
                            if (isFrontlineEducationAPI(xhr.responseURL)) {
                                window._networkErrors.push({
                                    type: 'XHR_ERROR',
                                    message: 'XHR request failed',
                                    url: xhr.responseURL || 'Unknown URL',
                                    timestamp: Date.now()
                                });
                            }
                        });
                        
                        return xhr;
                    };
                    window._xhrMonitorSetup = true;
                }
            """);
            
            time.sleep(0.1)
            
            try:
                save_elapsed = self._wait_for_save_completion_simple(initial_requests)
            except Exception as ex:
                self.logger.error(f"Form save popup timeout: {str(ex)}")
                raise
                
            elapsed = time.time() - start_time
            self.logger.info(f"Form save completed successfully in {elapsed:.3f}s")
            return elapsed
            
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as specific_error:
            self.logger.error(f"Form save specific error: {specific_error}")
            raise specific_error
        except Exception as general_error:
            self.logger.error(f"Form save unexpected error: {general_error}")
            raise Exception(f"Form save measurement failed: {general_error}")
    
    def _unpresence_of_element(self, locator):
        """Helper method for unpresence of element"""
        def _predicate(driver):
            try:
                driver.find_element(*locator)
                return False
            except (NoSuchElementException, StaleElementReferenceException):
                return True
            except Exception as e:
                self.logger.warning(f"Unexpected exception in unpresence_of_element: {str(e)}")
                raise
        return _predicate
    
    def _wait_for_form_page_load(self):
        """Wait for form page to load with error monitoring during loading"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        timeout = 30
        try:
            # STEP 1: Trigger reload FIRST
            self.driver.execute_script("location.reload(true);")
            
            # STEP 2: Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState === 'complete';")
            )
            
            # STEP 3: Enhanced loading with ERROR MONITORING during load
            load_result = self.driver.execute_script(f"""
                return new Promise((resolve, reject) => {{
                    const startTime = performance.now();
                    const maxWaitTime = {min(timeout, 15) * 1000}; // Max 15 seconds
                    
                    let formContainer = null;
                    let lastMutationTime = startTime;
                    const STABILITY_REQUIRED = 500; // 500ms of stability for wait function
                    
                    // ERROR MONITORING - Check for errors during loading
                    const checkForErrors = () => {{
                        try {{
                            // 1. Check for Kendo error notifications (your specific case)
                            const kendoErrors = document.querySelectorAll(`
                                .k-notification-error,
                                .k-widget.k-notification.k-notification-error,
                                [class*="k-notification"][class*="error"],
                                [class*="notification-error"]
                            `);
                            
                            for (let notification of kendoErrors) {{
                                if (notification.offsetHeight > 0 && notification.offsetWidth > 0) {{
                                    const text = notification.textContent || notification.innerText || '';
                                    if (text.includes('An error has occurred') || 
                                        text.includes('Sorry for inconvenience') ||
                                        text.includes('contact the site administrator')) {{
                                        return {{
                                            type: 'KENDO_ERROR_NOTIFICATION',
                                            message: 'Page load error: ' + text.substring(0, 150)
                                        }};
                                    }}
                                }}
                            }}
                            
                            // 2. Check for generic error alerts with role="alert"
                            const alertElements = document.querySelectorAll('[role="alert"]');
                            for (let alert of alertElements) {{
                                if (alert.offsetHeight > 0 && alert.offsetWidth > 0) {{
                                    const alertText = alert.textContent || alert.innerText || '';
                                    if (alertText.toLowerCase().includes('error') && 
                                        (alertText.includes('occurred') || alertText.includes('problem'))) {{
                                        return {{
                                            type: 'ERROR_ALERT',
                                            message: 'Page error alert: ' + alertText.substring(0, 150)
                                        }};
                                    }}
                                }}
                            }}
                            
                            // 3. Check for Bootstrap/generic error alerts
                            const genericErrors = document.querySelectorAll(`
                                .alert-danger,
                                .alert-error,
                                .error-message,
                                .error-notification,
                                [class*="error"][class*="alert"],
                                [class*="error"][class*="message"]
                            `);
                            
                            for (let errorEl of genericErrors) {{
                                if (errorEl.offsetHeight > 0 && errorEl.offsetWidth > 0) {{
                                    const text = errorEl.textContent || errorEl.innerText || '';
                                    if (text.trim().length > 10) {{ // Has meaningful content
                                        return {{
                                            type: 'GENERIC_ERROR',
                                            message: 'Page error: ' + text.substring(0, 150)
                                        }};
                                    }}
                                }}
                            }}
                            
                            return null; // No errors found
                        }} catch(e) {{
                            return null; // Ignore detection errors
                        }}
                    }};
                    
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
                        
                        // CHECK FOR ERRORS FIRST - during loading!
                        const errorFound = checkForErrors();
                        if (errorFound) {{
                            observer.disconnect();
                            reject(errorFound); // Reject with error details
                            return;
                        }}
                        
                        // Timeout check
                        if (elapsed > maxWaitTime) {{
                            observer.disconnect();
                            resolve({{ success: true, message: 'Timeout reached' }});
                            return;
                        }}
                        
                        // Check if form is ready
                        if (isFormReady()) {{
                            const timeSinceLastMutation = currentTime - lastMutationTime;
                            
                            if (timeSinceLastMutation >= STABILITY_REQUIRED) {{
                                // Form is ready and stable - final error check
                                const finalErrorCheck = checkForErrors();
                                if (finalErrorCheck) {{
                                    observer.disconnect();
                                    reject(finalErrorCheck);
                                    return;
                                }}
                                
                                observer.disconnect();
                                resolve({{ success: true, message: 'Form loaded successfully' }});
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
            
            # If we get here, either form loaded successfully or there was an error
            if load_result.get('success'):
                self.logger.debug(f"Form load completed: {load_result.get('message')}")
            
        except Exception as js_error:
            # This means JavaScript rejected the promise due to an error
            if hasattr(js_error, 'msg') and isinstance(js_error.msg, dict):
                error_details = js_error.msg
                error_type = error_details.get('type', 'UNKNOWN_ERROR')
                error_message = error_details.get('message', 'Unknown error during form load')
                
                self.logger.error(f"Form load error detected during loading: {error_type} - {error_message}")
                raise Exception(f"Form load failed: {error_message}")
            else:
                self.logger.error(f"Form page load wait failed: {js_error}")
                raise
    
    def _get_network_requests_simple(self) -> list:
        """Get network requests - simplified"""
        try:
            return self.driver.execute_script("""
                const entries = performance.getEntriesByType('resource') || [];
                return entries
                    .filter(entry => entry.name.includes('/api/'))
                    .map(entry => ({
                        url: entry.name,
                        duration: entry.duration,
                        status: entry.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                    }));
            """)
        except:
            return []
    
    def _hide_interfering_elements_simple(self):
        """Hide interfering elements - original logic"""
        try:
            self.driver.execute_script("""
                var launcher = document.getElementById('launcher');
                if (launcher) {
                    launcher.style.display = 'none';
                    launcher.style.visibility = 'hidden';
                    launcher.style.zIndex = '-1';
                }
                
                var interfering_selectors = [
                    'iframe[title*="widget"]', 'iframe[id="launcher"]', 
                    '.widget-overlay', '.chat-widget', '.support-widget'
                ];
                
                interfering_selectors.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        elements.forEach(function(el) {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.zIndex = '-1';
                        });
                    } catch(e) {}
                });
            """)
            self.logger.debug("Hidden interfering elements")
        except Exception as e:
            self.logger.debug(f"Could not hide interfering elements: {e}")
    
    def _wait_for_save_completion_simple(self, initial_requests) -> float:
        """Wait for save completion - SIMPLIFIED AND IMPROVED POPUP DETECTION"""
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                
                # Check for critical network errors first
                network_errors = self.driver.execute_script("""
                    var errors = [];
                    
                    function isFrontlineEducationAPI(url) {
                        if (!url) return false;
                        return url.includes('frontlineeducation') || url.includes('frontlineed');
                    }
                    
                    if (window._networkErrors && window._networkErrors.length > 0) {
                        window._networkErrors.forEach(error => {
                            if (error.type === 'HTTP_ERROR' && error.status >= 500 && 
                                isFrontlineEducationAPI(error.url)) {
                                if (error.url && (error.url.includes('/api/') || error.url.includes('/Api/'))) {
                                    errors.push(error);
                                }
                            } else if (error.type === 'XHR_ERROR' && error.status >= 500 && 
                                      isFrontlineEducationAPI(error.url)) {
                                errors.push(error);
                            }
                        });
                    }
                    
                    return errors;
                """)
                
                # If there are critical network errors, fail immediately
                if network_errors and len(network_errors) > 0:
                    error_messages = []
                    for error in network_errors:
                        if error.get('type') == 'HTTP_500_ERROR':
                            error_messages.append(f"HTTP 500 Error: {error.get('message', 'Internal Server Error')}")
                        elif error.get('type') in ['HTTP_ERROR', 'XHR_ERROR']:
                            error_messages.append(f"HTTP {error.get('status', 'Unknown')} Error: {error.get('url', 'Unknown URL')}")
                        else:
                            error_messages.append(f"Critical API Error: {error.get('message', 'Unknown error')}")
                    
                    elapsed = time.time() - start_time
                    error_summary = "; ".join(error_messages)
                    self.logger.error(f"CRITICAL API ERROR DETECTED: {error_summary}")
                    raise Exception(f"Form save failed due to critical API error: {error_summary}")
                
                # SIMPLIFIED SUCCESS POPUP DETECTION
                script_result = self.driver.execute_script("""
                    // Success keywords to look for
                    var successKeywords = [
                        'Form has been updated successfully',
                        'successfully updated', 
                        'saved successfully',
                        'Update successful',
                        'success'
                    ];
                    
                    // STEP 1: Check for ANY visible element containing success text
                    var allElements = document.querySelectorAll('*');
                    for (var i = 0; i < allElements.length; i++) {
                        var el = allElements[i];
                        
                        // Skip if element is not visible
                        if (el.offsetHeight === 0 && el.offsetWidth === 0) continue;
                        if (window.getComputedStyle(el).display === 'none') continue;
                        if (window.getComputedStyle(el).visibility === 'hidden') continue;
                        
                        var text = el.textContent || el.innerText || '';
                        if (!text.trim()) continue;
                        
                        // Check for success keywords
                        for (var j = 0; j < successKeywords.length; j++) {
                            if (text.toLowerCase().includes(successKeywords[j].toLowerCase())) {
                                // Found success text in visible element
                                return {
                                    found: true,
                                    text: text.trim(),
                                    element: el.tagName + (el.className ? '.' + el.className.split(' ').join('.') : ''),
                                    keyword: successKeywords[j]
                                };
                            }
                        }
                    }
                    
                    // STEP 2: Check common notification selectors specifically
                    var notificationSelectors = [
                        '.k-widget.k-notification',
                        '.k-notification',
                        '.notification',
                        '[class*="notification"]',
                        '.toast',
                        '.alert',
                        '[role="alert"]',
                        '.popup',
                        '.modal'
                    ];
                    
                    for (var k = 0; k < notificationSelectors.length; k++) {
                        var elements = document.querySelectorAll(notificationSelectors[k]);
                        for (var l = 0; l < elements.length; l++) {
                            var notifEl = elements[l];
                            var notifText = notifEl.textContent || notifEl.innerText || '';
                            
                            for (var m = 0; m < successKeywords.length; m++) {
                                if (notifText.toLowerCase().includes(successKeywords[m].toLowerCase())) {
                                    // Check if element or its parent is visible
                                    var isVisible = notifEl.offsetHeight > 0 || notifEl.offsetWidth > 0;
                                    var style = window.getComputedStyle(notifEl);
                                    var parentVisible = true;
                                    
                                    // Check parent container visibility (for animation containers)
                                    if (!isVisible) {
                                        var parent = notifEl.parentElement;
                                        while (parent && !isVisible) {
                                            var parentStyle = window.getComputedStyle(parent);
                                            if (parentStyle.display !== 'none' && parentStyle.visibility !== 'hidden' && 
                                                parent.offsetHeight > 0 && parent.offsetWidth > 0) {
                                                isVisible = true;
                                                break;
                                            }
                                            parent = parent.parentElement;
                                        }
                                    }
                                    
                                    if ((isVisible || parseFloat(style.opacity) > 0) && 
                                        style.display !== 'none' && 
                                        style.visibility !== 'hidden' && 
                                        parentVisible) {
                                        return {
                                            found: true,
                                            text: notifText.trim(),
                                            element: notifEl.tagName + (notifEl.className ? '.' + notifEl.className.split(' ').join('.') : ''),
                                            keyword: successKeywords[m],
                                            selector: notificationSelectors[k]
                                        };
                                    }
                                }
                            }
                        }
                    }
                    
                    // STEP 3: Special check for your specific popup structure
                    var specificPopup = document.querySelector('.k-widget.k-notification.button-notification');
                    if (specificPopup) {
                        var popupText = specificPopup.textContent || specificPopup.innerText || '';
                        if (popupText.includes('Form has been updated successfully')) {
                            return {
                                found: true,
                                text: popupText.trim(),
                                element: 'SPECIFIC_POPUP',
                                keyword: 'Form has been updated successfully',
                                selector: '.k-widget.k-notification.button-notification'
                            };
                        }
                    }
                    
                    return { found: false };
                """)
                
                # Check if we found success message
                if script_result and script_result.get('found'):
                    elapsed = time.time() - start_time
                    success_text = script_result.get('text', 'Success detected')
                    element_info = script_result.get('element', 'Unknown')
                    keyword = script_result.get('keyword', 'success')
                    selector = script_result.get('selector', 'N/A')
                    
                    self.logger.info(f"SUCCESS POPUP FOUND: '{success_text}' in {element_info} (keyword: {keyword}, selector: {selector}) after {elapsed:.3f}s")
                    return elapsed
                
            except Exception as e:
                # Check if this is a network error we should propagate
                if "network error" in str(e).lower() or "500" in str(e):
                    raise  # Re-raise network errors immediately
                
                # Log other errors but continue (only after significant time)
                elapsed = time.time() - start_time
                if elapsed > 10:  # Only log after 10 seconds to reduce noise
                    self.logger.debug(f"Popup search exception: {e}")
                
            time.sleep(0.1)  # Check every 100ms

        # Timeout - provide simple diagnostic
        elapsed = time.time() - start_time
        
        # Add diagnostic information before failing
        try:
            diagnostic_info = self.driver.execute_script("""
                var info = {
                    totalElements: document.querySelectorAll('*').length,
                    notifications: [],
                    bodyText: document.body.textContent ? document.body.textContent.substring(0, 200) : 'No body text',
                    popupSelectors: {}
                };
                
                // Check common notification selectors
                var selectors = [
                    '.k-widget.k-notification.button-notification',
                    '.k-widget.k-notification',
                    '.k-notification',
                    '.notification',
                    '[class*="notification"]',
                    '.toast',
                    '.alert',
                    '[role="alert"]'
                ];
                
                selectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    info.popupSelectors[selector] = {
                        count: elements.length,
                        texts: []
                    };
                    
                    for (var i = 0; i < Math.min(elements.length, 3); i++) {
                        var el = elements[i];
                        var text = (el.textContent || el.innerText || '').substring(0, 100);
                        var visible = el.offsetHeight > 0 && el.offsetWidth > 0;
                        var style = window.getComputedStyle(el);
                        
                        info.popupSelectors[selector].texts.push({
                            text: text,
                            visible: visible,
                            display: style.display,
                            visibility: style.visibility,
                            opacity: style.opacity
                        });
                    }
                });
                
                // Look for any element containing success text
                var successTexts = ['Form has been updated successfully', 'success'];
                successTexts.forEach(function(searchText) {
                    var found = document.body.textContent && document.body.textContent.includes(searchText);
                    if (found) {
                        info.notifications.push('Found "' + searchText + '" in body text');
                    }
                });
                
                return info;
            """)
            
            self.logger.error(f"POPUP SEARCH DIAGNOSTIC after {elapsed:.1f}s timeout:")
            self.logger.error(f"  Total DOM elements: {diagnostic_info.get('totalElements', 'unknown')}")
            self.logger.error(f"  Body text sample: {diagnostic_info.get('bodyText', 'none')}")
            
            for selector, data in diagnostic_info.get('popupSelectors', {}).items():
                if data['count'] > 0:
                    self.logger.error(f"  {selector}: {data['count']} elements found")
                    for i, text_info in enumerate(data['texts']):
                        self.logger.error(f"    [{i}] Text: '{text_info['text']}' | Visible: {text_info['visible']} | Display: {text_info['display']} | Visibility: {text_info['visibility']} | Opacity: {text_info['opacity']}")
                        
            notifications = diagnostic_info.get('notifications', [])
            if notifications:
                self.logger.error(f"  Success text found: {notifications}")
            else:
                self.logger.error("  No success text found in body")
                
        except Exception as diag_error:
            self.logger.error(f"Diagnostic failed: {diag_error}")
        
        raise TimeoutException(f"Form save completion timeout after {elapsed:.1f}s")
    
    def _check_form_load_errors(self) -> list:
        """Check for form load errors - ENHANCED: Comprehensive HTTP 500+ error detection"""
        critical_errors = []
        
        try:
            # 0. ENHANCED NETWORK MONITORING SETUP - More aggressive error detection
            self.logger.debug("🔍 Setting up ENHANCED network error monitoring...")
            self.driver.execute_script("""
                // ENHANCED Network Error Monitoring - Catch ALL HTTP errors
                if (!window._enhancedNetworkMonitoring) {
                    window._networkErrors = window._networkErrors || [];
                    window._allRequests = window._allRequests || [];
                    
                    // Helper function to check if URL should be monitored
                    function shouldMonitorURL(url) {
                        if (!url) return false;
                        // Monitor ALL requests, not just frontlineeducation
                        return url.includes('http') && !url.includes('data:') && !url.includes('chrome-extension:');
                    }
                    
                    // ENHANCED fetch monitoring - catch ALL errors
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        const url = args[0] && typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || 'Unknown URL';
                        const startTime = Date.now();
                        
                        return originalFetch.apply(this, args)
                            .then(response => {
                                const endTime = Date.now();
                                const duration = endTime - startTime;
                                
                                // Log ALL requests for debugging
                                window._allRequests.push({
                                    url: url,
                                    status: response.status,
                                    duration: duration,
                                    method: 'FETCH',
                                    timestamp: startTime
                                });
                                
                                // Track HTTP errors (400+)
                                if (response.status >= 400 && shouldMonitorURL(url)) {
                                    window._networkErrors.push({
                                        type: 'HTTP_ERROR',
                                        status: response.status,
                                        url: url,
                                        message: `HTTP ${response.status} ${response.statusText}`,
                                        method: 'FETCH',
                                        timestamp: startTime,
                                        duration: duration
                                    });
                                    console.error(`🔴 FETCH HTTP ${response.status} Error:`, url);
                                }
                                
                                return response;
                            })
                            .catch(error => {
                                const endTime = Date.now();
                                const duration = endTime - startTime;
                                
                                if (shouldMonitorURL(url)) {
                                    window._networkErrors.push({
                                        type: 'FETCH_ERROR',
                                        message: error.message,
                                        url: url,
                                        method: 'FETCH',
                                        timestamp: startTime,
                                        duration: duration
                                    });
                                    console.error('🔴 FETCH Error:', error.message, url);
                                }
                                throw error;
                            });
                    };
                    
                    // ENHANCED XMLHttpRequest monitoring - catch ALL errors
                    const originalXHR = window.XMLHttpRequest;
                    window.XMLHttpRequest = function() {
                        const xhr = new originalXHR();
                        const originalOpen = xhr.open;
                        const originalSend = xhr.send;
                        
                        let requestUrl = '';
                        let startTime = 0;
                        
                        xhr.open = function(method, url, ...args) {
                            requestUrl = url;
                            return originalOpen.apply(this, [method, url, ...args]);
                        };
                        
                        xhr.send = function(...args) {
                            startTime = Date.now();
                            return originalSend.apply(this, args);
                        };
                        
                        xhr.addEventListener('loadend', function() {
                            const endTime = Date.now();
                            const duration = endTime - startTime;
                            const finalUrl = xhr.responseURL || requestUrl;
                            
                            // Log ALL XHR requests
                            window._allRequests.push({
                                url: finalUrl,
                                status: xhr.status,
                                duration: duration,
                                method: 'XHR',
                                timestamp: startTime
                            });
                            
                            // Track HTTP errors (400+)
                            if (xhr.status >= 400 && shouldMonitorURL(finalUrl)) {
                                window._networkErrors.push({
                                    type: 'XHR_ERROR',
                                    status: xhr.status,
                                    url: finalUrl,
                                    message: `HTTP ${xhr.status} ${xhr.statusText}`,
                                    method: 'XHR',
                                    timestamp: startTime,
                                    duration: duration
                                });
                                console.error(`🔴 XHR HTTP ${xhr.status} Error:`, finalUrl);
                            }
                        });
                        
                        xhr.addEventListener('error', function() {
                            const endTime = Date.now();
                            const duration = endTime - startTime;
                            const finalUrl = xhr.responseURL || requestUrl;
                            
                            if (shouldMonitorURL(finalUrl)) {
                                window._networkErrors.push({
                                    type: 'XHR_ERROR',
                                    message: 'XHR request failed',
                                    url: finalUrl,
                                    method: 'XHR',
                                    timestamp: startTime,
                                    duration: duration
                                });
                                console.error('🔴 XHR Error:', finalUrl);
                            }
                        });
                        
                        return xhr;
                    };
                    
                    // Monitor resource loading errors
                    window.addEventListener('error', function(event) {
                        if (event.target && event.target.src && shouldMonitorURL(event.target.src)) {
                            window._networkErrors.push({
                                type: 'RESOURCE_ERROR',
                                message: 'Resource failed to load',
                                url: event.target.src,
                                method: 'RESOURCE',
                                timestamp: Date.now()
                            });
                            console.error('🔴 Resource Error:', event.target.src);
                        }
                    }, true);
                    
                    window._enhancedNetworkMonitoring = true;
                    console.log('🔍 Enhanced network error monitoring setup completed');
                }
            """)
            
            # 1. ENHANCED JavaScript network error detection
            self.logger.debug("🔍 Checking for HTTP 500+ errors via ENHANCED JavaScript...")
            js_errors = self._check_network_errors_via_devtools()
            self.logger.debug(f"🔍 JavaScript found {len(js_errors)} network errors")
            
            for error in js_errors:
                if any(code in error for code in ["500", "502", "503", "504", "400", "401", "403", "404"]):
                    critical_errors.append(error)
                    self.logger.error(f"🔴 HTTP Error: {error}")
                else:
                    self.logger.debug(f"🟡 Non-critical network error: {error}")
            
            # 2. ADDITIONAL: Check Performance API for failed resources
            self.logger.debug("🔍 Checking Performance API for failed resources...")
            performance_errors = self.driver.execute_script("""
                var performanceErrors = [];
                
                try {
                    // Check navigation entries
                    var navEntries = performance.getEntriesByType('navigation');
                    navEntries.forEach(function(entry) {
                        if (entry.responseStatus >= 400) {
                            performanceErrors.push({
                                type: 'NAVIGATION_ERROR',
                                status: entry.responseStatus,
                                url: entry.name,
                                message: 'Navigation failed with HTTP ' + entry.responseStatus
                            });
                        }
                    });
                    
                    // Check resource entries
                    var resourceEntries = performance.getEntriesByType('resource');
                    resourceEntries.forEach(function(entry) {
                        if (entry.responseStatus >= 400) {
                            performanceErrors.push({
                                type: 'RESOURCE_ERROR',
                                status: entry.responseStatus,
                                url: entry.name,
                                message: 'Resource failed with HTTP ' + entry.responseStatus
                            });
                        }
                    });
                    
                } catch(e) {
                    console.log('Performance API check failed:', e);
                }
                
                return performanceErrors;
            """)
            
            for perf_error in performance_errors or []:
                error_msg = f"Performance API: {perf_error.get('message', 'Unknown error')} - {perf_error.get('url', 'Unknown URL')}"
                critical_errors.append(error_msg)
                self.logger.error(f"🔴 Performance API Error: {error_msg}")
            
            # 3. ADDITIONAL: Get comprehensive network error report
            self.logger.debug("🔍 Getting comprehensive network error report...")
            network_report = self.driver.execute_script("""
                var report = {
                    totalRequests: window._allRequests ? window._allRequests.length : 0,
                    totalErrors: window._networkErrors ? window._networkErrors.length : 0,
                    errorsByStatus: {},
                    criticalErrors: [],
                    allErrors: window._networkErrors || []
                };
                
                // Categorize errors by status code
                if (window._networkErrors) {
                    window._networkErrors.forEach(function(error) {
                        var status = error.status || 'Unknown';
                        report.errorsByStatus[status] = (report.errorsByStatus[status] || 0) + 1;
                        
                        // Mark critical errors (500+)
                        if (error.status >= 500 || error.type === 'FETCH_ERROR' || error.type === 'XHR_ERROR') {
                            report.criticalErrors.push({
                                type: error.type,
                                status: error.status,
                                url: error.url,
                                message: error.message,
                                method: error.method
                            });
                        }
                    });
                }
                
                return report;
            """)
            
            if network_report:
                total_requests = network_report.get('totalRequests', 0)
                total_errors = network_report.get('totalErrors', 0)
                errors_by_status = network_report.get('errorsByStatus', {})
                critical_network_errors = network_report.get('criticalErrors', [])
                
                self.logger.info(f"📊 Network Report: {total_requests} requests, {total_errors} errors")
                if errors_by_status:
                    self.logger.info(f"📊 Errors by status: {errors_by_status}")
                
                # Add critical network errors to our error list
                for net_error in critical_network_errors:
                    error_type = net_error.get('type', 'UNKNOWN')
                    status = net_error.get('status', 'Unknown')
                    url = net_error.get('url', 'Unknown URL')
                    method = net_error.get('method', 'Unknown')
                    
                    error_msg = f"Network {error_type}: HTTP {status} via {method} - {url}"
                    critical_errors.append(error_msg)
                    self.logger.error(f"🔴 Critical Network Error: {error_msg}")
            
            # 4. Check DOM for visible error popups and dismiss them
            self.logger.debug("🔍 Checking for visible error popups...")
            error_check_result = self.driver.execute_script("""
                var criticalErrors = [];
                var popupsToClose = [];
                
                try {
                    // Check for Kendo error notifications (visible popups)
                    var kendoSelectors = [
                        '.k-notification-error',
                        '.k-widget.k-notification.k-notification-error',
                        '.k-animation-container .k-widget.k-popup.k-notification.k-notification-error',
                        '.k-animation-container .k-widget.k-notification.k-notification-error',
                        '[class*="k-notification"][class*="error"]'
                    ];
                    
                    var foundNotifications = new Set(); // Avoid duplicates
                    
                    kendoSelectors.forEach(function(selector) {
                        try {
                            var notifications = document.querySelectorAll(selector);
                            
                            for (var i = 0; i < notifications.length; i++) {
                                var notification = notifications[i];
                                
                                // Check if notification is actually visible to user
                                var isVisible = false;
                                
                                // Direct visibility check
                                if (notification.offsetHeight > 0 && notification.offsetWidth > 0) {
                                    var style = window.getComputedStyle(notification);
                                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                                        isVisible = true;
                                    }
                                }
                                
                                // Check parent container visibility (for animation containers)
                                if (!isVisible) {
                                    var parent = notification.parentElement;
                                    while (parent && !isVisible) {
                                        var parentStyle = window.getComputedStyle(parent);
                                        if (parentStyle.display !== 'none' && parentStyle.visibility !== 'hidden' && 
                                            parent.offsetHeight > 0 && parent.offsetWidth > 0) {
                                            isVisible = true;
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                }
                                
                                if (isVisible) {
                                    var text = notification.textContent || notification.innerText || '';
                                    
                                    // Only check for actual error messages
                                    var lowerText = text.toLowerCase();
                                    if (lowerText.includes('an error has occurred') ||
                                        lowerText.includes('error has occurred') ||
                                        lowerText.includes('server error') ||
                                        lowerText.includes('internal server error') ||
                                        lowerText.includes('500') ||
                                        lowerText.includes('sorry for inconvenience')) {
                                        
                                        // Use text as key to avoid duplicates
                                        var key = text.substring(0, 100);
                                        if (!foundNotifications.has(key)) {
                                            foundNotifications.add(key);
                                            
                                            criticalErrors.push({
                                                type: 'VISIBLE_ERROR_POPUP',
                                                message: 'Error popup: ' + text.replace(/\\s+/g, ' ').substring(0, 200),
                                                selector: selector
                                            });
                                            
                                            // Add to popups to close
                                            popupsToClose.push({
                                                element: notification,
                                                text: text.substring(0, 50)
                                            });
                                        }
                                    }
                                }
                            }
                        } catch(selectorError) {
                            // Continue with other selectors if one fails
                        }
                    });
                    
                    // Check for generic visible error alerts
                    var alertElements = document.querySelectorAll('[role="alert"]');
                    for (var j = 0; j < alertElements.length; j++) {
                        var alert = alertElements[j];
                        
                        // Only visible alerts
                        if (alert.offsetHeight > 0 && alert.offsetWidth > 0) {
                            var computedStyle = window.getComputedStyle(alert);
                            if (computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden') {
                                var alertText = alert.textContent || alert.innerText || '';
                                var lowerAlertText = alertText.toLowerCase();
                                
                                // Only serious error messages
                                if (lowerAlertText.includes('an error has occurred') ||
                                    lowerAlertText.includes('server error') ||
                                    lowerAlertText.includes('500') ||
                                    lowerAlertText.includes('internal server error')) {
                                    
                                    criticalErrors.push({
                                        type: 'VISIBLE_ERROR_POPUP',
                                        message: 'Error alert: ' + alertText.replace(/\\s+/g, ' ').substring(0, 200)
                                    });
                                    
                                    // Add to popups to close
                                    popupsToClose.push({
                                        element: alert,
                                        text: alertText.substring(0, 50)
                                    });
                                }
                            }
                        }
                    }
                    
                } catch(e) {
                    // Ignore DOM query errors
                }
                
                return {
                    criticalErrors: criticalErrors,
                    popupsToClose: popupsToClose
                };
            """)
            
            # Process visible error popups
            if error_check_result:
                for error in error_check_result.get('criticalErrors', []):
                    error_message = error.get('message', 'Unknown error')
                    critical_errors.append(f"Visible error popup: {error_message}")
                    self.logger.error(f"VISIBLE ERROR POPUP: {error_message}")
                
                # Close/dismiss error popups so they don't interfere with other tabs
                popups_to_close = error_check_result.get('popupsToClose', [])
                if popups_to_close:
                    self.logger.info(f"Attempting to close {len(popups_to_close)} error popups...")
                    
                    closed_popups = self.driver.execute_script("""
                        var popupsToClose = arguments[0];
                        var closedCount = 0;
                        var closedPopups = [];
                        
                        popupsToClose.forEach(function(popupInfo, index) {
                            try {
                                var popup = popupInfo.element;
                                var text = popupInfo.text;
                                
                                // Strategy 1: Look for close button within the popup
                                var closeButton = null;
                                
                                // EXPANDED close button selectors - more comprehensive search
                                var closeSelectors = [
                                    '.k-notification-close',
                                    '.k-close',
                                    '.close',
                                    '.btn-close',
                                    'button[aria-label="Close"]',
                                    'button[title="Close"]',
                                    '[data-dismiss="alert"]',
                                    '.fa-times',
                                    '.fa-close',
                                    '.icon-close',
                                    'span.k-icon.k-i-close',
                                    // Additional selectors for Kendo UI
                                    '.k-button-icon.k-icon.k-i-close',
                                    '.k-notification-actions .k-button',
                                    '.k-notification .k-button',
                                    // Generic close patterns
                                    'button[class*="close"]',
                                    '[class*="close"][role="button"]',
                                    '[onclick*="close"]',
                                    '[onclick*="dismiss"]',
                                    // X symbols and close text
                                    'button:contains("×")',
                                    'button:contains("✕")',
                                    'button:contains("Close")',
                                    'span:contains("×")',
                                    'span:contains("✕")'
                                ];
                                
                                // Look for close button within popup and its children
                                for (var i = 0; i < closeSelectors.length; i++) {
                                    var selector = closeSelectors[i];
                                    try {
                                        var closeBtn = popup.querySelector(selector);
                                        if (closeBtn && closeBtn.offsetHeight > 0 && closeBtn.offsetWidth > 0) {
                                            var style = window.getComputedStyle(closeBtn);
                                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                                closeButton = closeBtn;
                                                break;
                                            }
                                        }
                                    } catch(e) {
                                        // Skip invalid selectors
                                        continue;
                                    }
                                }
                                
                                // Strategy 2: Look for close button in parent containers
                                if (!closeButton) {
                                    var parent = popup.parentElement;
                                    var levels = 0;
                                    while (parent && !closeButton && levels < 3) { // Limit search depth
                                        for (var j = 0; j < closeSelectors.length; j++) {
                                            var selector = closeSelectors[j];
                                            try {
                                                var closeBtn = parent.querySelector(selector);
                                                if (closeBtn && closeBtn.offsetHeight > 0 && closeBtn.offsetWidth > 0) {
                                                    var style = window.getComputedStyle(closeBtn);
                                                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                                                        closeButton = closeBtn;
                                                        break;
                                                    }
                                                }
                                            } catch(e) {
                                                // Skip invalid selectors
                                                continue;
                                            }
                                        }
                                        parent = parent.parentElement;
                                        levels++;
                                        // Don't go too far up the DOM
                                        if (parent === document.body) break;
                                    }
                                }
                                
                                // Strategy 3: Try Escape key if popup is focused
                                if (!closeButton) {
                                    try {
                                        // Focus the popup first
                                        popup.focus();
                                        
                                        // Create and dispatch Escape key event
                                        var escapeEvent = new KeyboardEvent('keydown', {
                                            key: 'Escape',
                                            code: 'Escape',
                                            keyCode: 27,
                                            which: 27,
                                            bubbles: true,
                                            cancelable: true
                                        });
                                        
                                        popup.dispatchEvent(escapeEvent);
                                        
                                        // Also try on document
                                        document.dispatchEvent(escapeEvent);
                                        
                                        closedCount++;
                                        closedPopups.push({
                                            method: 'escape_key',
                                            text: text,
                                            selector: popup.tagName + (popup.className ? '.' + popup.className.split(' ').join('.') : '')
                                        });
                                        
                                    } catch(escapeError) {
                                        // Escape key didn't work, popup will remain open
                                        console.log('Escape key failed for popup:', escapeError);
                                    }
                                } else {
                                    // Found close button - click it
                                    try {
                                        closeButton.click();
                                        closedCount++;
                                        closedPopups.push({
                                            method: 'close_button',
                                            text: text,
                                            selector: closeButton.tagName + (closeButton.className ? '.' + closeButton.className.split(' ').join('.') : '')
                                        });
                                    } catch(clickError) {
                                        console.log('Close button click failed:', clickError);
                                        // If close button fails, try escape key as backup
                                        try {
                                            popup.focus();
                                            var escapeEvent = new KeyboardEvent('keydown', {
                                                key: 'Escape',
                                                code: 'Escape',
                                                keyCode: 27,
                                                which: 27,
                                                bubbles: true,
                                                cancelable: true
                                            });
                                            popup.dispatchEvent(escapeEvent);
                                            document.dispatchEvent(escapeEvent);
                                            
                                            closedCount++;
                                            closedPopups.push({
                                                method: 'escape_fallback',
                                                text: text,
                                                selector: popup.tagName + (popup.className ? '.' + popup.className.split(' ').join('.') : '')
                                            });
                                        } catch(escapeError) {
                                            console.log('Escape fallback also failed:', escapeError);
                                            // Leave popup open rather than risk redirect
                                        }
                                    }
                                }
                                
                            } catch(closeError) {
                                // Log error but continue with other popups
                                console.log('Failed to close popup:', closeError);
                            }
                        });
                        
                        return {
                            closedCount: closedCount,
                            closedPopups: closedPopups
                        };
                    """, popups_to_close)
                    
                    if closed_popups.get('closedCount', 0) > 0:
                        self.logger.info(f"✅ Successfully closed {closed_popups['closedCount']} error popups")
                        for popup_info in closed_popups.get('closedPopups', []):
                            method = popup_info.get('method', 'unknown')
                            text = popup_info.get('text', 'unknown')
                            selector = popup_info.get('selector', 'unknown')
                            self.logger.debug(f"  Closed popup via {method}: '{text}' (selector: {selector})")
                    else:
                        self.logger.warning("⚠️ Could not close error popups - they may still interfere with other tabs")
            
        except Exception as e:
            self.logger.warning(f"Error checking form load errors: {e}")
        
        if critical_errors:
            self.logger.warning(f"Found {len(critical_errors)} critical load errors (popups + HTTP errors)")
            # Log each error for debugging
            for i, error in enumerate(critical_errors, 1):
                self.logger.error(f"  {i}. {error}")
        else:
            self.logger.debug("No critical load errors found")
        
        return critical_errors
    
    def _check_network_errors_via_devtools(self) -> list:
        """Check for network errors using JavaScript monitoring - ENHANCED version"""
        errors = []
        
        try:
            # Get all network errors from our enhanced monitoring system
            network_errors = self.driver.execute_script("""
                var errors = [];
                
                try {
                    // Get errors from our enhanced network monitoring
                    if (window._networkErrors && window._networkErrors.length > 0) {
                        window._networkErrors.forEach(function(error) {
                            var errorMsg = '';
                            
                            if (error.type === 'HTTP_ERROR' || error.type === 'XHR_ERROR') {
                                errorMsg = 'Form load failed: HTTP ' + error.status + ' error: ' + error.url;
                            } else if (error.type === 'FETCH_ERROR') {
                                errorMsg = 'Form load failed: Network error: ' + error.message + ' - ' + error.url;
                            } else if (error.type === 'RESOURCE_ERROR') {
                                errorMsg = 'Form load failed: Resource error: ' + error.message + ' - ' + error.url;
                            } else {
                                errorMsg = 'Form load failed: ' + error.type + ': ' + (error.message || 'Unknown error') + ' - ' + (error.url || 'Unknown URL');
                            }
                            
                            errors.push(errorMsg);
                        });
                    }
                    
                    // Also check for any console errors that might indicate network issues
                    if (window.console && window.console.error) {
                        // This is a fallback - the main detection is via our interceptors above
                    }
                    
                } catch(e) {
                    console.log('Error retrieving network errors:', e);
                }
                
                return errors;
            """)
            
            if network_errors:
                errors.extend(network_errors)
                self.logger.debug(f"Enhanced JavaScript monitoring found {len(network_errors)} network errors")
            else:
                self.logger.debug("Enhanced JavaScript monitoring found no network errors")
                
        except Exception as e:
            self.logger.warning(f"Failed to check network errors via enhanced JavaScript: {e}")
        
        return errors
    
    # New unified interface methods
    def measure(self, measurement_type: str, url: str = None, **kwargs) -> MeasurementResult:
        """
        Unified measurement method - NEW INTERFACE
        
        Args:
            measurement_type: "form_load", "standard_load", or "form_save"
            url: URL to measure (required for form_load)
            **kwargs: Additional measurement parameters
            
        Returns:
            MeasurementResult: Complete measurement result with all metrics
        """
        measurer = create_measurer(self.driver, measurement_type, self.logger)
        result = measurer.measure(url, **kwargs)
        
        if self.config.log_measurement_details:
            self.logger.info(f"{measurement_type} measurement: {result.to_dict()}")
        
        return result
    
    def get_page_type(self, url: str) -> str:
        """Determine page type from URL"""
        if SeleniumHelper.is_form_page_url(url):
            return "form"
        else:
            return "standard"
    
    def auto_measure_page_load(self, url: str) -> MeasurementResult:
        """
        Automatically determine page type and measure accordingly - NEW INTERFACE
        
        Args:
            url: URL to measure
            
        Returns:
            MeasurementResult: Complete measurement result
        """
        page_type = self.get_page_type(url)
        
        if page_type == "form":
            return self.measure("form_load", url)
        else:
            # Navigate to URL first for standard pages
            self.driver.get(url)
            return self.measure("standard_load")
    
    def measure_with_retries(
        self, 
        measurement_type: str, 
        url: str = None, 
        max_retries: int = 3,
        **kwargs
    ) -> MeasurementResult:
        """
        Measure with automatic retries on failure - NEW INTERFACE
        
        Args:
            measurement_type: Type of measurement
            url: URL to measure
            max_retries: Maximum number of retries
            **kwargs: Additional parameters
            
        Returns:
            MeasurementResult: Best result from all attempts
        """
        best_result = None
        attempts = 0
        
        while attempts < max_retries:
            attempts += 1
            
            try:
                result = self.measure(measurement_type, url, **kwargs)
                
                # If successful, return immediately
                if result.is_successful:
                    return result
                
                # Keep track of best result (lowest load time for successful measurements)
                if best_result is None or (
                    result.is_successful and 
                    result.load_time < best_result.load_time
                ):
                    best_result = result
                    
            except Exception as e:
                self.logger.warning(f"Measurement attempt {attempts} failed: {e}")
                
                if best_result is None:
                    # Create fallback result for first attempt
                    measurer = create_measurer(self.driver, measurement_type, self.logger)
                    best_result = measurer._create_fallback_result(
                        measurement_type, 
                        f"All {attempts} attempts failed. Last error: {e}"
                    )
        
        return best_result or self._create_final_fallback(measurement_type, max_retries)
    
    def _create_final_fallback(self, measurement_type: str, attempts: int) -> MeasurementResult:
        """Create final fallback result when all retries fail"""
        from .performance_types import create_measurement_result, NetworkState, MeasurementStatus
        
        network_state = NetworkState(has_timeout=True)
        return create_measurement_result(
            load_time=self.config.fallback_timeout,
            measurement_type=measurement_type,
            network_state=network_state,
            status=MeasurementStatus.ERROR,
            strategy_used="fallback",
            error_message=f"All {attempts} measurement attempts failed"
        )

# Global instance for backward compatibility
_performance_manager = None

def get_performance_manager(driver: webdriver.Chrome, logger: logging.Logger = None) -> PerformanceManager:
    """Get or create global performance manager instance"""
    global _performance_manager
    if _performance_manager is None or _performance_manager.driver != driver:
        _performance_manager = PerformanceManager(driver, logger)
    return _performance_manager

# Backward compatibility functions - these will replace the ones in selenium_helper.py
def measure_form_page_load_time_compat(driver: webdriver.Chrome, url: str) -> Tuple[float, dict]:
    """Backward compatibility wrapper for form page load measurement"""
    manager = get_performance_manager(driver)
    return manager.measure_form_page_load_time(url)

def measure_standard_page_load_time_compat(driver: webdriver.Chrome) -> float:
    """Backward compatibility wrapper for standard page load measurement"""
    manager = get_performance_manager(driver)
    return manager.measure_standard_page_load_time()

def measure_form_save_time_compat(driver: webdriver.Chrome) -> float:
    """Backward compatibility wrapper for form save measurement"""
    manager = get_performance_manager(driver)
    return manager.measure_form_save_time() 