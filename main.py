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