## Architecture Overview

```
infra_audit/
│
├── core/
│   ├── __init__.py
│   ├── decorators.py       # Retries, Timers
│   ├── exceptions.py       # Custom error handling
│   └── models.py           # OOP Base classes
│
├── services/
│   ├── __init__.py
│   ├── log_parser.py       # Generators and memory optimization
│   └── health_checker.py   # Multithreading and API sessions
│
└── main.py                 # Execution entrypoint
```



This is an excellent strategy. Preparing for senior-level SRE and Platform Engineering interviews requires shifting the narrative from "I use these tools" to "I engineer automation systems." The interview transcripts make it clear: interviewers are actively weeding out candidates who only know how to trigger Jenkins jobs but lack the Python fluency, object-oriented design, and memory management skills required to build production-grade infrastructure tooling.

To hit every requirement you mentioned—OOP, decorators, generators, multithreading, API sessions, and error handling—we are going to build **InfraAudit (v1.0)**.

This is a production-ready Infrastructure Health & Log Analyzer. It simulates a real-world Platform Engineering task: fetching cloud inventory, performing concurrent health checks via APIs, and parsing massive local logs for anomalies without crashing the system.

Here is your end-to-end project, starting with the Sr. SRE-level README, followed by the complete, heavily commented Python codebase.

---

### **Project README: InfraAudit**

**Title:** InfraAudit: Extensible Infrastructure Health & Audit Engine
**Author:** Ravi Pratap Singh
**Role:** Senior Site Reliability Engineer / Platform Engineer

#### **Overview**

InfraAudit is a modular, Python-based automation engine designed to validate infrastructure health, audit cloud inventory, and process high-volume application logs. Built with memory optimization and concurrent execution in mind, it serves as a foundation for scalable Platform Engineering workflows.

#### **Architecture & Design Patterns**

This project demonstrates enterprise-grade Python automation maturity by implementing:

* 
**Object-Oriented Programming (OOP):** Extensible base classes for cloud providers, allowing seamless additions of GCP or Azure alongside AWS.


* 
**Memory Optimization (Generators):** Lazy-evaluation pipelines for processing 10GB+ log files using a fraction of system RAM (O(1) memory complexity for file reads).


* 
**Advanced Decorators:** Custom wrapper functions for exponential backoff retries and execution timing, ensuring resilient API interactions.


* 
**Concurrency:** Thread-pool execution for network-bound tasks (API health checks) to drastically reduce execution time.


* 
**Connection Pooling:** Utilizes `requests.Session()` to reuse TCP connections, avoiding socket exhaustion during mass API checks.



#### **Future Roadmap (Phase 2 & 3)**

* **Containerization:** Multi-stage Dockerfile for lightweight execution.
* **Orchestration:** Helm charts for Kubernetes CronJob deployment.
* **Observability:** Prometheus metrics exposition for execution times and failure rates.
* **CI/CD:** GitHub Actions pipeline with `pytest` and `flake8` enforcement.

---

### **The Codebase**

Structure this in your IDE as follows:

```text
infra_audit/
│
├── core/
│   ├── __init__.py
│   ├── decorators.py       # Retries, Timers
│   ├── exceptions.py       # Custom error handling
│   └── models.py           # OOP Base classes
│
├── services/
│   ├── __init__.py
│   ├── log_parser.py       # Generators and memory optimization
│   └── health_checker.py   # Multithreading and API sessions
│
└── main.py                 # Execution entrypoint

```

#### **1. `core/exceptions.py**`

Demonstrates structured exception handling.

```python
class InfraAuditError(Exception):
    """Base exception for all InfraAudit errors."""
    pass

class APIConnectionError(InfraAuditError):
    """Raised when an external API cannot be reached after retries."""
    pass

```

#### **2. `core/decorators.py**`

Demonstrates higher-order functions, retries, and execution timing.

```python
import time
import functools
import logging
from typing import Callable, Any
from .exceptions import APIConnectionError

logger = logging.getLogger(__name__)

def time_it(func: Callable) -> Callable:
    """Decorator to measure the execution time of functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Execution of {func.__name__} took {end_time - start_time:.4f} seconds.")
        return result
    return wrapper

def retry_with_backoff(max_attempts: int = 3, delay: int = 2, exceptions: tuple = (Exception,)) -> Callable:
    """
    Decorator that retries a function with exponential backoff if specific exceptions are raised.
    Critical for resilient API calls in CI/CD and automation scripts.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise APIConnectionError(f"Failed after {max_attempts} retries.") from e
                    
                    sleep_time = delay * (2 ** (attempt - 1)) # Exponential backoff
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
        return wrapper
    return decorator

```

#### **3. `core/models.py**`

Demonstrates OOP, inheritance, and `__init__` constructors.

```python
import boto3
from abc import ABC, abstractmethod
from typing import List, Dict

class CloudProvider(ABC):
    """
    Abstract base class enforcing a standard interface for all cloud integrations.
    Demonstrates OOP inheritance and encapsulation.
    """
    def __init__(self, name: str, region: str):
        self.name = name
        self.region = region

    @abstractmethod
    def fetch_inventory(self) -> List[Dict]:
        """Must be implemented by child classes to return normalized inventory."""
        pass

class AWSProvider(CloudProvider):
    """
    AWS implementation using boto3.
    """
    def __init__(self, region: str = "ap-south-1"):
        super().__init__(name="AWS", region=region)
        # Initializes session once per instance
        self.session = boto3.Session(region_name=self.region)
        self.ec2_client = self.session.client('ec2')

    def fetch_inventory(self) -> List[Dict]:
        """Fetches all running EC2 instances and returns standardized dicts."""
        instances = []
        try:
            # Paginator handles large numbers of instances natively
            paginator = self.ec2_client.get_paginator('describe_instances')
            page_iterator = paginator.paginate(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            for page in page_iterator:
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        # Safely extract Name tag, defaulting to Unnamed
                        name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), "Unnamed")
                        instances.append({
                            "id": instance['InstanceId'],
                            "name": name,
                            "ip": instance.get('PrivateIpAddress', 'N/A')
                        })
            return instances
        except Exception as e:
            # Catching generic Exception here as a fallback, but would normally catch botocore exceptions
            raise RuntimeError(f"AWS API Error: {e}")

```

#### **4. `services/log_parser.py**`

Demonstrates Generators, memory efficiency, and Sets for O(1) lookups.

```python
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

```

#### **5. `services/health_checker.py**`

Demonstrates `requests.Session`, Multithreading, and REST API integration.

```python
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

```

#### **6. `main.py**`

*The orchestration script tying it all together cleanly.*

```python
import logging
from core.models import AWSProvider
from services.log_parser import LogAnalyzer
from services.health_checker import APIHealthChecker
from core.decorators import time_it

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("InfraAudit-Main")

@time_it
def main():
    logger.info("Starting InfraAudit Pipeline...")
    
    # 1. OOP & Cloud SDK Integration
    logger.info("=== Fetching AWS Inventory ===")
    aws = AWSProvider(region="ap-south-1")
    try:
        # Note: boto3 requires valid credentials. If running locally without creds, 
        # comment this block out or ensure AWS_PROFILE is set.
        inventory = aws.fetch_inventory()
        logger.info(f"Discovered {len(inventory)} running EC2 instances.")
    except Exception as e:
        logger.error(f"Failed to fetch inventory: {e}")

    # 2. Generators & Large File Processing
    logger.info("=== Analyzing Local Application Logs ===")
    # Create a dummy log file for testing purposes if it doesn't exist
    with open("dummy_app.log", "w") as f:
        f.write("2026-05-22 server-1 INFO Booting up\n")
        f.write("2026-05-22 server-2 CRITICAL Kernel panic\n")
        f.write("2026-05-22 server-2 CRITICAL OOM Killer\n") # Duplicate to test Set logic
        
    unique_failed_hosts = LogAnalyzer.find_unique_failed_hosts("dummy_app.log", error_pattern="CRITICAL")
    logger.info(f"Found {len(unique_failed_hosts)} unique hosts with CRITICAL errors: {unique_failed_hosts}")

    # 3. Multithreading & API Requests
    logger.info("=== Executing Concurrent Health Checks ===")
    urls_to_check = [
        "https://httpstat.us/200",
        "https://httpstat.us/500",  # Will trigger error handling
        "https://httpstat.us/200?sleep=1000",
    ]
    
    checker = APIHealthChecker()
    health_results = checker.check_multiple_endpoints(urls_to_check)
    
    for result in health_results:
        logger.info(f"Health Check Result: {result}")

    logger.info("InfraAudit Pipeline Completed.")

if __name__ == "__main__":
    main()

```









The project structure in your VS Code looks solid. Given the multi-service layout in your workspace (`cl_platform_svc`, `gist_svc`, `infra_audit`), the best next step is to initialize `infra_audit` as its own dedicated Git repository to keep its lifecycle and CI/CD pipelines decoupled from the other services.

Here is the step-by-step guide to locking this code in locally and pushing it to a remote private repository (like GitHub, GitLab, or Bitbucket).

### 1. Set Up Your `.gitignore`

Before initializing Git, ensure you prevent Python cache files and potential secrets from being tracked.

Navigate into your project folder in your VS Code terminal:

```bash
cd applications/infra_audit

```

Create a `.gitignore` file:

```bash
touch .gitignore

```

Add the following standard Python exclusions to it:

```text
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Environments
.env
.venv
env/
venv/
ENV/

# OS generated files
.DS_Store

# IDEs
.vscode/

```

### 2. Initialize and Commit Locally

With your ignore rules in place, initialize the repository and make your first commit.

```bash
# Initialize the local repository
git init

# Stage all project files
git add .

# Commit with a clear, conventional message
git commit -m "feat: initial commit of InfraAudit core engine and health services"

```

### 3. Create the Private Remote Repository

1. Log in to your Git hosting provider (e.g., GitHub, GitLab, or Bitbucket).
2. Click **New Repository** (or equivalent).
3. Name the repository `infra_audit`.
4. **Crucial:** Select the **Private** visibility option so the code is not exposed publicly.
5. Do *not* initialize the repository with a README, `.gitignore`, or license via the web interface, as you already have local files ready to push.
6. Click **Create repository**.

### 4. Link and Push to Remote

Your Git provider will present a set of commands to push an existing repository from the command line. It will look exactly like this:

```bash
# Rename the default branch to 'main' (if your local git still defaults to 'master')
git branch -M main

# Link your local repo to the remote destination (replace the URL with your actual repo URL)
git remote add origin git@github.com:<your-username>/infra_audit.git

# Push the code and set the upstream tracking branch
git push -u origin main

```

### Next Steps for the Project

Once the code is safely in a private repository, the logical next steps for this project's evolution are:

* **Dependency Management:** Generate a `requirements.txt` or `Pipfile` locking in the versions of `boto3` and `requests`.
* **Containerization:** Draft a `Dockerfile` using a slim Python base image to ensure the environment is reproducible.
* **Testing:** Add a `tests/` directory and write a few `pytest` functions mocking the AWS API responses to validate your OOP models and retry decorators without hitting real endpoints.





This is exactly the right sequence. In Platform Engineering, you don't push to production without automated tests, a highly optimized artifact, and a CI pipeline to enforce the standards.

Here is the complete engineering setup for the next phase: Unit Testing, a Multi-Stage Dockerfile, and a GitHub Actions pipeline.

---

### 1. Unit Testing: Mocking APIs & Retries

Testing infrastructure code requires mocking external dependencies (like AWS APIs or HTTP endpoints) so tests run fast, offline, and deterministically. We will use `pytest` and `unittest.mock`.

Create a `tests/` directory and add `test_health_checker.py`:

```python
# tests/test_health_checker.py
import pytest
from unittest.mock import patch, MagicMock
from services.health_checker import APIHealthChecker
import requests
from core.exceptions import APIConnectionError

@pytest.fixture
def health_checker():
    return APIHealthChecker()

@patch('requests.Session.get')
def test_check_endpoint_success(mock_get, health_checker):
    """Test that a 200 OK response is parsed correctly without retries."""
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    result = health_checker._check_endpoint("https://fake-api.com/health")
    
    assert result['status'] == "UP"
    assert result['code'] == 200
    assert mock_get.call_count == 1

@patch('requests.Session.get')
def test_check_endpoint_retry_logic(mock_get, health_checker):
    """Test that the retry decorator attempts exactly 3 times on connection errors."""
    # Force the mock to raise a ConnectionError every time it's called
    mock_get.side_effect = requests.ConnectionError("Network down")

    with pytest.raises(APIConnectionError):
        health_checker._check_endpoint("https://fake-api.com/health")
    
    # Verify the backoff decorator actually retried 3 times before failing
    assert mock_get.call_count == 3

```

**To run the tests locally:**
Add `pytest` to your requirements or environment, then run:

```bash
python -m pytest tests/ -v

```

---

### 2. The Multi-Stage Production Dockerfile

A standard Dockerfile leaves build tools and caching artifacts in the final image, bloating the size and increasing the security attack surface.

A **Multi-Stage Build** fixes this by using a "builder" stage to compile dependencies into Python wheels, and a fresh, minimal "runtime" stage that only copies the compiled binaries and application code.

Replace your existing `Dockerfile` with this optimized version:

```dockerfile
# ==========================================
# STAGE 1: Builder
# Compiles dependencies and generates wheels
# ==========================================
FROM python:3.11-slim as builder

# Install build dependencies (gcc, etc.) needed for compiling Python C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copy only requirements to cache this layer
COPY requirements.txt .

# Build wheels for all dependencies to avoid installing build tools in final image
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

# ==========================================
# STAGE 2: Runtime
# Minimal final image optimized for space and security
# ==========================================
FROM python:3.11-slim

# Set strict Python runtime configurations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Create a non-root system user and group for security
RUN addgroup --system appgroup && \
    adduser --system --group appuser

WORKDIR /app

# Copy compiled wheels from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

# Install the pre-compiled wheels (no build tools needed here)
RUN pip install --no-cache /wheels/*

# Copy application source code and set ownership to the non-root user
COPY --chown=appuser:appgroup . .

# Switch to the restricted user
USER appuser

# Execute the application
CMD ["python", "main.py"]

```

---

### 3. GitHub Actions CI Pipeline (GA CI)

Now we wire it up so that every push to the repository runs the unit tests, checks for syntax errors, and verifies the multi-stage Docker build succeeds.

Create the file `.github/workflows/ci.yml`:

```yaml
name: InfraAudit CI Pipeline

# Trigger on pushes and PRs to the main branch
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  test:
    name: Run Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: 'pip' # Leverages GitHub's built-in caching for pip

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest flake8

      - name: Lint with Flake8
        run: |
          # Stop the build if there are Python syntax errors or undefined names
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run Pytest
        run: |
          pytest tests/ -v

  docker-build:
    name: Verify Multi-Stage Docker Build
    needs: test # Ensure tests pass before spending compute on Docker build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and Cache Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false # Set to true later when deploying to a registry (GCR/ECR)
          tags: infra-audit:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

```

### Why this setup stands out:

1. **The Pytest fixture** ensures the retry decorator is mathematically validated to hit `max_attempts=3`.
2. **The Dockerfile** drops the `gcc` compiler from the final image, significantly reducing the image size and eliminating common CVE vulnerabilities associated with OS-level build tools.
3. **The GitHub Action** utilizes `cache-from: type=gha`, meaning subsequent Docker builds in CI will use GitHub's cache API, dropping build times from minutes to seconds.

Once this CI pipeline is green and the image is compiling cleanly, we are ready for orchestration and deployment. Would you prefer to tackle the Kubernetes manifests (Deployments/CronJobs) next, or set up Terraform to provision the underlying GCP/AWS infrastructure?











Ah, the classic macOS global Python trap. You are currently hitting the system-level Python installation (specifically, a framework install of 3.14), which doesn't have `pytest` installed.

As a best practice in Platform Engineering, we strictly avoid installing packages into the global OS environment to prevent dependency conflicts and "it works on my machine" syndromes. We need to sandbox this project using a virtual environment (`venv`).

Here is the exact sequence to isolate your workspace, install the dependencies, and run the tests.

Run these commands in your VS Code terminal:

### 1. Create and Activate a Virtual Environment

```bash
# Create a hidden virtual environment directory named .venv
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

```

*(Tip: Once activated, your terminal prompt will usually update to show `(.venv)` on the left. From this point on, typing `python` or `pip` will automatically use the isolated environment, not the macOS global one.)*

### 2. Install Dependencies

Now that you are sandboxed, install your pinned project requirements along with the testing framework:

```bash
pip install -r requirements.txt pytest

```

### 3. Execute the Tests

With `pytest` installed inside the virtual environment, your original command will now execute perfectly:

```bash
python -m pytest tests/ -v

```

---

Once those unit tests light up green in your terminal, the local foundation of `InfraAudit` is rock solid. Shall we move on to drafting the Kubernetes manifests (Deployments/CronJobs) for orchestration, or would you prefer to set up the Terraform state to provision the underlying cloud infrastructure first?