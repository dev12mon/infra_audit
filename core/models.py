# inheritance, and __init__ constructors

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
