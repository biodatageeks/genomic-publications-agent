"""
Robust API Client with enhanced error handling and rate limiting.

This module provides a base class for API clients with:
- Exponential backoff retry mechanism
- Circuit breaker pattern for failing services
- Comprehensive rate limiting
- Request/response logging
- Timeout management
"""

import time
import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 5  # Maximum burst requests
    
    
@dataclass 
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before attempting recovery
    success_threshold: int = 2   # Successes needed to close circuit
    

@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    backoff_factor: float = 2.0
    status_forcelist: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 429])
    

class RateLimiter:
    """
    Token bucket rate limiter with multiple time windows.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_size
        self.last_update = time.time()
        
        # Request timestamps for different windows
        self.minute_requests = []
        self.hour_requests = []
        
    def wait_if_needed(self) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Returns:
            Time waited in seconds
        """
        now = time.time()
        wait_time = 0.0
        
        # Update token bucket
        time_passed = now - self.last_update
        self.tokens = min(
            self.config.burst_size,
            self.tokens + time_passed * self.config.requests_per_second
        )
        self.last_update = now
        
        # Check token bucket (requests per second)
        if self.tokens < 1:
            wait_time = max(wait_time, (1 - self.tokens) / self.config.requests_per_second)
        
        # Clean old requests
        minute_ago = now - 60
        hour_ago = now - 3600
        self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
        self.hour_requests = [t for t in self.hour_requests if t > hour_ago]
        
        # Check minute limit
        if len(self.minute_requests) >= self.config.requests_per_minute:
            oldest_in_minute = min(self.minute_requests)
            wait_time = max(wait_time, oldest_in_minute + 60 - now)
        
        # Check hour limit
        if len(self.hour_requests) >= self.config.requests_per_hour:
            oldest_in_hour = min(self.hour_requests)
            wait_time = max(wait_time, oldest_in_hour + 3600 - now)
        
        # Wait if necessary
        if wait_time > 0:
            time.sleep(wait_time)
            # Update after waiting
            self.tokens = max(0, self.tokens - 1)
            now = time.time()
        else:
            self.tokens = max(0, self.tokens - 1)
        
        # Record request
        self.minute_requests.append(now)
        self.hour_requests.append(now)
        
        return wait_time


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception(f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN


class RobustAPIClient:
    """
    Robust API client with comprehensive error handling and rate limiting.
    """
    
    def __init__(
        self,
        base_url: str,
        rate_limit_config: Optional[RateLimitConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config or CircuitBreakerConfig())
        self.retry_config = retry_config or RetryConfig()
        
        # Setup session
        self.session = requests.Session()
        
        # Simple adapter without complex retry (we handle retries manually)
        adapter = HTTPAdapter()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'RobustAPIClient/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        if headers:
            self.session.headers.update(headers)
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with all protection mechanisms.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data
            **kwargs: Additional request arguments
            
        Returns:
            Response object
            
        Raises:
            Exception: If request fails after all retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Apply rate limiting
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            self.logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        # Prepare request
        request_kwargs = {
            'url': url,
            'params': params,
            'timeout': self.timeout,
            **kwargs
        }
        
        if data:
            request_kwargs['data'] = data
        if json_data:
            request_kwargs['json'] = json_data
        
        # Execute with circuit breaker and manual retry
        def make_request_with_retry():
            last_exception = Exception("No exception occurred")
            
            for attempt in range(self.retry_config.max_retries + 1):
                start_time = time.time()
                try:
                    response = self.session.request(method, **request_kwargs)
                    duration = time.time() - start_time
                    
                    self.logger.debug(
                        f"{method} {url} -> {response.status_code} "
                        f"({duration:.2f}s, {len(response.content)} bytes)"
                    )
                    
                    # Check for rate limiting response
                    if response.status_code == 429:
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            sleep_time = int(retry_after)
                            self.logger.warning(f"Rate limited by server, sleeping {sleep_time}s")
                            time.sleep(sleep_time)
                            
                        if response.status_code in self.retry_config.status_forcelist:
                            raise requests.exceptions.RequestException("Rate limited by server")
                    
                    # Check if status code should trigger retry
                    if response.status_code in self.retry_config.status_forcelist:
                        raise requests.exceptions.RequestException(f"HTTP {response.status_code}")
                    
                    response.raise_for_status()
                    return response
                    
                except Exception as e:
                    duration = time.time() - start_time
                    last_exception = e
                    
                    if attempt < self.retry_config.max_retries:
                        # Calculate backoff time
                        backoff_time = self.retry_config.backoff_factor ** attempt
                        self.logger.warning(
                            f"{method} {url} failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}) "
                            f"after {duration:.2f}s: {e}. Retrying in {backoff_time:.1f}s"
                        )
                        time.sleep(backoff_time)
                    else:
                        self.logger.error(f"{method} {url} failed after {duration:.2f}s: {e}")
            
            # All retries exhausted
            raise last_exception
        
        return self.circuit_breaker.call(make_request_with_retry)
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Make GET request."""
        return self._make_request('GET', endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Make POST request."""
        return self._make_request('POST', endpoint, data=data, json_data=json_data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Make PUT request."""
        return self._make_request('PUT', endpoint, data=data, json_data=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request."""
        return self._make_request('DELETE', endpoint, **kwargs)
    
    def get_json(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Make GET request and return JSON response.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional request arguments
            
        Returns:
            Parsed JSON response
            
        Raises:
            ValueError: If response is not valid JSON
        """
        response = self.get(endpoint, params=params, **kwargs)
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.debug(f"Response content: {response.text[:500]}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def post_json(self, endpoint: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make POST request with JSON data and return JSON response.
        
        Args:
            endpoint: API endpoint
            json_data: JSON data to send
            **kwargs: Additional request arguments
            
        Returns:
            Parsed JSON response
        """
        response = self.post(endpoint, json_data=json_data, **kwargs)
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status information."""
        return {
            'state': self.circuit_breaker.state.value,
            'failure_count': self.circuit_breaker.failure_count,
            'success_count': self.circuit_breaker.success_count,
            'last_failure_time': self.circuit_breaker.last_failure_time
        }
    
    def get_rate_limiter_status(self) -> Dict[str, Any]:
        """Get rate limiter status information."""
        return {
            'tokens': self.rate_limiter.tokens,
            'requests_per_second': self.rate_limiter.config.requests_per_second,
            'minute_requests': len(self.rate_limiter.minute_requests),
            'hour_requests': len(self.rate_limiter.hour_requests)
        }
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker to closed state."""
        self.circuit_breaker.state = CircuitState.CLOSED
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.success_count = 0
        self.logger.info("Circuit breaker manually reset")


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create client with conservative rate limiting
    rate_config = RateLimitConfig(
        requests_per_second=0.5,  # 1 request per 2 seconds
        requests_per_minute=20,
        requests_per_hour=500
    )
    
    circuit_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30
    )
    
    retry_config = RetryConfig(
        max_retries=3,
        backoff_factor=2.0
    )
    
    # Example with a real API
    client = RobustAPIClient(
        base_url="https://httpbin.org",
        rate_limit_config=rate_config,
        circuit_breaker_config=circuit_config,
        retry_config=retry_config
    )
    
    try:
        # Test successful request
        response = client.get_json("/get", params={"test": "value"})
        print("Success:", response["args"])
        
        # Test circuit breaker and rate limiting
        for i in range(5):
            try:
                response = client.get_json("/status/200")
                print(f"Request {i+1}: OK")
            except Exception as e:
                print(f"Request {i+1}: Failed - {e}")
        
        # Check status
        print("Circuit breaker:", client.get_circuit_breaker_status())
        print("Rate limiter:", client.get_rate_limiter_status())
        
    except Exception as e:
        print(f"Error: {e}")