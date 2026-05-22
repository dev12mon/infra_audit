# requests.Session, Multithreading, and REST API integration

import requests
import concurrent.futures
import logging
from typing import List, Dict
from core.decorators import retry_with_backoff, time_it

logger = logging.getLogger(__name__)

class APIHealthChecker:
    """Manages concurrent REST API interactions."""
    
    def __init__(self):
        # Session pooling reuses underlying TCP connections for efficiency
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "InfraAudit-Agent/1.0",
            "Accept": "application/json"
        })

    @retry_with_backoff(max_attempts=3, delay=1, exceptions=(requests.ConnectionError, requests.Timeout))
    def _check_endpoint(self, url: str) -> Dict[str, str]:
        """
        Validates a single endpoint. Uses the retry decorator for transient network drops.
        """
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status() # Automatically handles 4xx/5xx errors
            return {"url": url, "status": "UP", "code": response.status_code}
        except requests.HTTPError as e:
            return {"url": url, "status": "DOWN", "error": str(e)}

    @time_it
    def check_multiple_endpoints(self, urls: List[str]) -> List[Dict[str, str]]:
        """
        Uses multithreading to check APIs concurrently. 
        Highly effective for network I/O bound tasks, overcoming the Python GIL constraint.
        """
        results = []
        # Using ThreadPoolExecutor instead of ProcessPoolExecutor because tasks are I/O bound, not CPU bound
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Map the function to the list of URLs
            future_to_url = {executor.submit(self._check_endpoint, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    data = future.result()
                    results.append(data)
                except Exception as exc:
                    url = future_to_url[future]
                    logger.error(f"{url} generated an exception: {exc}")
                    results.append({"url": url, "status": "ERROR"})
                    
        return results