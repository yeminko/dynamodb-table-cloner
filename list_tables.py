#!/usr/bin/env python3
"""
DynamoDB Table Lister

This script lists all tables in cloud DynamoDB across different regions.
It reads AWS credentials from a JSON file and shows available tables.
"""

import json
import boto3
import argparse
import sys
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List


class DynamoDBTableLister:
    def __init__(self, credentials_file: str, config_file: str = 'config.json'):
        """
        Initialize the DynamoDB Table Lister.
        
        Args:
            credentials_file (str): Path to the JSON file containing AWS credentials
            config_file (str): Path to the JSON file containing configuration
        """
        self.credentials_file = credentials_file
        self.config_file = config_file
        self._load_config()
        self._load_credentials()

    def _load_config(self) -> None:
        """Load configuration from the JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                print(f"✓ Configuration loaded from {self.config_file}")
        except FileNotFoundError:
            # Use default configuration if file not found
            self.config = {
                "aws_region": "us-east-1"
            }
            print(f"⚠️  Configuration file '{self.config_file}' not found. Using defaults.")
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _load_credentials(self) -> None:
        """Load AWS credentials from the JSON file."""
        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)
                self.credentials = data['roleCredentials']
                print(f"✓ Credentials loaded from {self.credentials_file}")
        except FileNotFoundError:
            print(f"❌ Error: Credentials file '{self.credentials_file}' not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"❌ Error: Missing key {e} in credentials file.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in credentials file: {e}")
            sys.exit(1)

    def _create_client(self, region: str) -> boto3.client:
        """Create a DynamoDB client for the specified region."""
        return boto3.client(
            'dynamodb',
            aws_access_key_id=self.credentials['accessKeyId'],
            aws_secret_access_key=self.credentials['secretAccessKey'],
            aws_session_token=self.credentials['sessionToken'],
            region_name=region
        )

    def list_tables_in_region(self, region: str = None) -> List[str]:
        """
        List all tables in the specified region.
        
        Args:
            region (str): AWS region to check. If None, uses config region.
            
        Returns:
            List[str]: List of table names
        """
        if region is None:
            region = self.config['aws_region']
            
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

    def display_tables(self, tables: List[str], region: str, filter_prefix: str = None) -> None:
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
            filtered_tables = [t for t in tables if t.startswith(filter_prefix)]
            if filtered_tables:
                print(f"📋 Found {len(filtered_tables)} table(s) with prefix '{filter_prefix}' in {region}:")
                for i, table in enumerate(filtered_tables, 1):
                    print(f"  {i:3d}. {table}")
            else:
                print(f"📋 No tables found with prefix '{filter_prefix}' in {region}")
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

    def check_multiple_regions(self, filter_prefix: str = None) -> Dict[str, List[str]]:
        """
        Check for tables across multiple AWS regions.
        
        Args:
            filter_prefix (str): Optional prefix to filter tables
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping regions to table lists
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
                    filtered_tables = [t for t in tables if t.startswith(filter_prefix)]
                    if filtered_tables:
                        found_tables[region] = filtered_tables
                else:
                    found_tables[region] = tables
        
        return found_tables

    def search_table(self, table_name: str) -> Dict[str, bool]:
        """
        Search for a specific table across multiple regions.
        
        Args:
            table_name (str): Name of the table to search for
            
        Returns:
            Dict[str, bool]: Dictionary mapping regions to whether table exists
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


def main():
    """Main function to run the table lister."""
    parser = argparse.ArgumentParser(
        description='List DynamoDB tables in cloud AWS'
    )
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        help='Path to the JSON file containing AWS credentials (default: credentials.json)'
    )
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to the JSON file containing configuration (default: config.json)'
    )
    parser.add_argument(
        '--region',
        help='Specific AWS region to check (overrides config file)'
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
    
    # Initialize the lister
    lister = DynamoDBTableLister(args.credentials, args.config)
    
    if args.search:
        # Search for specific table
        results = lister.search_table(args.search)
        found_regions = [region for region, found in results.items() if found]
        
        if found_regions:
            print(f"\n🎯 Table '{args.search}' found in {len(found_regions)} region(s):")
            for region in found_regions:
                print(f"  • {region}")
        else:
            print(f"\n❌ Table '{args.search}' not found in any checked regions")
            
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
            
            print(f"\n📊 Total tables found: {total_tables} across {len(found_tables)} regions")
        else:
            filter_msg = f" with prefix '{args.prefix}'" if args.prefix else ""
            print(f"\n📋 No tables found{filter_msg} in any checked regions")
            
    else:
        # Check single region
        region = args.region or lister.config['aws_region']
        tables = lister.list_tables_in_region(region)
        lister.display_tables(tables, region, args.prefix)


if __name__ == "__main__":
    main()