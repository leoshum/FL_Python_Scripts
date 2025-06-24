"""
Performance Measurement Types
Unified data structures for all performance measurement results
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import time

class MeasurementStatus(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    FALLBACK = "fallback"

class RequestStatus(Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"

@dataclass
class ApiRequest:
    """Individual API request information"""
    url: str
    duration: float  # milliseconds
    status: RequestStatus
    start_time: Optional[float] = None
    response_time: Optional[float] = None
    
    @property
    def is_slow(self) -> bool:
        """Check if request is considered slow (>3 seconds)"""
        return self.duration > 3000
    
    @property
    def is_pending(self) -> bool:
        """Check if request is still pending"""
        return self.status == RequestStatus.PENDING

@dataclass
class NetworkState:
    """Network and loading state information"""
    # API requests
    all_api_requests: List[ApiRequest] = field(default_factory=list)
    pending_api_count: int = 0
    slow_api_count: int = 0
    
    # Loading indicators
    active_loaders: List[str] = field(default_factory=list)
    loader_count: int = 0
    
    # General network info
    total_requests: int = 0
    has_timeout: bool = False
    stability_wait_time: float = 0.0
    
    # Reliability metrics
    reliability_score: float = 1.0  # 0.0 to 1.0
    
    @property
    def api_request_count(self) -> int:
        """Total number of API requests"""
        return len(self.all_api_requests)
    
    @property
    def has_pending_requests(self) -> bool:
        """Check if there are pending API requests"""
        return self.pending_api_count > 0
    
    @property
    def has_active_loaders(self) -> bool:
        """Check if there are active loading indicators"""
        return self.loader_count > 0
    
    @property
    def is_stable(self) -> bool:
        """Check if page is in stable state"""
        return not self.has_pending_requests and not self.has_active_loaders
    
    def calculate_reliability_score(self) -> float:
        """Calculate reliability score based on network state"""
        score = 1.0
        
        # Reduce score for timeouts
        if self.has_timeout:
            score *= 0.5
        
        # Reduce score for slow requests
        if self.slow_api_count > 0:
            score *= max(0.3, 1.0 - (self.slow_api_count * 0.1))
        
        # Reduce score for pending requests
        if self.pending_api_count > 0:
            score *= max(0.4, 1.0 - (self.pending_api_count * 0.1))
        
        self.reliability_score = max(0.0, min(1.0, score))
        return self.reliability_score

@dataclass
class MeasurementResult:
    """Unified result structure for all measurement types"""
    # Timing information
    load_time: float
    start_time: float
    end_time: float
    
    # Measurement metadata
    measurement_type: str  # "form_load", "standard_load", "form_save"
    status: MeasurementStatus
    strategy_used: str  # "hybrid", "navigation_timing", "fallback"
    
    # Network and state information
    network_state: NetworkState
    
    # Error information
    error_message: Optional[str] = None
    fallback_reason: Optional[str] = None
    
    # Additional metrics
    page_ready_time: Optional[float] = None
    dom_content_loaded_time: Optional[float] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if measurement was successful"""
        return self.status == MeasurementStatus.SUCCESS
    
    @property
    def reliability_score(self) -> float:
        """Get reliability score from network state"""
        return self.network_state.calculate_reliability_score()
    
    @property
    def quality_grade(self) -> str:
        """Get quality grade based on reliability score"""
        score = self.reliability_score
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'load_time': self.load_time,
            'measurement_type': self.measurement_type,
            'status': self.status.value,
            'strategy_used': self.strategy_used,
            'reliability_score': self.reliability_score,
            'quality_grade': self.quality_grade,
            'api_requests': len(self.network_state.all_api_requests),
            'pending_requests': self.network_state.pending_api_count,
            'slow_requests': self.network_state.slow_api_count,
            'has_timeout': self.network_state.has_timeout,
            'error_message': self.error_message,
            'fallback_reason': self.fallback_reason
        }

@dataclass
class SaveButtonInfo:
    """Information about found save button"""
    element_id: Optional[str] = None
    selector_used: Optional[str] = None
    button_text: Optional[str] = None
    is_enabled: bool = False
    is_visible: bool = False
    strategy_used: Optional[str] = None  # "css", "xpath", "fallback"

def create_network_state(
    api_requests: List[Dict] = None,
    active_loaders: List[str] = None,
    total_requests: int = 0,
    has_timeout: bool = False
) -> NetworkState:
    """Factory function to create NetworkState from raw data"""
    
    # Convert API request dictionaries to ApiRequest objects
    processed_requests = []
    if api_requests:
        for req_data in api_requests:
            if isinstance(req_data, dict):
                status = RequestStatus.COMPLETED
                if req_data.get('status') == 'PENDING':
                    status = RequestStatus.PENDING
                elif req_data.get('status') == 'FAILED':
                    status = RequestStatus.FAILED
                
                processed_requests.append(ApiRequest(
                    url=req_data.get('url', ''),
                    duration=req_data.get('duration', 0),
                    status=status
                ))
    
    # Count metrics
    pending_count = sum(1 for req in processed_requests if req.is_pending)
    slow_count = sum(1 for req in processed_requests if req.is_slow)
    loader_count = len(active_loaders) if active_loaders else 0
    
    return NetworkState(
        all_api_requests=processed_requests,
        pending_api_count=pending_count,
        slow_api_count=slow_count,
        active_loaders=active_loaders or [],
        loader_count=loader_count,
        total_requests=total_requests,
        has_timeout=has_timeout
    )

def create_measurement_result(
    load_time: float,
    measurement_type: str,
    network_state: NetworkState = None,
    status: MeasurementStatus = MeasurementStatus.SUCCESS,
    strategy_used: str = "unknown",
    error_message: str = None
) -> MeasurementResult:
    """Factory function to create MeasurementResult"""
    
    current_time = time.time()
    
    if network_state is None:
        network_state = NetworkState()
    
    return MeasurementResult(
        load_time=load_time,
        start_time=current_time - load_time,
        end_time=current_time,
        measurement_type=measurement_type,
        status=status,
        strategy_used=strategy_used,
        network_state=network_state,
        error_message=error_message
    ) 