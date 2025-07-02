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
    SAVE_FALLBACK_THRESHOLD = 15.0  # seconds - save times above this indicate fallback
    
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
    
    # Network monitoring
    SLOW_REQUEST_THRESHOLD = 3000  # milliseconds (3 seconds) - threshold for flagging slow API requests

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
        """SIMPLIFIED: Classify save error and return (error_type, simple_message)"""
        error_msg = str(exception).lower()
        
        # Check for timeout specifically
        if isinstance(exception, TimeoutException) or "timeout" in error_msg:
            if "save success popup not found" in error_msg:
                return Config.ErrorTypes.TIMEOUT_ERROR, "Save timeout - success popup not detected within 20 seconds"
            else:
                return Config.ErrorTypes.TIMEOUT_ERROR, "Save operation timeout"
        
        # Check for specific save errors
        if "save failed:" in error_msg:
            # Extract the actual error message after "Save failed:"
            if "500" in error_msg or "server error" in error_msg:
                return Config.ErrorTypes.API_ERROR, "Save failed due to server error (HTTP 500)"
            else:
                return Config.ErrorTypes.API_ERROR, "Save failed due to server error"
        
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
    
    def is_frontline_api_url(self, url):
        if not url:
            return False
            
        # Convert to lowercase for case-insensitive comparison
        url_lower = url.lower()
        
        # Check if URL contains frontlineeducation.com domain
        if 'frontlineeducation.com' not in url_lower:
            return False
            
        # Additional check: must be an API endpoint
        # Common API patterns in Frontline Education
        api_patterns = [
            '/api/',
            '/plan/api/',
            '/planng/api/',
            'api.frontlineeducation.com'
        ]
        
        return any(pattern in url_lower for pattern in api_patterns)
    
    def _check_for_form_content(self):
        try:
            # Check for form-specific elements
            form_indicators = self.driver.execute_script("""
                var indicators = [];
                
                var formElements = [
                    'form',
                    'input[type="text"]',
                    'input[type="email"]',
                    'input[type="tel"]',
                    'input[type="radio"]',
                    'input[type="checkbox"]',
                    'textarea',
                    'select',
                    'button[type="submit"]',
                    '.k-button',
                    '[kendobutton]',
                    '.form-group',
                    '.form-field'
                ];
                
                var kendoElements = [
                    'kendo-combobox',
                    'kendo-datepicker',
                    'kendo-textbox',
                    'kendo-maskedtextbox',
                    'kendo-dropdownlist',
                    'kendo-checkbox',
                    'kendo-tabstrip',
                    '[kendocheckbox]',
                    '[kendotextbox]',
                    '[kendocombobox]',
                    '[kendodatepicker]',
                    '.k-checkbox',
                    '.k-textbox',
                    '.k-combobox',
                    '.k-datepicker',
                    '.k-input',
                    '.k-widget'
                ];
                
                // Check for Accelify/Frontline specific elements
                var frontlineElements = [
                    'accelify-signature',
                    'accelify-form-builder-field',
                    'accelify-reactive-form-field-value',
                    'accelify-checkbox-list',
                    'accelify-lookup-type',
                    'accelify-date-picker',
                    '.signatureButton',
                    '.js-form-field-value',
                    '.js-checkbox-list',
                    '.js-radio-button-list'
                ];
                
                var totalFormElements = 0;
                var detectedTypes = [];
                
                // Count standard form elements
                formElements.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            totalFormElements += elements.length;
                            detectedTypes.push(selector + ': ' + elements.length);
                        }
                    } catch(e) {
                        // Skip invalid selectors
                    }
                });
                
                // Count Kendo UI elements
                kendoElements.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            totalFormElements += elements.length;
                            detectedTypes.push(selector + ': ' + elements.length);
                        }
                    } catch(e) {
                        // Skip invalid selectors
                    }
                });
                
                // Count Frontline specific elements
                frontlineElements.forEach(function(selector) {
                    try {
                        var elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            totalFormElements += elements.length;
                            detectedTypes.push(selector + ': ' + elements.length);
                        }
                    } catch(e) {
                        // Skip invalid selectors
                    }
                });
                
                // Check for Angular/Kendo UI components (typical for Frontline forms)
                var angularElements = document.querySelectorAll('[ng-star-inserted], .k-widget, [kendo-], [_nghost-], [_ngcontent-]');
                if (angularElements.length > 5) {
                    detectedTypes.push('Angular components: ' + angularElements.length);
                }
                
                // Lower threshold - even 2-3 form elements could indicate a valid form
                if (totalFormElements > 2) {
                    indicators.push('Form content detected - ' + totalFormElements + ' total elements');
                    indicators.push('Types: ' + detectedTypes.join(', '));
                }
                
                // Additional check for form-specific text content
                var formKeywords = ['consent', 'signature', 'parent', 'guardian', 'evaluation', 'services'];
                var pageText = document.body.textContent.toLowerCase();
                var keywordMatches = formKeywords.filter(keyword => pageText.includes(keyword));
                if (keywordMatches.length >= 2 && totalFormElements > 0) {
                    indicators.push('Form keywords detected: ' + keywordMatches.join(', '));
                }
                
                return indicators;
            """)
            
            if form_indicators:
                self.logger.info(f"Form content detected: {form_indicators}")
                return True
                
            self.logger.warning("No form content detected - possible authentication or access issue")
            return False
            
        except Exception as e:
            self.logger.error(f"Form content check failed: {e}")
            return False
    
    def measure_page_load(self, url, loops):
        """PROPER ARCHITECTURE: Load once, measure multiple times with AUTH CHECK"""
        try:
            times = []
            
            for i in range(loops):
                self.logger.debug(f"Load measurement {i+1}/{loops}")
                measure_start = time.time()
                
                if i == 0:
                    if self.driver.current_url != url:
                        self.logger.debug(f"URL mismatch, navigating to: {url}")
                        self.driver.get(url)
                    else:
                        self.logger.debug("URL matches, using already loaded page")
                    
                    self._wait_for_page_ready()
                else:
                    self.logger.debug(f"Refreshing page for measurement {i+1}")
                    self.driver.refresh()
                    self._wait_for_page_ready()
                
                load_time = time.time() - measure_start
                
                validation_result = self._validate_page_after_load()
                if not validation_result['success']:
                    self.logger.error(f"Page validation failed on measurement {i+1}: {validation_result['error']}")
                    return MeasurementResult(
                        success=False,
                        error_type=Config.ErrorTypes.FORM_LOAD_ERROR,
                        error_message=validation_result['error']
                    )
                
                times.append(load_time)
                self.logger.info(f"Load {i+1}/{loops}: {load_time:.1f}s")
            
            payload_size = self._calculate_payload_size(url)
            
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
            if not self._check_for_form_content():
                return {
                    'success': False, 
                    'error': "No form content detected - possible authentication or access issue"
                }
            
            errors = self._check_for_errors()
            if errors:
                return {
                    'success': False,
                    'error': errors[0]
                }
            
            return {'success': True, 'error': None}
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Page validation failed: {str(e)}"
            }
    
    def measure_save_time(self, url, loops):
        """
        Flow:
        1. Wait for Angular content to stabilize
        2. Fill required form fields if needed
        3. Find Save button (with 20-second retry logic)
        4. Click Save and measure time
        5. Wait for success popup or completion
        6. Check errors during save
        """
        try:
            self.logger.info("Starting save measurement on already loaded page...")
            
            # STEP 0: Wait for Angular/dynamic content to fully render
            self._wait_for_angular_content()
            
            # STEP 0.5: Fill required form fields if needed
            self._fill_required_fields_if_needed()
            
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
            
            # We found a Save button - now measure save time
            self.logger.info(f"Found Save button: '{save_button.text.strip()}' - starting save measurement")
            
            save_start_time = time.time()
            
            self._click_save_button_reliably(save_button)
            
            self._wait_for_save_success_popup(timeout=20)
            
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
            self.logger.error(f"Save measurement failed: {str(e)}")
            error_type, error_message = ErrorClassifier.classify_save_error(e)
            return MeasurementResult(
                success=False, 
                error_type=error_type, 
                error_message=error_message
            )
    
    def _wait_for_angular_content(self, timeout=3):
        self.logger.debug("Quick check for Angular content stability...")
        
        try:
            # Quick check for Angular stability
            angular_ready = self.driver.execute_script("""
                // Quick Angular stability check
                if (typeof window.getAllAngularTestabilities === 'function') {
                    var testabilities = window.getAllAngularTestabilities();
                    return testabilities.every(function(testability) {
                        return testability.isStable();
                    });
                }
                
                // Fallback: Just check if we have Angular elements
                var angularElements = document.querySelectorAll('[ng-star-inserted], [kendo-button]');
                return angularElements.length > 0;
            """)
            
            if not angular_ready:
                self.logger.debug("Angular not ready, waiting briefly...")
                time.sleep(timeout)
            else:
                self.logger.debug("Angular appears ready")
                
        except Exception as e:
            self.logger.debug(f"Angular check failed: {e}")
    
    def _fill_required_fields_if_needed(self):
        """
        Fill required form fields to prevent validation errors during save
        Uses the existing PageFormFiller infrastructure and respects disable_filler option
        """
        try:
            from frontline_selenium.selenium_helper import SeleniumHelper
            if hasattr(SeleniumHelper, 'options') and SeleniumHelper.options.get("disable_filler", False):
                self.logger.debug("Form filler disabled in options - skipping form filling")
                return
                
            from frontline_selenium.page_filler import PageFormFiller
            PageFormFiller.fill_form(self.driver)
            self.logger.info("Form filled successfully using PageFormFiller")
            
        except ImportError:
            self.logger.debug("PageFormFiller not available - skipping form fill")
        except Exception as e:
            self.logger.warning(f"Form filling failed (continuing anyway): {str(e)}")
    
    def _find_save_button_with_wait(self, max_attempts=20, delay=0.5):
        """
        Find Save button with smart retry logic
        Total max time: 20 * 0.5 = 10 sec
        """
        from selenium.webdriver.common.by import By
        
        self.logger.debug(f"Searching for Save button ({max_attempts} attempts, {delay}s intervals)...")
        
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
            self.logger.debug(f"Save button search attempt {attempt}/{max_attempts}")
            
            # Strategy 1: Try CSS selectors
            for selector in save_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_text = element.text.strip() or element.get_attribute('value') or ''
                            if self._is_save_button(button_text):
                                self.logger.debug(f"Found Save button: '{button_text}' using selector: {selector} (attempt {attempt})")
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
                                self.logger.debug(f"Found Save button: '{button_text}' using xpath: {xpath} (attempt {attempt})")
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
                    button_text = save_button.text.strip() or save_button.get_attribute('value') or ''
                    self.logger.debug(f"Found Save button via JavaScript: '{button_text}' (attempt {attempt})")
                    return save_button
                    
            except Exception:
                pass
            
            if attempt < max_attempts:
                time.sleep(delay)
        
        total_time = max_attempts * delay
        self.logger.debug(f"No Save button found after {max_attempts} attempts ({total_time}s total)")
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
        from selenium.common.exceptions import ElementClickInterceptedException
        
        try:
            # Ensure button is still clickable
            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.element_to_be_clickable(save_button))
            
            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
            time.sleep(0.2)
            
            # Try normal click first
            save_button.click()
            self.logger.debug("Save button clicked successfully")
            
        except ElementClickInterceptedException:
            self.logger.debug("Click intercepted, using JavaScript click...")
            self.driver.execute_script("arguments[0].click();", save_button)
            
        except Exception as e:
            raise Exception(f"Failed to click Save button: {str(e)}")
    
    def _wait_for_save_success_popup(self, timeout=20):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException
        
        self.logger.debug(f"Waiting for save success popup (timeout: {timeout}s)...")
        
        start_time = time.time()
        
        # Success keywords to look for
        success_keywords = [
            "successfully updated",
            "saved successfully", 
            "update successful",
            "form has been updated",
            "success"
        ]
        
        check_interval = 0.1  # Check every 100ms
        
        while time.time() - start_time < timeout:
            try:
                # FIRST: Check for errors http 500 for example
                self._check_for_save_errors()
                
                # SECOND: Check for success popup using JS
                success_found = self.driver.execute_script("""
                    // Look for success messages in common popup locations
                    var successSelectors = [
                        '.k-notification',           // Kendo notifications
                        '.notification', 
                        '.alert',
                        '.toast',
                        '[role="alert"]',
                        '.popup',
                        '.modal-body',
                        '.success-message',
                        '.k-notification-success'
                    ];
                    
                    var successKeywords = arguments[0];
                    
                    // 1. FIRST: Check popups/notifications (existing logic)
                    for (var i = 0; i < successSelectors.length; i++) {
                        var elements = document.querySelectorAll(successSelectors[i]);
                        
                        for (var j = 0; j < elements.length; j++) {
                            var element = elements[j];
                            
                            // Only check visible elements
                            if (element.offsetHeight > 0 && element.offsetWidth > 0) {
                                var text = (element.textContent || element.innerText || '').toLowerCase();
                                
                                // Check if any success keyword is found
                                for (var k = 0; k < successKeywords.length; k++) {
                                    if (text.includes(successKeywords[k].toLowerCase())) {
                                        return {
                                            found: true,
                                            text: element.textContent || element.innerText,
                                            selector: successSelectors[i],
                                            type: 'popup'
                                        };
                                    }
                                }
                            }
                        }
                    }
                    
                    // 2. ENHANCED: Check for success text ANYWHERE on the page
                    try {
                        var pageText = document.body.innerText || document.body.textContent || '';
                        var lowerPageText = pageText.toLowerCase();
                        
                        // Look for success keywords anywhere on the page
                        for (var k = 0; k < successKeywords.length; k++) {
                            if (lowerPageText.includes(successKeywords[k].toLowerCase())) {
                                // Extract some context around the success message
                                var msgIndex = lowerPageText.indexOf(successKeywords[k].toLowerCase());
                                var start = Math.max(0, msgIndex - 30);
                                var end = Math.min(pageText.length, msgIndex + 50);
                                var context = pageText.substring(start, end).trim();
                                
                                return {
                                    found: true,
                                    text: context,
                                    selector: 'page_content',
                                    type: 'page_text'
                                };
                            }
                        }
                        
                        // 3. ADDITIONAL: Check for common success patterns that might not be in keywords
                        var additionalSuccessPatterns = [
                            'form has been updated',
                            'saved successfully',
                            'form updated',
                            'successfully saved',
                            'update successful'
                        ];
                        
                        for (var p = 0; p < additionalSuccessPatterns.length; p++) {
                            if (lowerPageText.includes(additionalSuccessPatterns[p])) {
                                var msgIndex = lowerPageText.indexOf(additionalSuccessPatterns[p]);
                                var start = Math.max(0, msgIndex - 30);
                                var end = Math.min(pageText.length, msgIndex + 50);
                                var context = pageText.substring(start, end).trim();
                                
                                return {
                                    found: true,
                                    text: context,
                                    selector: 'page_content',
                                    type: 'page_text'
                                };
                            }
                        }
                        
                    } catch(pageError) {
                        // Ignore page text search errors
                    }
                    
                    return { found: false };
                """, success_keywords)
                
                if success_found['found']:
                    elapsed = time.time() - start_time
                    success_text = success_found['text'].strip()
                    success_type = success_found.get('type', 'unknown')
                    success_selector = success_found.get('selector', 'unknown')
                    
                    if success_type == 'popup':
                        self.logger.info(f"Save success popup found after {elapsed:.1f}s: '{success_text}' (selector: {success_selector})")
                    else:
                        self.logger.info(f"Save success message found on page after {elapsed:.1f}s: '{success_text}' (type: {success_type})")
                    
                    return
                
            except Exception as e:
                if "save failed:" in str(e).lower() or "500" in str(e):
                    raise e
                pass
            
            time.sleep(check_interval)
        
        elapsed = time.time() - start_time
        
        # Final error check only on timeout
        try:
            self._check_for_save_errors()
        except Exception as final_error:
            raise final_error
        
        raise TimeoutException(f"Save success popup not found after {elapsed:.1f}s timeout")
    
    def _check_for_save_errors(self):
        try:
            error_found = self.driver.execute_script("""
                var errorResult = { found: false, text: '', type: '' };
                
                // 1. Check for visible error popups
                var errorSelectors = [
                    '.k-notification-error',
                    '.alert-danger',
                    '.error',
                    '.error-popup',
                    '.popup-error',
                    '[role="alert"][class*="error"]',
                    '.notification-error'
                ];
                
                for (var i = 0; i < errorSelectors.length; i++) {
                    var elements = document.querySelectorAll(errorSelectors[i]);
                    for (var j = 0; j < elements.length; j++) {
                        var element = elements[j];
                        if (element.offsetHeight > 0 && element.offsetWidth > 0) {
                            var text = element.textContent || element.innerText || '';
                            if (text.trim().length > 0) {
                                errorResult.found = true;
                                errorResult.text = text.trim();
                                errorResult.type = 'popup';
                                return errorResult;
                            }
                        }
                    }
                }
                
                // 2. Check for HTTP 500 errors via Performance API
                try {
                    var entries = performance.getEntriesByType('resource');
                    for (var k = 0; k < entries.length; k++) {
                        var entry = entries[k];
                        if (entry.responseStatus >= 500) {
                            errorResult.found = true;
                            errorResult.text = 'HTTP ' + entry.responseStatus + ' server error';
                            errorResult.type = 'http';
                            return errorResult;
                        }
                    }
                } catch(perfError) {
                    // Performance API not available
                }
                
                // 3. Check for server error text in page content
                try {
                    var bodyText = document.body.innerText || document.body.textContent || '';
                    var lowerText = bodyText.toLowerCase();
                    
                    // Check for 404 Not Found errors first (most specific)
                    if (lowerText.includes('not found error') || 
                        (lowerText.includes('error 404') && lowerText.includes('not found'))) {
                        errorResult.found = true;
                        errorResult.text = 'Not Found Error';
                        errorResult.type = 'content';
                        return errorResult;  // Return immediately for 404 errors
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
                        if (lowerText.includes(errorMessages[i])) {
                            // Return standardized message for managers instead of raw context
                            errorResult.found = true;
                            errorResult.text = 'Page showed error: An error has occurred on the page you were requesting...';
                            errorResult.type = 'content';
                            return errorResult;
                        }
                    }
                } catch(contentError) {
                    // Ignore content check errors
                }
                
                return errorResult;
            """)
            
            if error_found['found']:
                error_text = error_found['text']
                error_type = error_found['type']
                
                self.logger.error(f"Save error detected ({error_type}): {error_text}")
                
                if "500" in error_text or "server error" in error_text.lower():
                    raise Exception(f"Save failed: HTTP 500 server error - {error_text}")
                else:
                    raise Exception(f"Save failed: {error_text}")
                
        except Exception as e:
            if "Save failed:" in str(e):
                raise e
    
    def _wait_for_page_ready(self, timeout=10):
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state == "complete":                    
                    loading_indicators = self.driver.execute_script("""
                        var loadingSelectors = [
                            '.loading', '.spinner', '.loader', 
                            '.k-loading-mask', '.blockUI'
                        ];
                        
                        for (var i = 0; i < loadingSelectors.length; i++) {
                            var elements = document.querySelectorAll(loadingSelectors[i]);
                            for (var j = 0; j < elements.length; j++) {
                                if (elements[j].offsetHeight > 0 && elements[j].offsetWidth > 0) {
                                    return true; // Found visible loading indicator
                                }
                            }
                        }
                        return false; // No loading indicators
                    """)
                    
                    if not loading_indicators:
                        return True  # Page is ready
                        
            except Exception as e:
                self.logger.debug(f"Page ready check error: {e}")
                
            time.sleep(0.5)
        
        self.logger.warning(f"Page ready timeout after {timeout}s")
        return False
    
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

            # 3. Check for HTTP errors via Performance API (aonly frontline api need)
            http_errors = self.driver.execute_script("""
                var errors = [];
                var filteredUrls = [];  // For debugging
                try {
                    var entries = performance.getEntriesByType('resource');

                    entries.forEach(function(entry) {
                        // Only check URLs that contain frontlineeducation.com
                        var url = entry.name.toLowerCase();
                        if (url.includes('frontlineeducation.com')) {
                            // Check for HTTP 500+ errors
                            if (entry.responseStatus >= 500) {
                                errors.push('HTTP ' + entry.responseStatus + ' error: ' + entry.name);
                            }
                            // Also check for failed requests (responseStatus might be 0) - but only for API endpoints
                            else if (entry.responseStatus === 0 && 
                                    (url.includes('/api/') || url.includes('/plan/api/') || url.includes('/planng/api/'))) {
                                // API requests with status 0 often indicate server errors
                                errors.push('Failed API request (possible server error): ' + entry.name);
                            }
                        } else if (entry.responseStatus >= 400) {
                            // Log filtered out URLs for debugging (only if they have errors)
                            filteredUrls.push('Filtered out (non-Frontline): ' + entry.name + ' (status: ' + entry.responseStatus + ')');
                        }
                    });
                    
                    // Additional check: Look for recent failed navigation requests - only Frontline domains
                    var navigationEntries = performance.getEntriesByType('navigation');
                    navigationEntries.forEach(function(entry) {
                        var url = entry.name.toLowerCase();
                        if (url.includes('frontlineeducation.com') && entry.responseStatus >= 500) {
                            errors.push('HTTP ' + entry.responseStatus + ' navigation error');
                        }
                    });
                    
                } catch(e) {
                    // Performance API not available
                }
                return {errors: errors, filtered: filteredUrls};
            """)

            if http_errors and http_errors.get('errors'):
                errors.extend(http_errors['errors'])
                
            # Log filtered URLs for debugging
            if http_errors and http_errors.get('filtered'):
                for filtered_url in http_errors['filtered']:
                    self.logger.debug(f"Filtered external error: {filtered_url}")
                    
        except Exception as e:
            self.logger.debug(f"Error checking failed: {e}")
        
        return errors
    
    def _calculate_payload_size(self, url):
        try:
            self.logger.debug("Calculating payload size from API requests...")
            
            # Get network performance data via JavaScript
            payload_data = self.driver.execute_script("""
                try {
                    var totalSize = 0;
                    var apiRequestCount = 0;
                    var allRequests = [];
                    
                    // Get all network requests from Performance API
                    var entries = performance.getEntriesByType('resource');
                    
                    entries.forEach(function(entry) {
                        var requestUrl = entry.name || '';
                        var size = 0;
                        
                        // Calculate request size - prefer transferSize, fallback to decodedBodySize
                        if (entry.transferSize && entry.transferSize > 0) {
                            size = entry.transferSize;
                        } else if (entry.decodedBodySize && entry.decodedBodySize > 0) {
                            size = entry.decodedBodySize;
                        }
                        
                        // Only count Frontline Education API requests
                        var isFrontlineAPI = requestUrl.toLowerCase().includes('frontlineeducation.com') && 
                                           (requestUrl.includes('/api/') || 
                                            requestUrl.includes('/plan/api/') || 
                                            requestUrl.includes('/planng/api/'));
                        
                        if (isFrontlineAPI && size > 0) {
                            totalSize += size;
                            apiRequestCount++;
                            allRequests.push({
                                url: requestUrl.substring(0, 100), // Truncate for logging
                                size: size
                            });
                        }
                    });
                    
                    return {
                        totalSize: totalSize,
                        apiRequestCount: apiRequestCount,
                        requests: allRequests,
                        success: true
                    };
                    
                } catch (error) {
                    return {
                        totalSize: 0,
                        apiRequestCount: 0,
                        requests: [],
                        success: false,
                        error: error.toString()
                    };
                }
            """)
            
            if not payload_data or not payload_data.get('success', False):
                error_msg = payload_data.get('error', 'Unknown error') if payload_data else 'No data returned'
                self.logger.warning(f"Payload calculation failed: {error_msg}")
                return 0.0
            
            total_bytes = payload_data.get('totalSize', 0)
            request_count = payload_data.get('apiRequestCount', 0)
            requests = payload_data.get('requests', [])
            
            if total_bytes == 0:
                self.logger.debug("No Frontline API payload data found")
                return 0.0
            
            # Convert bytes to KB
            total_kb = total_bytes / 1024.0
            
            self.logger.info(f"Payload analysis: {total_kb:.1f} KB from {request_count} API requests")
            
            # Log detailed breakdown if debug enabled
            if self.logger.isEnabledFor(logging.DEBUG) and requests:
                self.logger.debug("API Request breakdown:")
                for req in requests[:5]:  # Log first 5 requests
                    size_kb = req['size'] / 1024.0
                    self.logger.debug(f"  {size_kb:.1f} KB - {req['url']}")
                if len(requests) > 5:
                    remaining_kb = sum(req['size'] for req in requests[5:]) / 1024.0
                    self.logger.debug(f"  {remaining_kb:.1f} KB - {len(requests)-5} more requests")
            
            return round(total_kb, 1)
            
        except Exception as e:
            self.logger.warning(f"Payload size calculation failed: {str(e)}")
            return 0.0


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
        logger.debug(f"Opening new tab for: {url}")
        driver.execute_script("window.open('about:blank', '_blank');")
        new_tab = driver.window_handles[-1]
        driver.switch_to.window(new_tab)
        
        # 2. Load and measure form in new tab
        logger.debug(f"Measuring page load in new tab...")
        load_result = measurer.measure_page_load(url, loops)
        
        # 3. If load successful AND it's a form page AND save not disabled
        if load_result.success and is_form_page and not disable_save:
            logger.debug(f"Load successful")
            save_result = measurer.measure_save_time(url, loops)
        else:
            if not load_result.success:
                logger.debug(f"Skipping save measurement - load failed")
            elif not is_form_page:
                logger.debug(f"Skipping save measurement - not a form page")
            elif disable_save:
                logger.debug(f"Skipping save measurement - save disabled")
        
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
    #options.headless = True
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
            
            if load_result.success:
                print(f"Load successful: {load_result.mean_time:.1f}s average")
                
                # Process save result if available
                if save_result:
                    ExcelResultWriter.write_save_result(row, save_result)
                    if save_result.success:
                        if "No Save button found" in save_result.error_message:
                            print(f"No Save button found - this is normal for some forms")
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

    total_seconds = time.time() - start_time
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    print(f"\n" + "="*60)
    print(f"PROCESSING COMPLETED!\n")
    print(f"Loops per record: {loops}")
    print(f"Total records processed: {processed_records}")
    print(f"Total time: {hours:02d}h {minutes:02d}m {seconds:02d}s")
    if processed_records > 0:
        print(f"Average time per record: {(total_seconds/(processed_records * loops)):.1f}s")
    print(f"="*60)

if __name__ == "__main__":
    main()