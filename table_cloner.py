"""
DynamoDB Table Cloner

This script clones a table from cloud DynamoDB to local DynamoDB.
It automatically retrieves AWS credentials via SSO and uses configuration from .env file.
"""
from models.role_credentials import RoleCredentials
from models.all_config import AllConfig
from mypy_boto3_dynamodb.type_defs import DescribeTableOutputTypeDef, TableDescriptionTypeDef

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from typing import Dict, Any
from get_sso_credentials import get_aws_sso_credentials
from utils.common_utils import load_all_config_from_env
from models.sso_config import SSOConfig

from mypy_boto3_dynamodb import DynamoDBClient


class DynamoDBTableCloner:
    def __init__(self):
        """
        Initialize the DynamoDB Table Cloner.
        Loads configuration from .env file.
        """
        self.cloud_client: DynamoDBClient
        self.local_client: DynamoDBClient
        self._load_config()
        self._load_credentials()
        self._initialize_clients()

    def clone_table(self, source_table_name: str, custom_table_name: str | None = None) -> None:
        """
        Clone a table from cloud DynamoDB to local DynamoDB.

        Args:
            source_table_name (str): Name of the source table in cloud DynamoDB
            custom_table_name (str | None): Custom name for the target table in local DynamoDB

        """
        # Determine target table name
        target_table_name = custom_table_name if custom_table_name else self._generate_target_table_name(
            source_table_name)

        print(f"🚀 Starting table cloning process...")
        print(f"📋 Source table: {source_table_name}")
        print(f"📋 Target table: {target_table_name}")

        # Step 1: Get source table schema
        print(f"🔍 Getting schema for table '{source_table_name}'...")
        source_schema: TableDescriptionTypeDef = self._get_table_schema(
            source_table_name)

        # Step 2: Create target table in local DynamoDB
        print(f"🏗️  Creating table '{target_table_name}' in local DynamoDB...")
        self._create_local_table(source_schema, target_table_name)

        # Step 3: Copy data from source to target
        self._copy_table_data(source_table_name, target_table_name)

        print(f"🎉 Table cloning completed successfully!")
        print(
            f"✅ Table '{source_table_name}' has been cloned to '{target_table_name}' in local DynamoDB")

    def clone_tables_with_prefix(self, prefix: str) -> None:
        """
        Clone all tables from cloud DynamoDB that start with the given prefix.

        Args:
            prefix (str): Prefix to filter tables (e.g., "dev_")
        """

        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError(
                "Prefix must be a non-empty, non-whitespace string.")

        prefix = prefix.strip()
        print(
            f"🚀 Starting batch table cloning process for prefix '{prefix}'")

        try:
            # List and filter tables in cloud DynamoDB during pagination
            paginator = self.cloud_client.get_paginator('list_tables')
            page_iterator = paginator.paginate()

            tables_to_clone = []
            for page in page_iterator:
                tables_to_clone.extend(
                    table_name
                    for table_name in page.get('TableNames', [])
                    if table_name.startswith(prefix)
                )

            if not tables_to_clone:
                raise ValueError(
                    f"❌ No tables found with prefix '{prefix}' in cloud DynamoDB.")

            print(
                f"🔍 Found {len(tables_to_clone)} tables with prefix '{prefix}' in {self.config.aws_region}")

            for table_name in tables_to_clone:
                print(f"📋 {table_name}")

            successful_tables = []
            failed_tables = []

            # Clone each table
            for source_table_name in tables_to_clone:
                try:
                    self.clone_table(source_table_name)
                    successful_tables.append(source_table_name)
                except ValueError as e:
                    print(f"❌ Error cloning table '{source_table_name}': {e}")
                    failed_tables.append(source_table_name)

            print(f"✅ Successfully cloned tables: {successful_tables}")
            if failed_tables:
                raise RuntimeError(
                    f"Failed to clone {len(failed_tables)} table(s) with prefix '{prefix}': {failed_tables}"
                )

        except ClientError as e:
            raise RuntimeError(
                f"Error listing tables with prefix '{prefix}'"
            ) from e

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        try:
            self.config: AllConfig = load_all_config_from_env()
            print("✓ Configuration loaded successfully")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)

    def _load_credentials(self) -> None:
        """Load AWS credentials using SSO."""
        print("🔐 Getting AWS credentials via SSO...")

        sso_config = SSOConfig(
            aws_sso_profile=self.config.aws_sso_profile,
            aws_account_id=self.config.aws_account_id,
            aws_role_name=self.config.aws_role_name,
            aws_region=self.config.aws_region
        )

        role_credentials: RoleCredentials | None = get_aws_sso_credentials(
            sso_config)
        if not role_credentials:
            print("❌ Error: Failed to get credentials via SSO")
            sys.exit(1)
        self.credentials = role_credentials
        print("✓ Credentials obtained via SSO")

    def _initialize_clients(self) -> None:
        """Initialize DynamoDB clients for cloud and local."""
        try:
            # Cloud DynamoDB client
            self.cloud_client = boto3.client(
                'dynamodb',
                aws_access_key_id=self.credentials.access_key_id,
                aws_secret_access_key=self.credentials.secret_access_key,
                aws_session_token=self.credentials.session_token,
                region_name=self.config.aws_region
            )

            # Local DynamoDB client
            self.local_client = boto3.client(
                'dynamodb',
                endpoint_url=self.config.local_dynamodb_endpoint,
                region_name=self.config.aws_region,
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )

            print("✓ DynamoDB clients initialized")

            # Test local DynamoDB connection
            self._test_local_connection()

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

    def _test_local_connection(self) -> None:
        """Test the connection to local DynamoDB."""
        try:
            # Try to list tables to verify local DynamoDB is running
            response = self.local_client.list_tables(Limit=1)
            print("✓ Successfully connected to local DynamoDB")
        except Exception as e:
            print(f"❌ Error connecting to local DynamoDB: {e}")
            print("Please ensure local DynamoDB is running and accessible.")
            sys.exit(1)

    def _get_table_schema(self, table_name: str) -> TableDescriptionTypeDef:
        """
        Get the schema of the source table from cloud DynamoDB.

        Args:
            table_name (str): Name of the source table

        Returns:
            TableDescriptionTypeDef: Table schema information
        """
        try:
            response: DescribeTableOutputTypeDef = self.cloud_client.describe_table(
                TableName=table_name)
            return response['Table']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise ValueError(
                    f"Source table '{table_name}' does not exist in cloud DynamoDB.") from e
            else:
                raise ValueError(
                    f"Error describing table '{table_name}': {e}") from e

    def _create_local_table(self, source_schema: TableDescriptionTypeDef, target_table_name: str) -> None:
        """
        Create the target table in local DynamoDB based on source schema.

        Args:
            source_schema (TableDescriptionTypeDef): Schema of the source table
            target_table_name (str): Name of the target table
        """
        try:
            # Extract necessary schema information
            key_schema = source_schema['KeySchema']
            attribute_definitions = source_schema['AttributeDefinitions']

            # Set billing mode to PAY_PER_REQUEST for local DynamoDB
            table_params: Dict[str, Any] = {
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
                raise ValueError(
                    f"Target table '{target_table_name}' already exists in local DynamoDB.") from e

            else:
                raise ValueError(
                    f"Error creating local table '{target_table_name}': {e}") from e

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
            batch_size = self.config.batch_size
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

        except (ClientError, ValueError) as e:
            raise ValueError(
                f"Error copying table data from '{source_table_name}' to '{target_table_name}': {e}") from e

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
            raise ValueError(
                f"Error writing batch to table '{table_name}': {e}") from e

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
        # Environment prefixes to replace
        env_prefixes = ['dev_', 'qa_', 'stg_', 'test_']

        # Check if the table name starts with any environment prefix
        for env_prefix in env_prefixes:
            if source_table_name.startswith(env_prefix):
                # Replace the environment prefix with local prefix
                base_name = source_table_name[len(env_prefix):]
                return f"{self.config.local_table_prefix}{base_name}"

        # If no environment prefix found, just add local prefix
        return f"{self.config.local_table_prefix}{source_table_name}"


def main():
    """Main function to run the table cloner."""
    parser = argparse.ArgumentParser(
        description='Clone single or multiple DynamoDB tables from cloud to local based on table name or prefix.'
    )
    parser.add_argument(
        "name",
        nargs='?',
        help='Name of the source table to clone (e.g., "dev_users")'
    )
    parser.add_argument(
        '--target-table',
        help='Custom table name for the local DynamoDB (overrides default naming convention)'
    )
    parser.add_argument(
        '--prefix',
        help='Clone all tables with the provided prefix from a single region (e.g., "dev_")'
    )

    args = parser.parse_args()

    if not args.name and not args.prefix:
        parser.error(
            "You must provide either a table name to clone or a prefix to clone multiple tables. Use --help for more information.")

    if args.name and args.prefix:
        parser.error(
            "You cannot use both a table name and a prefix at the same time. Please choose one option.")

    if args.prefix and args.target_table:
        parser.error(
            "You cannot use --target-table with --prefix. --target-table only applies when cloning a single table.")

    if args.prefix and not args.prefix.strip():
        parser.error("Prefix cannot be empty. Please provide a valid prefix.")

    # Initialize the cloner (reads from .env automatically)
    cloner = DynamoDBTableCloner()

    try:

        if args.prefix:
            # Clone all tables with the specified prefix
            cloner.clone_tables_with_prefix(args.prefix)
        else:
            # Run the cloner with the provided table name
            cloner.clone_table(source_table_name=args.name,
                               custom_table_name=args.target_table)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
