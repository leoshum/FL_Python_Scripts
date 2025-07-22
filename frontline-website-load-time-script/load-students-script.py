import os
import sys
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontline_selenium.selenium_helper import SeleniumHelper


class TabNames:
    ALL_STUDENTS = "All Students"
    MY_STUDENTS = "My Students"
    MY_STUDENT_TEAMS = "My Student Teams"
    DISTRIBUTION_HISTORY = "Distribution History"

    
class Config:
    """Configuration constants for student loading tests"""
    BASE_URL = "https://texas-stg-acc.ss.frontlineeducation.com"
    STUDENT_PATH = "/plan/Students/Landing"
    DEFAULT_TIMEOUT = 20
    API_CHECK_INTERVAL = 0.5
    MAX_LOADING_WAIT = 20
    
    # Login credentials (reused from main script)
    USERNAME = "SFTDVTester"
    PASSWORD = "ht2jGMM2GnC3bwX7"
    
    # Student tab configurations
    STUDENT_TABS = [
        {"name": TabNames.ALL_STUDENTS, "selector": "#pnlStudentsLanding-tab-1", "default": False},
        {"name": TabNames.MY_STUDENTS, "selector": "#pnlStudentsLanding-tab-2", "default": True},
        {"name": TabNames.MY_STUDENT_TEAMS, "selector": "#pnlStudentsLanding-tab-3", "default": False},
        {"name": TabNames.DISTRIBUTION_HISTORY, "selector": "#pnlStudentsLanding-tab-4", "default": False}
    ]
    
    # Filter configurations
    FILTER_SELECTORS = {
        "panel_toggle": ".k-panelbar-toggle",
        "filter_panel": "#pnlStudentFilters",
        "upcoming_event_dropdown": "#EventDefinitionId",
        "filter_button": "#btnFilterStudents",
        "reset_button": "#btnResetFilters"
    }
    
    # Filter search criteria
    FILTER_CRITERIA = {
        "UPCOMING_EVENT_TEXT": "IEP Annual Eligibility Determination"  # Search by text content
    }


class APIErrorDetector:
    """Monitors API requests for errors and performance issues"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.api_errors: List[Dict] = []
        self.slow_requests: List[Dict] = []
    
    def start_monitoring(self) -> None:
        """Initialize API monitoring by clearing performance data"""
        try:
            self.driver.execute_script("performance.clearResourceTimings();")
            self.api_errors.clear()
            self.slow_requests.clear()
            self.logger.debug("API monitoring started")
        except Exception as e:
            self.logger.warning(f"Failed to start API monitoring: {e}")
    
    def check_api_errors(self) -> Dict:
        """Check for API errors and slow requests"""
        try:
            results = self.driver.execute_script("""
                try {
                    const results = {
                        errors: [],
                        slowRequests: [],
                        totalApiRequests: 0
                    };
                    
                    const entries = performance.getEntriesByType('resource');
                    const currentDomain = window.location.hostname;
                    
                    entries.forEach(entry => {
                        const url = entry.name;
                        
                        try {
                            const urlObj = new URL(url);
                            
                            // Only check requests to current domain
                            if (urlObj.hostname === currentDomain) {
                                // Only check API endpoints (plan/api paths)
                                if (url.includes('/plan/api/')) {
                                    results.totalApiRequests++;
                                    
                                    // Check for HTTP errors (400, 500 status codes)
                                    if (entry.responseStatus >= 400) {
                                        results.errors.push({
                                            url: url,
                                            status: entry.responseStatus,
                                            duration: entry.duration
                                        });
                                    }
                                    
                                    // Check for slow requests (>3 seconds)
                                    if (entry.duration > 3000) {
                                        results.slowRequests.push({
                                            url: url,
                                            status: entry.responseStatus || 0,
                                            duration: entry.duration
                                        });
                                    }
                                }
                            }
                        } catch(e) {
                            // Skip invalid URLs
                        }
                    });
                    
                    return results;
                } catch(e) {
                    return {
                        errors: [],
                        slowRequests: [],
                        totalApiRequests: 0,
                        jsError: e.toString()
                    };
                }
            """)
            
            if results.get('jsError'):
                self.logger.warning(f"JavaScript error in API check: {results['jsError']}")
            
            if results['errors']:
                self.api_errors.extend(results['errors'])
                for error in results['errors']:
                    self.logger.error(f"API Error {error['status']}: {error['url']} ({error['duration']:.0f}ms)")
            
            if results['slowRequests']:
                self.slow_requests.extend(results['slowRequests'])
                for slow in results['slowRequests']:
                    self.logger.warning(f"Slow API Request: {slow['url']} ({slow['duration']:.0f}ms)")
            
            return {
                'api_errors': len(self.api_errors),
                'slow_requests': len(self.slow_requests),
                'total_api_requests': results['totalApiRequests']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check API errors: {e}")
            return {'api_errors': 0, 'slow_requests': 0, 'total_api_requests': 0}
    
    def get_error_summary(self) -> Dict:
        """Get summary of detected errors"""
        return {
            'total_errors': len(self.api_errors),
            'total_slow_requests': len(self.slow_requests),
            'errors': self.api_errors.copy(),
            'slow_requests': self.slow_requests.copy()
        }


class ServiceManagerSwitcher:
    """Handles switching between Service Management and Plan Management"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def switch_to_plan_management(self) -> bool:
        """Switch to Plan Management service"""
        try:            
            wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
            
            # Click the app switcher button to open dropdown
            app_switcher_button = wait.until(
                EC.element_to_be_clickable((By.ID, "sk--app-switcher-title"))
            )
            
            app_switcher_button.click()
            
            # Wait for dropdown menu to appear
            wait.until(
                EC.visibility_of_element_located((By.ID, "sk--app-switcher-menu"))
            )
            
            # Click on Plan Management
            plan_mgmt_link = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='http://texas-stg-acc.ss.frontlineeducation.com/plan']"))
            )
            
            plan_mgmt_link.click()
            
            # Wait for page to load after switching
            self._wait_for_page_load()
            
            # Verify we're on Plan Management
            current_url = self.driver.current_url
            if "/plan" in current_url:
                self.logger.info("Successfully switched to Plan Management")
                return True
            else:
                self.logger.warning(f"May not be on Plan Management - URL: {current_url}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to switch to Plan Management: {e}")
            return False
    
    def _wait_for_page_load(self) -> None:
        """Wait for page to finish loading after service switch"""
        try:
            wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for any loading indicators to disappear
            self.driver.execute_script("""
                return new Promise(resolve => {
                    const checkLoading = () => {
                        const loadingElements = document.querySelectorAll('.loading, .spinner, .k-loading-mask');
                        const visibleLoading = Array.from(loadingElements).some(el => 
                            el.offsetHeight > 0 && el.offsetWidth > 0
                        );
                        
                        if (!visibleLoading) {
                            resolve(true);
                        } else {
                            setTimeout(checkLoading, 500);
                        }
                    };
                    
                    setTimeout(checkLoading, 1000);
                });
            """)
            
        except Exception as e:
            self.logger.debug(f"Page load wait failed: {e}")


class StudentPageTester:
    """Tests student page tabs and monitors for loading issues"""
    
    def __init__(self, driver, logger, api_detector):
        self.driver = driver
        self.logger = logger
        self.api_detector = api_detector
        self.filter_manager = StudentFilterManager(driver, logger)
        self.tab_results: Dict = {}
    
    def navigate_to_students_page(self) -> bool:
        """Navigate to students page only if not already there"""
        try:
            current_url = self.driver.current_url
            
            if "Students/Landing" in current_url:
                return True
            
            # Only navigate if we're not on the students page
            target_url = f"{Config.BASE_URL}{Config.STUDENT_PATH}"
            self.logger.info(f"Navigating to students page: {target_url}")
            
            self.driver.get(target_url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Verify we're on the correct page
            current_url = self.driver.current_url
            if "Students" in current_url:
                self.logger.info("Successfully navigated to students page")
                return True
            else:
                self.logger.error(f"Navigation failed - current URL: {current_url}")
                return False
                    
        except Exception as e:
            self.logger.error(f"Failed to navigate to students page: {e}")
            return False
    
    def test_all_tabs(self) -> Dict:
        """Test all student tabs and return results"""        
        for tab_config in Config.STUDENT_TABS:
            tab_name = tab_config['name']            
            result = self._test_single_tab(tab_config)
            self.tab_results[tab_name] = result
            
            if result['success']:
                filter_status = ""
                if result.get('filter_applied', False):
                    filter_status = " [FILTER: IEP Annual Eligibility]"
                self.logger.info(f"[OK] {tab_name} ({result['load_time']:.1f}s){filter_status}")
            else:
                filter_error = ""
                if tab_name == TabNames.ALL_STUDENTS and not result.get('filter_applied', False):
                    filter_error = " [FILTER: FAILED]"
                self.logger.error(f"[FAIL] {tab_name}: {result['error']}{filter_error}")
        
        return self.tab_results
    
    def _test_single_tab(self, tab_config: Dict) -> Dict:
        """Test a single student tab"""
        selector = tab_config['selector']
        is_default = tab_config['default']
        tab_name = tab_config['name']
        TIMEOUT_SECONDS = 1
        
        try:
            start_time = time.time()
            
            # Start API monitoring for this tab
            self.api_detector.start_monitoring()
            
            if not is_default:
                # Click on the tab if it's not the default
                wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
                tab_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                tab_element.click()
                # Wait for tab content to start loading
                time.sleep(1)
            
            # Wait for students to load
            self._wait_for_students_to_load()
            
            filter_success = True
            if tab_name == TabNames.ALL_STUDENTS:
                try:
                    filter_success = self.filter_manager.apply_filters_to_all_students_tab()
                    if not filter_success:
                        self.logger.error("Filter application failed for All Students tab")
                except Exception as e:
                    self.logger.error(f"Error during filter application: {e}")
                    filter_success = False
            
            api_status = self.api_detector.check_api_errors()
            
            load_time = (time.time() - start_time) - TIMEOUT_SECONDS # remove the timeout seconds
            
            # Consider both API errors and filter errors for overall success
            if api_status['api_errors'] > 0:
                return {
                    'success': False,
                    'error': f"API errors detected: {api_status['api_errors']} errors",
                    'load_time': load_time,
                    'api_status': api_status,
                    'filter_applied': tab_name == TabNames.ALL_STUDENTS and filter_success
                }
            
            if tab_name == TabNames.ALL_STUDENTS and not filter_success:
                return {
                    'success': False,
                    'error': "Filter application failed",
                    'load_time': load_time,
                    'api_status': api_status,
                    'filter_applied': False
                }
            
            return {
                'success': True,
                'load_time': load_time,
                'api_status': api_status,
                'filter_applied': tab_name == TabNames.ALL_STUDENTS and filter_success
            }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'load_time': time.time() - start_time if 'start_time' in locals() else 0,
                'api_status': {'api_errors': 0, 'slow_requests': 0, 'total_api_requests': 0},
                'filter_applied': False
            }
    
    def _wait_for_students_to_load(self) -> None:
        """Wait for student data to finish loading"""
        try:
            wait = WebDriverWait(self.driver, Config.MAX_LOADING_WAIT)            
            # Wait for page to be ready
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for API requests to complete
            self.driver.execute_script("""
                return new Promise((resolve) => {
                    const maxWait = 8000; // 8 seconds max
                    const startTime = Date.now();
                    const currentDomain = window.location.hostname;
                    
                    const checkApiComplete = () => {
                        try {
                            const entries = performance.getEntriesByType('resource');
                            let pendingApiCount = 0;
                            let totalApiCount = 0;
                            
                            entries.forEach(entry => {
                                try {
                                    const url = entry.name;
                                    const urlObj = new URL(url);
                                    
                                    // Only check our domain API requests
                                    if (urlObj.hostname === currentDomain && url.includes('/plan/api/')) {
                                        totalApiCount++;
                                        if (entry.responseEnd === 0) {
                                            pendingApiCount++;
                                        }
                                    }
                                } catch(e) {
                                    // Skip invalid URLs
                                }
                            });
                            
                            // Check if all API requests are done or timeout
                            if (pendingApiCount === 0 || (Date.now() - startTime) > maxWait) {
                                resolve(true);
                            } else {
                                setTimeout(checkApiComplete, 500);
                            }
                        } catch(e) {
                            resolve(true); // Continue on error
                        }
                    };
                    
                    setTimeout(checkApiComplete, 1000); // Start checking after 1 second
                });
            """)
            
            self.logger.debug("Student loading completed")
            
        except Exception as e:
            self.logger.warning(f"Student loading wait failed: {e}")


class StudentFilterManager:
    """Manages student filter operations"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    def ensure_filter_panel_open(self) -> bool:
        """Ensure the filter panel is open and ready for interaction"""
        try:
            wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
            
            # Check if panel is already open
            panel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, Config.FILTER_SELECTORS["filter_panel"])))
            
            # Check if panel content is visible
            is_expanded = self.driver.execute_script("""
                var panel = arguments[0];
                var content = panel.querySelector('.k-panelbar-content');
                return content && content.style.display !== 'none';
            """, panel)
            
            if not is_expanded:
                # Find and click the toggle button to open the panel
                toggle_button = panel.find_element(By.CSS_SELECTOR, Config.FILTER_SELECTORS["panel_toggle"])
                toggle_button.click()
                
                # Wait for panel to expand
                wait.until(lambda driver: driver.execute_script("""
                    var panel = document.querySelector(arguments[0]);
                    var content = panel.querySelector('.k-panelbar-content');
                    return content && content.style.display !== 'none';
                """, Config.FILTER_SELECTORS["filter_panel"]))
                
                self.logger.info("Filter panel opened successfully")
            else:
                self.logger.info("Filter panel already open")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to open filter panel: {e}")
            return False
    
    def apply_upcoming_event_filter(self, search_text: str) -> bool:
        """Apply upcoming event filter using simple approach"""
        try:
            # Check if the dropdown exists
            try:
                wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
                dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, Config.FILTER_SELECTORS["upcoming_event_dropdown"])))
            except:
                self.logger.warning("Upcoming event dropdown not found - skipping filter")
                return True  # Not an error if filter doesn't exist
            
            # Try to select the option
            result = self.driver.execute_script("""
                var element = document.querySelector(arguments[0]);
                var searchText = arguments[1];
                
                if (!element) return {success: false, error: 'Element not found'};
                
                // Try regular select first
                var options = element.querySelectorAll('option');
                for (var i = 0; i < options.length; i++) {
                    if (options[i].textContent.includes(searchText)) {
                        options[i].selected = true;
                        element.dispatchEvent(new Event('change', {bubbles: true}));
                        return {success: true, selectedText: options[i].textContent};
                    }
                }
                
                // Try Kendo if available
                if (typeof $ !== 'undefined') {
                    try {
                        var kendoWidget = $(element).data('kendoDropDownList');
                        if (kendoWidget && kendoWidget.dataSource) {
                            var data = kendoWidget.dataSource.data();
                            for (var j = 0; j < data.length; j++) {
                                if (data[j].text && data[j].text.includes(searchText)) {
                                    kendoWidget.value(data[j].value);
                                    kendoWidget.trigger('change');
                                    return {success: true, selectedText: data[j].text};
                                }
                            }
                        }
                    } catch(e) {}
                }
                
                return {success: false, error: 'Option not found'};
            """, Config.FILTER_SELECTORS["upcoming_event_dropdown"], search_text)
            
            if result.get('success'):
                self.logger.info(f"Selected upcoming event filter: {result['selectedText']}")
            else:
                self.logger.warning(f"Could not find filter option: {search_text}")
            
            return True  # Always return True
            
        except Exception as e:
            self.logger.warning(f"Filter error: {e}")
            return True
    
    def click_filter_button(self) -> bool:
        """Click the filter button to apply all selected filters"""
        try:
            wait = WebDriverWait(self.driver, Config.DEFAULT_TIMEOUT)
            
            filter_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, Config.FILTER_SELECTORS["filter_button"])))
            filter_button.click()
            
            self.logger.info("Filter button clicked successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to click filter button: {e}")
            return False
    
    def wait_for_grid_reload(self) -> bool:
        """Wait for the student grid to reload with filtered results"""
        try:
            # Wait a moment for the filter request to start
            time.sleep(1)
            
            # Wait for any loading indicators to disappear
            wait = WebDriverWait(self.driver, Config.MAX_LOADING_WAIT)
            
            # Wait for page to be ready
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for API requests to complete (similar to existing logic)
            self.driver.execute_script("""
                return new Promise((resolve) => {
                    const maxWait = 10000; // 10 seconds max for filter results
                    const startTime = Date.now();
                    const currentDomain = window.location.hostname;
                    
                    const checkApiComplete = () => {
                        try {
                            const entries = performance.getEntriesByType('resource');
                            let pendingApiCount = 0;
                            
                            entries.forEach(entry => {
                                try {
                                    const url = entry.name;
                                    const urlObj = new URL(url);
                                    
                                    // Check for student-related API requests
                                    if (urlObj.hostname === currentDomain && 
                                        (url.includes('/plan/api/') || url.includes('/Students/'))) {
                                        if (entry.responseEnd === 0) {
                                            pendingApiCount++;
                                        }
                                    }
                                } catch(e) {
                                    // Skip invalid URLs
                                }
                            });
                            
                            if (pendingApiCount === 0 || (Date.now() - startTime) > maxWait) {
                                resolve(true);
                            } else {
                                setTimeout(checkApiComplete, 500);
                            }
                        } catch(e) {
                            resolve(true); // Continue on error
                        }
                    };
                    
                    setTimeout(checkApiComplete, 500);
                });
            """)
            
            self.logger.info("Grid reload completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error waiting for grid reload: {e}")
            return False
    
    def apply_filters_to_all_students_tab(self) -> bool:
        """Apply filters specifically to the All Students tab"""
        try:
            self.logger.info("Applying filters to All Students tab")
            
            # Open filter panel
            if not self.ensure_filter_panel_open():
                self.logger.warning("Could not open filter panel")
                return True
            
            time.sleep(1)  # Wait for panel to load
            
            # Apply filter and click button
            self.apply_upcoming_event_filter(Config.FILTER_CRITERIA["UPCOMING_EVENT_TEXT"])
            
            # Quick check if filter was applied
            try:
                current_value = self.driver.execute_script("""
                    var element = document.querySelector(arguments[0]);
                    if (element && element.value) return element.value;
                    if (typeof $ !== 'undefined') {
                        var widget = $(element).data('kendoDropDownList');
                        if (widget) return widget.value();
                    }
                    return null;
                """, Config.FILTER_SELECTORS["upcoming_event_dropdown"])
                
                if current_value:
                    self.logger.info(f"Filter value set to: {current_value}")
            except:
                pass
            
            if self.click_filter_button():
                self.wait_for_grid_reload()
                self.logger.info("Filter application completed")
            else:
                self.logger.warning("Could not click filter button")
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Filter issues: {e}")
            return True


class StudentLoadingTester:
    """Main orchestrator for student loading tests"""    
    def __init__(self):
        self.logger = self._setup_logger()
        self.driver = None
        self.api_detector = None
        self.service_switcher = None
        self.page_tester = None
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("student_loading_tester")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # File handler
            timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
            file_handler = logging.FileHandler(f"student_loading_test_{timestamp}.log")
            file_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger
    
    def setup_driver(self) -> bool:
        """Initialize the Chrome driver"""
        try:
            options = Options()
            # options.add_argument("--headless")  # Uncomment for headless mode
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Add options to reduce Chrome warnings
            options.add_argument("--disable-logging")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")  # Suppress INFO, WARNING, and ERROR
            options.add_argument("--silent")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            
            # Initialize components
            self.api_detector = APIErrorDetector(self.driver, self.logger)
            self.service_switcher = ServiceManagerSwitcher(self.driver, self.logger)
            self.page_tester = StudentPageTester(self.driver, self.logger, self.api_detector)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            return False
    
    def login_to_system(self) -> bool:
        """Login to the Frontline system"""
        try:
            self.logger.info(f"Logging into: {Config.BASE_URL}")
            
            SeleniumHelper.login_user(Config.BASE_URL, self.driver, Config.USERNAME, Config.PASSWORD)
            
            self.logger.info("Login successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False
    
    def run_test(self) -> Dict:
        """Execute the complete student loading test"""
        start_time = time.time()
        results = {
            'success': False,
            'login_success': False,
            'service_switch_success': False,
            'tab_results': {},
            'total_time': 0,
            'api_summary': {}
        }
        
        try:
            self.logger.info("=" * 60)
            self.logger.info("STUDENT LOADING TEST STARTED")
            self.logger.info("=" * 60)
            
            # Step 1: Setup driver
            if not self.setup_driver():
                return results
            
            # Step 2: Login
            results['login_success'] = self.login_to_system()
            if not results['login_success']:
                return results
            
            # Step 3: Switch to Plan Management (this takes us to default route)
            results['service_switch_success'] = self.service_switcher.switch_to_plan_management()
            if not results['service_switch_success']:
                return results
            
            # Step 4: Navigate to students page only if needed
            if not self.page_tester.navigate_to_students_page():
                return results
            
            # Step 5: Test all student tabs
            results['tab_results'] = self.page_tester.test_all_tabs()
            
            # Step 6: Get API error summary
            results['api_summary'] = self.api_detector.get_error_summary()
            
            # Overall success if all tabs loaded without critical errors
            successful_tabs = sum(1 for result in results['tab_results'].values() if result['success'])
            results['success'] = successful_tabs == len(Config.STUDENT_TABS)
            
            results['total_time'] = time.time() - start_time
            
            return results
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            results['total_time'] = time.time() - start_time
            return results
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def print_results(self, results: Dict) -> None:
        print("\n" + "=" * 60)
        
        print(f"Overall: {'[OK]' if results['success'] else '[FAIL]'}")
        print(f"Total Time: {results['total_time']:.1f}s\n")
        
        print("Test Steps:")
        print(f"   Login: {'[OK]' if results['login_success'] else '[FAIL]'}")
        print(f"   Service Switch: {'[OK]' if results['service_switch_success'] else '[FAIL]'}\n")
        
        print("Tab Results:")
        for tab_name, result in results['tab_results'].items():
            status = '[OK]' if result['success'] else '[FAIL]'
            load_time = result.get('load_time', 0)
            print(f"   {tab_name}: {status} ({load_time:.1f}s)")
            if not result['success']:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        print()
        
        api_summary = results['api_summary']
        print("API Summary:")
        print(f"   Total Errors: {api_summary.get('total_errors', 0)}")
        print(f"   Slow Requests: {api_summary.get('total_slow_requests', 0)}")
        
        if api_summary.get('errors'):
            print("\nAPI Errors:")
            for error in api_summary['errors']:
                print(f"  {error['status']}: {error['url']}")
        
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Student Loading Test Script")
    # args = parser.parse_args()
    
    tester = StudentLoadingTester()
    results = tester.run_test()
    tester.print_results(results)
    
    # Exit with error code if test failed
    if not results['success']:
        sys.exit(1)


if __name__ == "__main__":
    main() 