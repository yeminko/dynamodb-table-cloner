"""
Test script to verify the DynamoDB Table Cloner setup.

This script performs basic checks to ensure all components
are properly configured and ready to use.
"""

import json
import os
import boto3
import sys
from datetime import datetime


def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False


def check_env_file():
    """Check if .env file is valid and contains required variables."""
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("💡 Please create a .env file based on .env.template")
        return False

    try:
        from dotenv import dotenv_values
        config = dotenv_values('.env')

        # Check required fields
        required_fields = [
            'AWS_SSO_PROFILE', 'AWS_ACCOUNT_ID', 'AWS_ROLE_NAME', 'AWS_REGION',
            'LOCAL_DYNAMODB_ENDPOINT', 'LOCAL_TABLE_PREFIX', 'BATCH_SIZE'
        ]

        missing_fields = [
            field for field in required_fields if field not in config or not config[field]]
        if missing_fields:
            print(f"❌ .env file missing or empty fields: {missing_fields}")
            return False

        print("✅ .env file is valid")
        print(f"   - AWS SSO Profile: {config['AWS_SSO_PROFILE']}")
        print(f"   - AWS Account ID: {config['AWS_ACCOUNT_ID']}")
        print(f"   - AWS Role Name: {config['AWS_ROLE_NAME']}")
        print(f"   - AWS Region: {config['AWS_REGION']}")
        print(f"   - Local DynamoDB: {config['LOCAL_DYNAMODB_ENDPOINT']}")
        print(f"   - Table Prefix: {config['LOCAL_TABLE_PREFIX']}")
        print(f"   - Batch Size: {config['BATCH_SIZE']}")
        return True

    except ImportError:
        print("❌ python-dotenv not installed")
        print("💡 Run: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False


def check_local_dynamodb():
    """Check if local DynamoDB is running."""
    try:
        # Load endpoint from .env or use default
        endpoint = "http://localhost:8000"
        if os.path.exists('.env'):
            from dotenv import dotenv_values
            config = dotenv_values('.env')
            endpoint = config.get('LOCAL_DYNAMODB_ENDPOINT', endpoint)

        client = boto3.client(
            'dynamodb',
            endpoint_url=endpoint,
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        response = client.list_tables()
        tables = response.get('TableNames', [])

        print(f"✅ Local DynamoDB is running at {endpoint}")
        if tables:
            print(
                f"   - Found {len(tables)} existing tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
        else:
            print("   - No existing tables found")

        return True

    except Exception as e:
        print(f"❌ Local DynamoDB is not accessible at {endpoint}")
        print(f"   Error: {e}")
        print("   Please start local DynamoDB before running the cloner")
        return False


def check_python_dependencies():
    """Check if required Python packages are installed."""
    try:
        import boto3
        import botocore
        print(f"✅ boto3 version: {boto3.__version__}")
        print(f"✅ botocore version: {botocore.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("   Install options:")
        print("   - With uv: uv pip install -r requirements.txt")
        print("   - With pip: pip install -r requirements.txt")
        print("   - Or run: make install")
        return False


def check_package_manager():
    """Check if uv or pip is available."""
    import subprocess

    managers = []

    # Check for uv
    try:
        result = subprocess.run(['uv', '--version'],
                                capture_output=True, text=True)
        if result.returncode == 0:
            managers.append(f"uv {result.stdout.strip()}")
    except FileNotFoundError:
        pass

    # Check for pip
    try:
        result = subprocess.run(['pip', '--version'],
                                capture_output=True, text=True)
        if result.returncode == 0:
            managers.append(f"pip {result.stdout.strip()}")
    except FileNotFoundError:
        pass

    if managers:
        print("✅ Package managers available:")
        for manager in managers:
            print(f"   - {manager}")
        return True
    else:
        print("❌ No package manager found (uv or pip)")
        print("   Please install uv or pip to manage dependencies")
        return False


def main():
    """Run all setup checks."""
    print("🔍 DynamoDB Table Cloner - Setup Verification")
    print("=" * 60)

    checks = [
        ("Package Manager", check_package_manager),
        ("Python Dependencies", check_python_dependencies),
        ("Main Script", lambda: check_file_exists(
            'table_cloner.py', 'Main script')),
        ("Requirements File", lambda: check_file_exists(
            'requirements.txt', 'Requirements file')),
        ("Environment Configuration", check_env_file),
        ("Local DynamoDB", check_local_dynamodb),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        result = check_func()
        results.append((check_name, result))

    # Summary
    print("\n" + "=" * 60)
    print("SETUP VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! You're ready to clone tables.")
        print("\nExample usage:")
        print("  python table_cloner.py dev_users")
        print("  python example_usage.py")
    else:
        print(
            f"\n⚠️  {total - passed} check(s) failed. Please fix the issues above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
