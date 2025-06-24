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
        # EventOverview is the only ViewEvent page that's NOT a form
        if "EventOverview" in url:
            return False
        
        # Any ViewEvent URL (except EventOverview) is a form page
        if "ViewEvent" in url:
            return True
            
        # Include other form types
        return ("Forms" in url or "DistributionManager" in url)
    
    @staticmethod
    def is_likely_readonly_form(url: str) -> bool:
        """
        Check if URL suggests this might be a readonly form.
        This is a HINT, not a definitive answer.
        """
        # Only check for very obvious readonly patterns
        url_lower = url.lower()
        
        # Very obvious readonly fragments that we're confident about
        obvious_readonly_fragments = [
            "eligibilitiesimpairments",  # Always readonly in practice
            "lre%26educationalplacement",  # Always readonly
            "lre&educationalplacement"     # Always readonly
        ]
        
        # Check URL hash fragment
        if "#" in url:
            fragment = url.split("#")[1].lower()
            if any(readonly in fragment for readonly in obvious_readonly_fragments):
                return True
        
        # Check for explicit readonly indicators in URL
        if any(indicator in url_lower for indicator in ["readonly", "view-only", "display-only"]):
            return True
            
        return False
    
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
            
            WebDriverWait(driver, timeout + 5).until(
                lambda d: d.execute_script("return true;")
            )
            
        except Exception as ex:
            # Simple fallback
            if SeleniumHelper.logger:
                SeleniumHelper.logger.warning(f"MutationObserver form detection failed, using simple fallback: {str(ex)}")
            
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState === 'complete';")
                )
                
                # TODO: think about removing this sleep
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
                # If no specific form container found assume page is ready
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
                # TODO: move magic number to config 
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
    def wait_for_form_save_popup(driver: webdriver.Chrome, initial_requests: list = None) -> float:
        temp_start_time = time.time()
        
        # Use provided initial_requests or get them now (fallback)
        if initial_requests is None:
            try:
                initial_requests = SeleniumHelper.get_ajax_requests(driver)
            except:
                initial_requests = []
        
        time.sleep(0.1)  # enough time for DOM updates ?
        
        success_found = False
        while time.time() - temp_start_time < SeleniumHelper.timeout:
            try:
                # Check for success messages first
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
                    success_found = True
                    break
                
                # Check network requests for errors every few seconds
                elapsed = time.time() - temp_start_time
                # TODO: think about this logic. Can we not wait for 3 sec?
                if elapsed > 3:  # After 3 seconds, start checking network errors
                    try:
                        current_requests = SeleniumHelper.get_ajax_requests(driver)
                        
                        # Find new requests made during save operation
                        new_requests = []
                        if len(current_requests) > len(initial_requests):
                            new_requests = current_requests[len(initial_requests):]
                        
                        # Check for save-related endpoints and their status codes
                        form_save_endpoints = [
                            "plan/Events/UpdateForm" if SeleniumHelper.is_plan_page_url(driver.current_url) else "plan/api/forms/",
                            "/api/",
                            "/update",
                            "/save",
                            "UpdateForm",
                            "SaveForm"
                        ]
                        
                        failed_requests = []
                        save_requests_found = False
                        
                        for request in new_requests:
                            request_url = request.get("url", "") if isinstance(request, dict) else str(request)
                            request_status = request.get("status", 0) if isinstance(request, dict) else 0
                            
                            # Check if this is a save-related request
                            is_save_request = any(endpoint in request_url for endpoint in form_save_endpoints)
                            
                            if is_save_request:
                                save_requests_found = True
                                
                                # Check for error status codes (anything not 2xx)
                                if isinstance(request_status, int) and (request_status < 200 or request_status >= 300):
                                    if request_status != 0:  # 0 means pending, which we handle below
                                        failed_requests.append({
                                            'url': request_url,
                                            'status': request_status,
                                            'method': request.get('method', 'Unknown')
                                        })
                                        
                                # Check for long-pending requests (>30s means stuck)
                                # TODO: move 30 sec to config
                                elif request_status == 0 or request_status == "pending":
                                    request_duration = request.get("duration", 0)
                                    if request_duration > 30000:  # 30+ seconds
                                        failed_requests.append({
                                            'url': request_url,
                                            'status': 'pending_timeout',
                                            'duration': request_duration
                                        })

                        # If we found failed requests then raise error immediately
                        if failed_requests:
                            error_details = []
                            for req in failed_requests:
                                if req['status'] == 'pending_timeout':
                                    detail = f"URL: {req['url']} - Status: PENDING for {req['duration']}ms"
                                else:
                                    detail = f"URL: {req['url']} - Status: {req['status']} ({req.get('method', 'Unknown')})"
                                error_details.append(detail)
                                
                            error_msg = f"Form save failed - Network errors detected:\n" + "\n".join(error_details)
                            if SeleniumHelper.logger:
                                SeleniumHelper.logger.error(error_msg)
                            
                            # Raise exception with detailed status code info for Excel colnm
                            raise ValueError(f"Form save network error: {len(failed_requests)} failed request(s)")
                    
                    except ValueError:
                         # Reraise ValueError looks like network errors 
                        raise
                    except Exception as e:
                        if SeleniumHelper.logger:
                            SeleniumHelper.logger.warning(f"Failed to check network requests: {str(e)}")
                    
            except UnexpectedAlertPresentException:
                try:
                    Alert(driver).accept()
                except:
                    pass
            except ValueError:
                # Reraise ValueError looks like network errors 
                raise
            except Exception:
                # Fallback: direct element search but still need to check for success
                try:
                if SeleniumHelper.is_plan_page_url(driver.current_url):
                    alert_elem = driver.find_element(By.CSS_SELECTOR, 'div[role="alert"]')

                    if alert_elem and "Form has been updated successfully" in alert_elem.text:
                            success_found = True
                        break
                else:
                    notification_elem = driver.find_element(By.TAG_NAME, 'kendo-notification')
                    if notification_elem and "Form has been updated successfully" in notification_elem.text:
                            success_found = True
                        break
                except:
                    # If fallback also fails, continue the loop
                    pass
                    
            time.sleep(0.1)

        elapsed = time.time() - temp_start_time
        if elapsed >= SeleniumHelper.timeout and not success_found:
            error_msg = f"Form save popup timeout after {SeleniumHelper.timeout}s"
            if SeleniumHelper.logger:
                SeleniumHelper.logger.error(error_msg)
            raise TimeoutException(error_msg)

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
        Uses the new PerformanceManager for improved reliability.
        """
        from .performance_manager import get_performance_manager
        
        manager = get_performance_manager(driver, SeleniumHelper.get_logger())
        return manager.measure_form_page_load_time(url)
    
    @staticmethod
    def measure_standard_page_load_time(driver: webdriver.Chrome) -> float:
        """
        Measure standard page load time using Navigation Timing API.
        Uses the new PerformanceManager for improved reliability.
        """
        from .performance_manager import get_performance_manager
        
        manager = get_performance_manager(driver, SeleniumHelper.get_logger())
        return manager.measure_standard_page_load_time()
    
    @staticmethod
    def measure_form_save_time(driver: webdriver.Chrome) -> float:
        """
        Measure form save time.
        Uses the new PerformanceManager for improved reliability.
        """
        from .performance_manager import get_performance_manager
        
        manager = get_performance_manager(driver, SeleniumHelper.get_logger())
        return manager.measure_form_save_time()
    
    @staticmethod
    def _hide_interfering_elements(driver: webdriver.Chrome):
        """Hide elements that can interfere with Save button clicks"""
        try:
            driver.execute_script("""
                // Hide iframe launcher that commonly intercepts clicks
                var launcher = document.getElementById('launcher');
                if (launcher) {
                    launcher.style.display = 'none';
                    launcher.style.visibility = 'hidden';
                    launcher.style.zIndex = '-1';
                }
                
                // Hide other common interfering elements
                var interfering_selectors = [
                    'iframe[title*="widget"]',
                    'iframe[id="launcher"]', 
                    '.widget-overlay',
                    '.chat-widget',
                    '.support-widget',
                    '[id*="support"][id*="widget"]',
                    '[class*="widget"][class*="overlay"]'
                ];
                
                interfering_selectors.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        elements.forEach(function(el) {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.zIndex = '-1';
                        });
                    } catch(e) {
                        // Ignore selector errors
                    }
                });
            """)
            
            if SeleniumHelper.logger:
                SeleniumHelper.logger.debug("Hidden interfering elements that could intercept clicks")
                
        except Exception as ex:
            # Not critical if hiding fails
            if SeleniumHelper.logger:
                SeleniumHelper.logger.debug(f"Could not hide interfering elements: {str(ex)}")
            pass

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
            var loadingElements = element.querySelectorAll('.loading, .spinner, .blockUI, .loader-circle, .sk-activity-indicator, .sidekick.sk-activity-indicator');
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