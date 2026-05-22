# Generators, memory efficiency, and Sets for O(1) lookups

import logging
from typing import Iterator, Set

logger = logging.getLogger(__name__)

class LogAnalyzer:
    """Handles high-volume log parsing with strict memory constraints."""
    
    @staticmethod
    def _read_chunks(filepath: str) -> Iterator[str]:
        """
        Generator function yielding lines one by one. 
        Prevents memory exhaustion on 10GB+ files by avoiding readlines().
        """
        try:
            with open(filepath, 'r') as file:
                for line in file:
                    yield line.strip()
        except FileNotFoundError:
            logger.error(f"Log file not found: {filepath}")
            # Letting the error propagate or returning empty generator
            return

    @classmethod
    def find_unique_failed_hosts(cls, filepath: str, error_pattern: str = "CRITICAL") -> Set[str]:
        """
        Scans a log file for a specific pattern and extracts unique hostnames.
        Uses a Set for automatic deduplication and O(1) membership checks.
        """
        failed_hosts = set()
        
        # Consuming the generator
        for line in cls._read_chunks(filepath):
            if error_pattern in line:
                # Naive split for example purposes: assuming format "TIMESTAMP HOSTNAME ERROR_MSG"
                parts = line.split()
                if len(parts) > 1:
                    hostname = parts[1]
                    failed_hosts.add(hostname)
                    
        return failed_hosts