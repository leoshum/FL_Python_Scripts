"""
Performance Measurement Base Classes
Unified measurement architecture with proper separation of concerns
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from .performance_config import get_config, PageType, MeasurementStrategy
from .performance_types import (
    MeasurementResult, NetworkState, MeasurementStatus, 
    create_network_state, create_measurement_result
)

class BaseMeasurer(ABC):
    """Base class for all performance measurements"""
    
    def __init__(self, driver: webdriver.Chrome, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)
        self.config = get_config()
        
    @abstractmethod
    def measure(self, url: str = None, **kwargs) -> MeasurementResult:
        """Perform the measurement and return unified result"""
        pass
    
    def _get_current_time(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    def _wait_for_document_ready(self, timeout: int = None) -> bool:
        """Wait for document ready state"""
        timeout = timeout or self.config.timing.default_timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState === 'complete';")
            )
            return True
        except TimeoutException:
            self.logger.warning(f"Document ready timeout after {timeout}s")
            return False
    
    def _check_loading_indicators(self) -> List[str]:
        """Check for active loading indicators"""
        active_loaders = []
        
        for selector in self.config.selectors.loading_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.size['height'] > 0:
                        active_loaders.append(selector)
                        break
            except Exception as e:
                self.logger.debug(f"Loading selector check failed for {selector}: {e}")
                
        return active_loaders
    
    def _get_network_requests(self) -> List[Dict]:
        """Get network requests using Performance API"""
        try:
            script = """
            const entries = performance.getEntriesByType('resource') || [];
            const apiPatterns = arguments[0];
            
            return entries
                .filter(entry => apiPatterns.some(pattern => entry.name.includes(pattern)))
                .map(entry => ({
                    url: entry.name,
                    duration: entry.duration,
                    status: entry.responseEnd > 0 ? 'COMPLETED' : 'PENDING',
                    startTime: entry.startTime,
                    responseEnd: entry.responseEnd
                }));
            """
            return self.driver.execute_script(script, self.config.api.form_api_patterns)
        except Exception as e:
            self.logger.warning(f"Failed to get network requests: {e}")
            return []
    
    def _create_fallback_result(
        self, 
        measurement_type: str, 
        error_message: str,
        fallback_time: float = None
    ) -> MeasurementResult:
        """Create fallback result when measurement fails"""
        
        if fallback_time is None:
            fallback_time = self.config.fallback_timeout
            
        network_state = NetworkState(has_timeout=True)
        
        return create_measurement_result(
            load_time=fallback_time,
            measurement_type=measurement_type,
            network_state=network_state,
            status=MeasurementStatus.FALLBACK,
            strategy_used="fallback",
            error_message=error_message
        )

class NavigationTimingMeasurer(BaseMeasurer):
    """Measures page load using Navigation Timing API - for standard pages"""
    
    def measure(self, url: str = None, **kwargs) -> MeasurementResult:
        """Measure standard page load time using Navigation Timing API"""
        
        start_time = self._get_current_time()
        
        try:
            # Refresh page for clean measurement
            self.driver.execute_script("location.reload(true);")
            
            # Wait for document ready
            if not self._wait_for_document_ready():
                return self._create_fallback_result(
                    "standard_load", 
                    "Document ready timeout"
                )
            
            # Use Navigation Timing API for precise measurement
            timing_script = """
            return new Promise((resolve) => {
                const maxWaitTime = arguments[0] * 1000;
                const startTime = performance.now();
                
                const checkPageReady = () => {
                    const elapsed = performance.now() - startTime;
                    
                    if (elapsed > maxWaitTime) {
                        resolve({
                            loadTime: elapsed / 1000,
                            timeout: true,
                            method: 'timeout'
                        });
                        return;
                    }
                    
                    const loadingSelectors = arguments[1];
                    const hasLoading = loadingSelectors.some(selector => {
                        const elements = document.querySelectorAll(selector);
                        return Array.from(elements).some(el => 
                            el.offsetHeight > 0 && 
                            window.getComputedStyle(el).display !== 'none'
                        );
                    });
                    
                    if (!hasLoading) {
                        const nav = performance.timing;
                        let loadTime;
                        
                        if (nav.loadEventEnd > 0) {
                            loadTime = (nav.loadEventEnd - nav.navigationStart) / 1000;
                        } else {
                            loadTime = elapsed / 1000;
                        }
                        
                        resolve({
                            loadTime: loadTime,
                            timeout: false,
                            method: 'navigation_timing'
                        });
                    } else {
                        requestAnimationFrame(checkPageReady);
                    }
                };
                
                checkPageReady();
            });
            """
            
            result = WebDriverWait(self.driver, self.config.timing.max_measurement_time).until(
                lambda d: d.execute_script(
                    timing_script, 
                    self.config.timing.max_measurement_time,
                    self.config.selectors.loading_selectors
                )
            )
            
            # Get network state
            network_requests = self._get_network_requests()
            active_loaders = self._check_loading_indicators()
            
            network_state = create_network_state(
                api_requests=network_requests,
                active_loaders=active_loaders,
                has_timeout=result.get('timeout', False)
            )
            
            status = MeasurementStatus.TIMEOUT if result.get('timeout') else MeasurementStatus.SUCCESS
            
            return create_measurement_result(
                load_time=result['loadTime'],
                measurement_type="standard_load",
                network_state=network_state,
                status=status,
                strategy_used="navigation_timing"
            )
            
        except Exception as e:
            self.logger.error(f"Navigation timing measurement failed: {e}")
            return self._create_fallback_result(
                "standard_load", 
                str(e),
                time.time() - start_time
            )

class HybridFormMeasurer(BaseMeasurer):
    """Measures form page load using hybrid approach - API monitoring + loading indicators"""
    
    def measure(self, url: str, **kwargs) -> MeasurementResult:
        """Measure form page load time using hybrid monitoring"""
        
        start_time = self._get_current_time()
        
        try:
            # Navigate to URL and refresh for clean measurement
            if url:
                self.driver.get(url)
            
            self.driver.execute_script("performance.clearResourceTimings();")
            self.driver.refresh()
            
            # Enable network monitoring
            try:
                self.driver.execute_cdp_cmd('Network.enable', {})
            except Exception as e:
                self.logger.debug(f"CDP Network.enable failed: {e}")
            
            # Hybrid monitoring script - simplified and more reliable
            monitoring_script = """
            return new Promise((resolve) => {
                const maxWaitTime = arguments[0] * 1000;
                const loadingSelectors = arguments[1];
                const apiPatterns = arguments[2];
                const stabilityWait = arguments[3] * 1000;
                
                let lastActivityTime = Date.now();
                let documentReady = false;
                
                const checkState = () => {
                    const now = Date.now();
                    const elapsed = now - Date.now();
                    
                    if (elapsed > maxWaitTime) {
                        const resources = performance.getEntriesByType('resource') || [];
                        const apiRequests = resources
                            .filter(r => apiPatterns.some(pattern => r.name.includes(pattern)))
                            .map(r => ({
                                url: r.name,
                                duration: r.duration,
                                status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                            }));
                            
                        resolve({
                            timeout: true,
                            apiRequests: apiRequests,
                            totalRequests: resources.length,
                            activeLoaders: []
                        });
                        return;
                    }
                    
                    if (!documentReady && document.readyState === 'complete') {
                        documentReady = true;
                    }
                    
                    const activeLoaders = loadingSelectors.filter(selector => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            return Array.from(elements).some(el => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       el.offsetHeight > 0;
                            });
                        } catch (e) {
                            return false;
                        }
                    });
                    
                    const resources = performance.getEntriesByType('resource') || [];
                    const apiRequests = resources
                        .filter(r => apiPatterns.some(pattern => r.name.includes(pattern)))
                        .map(r => ({
                            url: r.name,
                            duration: r.duration,
                            status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                        }));
                    
                    const pendingRequests = apiRequests.filter(r => r.status === 'PENDING');                    
                    const hasActivity = activeLoaders.length > 0 || pendingRequests.length > 0;
                    
                    if (hasActivity) {
                        lastActivityTime = now;
                    }
                    
                    const timeSinceActivity = now - lastActivityTime;
                    const isStable = documentReady && 
                                   activeLoaders.length === 0 && 
                                   pendingRequests.length === 0 && 
                                   timeSinceActivity >= stabilityWait;
                    
                    if (isStable) {
                        resolve({
                            timeout: false,
                            apiRequests: apiRequests,
                            totalRequests: resources.length,
                            activeLoaders: activeLoaders,
                            stabilityWaitTime: timeSinceActivity / 1000
                        });
                    } else {
                        setTimeout(checkState, 500);
                    }
                };
                
                checkState();
            });
            """
            
            result = WebDriverWait(self.driver, self.config.timing.max_measurement_time).until(
                lambda d: d.execute_script(
                    monitoring_script,
                    self.config.timing.max_measurement_time,
                    self.config.selectors.loading_selectors,
                    self.config.api.form_api_patterns,
                    self.config.timing.page_stability_wait
                )
            )
            
            # Calculate load time
            load_time = time.time() - start_time
            
            # Create network state
            network_state = create_network_state(
                api_requests=result.get('apiRequests', []),
                active_loaders=result.get('activeLoaders', []),
                total_requests=result.get('totalRequests', 0),
                has_timeout=result.get('timeout', False)
            )
            network_state.stability_wait_time = result.get('stabilityWaitTime', 0)
            
            status = MeasurementStatus.TIMEOUT if result.get('timeout') else MeasurementStatus.SUCCESS
            
            return create_measurement_result(
                load_time=load_time,
                measurement_type="form_load",
                network_state=network_state,
                status=status,
                strategy_used="hybrid"
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid form measurement failed: {e}")
            return self._create_fallback_result(
                "form_load", 
                str(e),
                time.time() - start_time
            )

class FormSaveMeasurer(BaseMeasurer):
    """Measures form save time using simple and reliable logic"""
    
    def measure(self, url: str = None, **kwargs) -> MeasurementResult:
        """Measure form save time using simple proven logic"""
        
        start_time = self._get_current_time()
        
        try:
            # Check if readonly form using original logic
            current_url = self.driver.current_url
            if self._is_readonly_form_original(current_url):
                self.logger.info(f"Skipping save measurement - form is read-only: {current_url}")
                return self._create_fallback_result(
                    "form_save",
                    "Form is read-only",
                    0.0
                )
            
            # Get initial network requests for comparison
            initial_requests = self._get_network_requests()
            
            # Find Save button using simple and reliable method
            save_button = self._find_save_button_simple()
            if not save_button:
                self.logger.error("Save button not found")
                return self._create_fallback_result(
                    "form_save",
                    "Save button not found"
                )
            
            self.logger.info(f"Found save button: {save_button.tag_name} with text '{save_button.text.strip()}'")
            
            # Hide interfering elements
            self._hide_interfering_elements()
            
            # Fill form if needed
            self._fill_form_if_needed()
            
            # Click save button and measure time
            save_start_time = self._get_current_time()
            self._click_save_button_simple(save_button)
            
            # Wait for save completion using the original proven method
            save_elapsed = self._wait_for_save_completion_simple(initial_requests)
            
            # Get final network state
            final_requests = self._get_network_requests()
            network_state = create_network_state(
                api_requests=final_requests,
                total_requests=len(final_requests)
            )
            
            self.logger.info(f"Form save completed successfully in {save_elapsed:.3f}s")
            
            return create_measurement_result(
                load_time=save_elapsed,
                measurement_type="form_save",
                network_state=network_state,
                status=MeasurementStatus.SUCCESS,
                strategy_used="simple_save_logic"
            )
            
        except Exception as e:
            error_time = time.time() - start_time
            self.logger.error(f"Form save measurement failed after {error_time:.3f}s: {e}")
            return self._create_fallback_result(
                "form_save", 
                str(e),
                error_time
            )
    
    def _find_save_button_simple(self):
        """Find Save button using simple and reliable selectors - WITH 10 SECOND WAIT"""
        self.logger.debug("Searching for Save button with 10-second wait for dynamic rendering...")
        
        # Wait up to 10 seconds for Save button to appear (forms may render asynchronously)
        max_wait_time = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Strategy 1: Look for the main Save button by ID (original working logic)
            try:
                button = self.driver.find_element(By.ID, "btnUpdateForm")
                if button.is_enabled() and button.is_displayed():
                    btn_text = button.text.strip() or button.get_attribute('value') or 'btnUpdateForm'
                    self.logger.info(f"Found Save button by ID 'btnUpdateForm': text='{btn_text}' (after {time.time() - start_time:.1f}s)")
                    return button
            except:
                pass  # Continue searching
            
            # Strategy 2: Look for other common Save button IDs
            save_button_ids = [
                "btnSave", 
                "saveButton",
                "save-button",
                "btn-save"
            ]
            
            for button_id in save_button_ids:
                try:
                    button = self.driver.find_element(By.ID, button_id)
                    if button.is_enabled() and button.is_displayed():
                        btn_text = button.text.strip() or button.get_attribute('value') or button_id
                        self.logger.info(f"Found Save button by ID '{button_id}': text='{btn_text}' (after {time.time() - start_time:.1f}s)")
                        return button
                except:
                    continue
            
            # Strategy 3: Look for buttons with EXACT "Save" text only
            try:
                # More precise XPath - exact text match and exclude Previous buttons
                xpath_queries = [
                    "//button[normalize-space(text())='Save']",
                    "//input[@type='button' and @value='Save']",
                    "//input[@type='submit' and @value='Save']",
                    "//button[normalize-space(text())='Save Changes']",
                    "//button[normalize-space(text())='Update']"
                ]
                
                for xpath in xpath_queries:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            if button.is_enabled() and button.is_displayed():
                                btn_text = button.text.strip() or button.get_attribute('value')
                                # Double check - exclude Previous, Next, Cancel, etc.
                                if btn_text.lower() not in ['previous', 'next', 'cancel', 'back', 'close']:
                                    self.logger.info(f"Found Save button by XPath: '{btn_text}' (after {time.time() - start_time:.1f}s)")
                                    return button
                    except Exception as e:
                        continue
            except Exception as e:
                pass
            
            # Strategy 4: Look for any submit button with Save-like text (but be very selective)
            try:
                submit_buttons = self.driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                for button in submit_buttons:
                    if button.is_enabled() and button.is_displayed():
                        btn_text = (button.text.strip() or button.get_attribute('value') or '').lower()
                        # Only accept buttons with save-related text
                        if any(save_word in btn_text for save_word in ['save', 'update', 'submit']) and \
                           not any(exclude_word in btn_text for exclude_word in ['previous', 'next', 'cancel', 'back', 'close']):
                            actual_text = button.text.strip() or button.get_attribute('value') or 'Submit'
                            self.logger.info(f"Found Save submit button: '{actual_text}' (after {time.time() - start_time:.1f}s)")
                            return button
            except Exception as e:
                pass
            
            # Strategy 5: Look for buttons with Save-related CSS classes
            try:
                save_class_selectors = [
                    ".btn-save", ".save-btn", ".save-button", ".btn-primary[class*='save']",
                    ".button-save", ".save", "[class*='save'][class*='btn']"
                ]
                
                for selector in save_class_selectors:
                    try:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            if button.is_enabled() and button.is_displayed():
                                btn_text = button.text.strip() or button.get_attribute('value') or selector
                                if btn_text.lower() not in ['previous', 'next', 'cancel', 'back', 'close']:
                                    self.logger.info(f"Found Save button by CSS class '{selector}': text='{btn_text}' (after {time.time() - start_time:.1f}s)")
                                    return button
                    except Exception:
                        continue
            except Exception as e:
                pass
            
            # Strategy 6: Look for buttons with Save-related attributes (data-*, title, aria-label)
            try:
                attribute_selectors = [
                    "//button[@title*='Save' or @title*='save']",
                    "//button[@aria-label*='Save' or @aria-label*='save']",
                    "//button[@data-action*='save' or @data-action*='Save']",
                    "//input[@title*='Save' or @title*='save']",
                    "//input[@aria-label*='Save' or @aria-label*='save']"
                ]
                
                for xpath in attribute_selectors:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            if button.is_enabled() and button.is_displayed():
                                btn_text = button.text.strip() or button.get_attribute('value') or button.get_attribute('title') or button.get_attribute('aria-label') or 'Save Button'
                                if btn_text.lower() not in ['previous', 'next', 'cancel', 'back', 'close']:
                                    self.logger.info(f"Found Save button by attribute: text='{btn_text}' (after {time.time() - start_time:.1f}s)")
                                    return button
                    except Exception:
                        continue
            except Exception as e:
                pass
            
            # Wait a bit before next attempt
            elapsed = time.time() - start_time
            self.logger.debug(f"Save button not found yet, continuing search... ({elapsed:.1f}s elapsed)")
            time.sleep(0.5)  # Wait 500ms before next attempt
        
        # If we get here, button was not found after 10 seconds
        total_wait = time.time() - start_time
        self.logger.error(f"No Save button found after {total_wait:.1f}s wait!")
        
        # Enhanced Diagnostic: Log all buttons found on page
        try:
            self.logger.info("=== ENHANCED DIAGNOSTIC: All buttons on page ===")
            all_buttons = self.driver.find_elements(By.XPATH, "//button | //input[@type='button'] | //input[@type='submit']")
            self.logger.info(f"Total buttons found: {len(all_buttons)}")
            
            for i, btn in enumerate(all_buttons[:15]):  # Show first 15 buttons
                try:
                    btn_text = btn.text.strip() or btn.get_attribute('value') or btn.get_attribute('id') or f'button_{i}'
                    btn_id = btn.get_attribute('id') or 'no-id'
                    btn_type = btn.tag_name
                    if btn.tag_name == 'input':
                        btn_type = f"input[type='{btn.get_attribute('type')}']"
                    visible = btn.is_displayed()
                    enabled = btn.is_enabled()
                    classes = btn.get_attribute('class') or 'no-class'
                    self.logger.info(f"Button {i+1:2d}: {btn_type:20} id='{btn_id:15}' text='{btn_text:20}' visible={visible} enabled={enabled} class='{classes[:30]}'")
                except Exception as e:
                    self.logger.info(f"Button {i+1:2d}: Error reading button info: {e}")
            
            if len(all_buttons) > 15:
                self.logger.info(f"... and {len(all_buttons) - 15} more buttons")
                
            self.logger.info("=== END ENHANCED DIAGNOSTIC ===")
        except Exception as e:
            self.logger.error(f"Enhanced diagnostic failed: {e}")
        
        return None
    
    def _click_save_button_simple(self, save_button):
        """Click save button with retry logic"""
        attempts = 3
        
        while attempts > 0:
            attempts -= 1
            try:
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_button)
                time.sleep(0.3)  # Wait for scroll
                
                # Try normal click first
                save_button.click()
                self.logger.debug("Save button clicked successfully")
                return
                
            except Exception as e:
                if attempts > 0:
                    self.logger.warning(f"Save button click failed, retrying with JS: {e}")
                    try:
                        # Try JavaScript click
                        self.driver.execute_script("arguments[0].click();", save_button)
                        self.logger.debug("Save button clicked with JavaScript")
                        return
                    except Exception as js_e:
                        self.logger.warning(f"JS click also failed: {js_e}")
                        time.sleep(0.5)
                else:
                    raise Exception(f"Failed to click save button after 3 attempts: {e}")
    
    def _wait_for_save_completion_simple(self, initial_requests):
        """Wait for save completion using simple and reliable method"""
        temp_start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        time.sleep(0.2)  # Brief pause for DOM updates
        
        success_found = False
        
        while time.time() - temp_start_time < timeout:
            try:
                # Check for success messages
                current_url = self.driver.current_url
                
                if "plan" in current_url.lower():
                    # Plan pages use div[role="alert"]
                    script_result = self.driver.execute_script("""
                        var alertDiv = document.querySelector('div[role="alert"]');
                        return alertDiv ? alertDiv.textContent : null;
                    """)
                else:
                    # Other pages use kendo-notification
                    script_result = self.driver.execute_script("""
                        var notification = document.querySelector('kendo-notification');
                        return notification ? notification.textContent : null;
                    """)
                
                if script_result and ("successfully" in script_result.lower() or "updated" in script_result.lower()):
                    success_found = True
                    self.logger.debug(f"Success message found: {script_result.strip()}")
                    break
                
                # Check for network errors after 3 seconds
                elapsed = time.time() - temp_start_time
                if elapsed > 3:
                    try:
                        # Simple network error check
                        error_check = self.driver.execute_script("""
                            // Check for error messages in common locations
                            var errorSelectors = [
                                '.error', '.alert-danger', '.validation-summary-errors',
                                '[role="alert"][class*="error"]', '.field-validation-error'
                            ];
                            
                            for (var i = 0; i < errorSelectors.length; i++) {
                                var errors = document.querySelectorAll(errorSelectors[i]);
                                for (var j = 0; j < errors.length; j++) {
                                    if (errors[j].offsetHeight > 0 && errors[j].textContent.trim()) {
                                        return errors[j].textContent.trim();
                                    }
                                }
                            }
                            return null;
                        """)
                        
                        if error_check:
                            raise Exception(f"Form save error detected: {error_check}")
                            
                    except Exception as check_error:
                        if "Form save error detected" in str(check_error):
                            raise check_error
                        # Ignore other check errors
                        pass
                
            except Exception as e:
                if "Form save error detected" in str(e):
                    raise e
                # Continue loop for other exceptions
                pass
                    
            time.sleep(0.2)  # Check every 200ms

        elapsed = time.time() - temp_start_time
        
        if not success_found:
            if elapsed >= timeout:
                raise TimeoutException(f"Form save popup timeout after {timeout}s")
            else:
                raise Exception("Form save completion check failed")

        return elapsed
    
    def _hide_interfering_elements(self):
        """Hide elements that can interfere with Save button clicks"""
        try:
            self.driver.execute_script("""
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
            
            self.logger.debug("Hidden interfering elements that could intercept clicks")
                
        except Exception as ex:
            # Not critical if hiding fails
            self.logger.debug(f"Could not hide interfering elements: {str(ex)}")
    
    def _fill_form_if_needed(self):
        """Fill form if form filler is available and enabled"""
        try:
            # Check if form filler is disabled in options
            if hasattr(self.config, 'options') and self.config.options.get("disable_filler", False):
                return
                
            from frontline_selenium.page_filler import PageFormFiller
            PageFormFiller.fill_form(self.driver)
            self.logger.debug("Form filled successfully")
        except ImportError:
            self.logger.debug("PageFormFiller not available - skipping form fill")
        except Exception as e:
            self.logger.debug(f"Form filler error (non-critical): {e}")
    
    def _is_readonly_form_original(self, url: str) -> bool:
        """Check if form is readonly using original logic from selenium_helper"""
        try:
            from .selenium_helper import SeleniumHelper
            # Use the original method if it exists
            if hasattr(SeleniumHelper, 'is_likely_readonly_form'):
                return SeleniumHelper.is_likely_readonly_form(url)
        except:
            pass
        
        # Fallback to very conservative readonly detection
        url_lower = url.lower()
        
        # Only very specific readonly patterns that we're 100% sure about
        readonly_patterns = [
            "eligibilitiesimpairments",
            "lre%26educationalplacement", 
            "lre&educationalplacement",
            "readonly=true",
            "mode=readonly"
        ]
        
        return any(pattern in url_lower for pattern in readonly_patterns)

# Factory function to create appropriate measurer
def create_measurer(
    driver: webdriver.Chrome, 
    measurement_type: str, 
    logger: logging.Logger = None
) -> BaseMeasurer:
    """Factory function to create appropriate measurer based on type"""
    
    if measurement_type == "form_load":
        return OptimizedFormMeasurer(driver, logger)
    elif measurement_type == "standard_load":
        return OptimizedStandardMeasurer(driver, logger)
    elif measurement_type == "form_save":
        return FormSaveMeasurer(driver, logger)
    else:
        raise ValueError(f"Unknown measurement type: {measurement_type}")

class OptimizedStandardMeasurer(BaseMeasurer):
    """Optimized standard page measurer - NO UNNECESSARY RELOADS"""
    
    def measure(self, url: str = None, **kwargs) -> MeasurementResult:
        """Measure standard page load time WITHOUT unnecessary reload"""
        
        start_time = self._get_current_time()
        
        try:
            self.logger.info("Measuring standard page load (optimized - no reload)")
            
            # Wait for document ready (page is already loaded)
            if not self._wait_for_document_ready():
                return self._create_fallback_result(
                    "standard_load", 
                    "Document ready timeout"
                )
            
            # Use Navigation Timing API for precise measurement
            timing_script = """
            return new Promise((resolve) => {
                const maxWaitTime = arguments[0] * 1000;
                const startTime = performance.now();
                
                const checkPageReady = () => {
                    const elapsed = performance.now() - startTime;
                    
                    if (elapsed > maxWaitTime) {
                        resolve({
                            loadTime: elapsed / 1000,
                            timeout: true,
                            method: 'timeout'
                        });
                        return;
                    }
                    
                    const loadingSelectors = arguments[1];
                    const hasLoading = loadingSelectors.some(selector => {
                        const elements = document.querySelectorAll(selector);
                        return Array.from(elements).some(el => 
                            el.offsetHeight > 0 && 
                            window.getComputedStyle(el).display !== 'none'
                        );
                    });
                    
                    if (!hasLoading) {
                        const nav = performance.timing;
                        let loadTime;
                        
                        if (nav.loadEventEnd > 0) {
                            loadTime = (nav.loadEventEnd - nav.navigationStart) / 1000;
                        } else {
                            loadTime = elapsed / 1000;
                        }
                        
                        resolve({
                            loadTime: loadTime,
                            timeout: false,
                            method: 'navigation_timing'
                        });
                    } else {
                        requestAnimationFrame(checkPageReady);
                    }
                };
                
                checkPageReady();
            });
            """
            
            result = WebDriverWait(self.driver, self.config.timing.max_measurement_time).until(
                lambda d: d.execute_script(
                    timing_script, 
                    self.config.timing.max_measurement_time,
                    self.config.selectors.loading_selectors
                )
            )
            
            # Get network state
            network_requests = self._get_network_requests()
            active_loaders = self._check_loading_indicators()
            
            network_state = create_network_state(
                api_requests=network_requests,
                active_loaders=active_loaders,
                has_timeout=result.get('timeout', False)
            )
            
            status = MeasurementStatus.TIMEOUT if result.get('timeout') else MeasurementStatus.SUCCESS
            
            self.logger.info(f"Standard page load measured: {result['loadTime']:.3f}s (no reload)")
            
            return create_measurement_result(
                load_time=result['loadTime'],
                measurement_type="standard_load",
                network_state=network_state,
                status=status,
                strategy_used="optimized_navigation_timing"
            )
            
        except Exception as e:
            self.logger.error(f"Optimized standard page measurement failed: {e}")
            return self._create_fallback_result(
                "standard_load", 
                str(e),
                time.time() - start_time
            )

class OptimizedFormMeasurer(BaseMeasurer):
    """Optimized form page measurer - NO UNNECESSARY RELOADS"""
    
    def measure(self, url: str, **kwargs) -> MeasurementResult:
        """Measure form page load time WITHOUT unnecessary reload"""
        
        start_time = self._get_current_time()
        
        try:
            self.logger.info("Measuring form page load (optimized - no reload)")
            
            # Navigate to URL only if needed (first time)
            if url and self.driver.current_url != url:
                self.logger.debug(f"Navigating to URL: {url}")
                self.driver.get(url)
            
            # Clear performance timings for accurate measurement (but don't reload)
            self.driver.execute_script("performance.clearResourceTimings();")
            
            # Enable network monitoring
            try:
                self.driver.execute_cdp_cmd('Network.enable', {})
            except Exception as e:
                self.logger.debug(f"CDP Network.enable failed: {e}")
            
            # Optimized monitoring script - works on current page state
            monitoring_script = """
            return new Promise((resolve) => {
                const maxWaitTime = arguments[0] * 1000;
                const loadingSelectors = arguments[1];
                const apiPatterns = arguments[2];
                const stabilityWait = arguments[3] * 1000;
                
                let lastActivityTime = Date.now();
                let documentReady = document.readyState === 'complete';
                
                const checkState = () => {
                    const now = Date.now();
                    const elapsed = now - Date.now();
                    
                    if (elapsed > maxWaitTime) {
                        const resources = performance.getEntriesByType('resource') || [];
                        const apiRequests = resources
                            .filter(r => apiPatterns.some(pattern => r.name.includes(pattern)))
                            .map(r => ({
                                url: r.name,
                                duration: r.duration,
                                status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                            }));
                            
                        resolve({
                            timeout: true,
                            apiRequests: apiRequests,
                            totalRequests: resources.length,
                            activeLoaders: []
                        });
                        return;
                    }
                    
                    if (!documentReady && document.readyState === 'complete') {
                        documentReady = true;
                    }
                    
                    const activeLoaders = loadingSelectors.filter(selector => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            return Array.from(elements).some(el => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       el.offsetHeight > 0;
                            });
                        } catch (e) {
                            return false;
                        }
                    });
                    
                    const resources = performance.getEntriesByType('resource') || [];
                    const apiRequests = resources
                        .filter(r => apiPatterns.some(pattern => r.name.includes(pattern)))
                        .map(r => ({
                            url: r.name,
                            duration: r.duration,
                            status: r.responseEnd > 0 ? 'COMPLETED' : 'PENDING'
                        }));
                    
                    const pendingRequests = apiRequests.filter(r => r.status === 'PENDING');                    
                    const hasActivity = activeLoaders.length > 0 || pendingRequests.length > 0;
                    
                    if (hasActivity) {
                        lastActivityTime = now;
                    }
                    
                    const timeSinceActivity = now - lastActivityTime;
                    const isStable = documentReady && 
                                   activeLoaders.length === 0 && 
                                   pendingRequests.length === 0 && 
                                   timeSinceActivity >= stabilityWait;
                    
                    if (isStable) {
                        resolve({
                            timeout: false,
                            apiRequests: apiRequests,
                            totalRequests: resources.length,
                            activeLoaders: activeLoaders,
                            stabilityWaitTime: timeSinceActivity / 1000
                        });
                    } else {
                        setTimeout(checkState, 500);
                    }
                };
                
                checkState();
            });
            """
            
            result = WebDriverWait(self.driver, self.config.timing.max_measurement_time).until(
                lambda d: d.execute_script(
                    monitoring_script,
                    self.config.timing.max_measurement_time,
                    self.config.selectors.loading_selectors,
                    self.config.api.form_api_patterns,
                    self.config.timing.page_stability_wait
                )
            )
            
            # Calculate load time
            load_time = time.time() - start_time
            
            # Create network state
            network_state = create_network_state(
                api_requests=result.get('apiRequests', []),
                active_loaders=result.get('activeLoaders', []),
                total_requests=result.get('totalRequests', 0),
                has_timeout=result.get('timeout', False)
            )
            network_state.stability_wait_time = result.get('stabilityWaitTime', 0)
            
            status = MeasurementStatus.TIMEOUT if result.get('timeout') else MeasurementStatus.SUCCESS
            
            self.logger.info(f"Form page load measured: {load_time:.3f}s (no reload)")
            
            return create_measurement_result(
                load_time=load_time,
                measurement_type="form_load",
                network_state=network_state,
                status=status,
                strategy_used="optimized_hybrid"
            )
            
        except Exception as e:
            self.logger.error(f"Optimized form measurement failed: {e}")
            return self._create_fallback_result(
                "form_load", 
                str(e),
                time.time() - start_time
            ) 