"""
DynamoDB Table Lister

This script lists all tables in cloud DynamoDB across different regions.
It automatically retrieves AWS credentials via SSO and uses configuration from .env file.
"""
from models.environment_config import EnvironmentConfig
from models.role_credentials import RoleCredentials

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pathlib import Path

from mypy_boto3_dynamodb import DynamoDBClient

from get_sso_credentials import get_aws_sso_credentials

from utils.common_utils import load_config_from_env


class DynamoDBTableLister:
    def __init__(self):
        """
        Initialize the DynamoDB Table Lister.
        Loads configuration from .env file.
        """
        self._load_config()
        self._load_credentials()

    def list_tables_in_region(self, region: str | None = None) -> list[str]:
        """
        List all tables in the specified region.

        Args:
            region (str | None): AWS region to check. If None, uses config region.

        Returns:
            List[str]: List of table names
        """
        if region is None:
            region = self.config.aws_region

        try:
            print(f"🔍 Listing tables in region: {region}")
            client = self._create_client(region)

            # Test connection first
            client.list_tables(Limit=1)
            print(f"✓ Successfully connected to DynamoDB in {region}")

            # Get all tables
            paginator = client.get_paginator('list_tables')
            page_iterator = paginator.paginate()

            all_tables = []
            for page in page_iterator:
                all_tables.extend(page.get('TableNames', []))

            return sorted(all_tables)

        except ClientError as e:
            if e.response['Error']['Code'] == 'UnrecognizedClientException':
                print(f"❌ Error: Invalid AWS credentials for region {region}")
            elif e.response['Error']['Code'] == 'AccessDeniedException':
                print(f"❌ Error: Access denied to region {region}")
            else:
                print(f"❌ Error in region {region}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error connecting to region {region}: {e}")
            return []

    def display_tables(self, tables: list[str], region: str, filter_prefix: str) -> None:
        """
        Display the list of tables with formatting.

        Args:
            tables (List[str]): List of table names
            region (str): AWS region
            filter_prefix (str): Optional prefix to filter tables
        """
        if not tables:
            print(f"📋 No tables found in region {region}")
            return

        # Filter tables if prefix is specified
        if filter_prefix:
            filtered_tables = [
                t for t in tables if t.startswith(filter_prefix)]
            if filtered_tables:
                print(
                    f"📋 Found {len(filtered_tables)} table(s) with prefix '{filter_prefix}' in {region}:")
                for i, table in enumerate(filtered_tables, 1):
                    print(f"  {i:3d}. {table}")
            else:
                print(
                    f"📋 No tables found with prefix '{filter_prefix}' in {region}")
                print(f"💡 Total tables in region: {len(tables)}")
        else:
            print(f"📋 Found {len(tables)} table(s) in {region}:")
            for i, table in enumerate(tables, 1):
                print(f"  {i:3d}. {table}")

        # Show common prefixes
        if not filter_prefix and tables:
            prefixes = {}
            for table in tables:
                if '_' in table:
                    prefix = table.split('_')[0] + '_'
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1

            if prefixes:
                print(f"\n📊 Common prefixes found:")
                for prefix, count in sorted(prefixes.items(), key=lambda x: x[1], reverse=True):
                    if count >= 2:  # Only show prefixes with 2+ tables
                        print(f"  • {prefix}: {count} tables")

    def check_multiple_regions(self, filter_prefix: str) -> dict[str, list[str]]:
        """
        Check for tables across multiple AWS regions.

        Args:
            filter_prefix (str): Optional prefix to filter tables

        Returns:
            dict[str, list[str]]: Dictionary mapping regions to table lists
        """
        regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
            'ap-south-1', 'ca-central-1', 'sa-east-1'
        ]

        print("🌍 Checking for tables across multiple AWS regions...")
        found_tables = {}

        for region in regions:
            tables = self.list_tables_in_region(region)
            if tables:
                if filter_prefix:
                    filtered_tables = [
                        t for t in tables if t.startswith(filter_prefix)]
                    if filtered_tables:
                        found_tables[region] = filtered_tables
                else:
                    found_tables[region] = tables

        return found_tables

    def search_table(self, table_name: str) -> dict[str, bool]:
        """
        Search for a specific table across multiple regions.

        Args:
            table_name (str): Name of the table to search for

        Returns:
            dict[str, bool]: Dictionary mapping regions to whether table exists
        """
        regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
            'ap-south-1', 'ca-central-1', 'sa-east-1'
        ]

        print(f"🔍 Searching for table '{table_name}' across regions...")
        results = {}

        for region in regions:
            try:
                client = self._create_client(region)
                client.describe_table(TableName=table_name)
                results[region] = True
                print(f"  ✓ Found '{table_name}' in {region}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    results[region] = False
                else:
                    print(f"  ❌ Error checking {region}: {e}")
                    results[region] = False
            except Exception as e:
                print(f"  ❌ Error checking {region}: {e}")
                results[region] = False

        return results

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        try:
            self.config: EnvironmentConfig = load_config_from_env()
            print("✓ Configuration loaded successfully")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)

    def _load_credentials(self) -> None:
        """Load AWS credentials using SSO."""
        print("🔐 Getting AWS credentials via SSO...")
        creds_data: RoleCredentials | None = get_aws_sso_credentials(
            self.config)

        if not creds_data:
            print("❌ Error: Failed to get credentials via SSO")
            sys.exit(1)

        self.credentials: RoleCredentials = creds_data
        print("✓ Credentials obtained via SSO")

    def _create_client(self, region: str) -> DynamoDBClient:
        """Create a DynamoDB client for the specified region."""

        return boto3.client(
            'dynamodb',
            aws_access_key_id=self.credentials.access_key_id,
            aws_secret_access_key=self.credentials.secret_access_key,
            aws_session_token=self.credentials.session_token,
            region_name=region
        )


def main():
    """Main function to run the table lister."""
    parser = argparse.ArgumentParser(
        description='List DynamoDB tables in cloud AWS'
    )
    parser.add_argument(
        '--region',
        help='Specific AWS region to check (overrides .env file)'
    )
    parser.add_argument(
        '--all-regions',
        action='store_true',
        help='Check all major AWS regions'
    )
    parser.add_argument(
        '--prefix',
        help='Filter tables by prefix (e.g., "dev_", "prod_")'
    )
    parser.add_argument(
        '--search',
        help='Search for a specific table name across regions'
    )

    args = parser.parse_args()

    # Initialize the lister (reads from .env automatically)
    lister = DynamoDBTableLister()

    if args.search:
        # Search for specific table
        results = lister.search_table(args.search)
        found_regions = [region for region, found in results.items() if found]

        if found_regions:
            print(
                f"\n🎯 Table '{args.search}' found in {len(found_regions)} region(s):")
            for region in found_regions:
                print(f"  • {region}")
        else:
            print(
                f"\n❌ Table '{args.search}' not found in any checked regions")

    elif args.all_regions:
        # Check all regions
        found_tables = lister.check_multiple_regions(args.prefix)

        if found_tables:
            print(f"\n📋 Summary of tables found across regions:")
            total_tables = 0
            for region, tables in found_tables.items():
                total_tables += len(tables)
                print(f"\n🌍 Region: {region}")
                lister.display_tables(tables, region, args.prefix)

            print(
                f"\n📊 Total tables found: {total_tables} across {len(found_tables)} regions")
        else:
            filter_msg = f" with prefix '{args.prefix}'" if args.prefix else ""
            print(f"\n📋 No tables found{filter_msg} in any checked regions")

    else:
        # Check single region
        region = args.region or lister.config.aws_region
        tables = lister.list_tables_in_region(region)
        lister.display_tables(tables, region, args.prefix)


if __name__ == "__main__":
    main()
