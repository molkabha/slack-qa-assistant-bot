import requests
import time
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

@dataclass
class EndpointConfig:
    name: str
    url: str
    method: str = "GET"
    headers: Dict = None
    payload: Dict = None
    expected_status: int = 200
    max_response_time: float = 5.0
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0

@dataclass
class HealthCheckResult:
    endpoint_name: str
    url: str
    status: str
    status_code: Optional[int]
    response_time: float
    timestamp: datetime
    error_message: Optional[str] = None

class APIMonitor:
    def __init__(self, endpoints: List[EndpointConfig]):
        self.endpoints = endpoints
        self.results_history = []
        self.max_history = 1000
        self.logger = logging.getLogger(__name__)
    
    def check_endpoint_sync(self, endpoint: EndpointConfig) -> HealthCheckResult:
        start_time = time.time()
        
        for attempt in range(endpoint.retry_count):
            try:
                if endpoint.method.upper() == "GET":
                    response = requests.get(
                        endpoint.url,
                        headers=endpoint.headers,
                        timeout=endpoint.timeout
                    )
                elif endpoint.method.upper() == "POST":
                    response = requests.post(
                        endpoint.url,
                        headers=endpoint.headers,
                        json=endpoint.payload,
                        timeout=endpoint.timeout
                    )
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == endpoint.expected_status:
                    if response_time <= endpoint.max_response_time * 1000:
                        status = "healthy"
                        error_message = None
                    else:
                        status = "slow"
                        error_message = f"Response time {response_time:.2f}ms exceeds threshold {endpoint.max_response_time * 1000}ms"
                else:
                    status = "unhealthy"
                    error_message = f"Expected status {endpoint.expected_status}, got {response.status_code}"
                
                result = HealthCheckResult(
                    endpoint_name=endpoint.name,
                    url=endpoint.url,
                    status=status,
                    status_code=response.status_code,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message=error_message
                )
                
                self._add_to_history(result)
                return result
                
            except requests.exceptions.Timeout:
                if attempt < endpoint.retry_count - 1:
                    time.sleep(endpoint.retry_delay)
                    continue
                
                error_message = f"Request timeout after {endpoint.timeout}s"
                
            except requests.exceptions.ConnectionError:
                if attempt < endpoint.retry_count - 1:
                    time.sleep(endpoint.retry_delay)
                    continue
                
                error_message = "Connection error"
                
            except Exception as e:
                if attempt < endpoint.retry_count - 1:
                    time.sleep(endpoint.retry_delay)
                    continue
                
                error_message = str(e)
        
        response_time = (time.time() - start_time) * 1000
        result = HealthCheckResult(
            endpoint_name=endpoint.name,
            url=endpoint.url,
            status="error",
            status_code=None,
            response_time=response_time,
            timestamp=datetime.now(),
            error_message=error_message
        )
        
        self._add_to_history(result)
        return result
    
    async def check_endpoint_async(self, endpoint: EndpointConfig) -> HealthCheckResult:
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(endpoint.retry_count):
                try:
                    if endpoint.method.upper() == "GET":
                        async with session.get(
                            endpoint.url,
                            headers=endpoint.headers,
                            timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                        ) as response:
                            response_time = (time.time() - start_time) * 1000
                            
                            if response.status == endpoint.expected_status:
                                if response_time <= endpoint.max_response_time * 1000:
                                    status = "healthy"
                                    error_message = None
                                else:
                                    status = "slow"
                                    error_message = f"Response time {response_time:.2f}ms exceeds threshold {endpoint.max_response_time * 1000}ms"
                            else:
                                status = "unhealthy"
                                error_message = f"Expected status {endpoint.expected_status}, got {response.status}"
                            
                            result = HealthCheckResult(
                                endpoint_name=endpoint.name,
                                url=endpoint.url,
                                status=status,
                                status_code=response.status,
                                response_time=response_time,
                                timestamp=datetime.now(),
                                error_message=error_message
                            )
                            
                            self._add_to_history(result)
                            return result
                    
                    elif endpoint.method.upper() == "POST":
                        async with session.post(
                            endpoint.url,