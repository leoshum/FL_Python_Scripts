# Import statements
from typing import Tuple
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By

# Add parent directory to path for imports (frontline_selenium is in parent directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from frontline_selenium.selenium_helper import SeleniumHelper

# Additional imports for the main script functionality
import validators
import numpy as np
import speedtest
from collections import namedtuple
from urllib.parse import urlparse 
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Font
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException

# Import additional modules after path setup
from frontline_selenium.page_filler import PageFormFiller
from frontline_selenium.support_tech_helper import SupportTech

logger = logging.getLogger()

# Configuration Constants
class Config:
    # Timeout settings
    DEFAULT_TIMEOUT = 30  # seconds
    
    # Decimal precision
    LOAD_TIME_DECIMAL_PLACES = 1
    
    # Payload size monitoring
    PAYLOAD_SIZE_THRESHOLD = 500.0
    
    # Excel column indices
    class ExcelColumns:
        FROM_NAME = 0
        FORM_URL = 1
        JIRA_TICKET = 2
        ERROR_MESSAGE = 3
        PAYLOAD_SIZE = 4
        TIMESTAMP = 5          
        LOAD_FIRST = 6
        LOAD_MIN = 7            
        LOAD_MAX = 8           
        LOAD_MEAN = 9         
        SAVE_FIRST = 10
        SAVE_MIN = 11         
        SAVE_MAX = 12          
        SAVE_MEAN = 13
    
    # Color codes for Excel formatting
    class Colors:
        RED = "FF0000"      # Critical errors
        ORANGE = "FF9900"   # Warnings/investigation needed
        PURPLE = "800080"   # Technical issues
        GREEN = "00FF00"    # Good performance
        YELLOW = "FFFF00"   # Average performance    

    # Error classification
    class ErrorTypes:
        TIMEOUT = "timeout"
        FALLBACK = "fallback"
        API_ERROR = "api_error"
        NETWORK_ERROR = "network_error"
        READONLY = "readonly"
        ELEMENT_NOT_FOUND = "element_not_found"
        TECHNICAL = "technical"
        FORM_LOAD_ERROR = "form_load_error"  # NEW: For form load errors during page load
        TIMEOUT_ERROR = "timeout_error"
        TECHNICAL_ERROR = "technical_error"
        SERVER_DOWN = "server_down"  # NEW: For HTTP 503 Service Unavailable


class MeasurementResult:
    def __init__(self, success=True, error_type=None, error_message="", 
                 first_measure=0.0, min_time=0.0, max_time=0.0, mean_time=0.0, payload_size=0.0):
        self.success = success
        self.error_type = error_type
        self.error_message = error_message
        self.first_measure = first_measure
        self.min_time = min_time
        self.max_time = max_time
        self.mean_time = mean_time
        self.payload_size = payload_size
    
    @property
    def is_timeout_or_fallback(self):
        return self.error_type in [Config.ErrorTypes.TIMEOUT, Config.ErrorTypes.FALLBACK]


class ErrorClassifier:
    @staticmethod
    def classify_load_error(error_message: str) -> Tuple[str, str]:
        """SIMPLIFIED: Classify load error and return (error_type, simple_message)"""
        error_lower = error_message.lower()
        
        # PRIORITY: HTTP 503 Service Unavailable (server down)
        if ("service unavailable" in error_lower or "http 503" in error_lower or 
            ("503" in error_lower and "service" in error_lower)):
            return Config.ErrorTypes.SERVER_DOWN, error_message
        
        # Chrome crashes - very common
        if ("gethandleverifier" in error_lower or "stacktrace" in error_lower or 
            "chrome" in error_lower or "driver" in error_lower):
            return Config.ErrorTypes.TECHNICAL_ERROR, "Browser crashed - restart needed"
        
        # HTTP errors - server problems
        if ("http 500" in error_lower or "500" in error_message or 
            "server error" in error_lower or "internal server" in error_lower):
            return Config.ErrorTypes.FORM_LOAD_ERROR, "Server error (HTTP 500)"
        
        # Network/connection issues
        if ("timeout" in error_lower or "timed out" in error_lower or 
            "connection" in error_lower or "network" in error_lower):
            return Config.ErrorTypes.TIMEOUT_ERROR, "Page loading timeout"
        
        # Popup or text errors
        if ("popup" in error_lower or "error has occurred" in error_lower):
            return Config.ErrorTypes.FORM_LOAD_ERROR, error_message  # Use the message as-is from JavaScript
        
        # 404 Not Found errors - return as-is (already clear for managers)
        if ("not found error" in error_lower):
            return Config.ErrorTypes.FORM_LOAD_ERROR, error_message  # Use the message as-is from JavaScript
        
        # Default - keep it simple
        return Config.ErrorTypes.TECHNICAL_ERROR, "Page loading failed"
    
    @staticmethod
    def classify_save_error(exception):
        error_msg = str(exception).lower()
        
        # Check for timeout specifically
        if isinstance(exception, TimeoutException) or "timeout" in error_msg:
            return Config.ErrorTypes.TIMEOUT_ERROR, "Save message timeout"
        
        # Check for specific save errors (API errors)
        if "save failed:" in error_msg or "api error" in error_msg:
            if "500" in error_msg or "server error" in error_msg:
                return Config.ErrorTypes.API_ERROR, "Save failed due to server error (HTTP 500)"
            else:
                return Config.ErrorTypes.API_ERROR, str(exception)  # Use full exception message for API errors
        
        # Chrome crashes
        if ("gethandleverifier" in error_msg or "stacktrace" in error_msg or 
            "chrome" in error_msg or "driver" in error_msg):
            return Config.ErrorTypes.TECHNICAL_ERROR, "Browser crashed during save"
        
        # Button not found
        if isinstance(exception, NoSuchElementException) or "no such element" in error_msg:
            return Config.ErrorTypes.TECHNICAL_ERROR, "Save button not found"
        
        # Click issues
        if "failed to click save button" in error_msg:
            return Config.ErrorTypes.TECHNICAL_ERROR, "Could not click Save button"
        
        # Default
        return Config.ErrorTypes.TECHNICAL_ERROR, "Save operation failed"


class FormMeasurer:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def _check_for_form_content(self, url):
        try:
            # Strategy 1: Check for real interactive inputs
            input_analysis = self.driver.execute_script("""
                const result = {
                    totalInputs: 0,
                    visibleInputs: 0,
                    interactableInputs: 0
                };
                
                const inputSelectors = [
                    'input:not([type="hidden"])',
                    'select', 'textarea', 'button',
                    '[contenteditable="true"]',
                    '.k-editor', 'accelify-rich-editor',
                    'kendo-datepicker', 'kendo-combobox', 'kendo-dropdownlist', 'kendo-multiselect',
                    'accelify-date-picker', 'accelify-signature',
                    '.k-checkbox', '.k-radio'
                ];
                
                const allInputs = [];
                inputSelectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(elem => {
                            if (!allInputs.includes(elem)) {
                                allInputs.push(elem);
                            }
                        });
                    } catch (e) {
                        // Ignore selector errors
                    }
                });
                
                result.totalInputs = allInputs.length;
                
                allInputs.forEach(input => {
                    try {
                        const isVisible = input.offsetHeight > 0 && input.offsetWidth > 0 && 
                                         getComputedStyle(input).visibility !== 'hidden' && 
                                         getComputedStyle(input).display !== 'none';
                        
                        if (isVisible) {
                            result.visibleInputs++;
                            
                            const isInteractable = !input.disabled && !input.readOnly;
                            if (isInteractable) {
                                result.interactableInputs++;
                            }
                        }
                    } catch (e) {
                        // Skip problematic elements
                    }
                });
                
                return result;
            """)
            
            # Strategy 1 Success: 1+ interactable inputs OR 2+ visible inputs
            if input_analysis['interactableInputs'] >= 1 or input_analysis['visibleInputs'] >= 2:
                self.logger.info(f"Found {input_analysis['interactableInputs']} interactable inputs, {input_analysis['visibleInputs']} visible inputs - form content confirmed")
                return True
            
            # Strategy 2: Check for live form containers with actual content
            container_analysis = self.driver.execute_script("""
                const result = {
                    hasLiveAngularForms: false,
                    hasLiveContainers: false,
                    debugInfo: {
                        routerOutletContent: 0,
                        formSectionCount: 0
                    }
                };
                
                // Check Angular router-outlet has actual MEANINGFUL content
                const routerOutlet = document.querySelector('router-outlet');
                if (routerOutlet && routerOutlet.children.length > 0) {
                    result.debugInfo.routerOutletContent = routerOutlet.children.length;
                    
                    // Check if router-outlet or its descendants have meaningful content
                    const inputs = routerOutlet.querySelectorAll(`
                        input, select, textarea, button, [contenteditable],
                        kendo-datepicker, kendo-combobox, kendo-dropdownlist, kendo-multiselect,
                        accelify-date-picker, accelify-signature, accelify-rich-editor,
                        .k-editor, .k-checkbox, .k-radio
                    `);
                    const text = routerOutlet.textContent?.trim() || '';
                    
                    if (inputs.length > 0 || text.length > 50) {
                        result.hasLiveAngularForms = true;
                    }
                }
                
                // Check for actual form sections with content
                const formSections = document.querySelectorAll('accelify-form-section');
                result.debugInfo.formSectionCount = formSections.length;
                
                // Legacy form containers with controls
                const containerSelectors = [
                    'form',
                    '.form-container',
                    '.main-content',
                    '#pnlForm',
                    '#pnlEventContent'
                ];
                
                containerSelectors.forEach(selector => {
                    try {
                        const containers = document.querySelectorAll(selector);
                        containers.forEach(container => {
                            const isVisible = container.offsetHeight > 0 && container.offsetWidth > 0;
                            
                            if (isVisible) {
                                const controls = container.querySelectorAll(`
                                    input, select, textarea, button, [contenteditable],
                                    kendo-datepicker, kendo-combobox, kendo-dropdownlist, kendo-multiselect,
                                    accelify-date-picker, accelify-signature, accelify-rich-editor,
                                    .k-editor, .k-checkbox, .k-radio
                                `);
                                
                                const visibleControls = Array.from(controls).filter(ctrl => {
                                    return ctrl.offsetHeight > 0 && ctrl.offsetWidth > 0 && 
                                           getComputedStyle(ctrl).display !== 'none';
                                });
                                
                                if (visibleControls.length > 0) {
                                    result.hasLiveContainers = true;
                                }
                            }
                        });
                    } catch (e) {
                        // Ignore selector errors
                    }
                });
                
                return result;
            """)
            
            # Strategy 2 Success: Any live containers found
            if (container_analysis['hasLiveAngularForms'] or 
                container_analysis['hasLiveContainers']):
                
                debug_info = container_analysis['debugInfo']
                self.logger.info(f"Found live containers - Angular content: {debug_info['routerOutletContent']}, "
                               f"form sections: {debug_info['formSectionCount']} - form content confirmed")
                return True
            
            # Strategy 3: Dynamic content with actual wait and verification
            angular_check = self.driver.execute_script("""
                const result = {
                    hasAngular: false,
                    hasAsyncContent: false,
                    requiresWait: false
                };
                
                // Check for Angular
                result.hasAngular = !!(window.angular || window.ng || 
                                     document.querySelector('[ng-app], [data-ng-app], ng-component, [ng-controller]'));
                
                // Check for async content indicators
                const asyncSelectors = [
                    '[ng-if]', '[*ngIf]', '[v-if]',
                    '.async-content', '.lazy-load', '.dynamic-content'
                ];
                
                asyncSelectors.forEach(selector => {
                    try {
                        if (document.querySelector(selector)) {
                            result.hasAsyncContent = true;
                        }
                    } catch (e) {
                        // Ignore
                    }
                });
                
                result.requiresWait = result.hasAngular || result.hasAsyncContent;
                
                return result;
            """)
            
            # Strategy 3: Wait for dynamic content only if Angular detected
            if angular_check['requiresWait']:
                self.logger.info(f"Detected dynamic content (Angular: {angular_check['hasAngular']}, Async: {angular_check['hasAsyncContent']}) - waiting for rendering...")
                
                # Try up to 3 times with increasing delays
                for attempt in range(3):
                    time.sleep(attempt)
                    
                    # Check for actual rendered content
                    retry_result = self.driver.execute_script("""
                        const result = {
                            hasRealInputs: false,
                            hasLiveTabs: false,
                            inputCount: 0,
                            tabCount: 0
                        };
                        
                        // Check for real form inputs
                        const formInputs = document.querySelectorAll(`
                            input, select, textarea, button,
                            kendo-datepicker, kendo-combobox, kendo-dropdownlist, kendo-multiselect,
                            accelify-date-picker, accelify-signature,
                            .k-checkbox, .k-radio
                        `);
                        const visibleInputs = Array.from(formInputs).filter(elem => {
                            const rect = elem.getBoundingClientRect();
                            const style = window.getComputedStyle(elem);
                            return rect.width > 0 && rect.height > 0 && 
                                   style.visibility !== 'hidden' && 
                                   style.display !== 'none' && 
                                   !elem.disabled && !elem.readOnly;
                        });
                        
                        result.inputCount = visibleInputs.length;
                        result.hasRealInputs = result.inputCount > 0;
                        
                        // Check for live Kendo tabs
                        const tabs = document.querySelectorAll('.k-tabstrip-items li');
                        result.tabCount = tabs.length;
                        result.hasLiveTabs = result.tabCount > 0;
                        
                        return result;
                    """)
                    
                    if retry_result['hasRealInputs'] or retry_result['hasLiveTabs']:
                        self.logger.info(f"Dynamic content loaded after {attempt:.1f}s wait: {retry_result['inputCount']} inputs, {retry_result['tabCount']} tabs - form content confirmed")
                        return True
            
            # Final result: No valid form content detected
            self.logger.info(f"No form content found: {input_analysis['visibleInputs']} visible inputs, "
                f"{input_analysis['interactableInputs']} interactable inputs")
            
            # Strategy 4: Check for ACTUAL readonly content (data tables, reports)
            readonly_check = self.driver.execute_script("""
                const result = {
                    hasGrid: false,
                    hasReports: false,
                    dataRowCount: 0
                };
                
                // Check for data tables with actual content rows
                const tableSelectors = ['kendo-grid', '.k-grid', 'table[role="grid"]'];
                tableSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(element => {
                        if (element.offsetHeight > 0) {
                            result.hasGrid = true;                            
                            const dataRows = element.querySelectorAll('tr:not(.k-grid-norecords):not(.k-header)');
                            result.dataRowCount += Math.max(0, dataRows.length - 1);
                        }
                    });
                });
                
                // Check for report-like content (structured data displays)
                const reportSelectors = [
                    '.report-content',
                    '.data-display',
                    '.readonly-form',
                    '.form-display',
                    '[class*="report"]',
                    '[class*="summary"]'
                ];
                
                reportSelectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(element => {
                            if (element.offsetHeight > 0) {
                                const text = element.textContent || '';
                                const hasStructuredData = text.length > 50 &&
                                    (text.includes(':') || text.includes('|') || text.includes('\t'));
                                
                                if (hasStructuredData) {
                                    result.hasReports = true;
                                }
                            }
                        });
                    } catch (e) {
                        // Ignore selector errors
                    }
                });
                
                return result;
            """)
            
            if readonly_check['hasGrid'] or readonly_check['hasReports']:
                self.logger.info(f"Found readonly content: {readonly_check['dataRowCount']} data rows, reports: {readonly_check['hasReports']}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Form content check failed: {e}")
            return False
    
    def measure_page_load(self, url, loops):
        try:
            times = []
            payload_size = 0.0  # calculate only once 
            
            for i in range(loops):
                # clear Performance API before each measurement
                self.driver.execute_script("performance.clearResourceTimings();")
                
                if i == 0:
                    if self.driver.current_url != url:
                        self.driver.get(url)
                else:
                    self.driver.refresh()

                measure_start = time.time()
                
                # Wait for complete page and content readiness
                self._wait_for_content_ready()
                
                # Wait for API requests to complete
                self._wait_for_api_requests_complete(url)
                
                load_time = time.time() - measure_start
                
                # Calculate payload ONLY for first measurement (cleanest data)
                if i == 0:
                    payload_size = self._calculate_payload_size(url)
                
                validation_result = self._validate_page_after_load()
                
                if not validation_result['success']:
                    self.logger.error(f"Page validation failed on measurement {i+1}: {validation_result['error']}")
                    error_type = validation_result.get('error_type', Config.ErrorTypes.FORM_LOAD_ERROR)
                    return MeasurementResult(
                        success=False,
                        error_type=error_type,
                        error_message=validation_result['error']
                    )
                
                times.append(load_time)
                self.logger.info(f"Load {i+1}/{loops}: {load_time:.1f}s")
            
            return MeasurementResult(
                success=True,
                first_measure=times[0],
                min_time=min(times),
                max_time=max(times),
                mean_time=sum(times) / len(times),
                payload_size=payload_size
            )
            
        except Exception as e:
            self.logger.error(f"Page load measurement failed: {str(e)}")
            error_type, error_message = ErrorClassifier.classify_load_error(str(e))
            return MeasurementResult(success=False, error_type=error_type, error_message=error_message)

    def _validate_page_after_load(self):
        try:
            if not self._check_for_form_content(self.driver.current_url):
                return {
                    'success': False, 
                    'error': "No form content detected"
                }
            
            errors = self._check_for_errors()
            if errors:
                error_type, error_message = ErrorClassifier.classify_load_error(errors[0])
                return {
                    'success': False,
                    'error': error_message,
                    'error_type': error_type
                }
            
            return {'success': True, 'error': None}
            
        except Exception as e:
            error_type, error_message = ErrorClassifier.classify_load_error(str(e))
            return {
                'success': False,
                'error': error_message,
                'error_type': error_type
            }
    
    def measure_save_time(self, url, loops):
        """
        Flow:
        1. Finding Save button
        2. Fill required form fields if needed
        3. Find Save button (with 20-second retry logic)
        4. Click Save and measure time
        5. Wait for success popup or completion
        6. Check errors during save
        """
        try:
            self.logger.info("Starting save measurement")          
            
            # STEP 1: Find Save button with 20-second wait (page might render dynamically)
            save_button = self._find_save_button_with_wait()
            
            if not save_button:
                self.logger.info("No Save button found")
                return MeasurementResult(
                    success=True,
                    error_type=None,
                    error_message="No Save button found on this form",
                    first_measure=0.0,
                    min_time=0.0,
                    max_time=0.0,
                    mean_time=0.0
                )
            
            self._fill_required_fields_if_needed()
            
            self._click_save_button_reliably(save_button)

            save_start_time = time.time()

            SeleniumHelper.wait_for_form_save_popup(self.driver)
            
            save_elapsed_time = time.time() - save_start_time
            
            self.logger.info(f"Save completed successfully in {save_elapsed_time:.1f}s")
            
            return MeasurementResult(
                success=True,
                error_type=None,
                error_message="",
                first_measure=save_elapsed_time,
                min_time=save_elapsed_time,
                max_time=save_elapsed_time,
                mean_time=save_elapsed_time
            )
            
        except Exception as e:
            error_msg = str(e).strip()
            if not error_msg:
                error_msg = f"Unknown error during save: {type(e).__name__}"
            self.logger.error(f"Save measurement failed. {error_msg}")

            error_type, error_message = ErrorClassifier.classify_save_error(e)
            return MeasurementResult(
                success=False, 
                error_type=error_type, 
                error_message=error_message
            )
    
    def _wait_for_content_ready(self, timeout: int = 10) -> bool:
        end_time = time.time() + timeout
        poll_interval = 0.1
        
        # Phase 1: Wait for document ready
        while time.time() < end_time:
            try:
                if self.driver.execute_script("return document.readyState") == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.1)
        
        # Phase 2: Wait for content stability
        consecutive_stable_checks = 0
        required_stable_checks = 3
        
        while time.time() < end_time:
            try:
                debug_info = self.driver.execute_script("""
                    const result = {
                        foundLoaders: [],
                        hasContent: false,
                        contentCount: 0
                    };
                    
                    // Check each loading selector individually
                    const loadingSelectors = [
                        '.loading', '.spinner', '.k-loading-mask', 
                        '.blockUI', '.loading-wrapper', '.loading-overlay',
                        '.loading-spinner', '.content-loading', '.page-loading',
                        '[data-loading="true"]', '[aria-busy="true"]'
                    ];
                    
                    for (const selector of loadingSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (el.offsetHeight > 0 && el.offsetWidth > 0) {
                                result.foundLoaders.push({
                                    selector: selector,
                                    text: el.textContent?.trim() || '',
                                    classes: el.className
                                });
                            }
                        }
                    }
                    
                    // Content check
                    const contentElements = document.querySelectorAll('input, button, select, textarea');
                    result.contentCount = contentElements.length;
                    result.hasContent = contentElements.length > 0;
                    
                    return result;
                """)
                
                if not debug_info['foundLoaders'] and debug_info['hasContent']:
                    consecutive_stable_checks += 1
                    if consecutive_stable_checks >= required_stable_checks:
                        self.logger.debug(f"Content ready after {time.time() - (end_time - timeout):.1f}s")
                        
                        # Phase 3: Wait for Angular stability if detected
                        if self._wait_for_angular_stability():
                            self.logger.debug("Angular stability achieved")
                        
                        # Phase 4: Wait for visual rendering completion
                        # TODO: probably this part of code is not reliable, we should use a more reliable way to check if the page is ready
                        # TODO: also, we should not wait for visual readiness, we should wait for the page to be fully loaded
                        if self._wait_for_visual_readiness(2):
                            self.logger.debug("Visual readiness achieved")
                            return True
                        else:
                            self.logger.debug("Visual readiness timeout - continuing anyway")
                            return True
                else:
                    consecutive_stable_checks = 0
                    # Detailed logging
                    if debug_info['foundLoaders']:
                        loader_info = debug_info['foundLoaders'][0]  # First found loader
                        self.logger.debug(f"Content not ready: found loader '{loader_info['selector']}' with classes '{loader_info['classes']}'")
                    else:
                        self.logger.debug(f"Content not ready: no content (found {debug_info['contentCount']} elements)")
                    
            except Exception as e:
                self.logger.debug(f"Content readiness check failed: {e}")
                consecutive_stable_checks = 0
                
            time.sleep(poll_interval)
        
        self.logger.debug(f"Content ready timeout after {timeout}s")
        return False  # Timeout reached
    
    def _wait_for_visual_readiness(self, timeout: int = 3) -> bool:
        """Wait for visual rendering completion using multiple indicators"""
        end_time = time.time() + timeout
        previous_metrics = None
        
        while time.time() < end_time:
            try:
                current_metrics = self.driver.execute_script("""
                    const result = {
                        domNodeCount: document.querySelectorAll('*').length,
                        visibleElements: 0,
                        hasTransitions: false,
                        hasAnimations: false,
                        pendingImages: 0,
                        stylesheetsPending: false
                    };
                    
                    // Count visible elements
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && 
                            el.offsetWidth > 0 && el.offsetHeight > 0) {
                            result.visibleElements++;
                            
                            // Check for ongoing transitions/animations
                            if (style.transition !== 'none' && style.transition !== '') {
                                result.hasTransitions = true;
                            }
                            if (style.animation !== 'none' && style.animation !== '') {
                                result.hasAnimations = true;
                            }
                        }
                    });
                    
                    // Check for pending images
                    const images = document.querySelectorAll('img');
                    images.forEach(img => {
                        if (!img.complete || img.naturalHeight === 0) {
                            result.pendingImages++;
                        }
                    });
                    
                    // Check stylesheets
                    const styleSheets = document.styleSheets;
                    for (let i = 0; i < styleSheets.length; i++) {
                        try {
                            // If we can access cssRules, the stylesheet is loaded
                            const rules = styleSheets[i].cssRules;
                        } catch (e) {
                            if (e.name === 'InvalidAccessError') {
                                // Cross-origin, but loaded
                                continue;
                            }
                            result.stylesheetsPending = true;
                            break;
                        }
                    }
                    
                    return result;
                """)
                
                # Check if metrics are stable (no changes between checks)
                if previous_metrics:
                    metrics_stable = (
                        current_metrics['domNodeCount'] == previous_metrics['domNodeCount'] and
                        current_metrics['visibleElements'] == previous_metrics['visibleElements'] and
                        current_metrics['pendingImages'] == 0 and
                        not current_metrics['stylesheetsPending'] and
                        not current_metrics['hasTransitions'] and
                        not current_metrics['hasAnimations']
                    )
                    
                    if metrics_stable:
                        return True
                
                previous_metrics = current_metrics
                
            except Exception as e:
                self.logger.debug(f"Visual readiness check failed: {e}")
                return True  # Assume ready on error
            
            time.sleep(0.1)  # Check every 200ms
        
        return False  # Timeout reached
    
    def _wait_for_angular_stability(self, timeout: int = 3) -> bool:
        """Wait for Angular to finish rendering and stabilize"""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                angular_check = self.driver.execute_script("""
                    const result = {
                        hasAngular: false,
                        isStable: false,
                        hasAsyncContent: false
                    };
                    
                    // Check for Angular presence
                    result.hasAngular = !!(window.angular || window.ng || 
                                         document.querySelector('[ng-app], [data-ng-app], ng-component, [ng-controller]'));
                    
                    if (!result.hasAngular) {
                        result.isStable = true; // No Angular = stable
                        return result;
                    }
                    
                    // Check Angular stability
                    try {
                        if (window.angular) {
                            // AngularJS
                            const rootScope = angular.element(document).scope()?.$root;
                            if (rootScope) {
                                result.isStable = !rootScope.$$phase && 
                                                (rootScope.$$pendingRequests?.length || 0) === 0;
                            } else {
                                result.isStable = true; // Fallback if scope not accessible
                            }
                        } else if (window.ng && window.ng.getTestability) {
                            // Angular 2+
                            result.isStable = window.ng.getTestability(document.body).isStable();
                        } else {
                            result.isStable = true; // Fallback if testability not available
                        }
                    } catch(e) {
                        result.isStable = true; // Assume stable if we can't check
                    }
                    
                    // Check for async content indicators that might still be loading
                    const asyncSelectors = [
                        '[ng-if]', '[*ngIf]', '[v-if]',
                        '.async-content', '.lazy-load', '.dynamic-content',
                        '.skeleton', '.loading-skeleton', '[class*="skeleton"]'
                    ];
                    
                    for (const selector of asyncSelectors) {
                        try {
                            const elements = document.querySelectorAll(selector);
                            const visibleElements = Array.from(elements).filter(el => 
                                el.offsetHeight > 0 && el.offsetWidth > 0
                            );
                            if (visibleElements.length > 0) {
                                result.hasAsyncContent = true;
                                break;
                            }
                        } catch (e) {
                            // Ignore selector errors
                        }
                    }
                    
                    return result;
                """)
                
                if not angular_check['hasAngular']:
                    return True  # No Angular detected, consider stable
                
                if angular_check['isStable'] and not angular_check['hasAsyncContent']:
                    return True  # Angular is stable and no async content loading
                
            except Exception as e:
                self.logger.debug(f"Angular stability check failed: {e}")
                return True  # Assume stable on error
            
            time.sleep(0.1)
        
        self.logger.debug(f"Angular stability timeout after {timeout}s")
        return True  # Continue anyway after timeout
    
    def _fill_required_fields_if_needed(self):
        try:
            from frontline_selenium.selenium_helper import SeleniumHelper
            if hasattr(SeleniumHelper, 'options') and SeleniumHelper.options.get("disable_filler", False):
                return
                
            from frontline_selenium.page_filler import PageFormFiller
            PageFormFiller.fill_form(self.driver)
            
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"Form filling failed (continuing anyway): {str(e)}")
    
    def _find_save_button_with_wait(self, max_attempts=20, delay=0.5):
        """
        Find Save button with smart retry logic
        Total max time: 20 * 0.5 = 10 sec
        """        
        # All selectors
        save_button_selectors = [
            "#btnUpdateForm",                    # Most common ID
            "button[type='submit']",             # Generic submit
            ".k-button[type='submit']",          # Kendo UI submit button
            "button.k-button",                   # Any Kendo button
            "button[kendobutton]",               # Kendo button directive
            "button.k-button-solid",             # Kendo solid button
            "input[type='submit'][value*='Save']", # Input with Save text
            "button.ng-star-inserted[type='submit']", # Angular dynamic button
        ]
        
        # XPath selectors
        save_button_xpaths = [
            "//button[contains(text(), 'Save')]",
            "//button[contains(text(), 'Update')]", 
            "//button[.//span[contains(text(), 'Save')]]",  # For Angular <span> inside button
            "//button[@kendobutton and .//span[contains(text(), 'Save')]]",  # Kendo + span
            "//input[@type='submit' and contains(@value, 'Save')]"
        ]
        
        for attempt in range(1, max_attempts + 1):
            # Strategy 1: Try CSS selectors
            for selector in save_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_text = element.text.strip() or element.get_attribute('value') or ''
                            if self._is_save_button(button_text):
                                return element
                except Exception:
                    continue
            
            # Strategy 2: Try XPath selectors
            for xpath in save_button_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_text = element.text.strip() or element.get_attribute('value') or ''
                            if self._is_save_button(button_text):
                                return element
                except Exception:
                    continue
            
            # Strategy 3: JavaScript search
            try:
                save_button = self.driver.execute_script("""
                    // Look for Save buttons using JavaScript
                    var buttons = document.querySelectorAll('button, input[type="submit"]');
                    
                    for (var i = 0; i < buttons.length; i++) {
                        var button = buttons[i];
                        
                        // Check if button is visible
                        if (button.offsetHeight > 0 && button.offsetWidth > 0) {
                            var text = (button.textContent || button.innerText || button.value || '').toLowerCase();
                            
                            // Look for Save keywords
                            if (text.includes('save') || text.includes('update')) {
                                // Exclude unwanted buttons
                                if (!text.includes('cancel') && !text.includes('close') && 
                                    !text.includes('back') && !text.includes('delete')) {
                                    return button;
                                }
                            }
                        }
                    }
                    
                    return null;
                """)
                
                if save_button:
                    return save_button
                    
            except Exception:
                pass
            
            if attempt < max_attempts:
                time.sleep(delay)
        
        return None
    
    def _is_save_button(self, button_text):
        if not button_text:
            return False
        
        text_lower = button_text.lower()
        
        save_keywords = ['save', 'update', 'submit']
        has_save_keyword = any(keyword in text_lower for keyword in save_keywords)
        
        exclude_keywords = ['cancel', 'close', 'back', 'previous', 'next', 'delete']
        has_exclude_keyword = any(keyword in text_lower for keyword in exclude_keywords)
        
        return has_save_keyword and not has_exclude_keyword
    
    def _click_save_button_reliably(self, save_button):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException

        def _safe_click(element):
            try:
                element.click()
                return True
            except ElementClickInterceptedException:
                # Covered below by JS click
                return False
            except StaleElementReferenceException:
                return False
            except Exception:
                return False

        # Try up to 3 attempts: normal click → JS click → re-find & JS click
        for attempt in range(3):
            try:
                # Ensure (new) button is clickable
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(save_button))
            except StaleElementReferenceException:
                # Re-locate button if it became stale during wait
                save_button = self._find_save_button_with_wait(max_attempts=10, delay=0.2)
                if not save_button:
                    break
            
            # Scroll into view (element might be detached, ignore errors)
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
            except Exception:
                pass
            
            # 1. Native click
            if _safe_click(save_button):
                return
            
            # 2. Fallback JS click
            try:
                self.driver.execute_script("arguments[0].click();", save_button)
                return
            except Exception:
                # Re-locate and retry next loop
                save_button = self._find_save_button_with_wait(max_attempts=2, delay=0.25)
                if not save_button:
                    break

        # If we reached here, all click attempts failed
        raise Exception("Failed to click Save button after multiple attempts")
  
    def _wait_for_api_requests_complete(self, url):
        """Wait only for API requests to complete (not static resources)"""
        try:
            start_time = time.time()
            max_wait = 5.0
            current_domain = self._extract_domain_from_url(url)
            
            while time.time() - start_time < max_wait:
                pending_api_requests = self.driver.execute_script("""
                    try {
                        var currentDomain = arguments[0];
                        var pendingApiCount = 0;
                        var totalApiCount = 0;
                        
                        var entries = performance.getEntriesByType('resource');
                        
                        entries.forEach(function(entry) {
                            var requestUrl = entry.name || '';
                            
                            // Get request domain
                            var requestDomain = '';
                            try {
                                var urlObj = new URL(requestUrl);
                                requestDomain = urlObj.hostname.toLowerCase();
                            } catch(e) {
                                return; // Skip invalid URLs
                            }
                            
                            // Only check requests to our domain
                            if (requestDomain === currentDomain) {
                                // Only count API requests
                                var isApiRequest = requestUrl.includes('/api/');
                                
                                if (isApiRequest) {
                                    totalApiCount++;
                                    if (entry.responseEnd === 0) {
                                        pendingApiCount++;
                                    }
                                }
                            }
                        });
                        
                        return {
                            pendingCount: pendingApiCount,
                            totalApiCount: totalApiCount,
                            success: true
                        };
                    } catch(e) {
                        return {success: false, error: e.toString()};
                    }
                """, current_domain)
                
                if not pending_api_requests.get('success'):
                    break
                    
                pending_count = pending_api_requests.get('pendingCount', 0)
                total_api_count = pending_api_requests.get('totalApiCount', 0)
                
                if pending_count == 0:
                    elapsed = time.time() - start_time
                    return True
                    
                time.sleep(0.2)
            
            # Timeout
            elapsed = time.time() - start_time
            self.logger.debug(f"API request wait timeout after {elapsed:.2f}s")
            return True  # Continue anyway
            
        except Exception as e:
            return True

    def _extract_domain_from_url(self, url):
        """Extract domain from URL for payload matching"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname.lower() if parsed.hostname else ''
        except Exception as e:
            self.logger.debug(f"Failed to extract domain from {url}: {e}")
            return ''
    
    def _check_for_errors(self):
        errors = []
        
        try:
            # 1. Check for visible error popups/notifications
            popup_errors = self.driver.execute_script("""
                var errors = [];
                var errorSelectors = [
                    '.k-notification-error',
                    '.k-widget.k-notification.k-notification-error',
                    '[role="alert"]',
                    '.alert-danger',
                    '.error-message',
                    '.error-popup',
                    '.popup-error'
                ];
                
                errorSelectors.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        for (var i = 0; i < elements.length; i++) {
                            var el = elements[i];
                            if (el.offsetHeight > 0 && el.offsetWidth > 0) {
                                var text = el.textContent || el.innerText || '';
                                if (text.toLowerCase().includes('error') || 
                                    text.toLowerCase().includes('occurred') ||
                                    text.toLowerCase().includes('500') ||
                                    text.toLowerCase().includes('internal server') ||
                                    text.toLowerCase().includes('server error')) {
                                    errors.push('Page showed error: ' + text.substring(0, 100));
                                    break;
                                }
                            }
                        }
                    } catch(e) {
                        // Skip invalid selectors
                    }
                });
                
                // 2. ENHANCED: Check for error text ANYWHERE on the page
                try {
                    var pageText = document.body.innerText || document.body.textContent || '';
                    var lowerPageText = pageText.toLowerCase();
                    
                    // PRIORITY: Check for HTTP 503 Service Unavailable (server down)
                    if (lowerPageText.includes('HTTP Error 503. The Service is unavalible')) {
                        errors.push('Service Unavailable (HTTP 503) - Server is down');
                        return errors;  // Return immediately for server down
                    }
                    
                    // Check for 404 Not Found errors first
                    if (lowerPageText.includes('not found error') || 
                        (lowerPageText.includes('error 404') && lowerPageText.includes('not found'))) {
                        errors.push('Not Found Error');
                        return errors;  // Return immediately for 404 errors
                    }
                    
                    // Common error messages to look for
                    var errorMessages = [
                        'an error has occurred',
                        'an error occurred',
                        'sorry for inconvenience',
                        'contact the site administrator',
                        'internal server error',
                        'server error occurred',
                        'unexpected error',
                    ];
                    
                    for (var i = 0; i < errorMessages.length; i++) {
                        if (lowerPageText.includes(errorMessages[i])) {
                            // Return standardized message for managers instead of raw context
                            errors.push('Page showed error: An error has occurred on the page you were requesting.Sorry for inconvenience.If this problem persists, please contact the site administrator');
                            break; // Only report first error found
                        }
                    }
                } catch(textError) {
                    // Ignore text search errors
                }
                
                return errors;
            """)

            if popup_errors:
                errors.extend(popup_errors)

            # 3. Check for HTTP errors via Performance API (only frontline api need)
            http_errors = self.driver.execute_script("""
                var errors = [];
                var failedRequests = [];  // Store request details
                try {
                    var entries = performance.getEntriesByType('resource');

                    entries.forEach(function(entry) {
                        // Only check URLs that contain frontlineeducation.com
                        var url = entry.name.toLowerCase();
                        if (url.includes('frontlineeducation.com')) {
                            // Check for HTTP 500+ errors
                            if (entry.responseStatus >= 500) {
                                errors.push({
                                    message: 'HTTP ' + entry.responseStatus + ' error: ' + entry.name,
                                    requestDetails: {
                                        fullUrl: entry.name,
                                        status: entry.responseStatus,
                                        duration: entry.duration
                                    }
                                });
                            }
                            // Also check for failed requests (responseStatus might be 0) - but only for API endpoints
                            else if (entry.responseStatus === 0 && entry.responseEnd > 0 && 
                                    (url.includes('/api/') || url.includes('/plan/api/') || url.includes('/planng/api/'))) {
                                var isCancelledRequest = (
                                    entry.responseStart === 0 ||           // No response started
                                    entry.transferSize === 0 ||            // No data transferred
                                    (entry.duration > 0 && entry.duration < 1) // Very short duration suggests cancellation
                                );
                                
                                if (!isCancelledRequest) {
                                    // API requests with status 0 often indicate server errors
                                    errors.push({
                                        message: 'Failed API request (possible network error): ' + entry.name,
                                        requestDetails: {
                                            fullUrl: entry.name,
                                            status: 0,
                                            duration: entry.duration
                                        }
                                    });
                                }
                            }
                        }
                    });
                    
                } catch(e) {
                    // Performance API not available
                }
                return {errors: errors};
            """)

            if http_errors and http_errors.get('errors'):
                # Log each failed request
                for error in http_errors['errors']:
                    if isinstance(error, dict) and 'requestDetails' in error:
                        self._log_server_error_request(error['requestDetails'])
                
                # Extract error messages for return
                error_messages = []
                for error in http_errors['errors']:
                    if isinstance(error, dict):
                        error_messages.append(error['message'])
                    else:
                        error_messages.append(error)
                
                errors.extend(error_messages)
                
        except Exception as e:
            self.logger.debug(f"Error checking failed: {e}")
        
        return errors
    
    def _calculate_payload_size(self, url):
        try:
            current_domain = self._extract_domain_from_url(url)
            
            # Get network performance data via JS
            payload_data = self.driver.execute_script("""
                try {
                    var currentDomain = arguments[0];
                    var totalSize = 0;
                    var apiRequestCount = 0;
                    var debugInfo = [];
                    
                    // Get all network requests from Performance API
                    var entries = performance.getEntriesByType('resource');
                    
                    entries.forEach(function(entry) {
                        var requestUrl = entry.name || '';
                        var size = 0;
                        
                        // Calculate request size - NETWORK TRANSFER PRIORITY
                        if (entry.transferSize && entry.transferSize > 0) {
                            size = entry.transferSize;
                        } else if (entry.decodedBodySize && entry.decodedBodySize > 0) {
                            size = entry.decodedBodySize;
                        } else if (entry.encodedBodySize && entry.encodedBodySize > 0) {
                            size = entry.encodedBodySize;
                        }
                        
                        // Check if this request is from the same domain as the form
                        var requestDomain = '';
                        try {
                            var urlObj = new URL(requestUrl);
                            requestDomain = urlObj.hostname.toLowerCase();
                        } catch(e) {
                            return; // Skip invalid URLs
                        }
                        
                        // DEBUG: Log all requests to our domain
                        if (requestDomain === currentDomain) {
                            var isStaticResource = (
                                requestUrl.endsWith('.css') ||
                                requestUrl.endsWith('.js') ||
                                requestUrl.endsWith('.png') ||
                                requestUrl.endsWith('.jpg') ||
                                requestUrl.endsWith('.jpeg') ||
                                requestUrl.endsWith('.gif') ||
                                requestUrl.endsWith('.svg') ||
                                requestUrl.endsWith('.ico') ||
                                requestUrl.endsWith('.woff') ||
                                requestUrl.endsWith('.woff2') ||
                                requestUrl.endsWith('.ttf') ||
                                requestUrl.endsWith('.eot') ||
                                requestUrl.includes('/Content/') ||
                                requestUrl.includes('/Scripts/') ||
                                requestUrl.includes('/fonts/') ||
                                requestUrl.includes('/images/')
                            );
                            
                            // Only count API requests (not all non-static requests)
                            var isApiRequest = requestUrl.includes('/api/');
                            
                            debugInfo.push({
                                url: requestUrl,
                                transferSize: entry.transferSize || 0,
                                decodedBodySize: entry.decodedBodySize || 0,
                                encodedBodySize: entry.encodedBodySize || 0,
                                size: size,
                                isStatic: isStaticResource,
                                isApi: isApiRequest,
                                responseEnd: entry.responseEnd,
                                included: isApiRequest && size > 0
                            });
                            
                            // Count only API requests
                            if (isApiRequest && size > 0) {
                                totalSize += size;
                                apiRequestCount++;
                            }
                        }
                    });
                    
                    return {
                        totalSize: totalSize,
                        apiRequestCount: apiRequestCount,
                        debugInfo: debugInfo,
                        totalEntries: entries.length,
                        success: true
                    };
                    
                } catch (error) {
                    return {
                        totalSize: 0,
                        apiRequestCount: 0,
                        debugInfo: [],
                        totalEntries: 0,
                        success: false,
                        error: error.toString()
                    };
                }
            """, current_domain)
            
            if not payload_data or not payload_data.get('success', False):
                return 0.0
            
            total_bytes = payload_data.get('totalSize', 0)
            request_count = payload_data.get('apiRequestCount', 0)
            
            if total_bytes == 0:
                return 0.0
            
            # Convert bytes to KB
            total_kb = total_bytes / 1024.0
            
            self.logger.info(f"Payload analysis: {total_kb:.1f} KB from {request_count} API requests")
            
            return round(total_kb, 1)
            
        except Exception as e:
            self.logger.warning(f"Payload size calculation failed: {str(e)}")
            return 0.0

    def _log_server_error_request(self, request_details):
        """Log details of server error"""
        full_url = request_details.get('fullUrl', 'unknown')
        status = request_details.get('status', 'unknown')
        duration = request_details.get('duration', 0)
        
        form_data = self._get_form_data_for_logging()
        has_payload = form_data and form_data != "{}"
        
        # payload = POST, no payload = GET
        http_method = 'POST' if has_payload else 'GET' 
        
        self.logger.error(f"Server error: {http_method} {full_url} - HTTP {status} (took {duration/1000:.1f}s)")
        
        if http_method == 'POST' and form_data:
            self.logger.error(f"POST payload: {form_data}")

    def _get_form_data_for_logging(self):
        """Get form data for logging"""
        try:
            return self.driver.execute_script("""
                var formData = {};
                var inputs = document.querySelectorAll('input, select, textarea');
                
                for (var i = 0; i < inputs.length; i++) {
                    var input = inputs[i];
                    if (input.value) {
                        var name = input.name || input.id || 'field_' + i;
                        formData[name] = input.value;
                    }
                }
                
                return JSON.stringify(formData);
            """)
        except:
            return None


class ExcelResultWriter:
    @staticmethod
    def reset_row_values(row):
        # Clear values
        measurement_columns = [            
            Config.ExcelColumns.ERROR_MESSAGE,
            Config.ExcelColumns.PAYLOAD_SIZE,
            Config.ExcelColumns.LOAD_FIRST,
            Config.ExcelColumns.LOAD_MIN,
            Config.ExcelColumns.LOAD_MAX,
            Config.ExcelColumns.LOAD_MEAN,
            Config.ExcelColumns.SAVE_FIRST,
            Config.ExcelColumns.SAVE_MIN,
            Config.ExcelColumns.SAVE_MAX,
            Config.ExcelColumns.SAVE_MEAN
        ]
        
        for col_idx in measurement_columns:
            row[col_idx].value = ""
            row[col_idx].font = Font(color="000000")
            row[col_idx].fill = PatternFill()
        
        row[Config.ExcelColumns.TIMESTAMP].font = Font(color="000000")
        row[Config.ExcelColumns.TIMESTAMP].fill = PatternFill()

    @staticmethod
    def write_load_result(row, result):
        """Write load measurement result to Excel row"""
        if result.success:
            ExcelResultWriter._write_times(row, result, [Config.ExcelColumns.LOAD_FIRST, Config.ExcelColumns.LOAD_MIN, Config.ExcelColumns.LOAD_MAX, Config.ExcelColumns.LOAD_MEAN])
            ExcelResultWriter._write_payload_size(row, result)
        else:
            ExcelResultWriter._write_error(row, result)
            ExcelResultWriter._clear_load_columns(row)
            ExcelResultWriter._clear_payload_column(row)
    
    @staticmethod
    def write_save_result(row, result):
        """Write save measurement result to Excel row"""
        if result.success:
            if "No Save button found" in result.error_message:
                ExcelResultWriter._clear_save_columns(row)
                row[Config.ExcelColumns.ERROR_MESSAGE].value = "No Save button found"
            else:
                ExcelResultWriter._write_times(row, result, [Config.ExcelColumns.SAVE_MIN, Config.ExcelColumns.SAVE_MAX, Config.ExcelColumns.SAVE_MEAN])
                row[Config.ExcelColumns.ERROR_MESSAGE].value = ""
        else:
            ExcelResultWriter._write_error(row, result)
            ExcelResultWriter._clear_save_columns(row)
    
    @staticmethod
    def _write_times(row, result, columns):
        """Write measurement times to specified columns"""
        times = [result.first_measure, result.min_time, result.max_time, result.mean_time]
        for i, col_idx in enumerate(columns):
            if i < len(times):
                row[col_idx].value = f"{times[i]:.{Config.LOAD_TIME_DECIMAL_PLACES}f}"
    
    @staticmethod
    def _write_fallback_times(row, result, columns):
        """Write timeout values for fallback cases"""
        timeout_val = Config.DEFAULT_TIMEOUT
        for col_idx in columns:
            row[col_idx].value = f"{timeout_val:.{Config.LOAD_TIME_DECIMAL_PLACES}f}"
    
    @staticmethod
    def _write_error(row, result):
        """Write error message and apply appropriate formatting"""
        row[Config.ExcelColumns.ERROR_MESSAGE].value = result.error_message
        
        color_map = {
            Config.ErrorTypes.TIMEOUT_ERROR: Config.Colors.RED,
            Config.ErrorTypes.FORM_LOAD_ERROR: Config.Colors.RED,
            Config.ErrorTypes.API_ERROR: Config.Colors.RED,
            Config.ErrorTypes.NETWORK_ERROR: Config.Colors.RED,
            Config.ErrorTypes.TECHNICAL_ERROR: Config.Colors.PURPLE,
            Config.ErrorTypes.TIMEOUT: Config.Colors.RED,
            Config.ErrorTypes.FALLBACK: Config.Colors.RED,
            Config.ErrorTypes.ELEMENT_NOT_FOUND: Config.Colors.ORANGE,
            Config.ErrorTypes.TECHNICAL: Config.Colors.PURPLE,
            Config.ErrorTypes.SERVER_DOWN: Config.Colors.RED,  # NEW: Red for server down
            Config.ErrorTypes.READONLY: None  # No coloring for readonly. DO WE HAVE THIS?
        }
        
        color = color_map.get(result.error_type, Config.Colors.PURPLE)
        if color:
            mark_form_as_invalid(row, color)
    
    @staticmethod
    def _clear_save_columns(row):
        """Clear save time columns"""
        for col_idx in [Config.ExcelColumns.SAVE_MIN, Config.ExcelColumns.SAVE_MAX, Config.ExcelColumns.SAVE_MEAN]:
            row[col_idx].value = ""

    @staticmethod
    def _clear_load_columns(row):
        """Clear load time columns"""
        for col_idx in [Config.ExcelColumns.LOAD_FIRST, Config.ExcelColumns.LOAD_MIN, Config.ExcelColumns.LOAD_MAX, Config.ExcelColumns.LOAD_MEAN]:
            row[col_idx].value = ""

    @staticmethod
    def _write_payload_size(row, result):
        """Write payload size to Excel row with color coding for critical sizes"""
        if result.payload_size > 0:
            row[Config.ExcelColumns.PAYLOAD_SIZE].value = f"{result.payload_size:.1f} KB"
            
            if result.payload_size > Config.PAYLOAD_SIZE_THRESHOLD:
                row[Config.ExcelColumns.PAYLOAD_SIZE].font = Font(color=Config.Colors.RED)
            else:
                row[Config.ExcelColumns.PAYLOAD_SIZE].font = Font(color="000000")
        else:
            row[Config.ExcelColumns.PAYLOAD_SIZE].value = "N/A"
            row[Config.ExcelColumns.PAYLOAD_SIZE].font = Font(color="000000")
    
    @staticmethod
    def _clear_payload_column(row):
        row[Config.ExcelColumns.PAYLOAD_SIZE].value = ""
        row[Config.ExcelColumns.PAYLOAD_SIZE].font = Font(color="000000")


class HideBacktraceFormatter(logging.Formatter):
    def formatException(self, exc_info):
        tb = super().formatException(exc_info)
        return HideBacktraceFormatter.removeBackTrace(tb)
    
    def format(self, record: logging.LogRecord):
        record.msg = HideBacktraceFormatter.removeBackTrace(record.msg)
        return super().format(record)
    
    @staticmethod
    def removeBackTrace(record):
        tb_lines = str(record).splitlines()
        filtered_tb_lines = []
        skip_slce = False
        for line in tb_lines:
            if "Backtrace:" in line:
                skip_slce = True
            if "Traceback (most recent call last):" in line:
                skip_slce = False
            if not skip_slce:
                filtered_tb_lines.append(line)
        return "\n".join(filtered_tb_lines)
    
    
def split_path(path):
    folders = []
    head, tail = os.path.split(path)
    
    while tail:
        folders.insert(0, tail)
        head, tail = os.path.split(head)
    return folders


def is_excel_file_opened(filename):
    try:
        wb = load_workbook(filename)
        wb.save(filename)
        return False
    except Exception as e:
        logger.error(e)
        return True


def extract_base_url(url):
    url_parts = urlparse(url)
    return f"{url_parts.scheme}://{url_parts.netloc}"


def mark_form_as_invalid(row, color=None):
    if color is None:
        color = Config.Colors.RED
    for cell in row:
        cell.font = Font(color=color)


def measure_network_speed():
    try:
        st = speedtest.Speedtest()
        return round(st.download() / 1000000, 2)
    except:
        return -1


def specify_sheet_layout(sheet):
    sheet.move_range("N1:N1", rows=0, cols=9)
    sheet.move_range("E1:E1", rows=0, cols=9)
    sheet.move_range("N2:N2", rows=0, cols=9)
    sheet.move_range("E2:E2", rows=0, cols=9)


def reset_styles(cells):
    for cell in cells:
        cell.style = "Normal"
        cell.fill = PatternFill(fill_type=None)
        cell.font = Font(color="000000")  # Black text


def flag_high_load_time(cells, threshold):
    for cell in cells:
        if cell.value != None and cell.value != "":
            try:
                # Only flag if it's actually a number and above threshold
                time_value = float(cell.value)
                if time_value > threshold:
                    cell.font = Font(color=Config.Colors.RED)
            except (ValueError, TypeError):
                # If it's not a number (like error text), set to black
                cell.font = Font(color="000000")


def compare_measures(curr_cell, prev_cell, diff_cell):
    if curr_cell.value == None or prev_cell.value == None:
        reset_styles([curr_cell, prev_cell, diff_cell])
        return

    prev_row_float = 0.0
    try:
        prev_row_float = float(prev_cell.value[:prev_cell.value.index("(")])
    except:
        prev_row_float = float(prev_cell.value)

    try:
        diff = float(curr_cell.value) / prev_row_float
    except:
        diff = 0
    growth = (diff * 100) - 100
    diff_cell.value = f"{abs(growth):.2f}%"
    if growth < -10:
        diff_cell.fill = PatternFill(start_color=Config.Colors.GREEN, fill_type="solid")
    elif growth <= 10 and growth >= -10:
        diff_cell.fill = PatternFill(start_color=Config.Colors.YELLOW, fill_type="solid")
    else:
        diff_cell.fill = PatternFill(start_color=Config.Colors.RED, fill_type="solid")


def configure_logger(file_name: str, processing_filename: str) -> logging.Logger:
    logger = logging.getLogger("main")
    logger.setLevel(logging.DEBUG)  # Enable DEBUG logging to see network monitoring details

    formatter = HideBacktraceFormatter("%(asctime)s - %(message)s", datefmt="%m-%d-%y_%H:%M")
    timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
    parts = split_path(processing_filename)
    folders = parts[0:len(parts)-1]
    filename = parts[-1]
    fh = logging.FileHandler(f"{file_name}_{'_'.join(folders)}_{filename.split('.')[0]}_{timestamp}.log")
    fh.setLevel(logging.DEBUG)  # Enable DEBUG logging
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    SeleniumHelper.setup_logger(logger)
    PageFormFiller.setup_logger(logger)
    return logger


def close_current_tab(driver):
    """Close current tab and switch to the first one"""
    try:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except:
        pass  # Ignore cleanup errors


def process_form(driver, url, measurer, loops, logger, is_form_page, disable_save):
    """
    Flow:
    1. Open new tab
    2. Load form + measure load time
    3. If successful: measure save time on same tab
    4. Close tab and return results
    """
    load_result = None
    save_result = None
    
    try:
        # 1. Open new tab
        driver.execute_script("window.open('about:blank', '_blank');")
        new_tab = driver.window_handles[-1]
        driver.switch_to.window(new_tab)
        
        # 2. Load and measure form in new tab
        load_result = measurer.measure_page_load(url, loops)
        
        # 3. If load successful AND it's a form page AND save not disabled
        if load_result.success and is_form_page and not disable_save:
            save_result = measurer.measure_save_time(url, loops)
        
        return load_result, save_result
        
    except Exception as e:
        logger.error(f"Error processing form in new tab: {e}")
        
        if not load_result:
            error_type, error_message = ErrorClassifier.classify_load_error(str(e))
            load_result = MeasurementResult(success=False, error_type=error_type, error_message=error_message)
        
        return load_result, save_result
        
    finally:
        # 4. Always close current tab and switch back to first tab
        try:
            if len(driver.window_handles) > 1:
                logger.debug("Closing form tab and switching back to main tab")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except Exception as cleanup_ex:
            logger.warning(f"Tab cleanup failed: {cleanup_ex}")


def print_server_down_error(error_message: str):
    print(f"\n" + "="*60)
    print(f"HTTP 503 Service Unavailable detected")
    print(f"Error details: {error_message}")
    print(f"Stopping script...")
    print(f"="*60)


def print_final_stats(start_time: float, loops: int, processed_records: int):
    total_seconds = time.time() - start_time
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    print(f"\n" + "="*60)
    print(f"🎉 PROCESSING COMPLETED!")
    print(f"="*60)
    print(f"📊 EXECUTION STATISTICS:")
    print(f"   • Loops per record: {loops}")
    print(f"   • Total records processed: {processed_records}")
    print(f"   • Total execution time: {hours:02d}h {minutes:02d}m {seconds:02d}s")
    
    if processed_records > 0:
        records_per_hour = (processed_records / total_seconds) * 3600
        print(f"   • Processing rate: {records_per_hour:.1f} records/hour")
    
    print(f"="*60)


def main():
    timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--disable_save", action="store_true")
    parser.add_argument("--disable_filler", action="store_true", default=False)
    parser.add_argument("--idm_auth", action="store_true", default=False)
    my_namespace = parser.parse_args()

    input_file = my_namespace.input_file
    loops = my_namespace.loops
    disable_save = my_namespace.disable_save
    disable_filler = my_namespace.disable_filler
    idm_auth = my_namespace.idm_auth

    logger = configure_logger("script-log", input_file)
    SeleniumHelper.set_options({
        "disable_filler": disable_filler
    })
    print(f"Input file: {input_file}")
    if not os.path.isfile(input_file):
        print("Input file doesn't exist.")
        return
    if is_excel_file_opened(input_file):
        print(f"Close opened {input_file} file!")
        return
    
    network_speed = measure_network_speed()

    wb = load_workbook(input_file, data_only=True)
    wb_sheet = wb.active
    specify_sheet_layout(wb_sheet)

    options = Options()
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    head_cell_top = wb_sheet["F1"]
    head_cell_top.alignment = Alignment(horizontal='center')
    head_cell_bottom = wb_sheet["F2"]
    head_cell_bottom.alignment = Alignment(horizontal='center')

    for row in wb_sheet.iter_rows(min_row=5):
        for i in range(15, 19):
            row[i + 9].value = row[i].value

        for i in range(20, 23):
            row[i + 8].value = row[i].value

        reset_styles([row[15], row[16], row[17], 
                      row[18], row[24], row[25], 
                      row[26], row[27], row[28],
                      row[20], row[21], row[22],
                      row[10], row[14], row[19],
                      row[29], row[30], row[23]])

        for i in range(6, 10):
            row[i + 9].value = row[i].value

        for i in range(11, 14):
            row[i + 9].value = row[i].value

        flag_high_load_time([row[15], row[16], row[17], 
                             row[18], row[25], row[25], 
                             row[26], row[27], row[28],
                             row[20], row[21], row[22],
                             row[29], row[30]], 15)
        
        
        for i in range(4, 14):
            row[i].value = ""
            
        reset_styles([row[3], row[4], row[6], row[7], row[8], row[9], row[11], row[12], row[13]])

    build_version = ""
    prev_base_url = ""
    processed_records = 0

    base_url = ""
    is_first_row = True
    measurer = FormMeasurer(driver, logger)
    
    for row in wb_sheet.iter_rows(min_row=5):
        url = row[1].value
        if url == None or not validators.url(url):
            continue
        
        processed_records += 1
        
        ExcelResultWriter.reset_row_values(row)
        reset_styles([row[Config.ExcelColumns.FROM_NAME], row[Config.ExcelColumns.FORM_URL]])
        
        print(f"\n{url}")
        logger.debug(f"Processing: {url}")
        
        row[Config.ExcelColumns.TIMESTAMP].value = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        
        try:
            base_url = extract_base_url(url)
            if prev_base_url != base_url or is_first_row:
                if idm_auth:
                    SupportTech.login(driver)
                    time.sleep(3)
                    SupportTech.open_website(driver, base_url, "SFTDVTester")
                    driver.get(url)
                else:
                    SeleniumHelper.login_user(base_url, driver, "SFTDVTester", "ht2jGMM2GnC3bwX7")
                build_version = SeleniumHelper.get_build_version(driver)
                is_first_row = False

            driver.get(url)
            is_form_page_url = SeleniumHelper.is_form_page_url(url)

            load_result, save_result = process_form(driver, url, measurer, loops, logger, is_form_page_url, disable_save)
            
            # Write load result to Excel
            ExcelResultWriter.write_load_result(row, load_result)
            
            # CRITICAL: Check for server down and terminate immediately
            if not load_result.success and load_result.error_type == Config.ErrorTypes.SERVER_DOWN:
                print_server_down_error(load_result.error_message)
                logger.error(f"SERVER DOWN detected: {load_result.error_message}")                
                wb.save(input_file)                
                print_final_stats(start_time, loops, processed_records)
                
                try:
                    driver.quit()
                except:
                    pass
                
                return
            
            if load_result.success:
                print(f"Load successful: {load_result.mean_time:.1f}s average")
                
                # Process save result if available
                if save_result:
                    ExcelResultWriter.write_save_result(row, save_result)
                    if save_result.success:
                        if "No Save button found" in save_result.error_message:
                            print(save_result.error_message)
                        else:
                            print(f"Save successful: {save_result.mean_time:.1f}s average")
                    else:
                        print(f"Save failed: {save_result.error_message}")
                
                compare_measures(row[18], row[27], row[19])
                compare_measures(row[9], row[18], row[10])
                flag_high_load_time([row[6], row[7], row[8], row[9], row[11], row[12], row[13]], 15)
            else:
                print(f"Load failed: {load_result.error_message}")
                ExcelResultWriter._clear_save_columns(row)
                row[19].value = ""
                row[10].value = ""
        except Exception as critical_ex:
            error_msg = str(critical_ex)
            
            # parse error message at readable format
            if "gethandleverifier" in error_msg.lower() or "stacktrace" in error_msg.lower():
                simple_error = "Browser crashed - restart needed"
            elif "timeout" in error_msg.lower():
                simple_error = "Connection timeout"
            elif "connection" in error_msg.lower():
                simple_error = "Network connection failed"
            else:
                simple_error = "Processing failed"
            
            print(f"Critical error: {simple_error}")
            logger.error(f"Critical error for {url}: {error_msg}")
            
            try:
                close_current_tab(driver)
            except:
                print(f"Could not clean up tabs - continuing anyway")

            # write to excel
            row[Config.ExcelColumns.ERROR_MESSAGE].value = simple_error
            mark_form_as_invalid(row, color=Config.Colors.RED)
            
            ExcelResultWriter._clear_load_columns(row)
            ExcelResultWriter._clear_save_columns(row)
        
        prev_base_url = base_url
        head_cell_top.value = f"{build_version} {timestamp}"
        head_cell_bottom.value = f"{((time.time() - start_time) / 60):.2f}m, {network_speed}mb/s, loops: {loops}"
        wb.save(input_file)
    
    driver.quit()

    print_final_stats(start_time, loops, processed_records)

if __name__ == "__main__":
    main()