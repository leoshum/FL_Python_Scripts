"""
Performance Measurement Configuration
Centralized configuration for all performance measurement parameters
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class PageType(Enum):
    FORM = "form"
    STANDARD = "standard"
    READONLY_FORM = "readonly_form"

class MeasurementStrategy(Enum):
    HYBRID = "hybrid"  # For forms with API monitoring
    NAVIGATION_TIMING = "navigation_timing"  # For standard pages
    FALLBACK = "fallback"  # Simple timing fallback

@dataclass
class TimingConfig:
    """Timing configuration for measurements"""
    default_timeout: int = 30
    save_button_timeout: int = 15
    page_stability_wait: int = 3  # seconds to wait for page stability
    measurement_interval: int = 500  # milliseconds between checks
    max_measurement_time: int = 35  # maximum time to wait for measurement
    
@dataclass 
class SelectorConfig:
    """CSS selectors for different page elements"""
    # Loading indicators
    loading_selectors: List[str] = None
    
    # Form save buttons
    save_button_selectors: List[str] = None
    
    # Form containers
    form_containers: List[str] = None
    
    # Interfering elements
    interfering_elements: List[str] = None
    
    def __post_init__(self):
        if self.loading_selectors is None:
            self.loading_selectors = [
                '.loading', '.spinner', '.blockUI', '.loader-circle',
                '.loading-wrapper', '.blockMsg', '.blockPage',
                '.k-loading-mask', '[kendogridloading]', '.k-loading-text',
                '.k-loading-image', '.k-i-loading', '.loading-overlay',
                '.spinner-border', '.fa-spinner'
            ]
            
        if self.save_button_selectors is None:
            self.save_button_selectors = [
                "#btnUpdateForm",
                "button[kendobutton][type='submit']",
                "button[kendobutton] span.k-button-text",
                "button.k-button.k-button-solid span.k-button-text",
                "button[role='button'] span.k-button-text",
                "button[type='submit']",
                "input[type='submit']",
                ".k-button",
                "button"
            ]
            
        if self.form_containers is None:
            self.form_containers = [
                "accelify-forms-details",
                ".form-container",
                ".main-content", 
                "#pnlForm",
                "#pnlEventContent"
            ]
            
        if self.interfering_elements is None:
            self.interfering_elements = [
                "#launcher",
                ".blockUI",
                ".blockOverlay"
            ]

@dataclass
class ApiConfig:
    """API request patterns for monitoring"""
    form_api_patterns: List[str] = None
    slow_request_threshold: int = 3000  # milliseconds
    recent_request_window: int = 10000  # milliseconds
    
    def __post_init__(self):
        if self.form_api_patterns is None:
            self.form_api_patterns = [
                '/sections/',
                '/exceptionalities/', 
                '/distributionrecipients/',
                '/getDistribution',
                '/translationProjects/',
                '/entity-locking/',
                '/getSectionHistory/',
                '/lookupValues/',
                '/events/',
                '/api/'
            ]

@dataclass
class PerformanceConfig:
    """Main performance configuration"""
    timing: TimingConfig = None
    selectors: SelectorConfig = None
    api: ApiConfig = None
    
    # Measurement behavior
    enable_network_monitoring: bool = True
    enable_mutation_observer: bool = True
    enable_performance_api: bool = True
    
    # Logging
    log_slow_requests: bool = True
    log_network_state: bool = True
    log_measurement_details: bool = True
    
    # Fallback behavior
    use_fallback_on_error: bool = True
    fallback_timeout: int = 10
    
    def __post_init__(self):
        if self.timing is None:
            self.timing = TimingConfig()
        if self.selectors is None:
            self.selectors = SelectorConfig()
        if self.api is None:
            self.api = ApiConfig()

# Global configuration instance
CONFIG = PerformanceConfig()

def get_config() -> PerformanceConfig:
    """Get the global performance configuration"""
    return CONFIG

def update_config(**kwargs) -> None:
    """Update configuration parameters"""
    global CONFIG
    for key, value in kwargs.items():
        if hasattr(CONFIG, key):
            setattr(CONFIG, key, value) 