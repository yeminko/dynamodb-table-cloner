"""
DynamoDB Table Cloner

This script clones a table from cloud DynamoDB to local DynamoDB.
It automatically retrieves AWS credentials via SSO and uses configuration from .env file.
"""

import os
import boto3
import argparse
import sys
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path
from get_sso_credentials import get_aws_sso_credentials


class DynamoDBTableCloner:
    def __init__(self):
        """
        Initialize the DynamoDB Table Cloner.
        Loads configuration from .env file.
        """
        self.cloud_client = None
        self.local_client = None
        self._load_config()
        self._load_credentials()
        self._initialize_clients()

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        # Load .env file
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            print(f"❌ Error: .env file not found at {env_path}")
            print("💡 Please create a .env file based on .env.template")
            sys.exit(1)

        load_dotenv(env_path)

        # Load configuration from environment variables
        self.config = {
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "local_dynamodb_endpoint": os.getenv("LOCAL_DYNAMODB_ENDPOINT", "http://localhost:8000"),
            "local_table_prefix": os.getenv("LOCAL_TABLE_PREFIX", "local_"),
            "batch_size": int(os.getenv("BATCH_SIZE", "25"))
        }
        print("✓ Configuration loaded from .env file")

    def _load_credentials(self) -> None:
        """Load AWS credentials using SSO."""
        print("🔐 Getting AWS credentials via SSO...")
        creds_data = get_aws_sso_credentials()
        if not creds_data:
            print("❌ Error: Failed to get credentials via SSO")
            sys.exit(1)
        self.credentials = creds_data['roleCredentials']
        print("✓ Credentials obtained via SSO")

    def _initialize_clients(self) -> None:
        """Initialize DynamoDB clients for cloud and local."""
        try:
            # Cloud DynamoDB client
            self.cloud_client = boto3.client(
                'dynamodb',
                aws_access_key_id=self.credentials['accessKeyId'],
                aws_secret_access_key=self.credentials['secretAccessKey'],
                aws_session_token=self.credentials['sessionToken'],
                region_name=self.config['aws_region']
            )

            # Local DynamoDB client
            self.local_client = boto3.client(
                'dynamodb',
                endpoint_url=self.config['local_dynamodb_endpoint'],
                region_name=self.config['aws_region'],
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )

            print("✓ DynamoDB clients initialized")

            # Test cloud DynamoDB connection
            self._test_cloud_connection()

        except Exception as e:
            print(f"❌ Error initializing DynamoDB clients: {e}")
            sys.exit(1)

    def _test_cloud_connection(self) -> None:
        """Test the connection to cloud DynamoDB."""
        try:
            # Try to list tables to verify credentials work
            response = self.cloud_client.list_tables(Limit=1)
            print("✓ Successfully connected to cloud DynamoDB")
        except ClientError as e:
            if e.response['Error']['Code'] == 'UnrecognizedClientException':
                print("❌ Error: Invalid AWS credentials")
            elif e.response['Error']['Code'] == 'AccessDeniedException':
                print("❌ Error: Access denied. Check your AWS permissions.")
            else:
                print(f"❌ Error connecting to cloud DynamoDB: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error testing cloud connection: {e}")
            sys.exit(1)

    def _get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get the schema of the source table from cloud DynamoDB.

        Args:
            table_name (str): Name of the source table

        Returns:
            Dict[str, Any]: Table schema information
        """
        try:
            response = self.cloud_client.describe_table(TableName=table_name)
            return response['Table']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(
                    f"❌ Error: Table '{table_name}' not found in cloud DynamoDB.")
                print("📋 Let me check what tables are available...")
                self._list_available_tables()
            else:
                print(f"❌ Error describing table: {e}")
            sys.exit(1)

    def _list_available_tables(self) -> None:
        """List all available tables in cloud DynamoDB."""
        try:
            print("🔍 Listing available tables in cloud DynamoDB...")
            paginator = self.cloud_client.get_paginator('list_tables')
            page_iterator = paginator.paginate()

            all_tables = []
            for page in page_iterator:
                all_tables.extend(page.get('TableNames', []))

            if not all_tables:
                print("📋 No tables found in cloud DynamoDB.")
            else:
                print(f"📋 Found {len(all_tables)} table(s) in cloud DynamoDB:")
                for i, table in enumerate(sorted(all_tables), 1):
                    print(f"  {i}. {table}")

                # Show tables that match common prefixes
                dev_tables = [t for t in all_tables if t.startswith('dev_')]
                if dev_tables:
                    print(f"\n📋 Tables with 'dev_' prefix:")
                    for table in sorted(dev_tables):
                        print(f"  • {table}")

        except ClientError as e:
            print(f"❌ Error listing tables: {e}")
            print(
                "💡 This might indicate an issue with your AWS credentials or permissions.")

    def _check_multiple_regions(self) -> None:
        """Check for tables across multiple AWS regions."""
        regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
        ]

        print("🌍 Checking for tables across multiple AWS regions...")
        found_tables = {}

        for region in regions:
            try:
                print(f"🔍 Checking region: {region}")
                regional_client = boto3.client(
                    'dynamodb',
                    aws_access_key_id=self.credentials['accessKeyId'],
                    aws_secret_access_key=self.credentials['secretAccessKey'],
                    aws_session_token=self.credentials['sessionToken'],
                    region_name=region
                )

                paginator = regional_client.get_paginator('list_tables')
                page_iterator = paginator.paginate()

                region_tables = []
                for page in page_iterator:
                    region_tables.extend(page.get('TableNames', []))

                if region_tables:
                    found_tables[region] = region_tables
                    print(
                        f"  ✓ Found {len(region_tables)} table(s) in {region}")

            except ClientError as e:
                if e.response['Error']['Code'] in ['UnauthorizedOperation', 'AccessDenied']:
                    print(f"  ⚠️  No access to region {region}")
                else:
                    print(f"  ❌ Error checking {region}: {e}")
            except Exception as e:
                print(f"  ❌ Error checking {region}: {e}")

        if found_tables:
            print(f"\n📋 Summary of tables found across regions:")
            for region, tables in found_tables.items():
                print(f"\n🌍 Region: {region}")
                for table in sorted(tables):
                    print(f"  • {table}")

                # Highlight tables matching the search pattern
                dev_tables = [
                    t for t in tables if 'Dashboard' in t or t.startswith('dev_')]
                if dev_tables:
                    print(f"  🎯 Relevant tables:")
                    for table in dev_tables:
                        print(f"    → {table}")
        else:
            print("\n📋 No tables found in any checked regions.")
            print("💡 Possible reasons:")
            print("   • Tables might be in a region not checked")
            print("   • AWS credentials might not have DynamoDB permissions")
            print("   • Tables might be in a different AWS account")

    def _create_local_table(self, source_schema: Dict[str, Any], target_table_name: str) -> None:
        """
        Create the target table in local DynamoDB based on source schema.

        Args:
            source_schema (Dict[str, Any]): Schema of the source table
            target_table_name (str): Name of the target table
        """
        try:
            # Extract necessary schema information
            key_schema = source_schema['KeySchema']
            attribute_definitions = source_schema['AttributeDefinitions']

            # Set billing mode to PAY_PER_REQUEST for local DynamoDB
            table_params = {
                'TableName': target_table_name,
                'KeySchema': key_schema,
                'AttributeDefinitions': attribute_definitions,
                'BillingMode': 'PAY_PER_REQUEST'
            }

            # Add Global Secondary Indexes if they exist
            if 'GlobalSecondaryIndexes' in source_schema:
                gsi_list = []
                for gsi in source_schema['GlobalSecondaryIndexes']:
                    gsi_params = {
                        'IndexName': gsi['IndexName'],
                        'KeySchema': gsi['KeySchema'],
                        'Projection': gsi['Projection']
                    }
                    gsi_list.append(gsi_params)
                table_params['GlobalSecondaryIndexes'] = gsi_list

            # Add Local Secondary Indexes if they exist
            if 'LocalSecondaryIndexes' in source_schema:
                lsi_list = []
                for lsi in source_schema['LocalSecondaryIndexes']:
                    lsi_params = {
                        'IndexName': lsi['IndexName'],
                        'KeySchema': lsi['KeySchema'],
                        'Projection': lsi['Projection']
                    }
                    lsi_list.append(lsi_params)
                table_params['LocalSecondaryIndexes'] = lsi_list

            # Create the table
            self.local_client.create_table(**table_params)
            print(f"✓ Created table '{target_table_name}' in local DynamoDB")

            # Wait for table to be active
            waiter = self.local_client.get_waiter('table_exists')
            waiter.wait(TableName=target_table_name)
            print(f"✓ Table '{target_table_name}' is now active")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(
                    f"⚠️  Table '{target_table_name}' already exists in local DynamoDB")
            else:
                print(f"❌ Error creating local table: {e}")
                sys.exit(1)

    def _copy_table_data(self, source_table_name: str, target_table_name: str) -> None:
        """
        Copy all data from source table to target table.

        Args:
            source_table_name (str): Name of the source table
            target_table_name (str): Name of the target table
        """
        try:
            print(
                f"📊 Starting data migration from '{source_table_name}' to '{target_table_name}'...")

            # Scan the source table
            paginator = self.cloud_client.get_paginator('scan')
            page_iterator = paginator.paginate(TableName=source_table_name)

            item_count = 0
            # Use configurable batch size
            batch_size = self.config['batch_size']
            batch_items = []

            for page in page_iterator:
                items = page.get('Items', [])

                for item in items:
                    batch_items.append({
                        'PutRequest': {
                            'Item': item
                        }
                    })

                    # Write batch when it reaches the limit
                    if len(batch_items) >= batch_size:
                        self._write_batch(target_table_name, batch_items)
                        item_count += len(batch_items)
                        batch_items = []
                        print(f"📝 Migrated {item_count} items...")

            # Write remaining items
            if batch_items:
                self._write_batch(target_table_name, batch_items)
                item_count += len(batch_items)

            print(
                f"✅ Successfully migrated {item_count} items to '{target_table_name}'")

        except ClientError as e:
            print(f"❌ Error copying table data: {e}")
            sys.exit(1)

    def _write_batch(self, table_name: str, batch_items: list) -> None:
        """
        Write a batch of items to the target table.

        Args:
            table_name (str): Name of the target table
            batch_items (list): List of items to write
        """
        try:
            response = self.local_client.batch_write_item(
                RequestItems={
                    table_name: batch_items
                }
            )

            # Handle unprocessed items
            unprocessed = response.get('UnprocessedItems', {})
            while unprocessed:
                print("⏳ Retrying unprocessed items...")
                response = self.local_client.batch_write_item(
                    RequestItems=unprocessed
                )
                unprocessed = response.get('UnprocessedItems', {})

        except ClientError as e:
            print(f"❌ Error writing batch: {e}")
            raise

    def _generate_target_table_name(self, source_table_name: str) -> str:
        """
        Generate the target table name by replacing environment prefix with local prefix.

        Examples:
            dev_users -> local_users
            qa_orders -> local_orders
            stg_products -> local_products
            test_data -> local_data
            users -> local_users (no prefix to replace)

        Args:
            source_table_name (str): Name of the source table

        Returns:
            str: Target table name with local prefix
        """
        # Environment prefixes to replace (as specified in requirements)
        env_prefixes = ['dev_', 'qa_', 'stg_', 'test_']

        # Check if the table name starts with any environment prefix
        for env_prefix in env_prefixes:
            if source_table_name.startswith(env_prefix):
                # Replace the environment prefix with local prefix
                base_name = source_table_name[len(env_prefix):]
                return f"{self.config['local_table_prefix']}{base_name}"

        # If no environment prefix found, just add local prefix
        return f"{self.config['local_table_prefix']}{source_table_name}"

    def clone_table(self, source_table_name: str) -> None:
        """
        Clone a table from cloud DynamoDB to local DynamoDB.

        Args:
            source_table_name (str): Name of the source table in cloud DynamoDB
        """
        # Generate target table name by replacing environment prefix with local prefix
        target_table_name = self._generate_target_table_name(source_table_name)

        print(f"🚀 Starting table cloning process...")
        print(f"📋 Source table: {source_table_name}")
        print(f"📋 Target table: {target_table_name}")

        # Step 1: Get source table schema
        print(f"🔍 Getting schema for table '{source_table_name}'...")
        source_schema = self._get_table_schema(source_table_name)

        # Step 2: Create target table in local DynamoDB
        print(f"🏗️  Creating table '{target_table_name}' in local DynamoDB...")
        self._create_local_table(source_schema, target_table_name)

        # Step 3: Copy data from source to target
        self._copy_table_data(source_table_name, target_table_name)

        print(f"🎉 Table cloning completed successfully!")
        print(
            f"✅ Table '{source_table_name}' has been cloned to '{target_table_name}' in local DynamoDB")


def main():
    """Main function to run the table cloner."""
    parser = argparse.ArgumentParser(
        description='Clone a DynamoDB table from cloud to local DynamoDB'
    )
    parser.add_argument(
        'table_name',
        nargs='?',
        help='Name of the source table to clone (e.g., "dev_users")'
    )
    parser.add_argument(
        '--list-tables',
        action='store_true',
        help='List all available tables in cloud DynamoDB and exit'
    )

    parser.add_argument(
        '--check-regions',
        action='store_true',
        help='Check for tables across multiple AWS regions'
    )

    args = parser.parse_args()

    # Initialize the cloner (reads from .env automatically)
    cloner = DynamoDBTableCloner()

    # If list-tables option is used, just list tables and exit
    if args.list_tables:
        cloner._list_available_tables()
        return

    # If check-regions option is used, check multiple regions and exit
    if args.check_regions:
        cloner._check_multiple_regions()
        return

    # Check if table name is provided
    if not args.table_name:
        print("❌ Error: table_name is required unless using --list-tables")
        parser.print_help()
        sys.exit(1)

    # Check if local DynamoDB is running
    try:
        endpoint = os.getenv("LOCAL_DYNAMODB_ENDPOINT",
                             "http://localhost:8000")
        region = os.getenv("AWS_REGION", "us-east-1")

        test_client = boto3.client(
            'dynamodb',
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        test_client.list_tables()
        print(f"✓ Local DynamoDB is running on {endpoint}")
    except Exception as e:
        endpoint = os.getenv("LOCAL_DYNAMODB_ENDPOINT",
                             "http://localhost:8000")
        print(f"❌ Error: Local DynamoDB is not running on {endpoint}")
        print("Please start local DynamoDB before running this script.")
        sys.exit(1)

    # Run the cloner with the provided table name
    cloner.clone_table(args.table_name)


if __name__ == "__main__":
    main()
