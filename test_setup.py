#!/usr/bin/env python3
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

def check_credentials_file():
    """Check if credentials file is valid."""
    if not os.path.exists('credentials.json'):
        return False
    
    try:
        with open('credentials.json', 'r') as f:
            data = json.load(f)
            
        # Check required fields
        required_fields = ['accessKeyId', 'secretAccessKey', 'sessionToken', 'expiration']
        creds = data.get('roleCredentials', {})
        
        missing_fields = [field for field in required_fields if field not in creds]
        if missing_fields:
            print(f"❌ Credentials file missing fields: {missing_fields}")
            return False
        
        # Check expiration
        expiration = creds.get('expiration', 0)
        if expiration < datetime.now().timestamp() * 1000:
            print("⚠️  Warning: Credentials appear to be expired")
        
        print("✅ Credentials file format is valid")
        return True
        
    except json.JSONDecodeError:
        print("❌ Credentials file contains invalid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return False

def check_config_file():
    """Check if config file is valid."""
    if not os.path.exists('config.json'):
        print("⚠️  Config file not found, will use defaults")
        return True
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            
        print("✅ Configuration file is valid")
        print(f"   - AWS Region: {config.get('aws_region', 'us-east-1')}")
        print(f"   - Local DynamoDB: {config.get('local_dynamodb_endpoint', 'http://localhost:8000')}")
        print(f"   - Table Prefix: {config.get('local_table_prefix', 'local_')}")
        print(f"   - Batch Size: {config.get('batch_size', 25)}")
        return True
        
    except json.JSONDecodeError:
        print("❌ Config file contains invalid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False

def check_local_dynamodb():
    """Check if local DynamoDB is running."""
    try:
        # Load config to get endpoint
        endpoint = "http://localhost:8000"
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)
                endpoint = config.get('local_dynamodb_endpoint', endpoint)
        
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
            print(f"   - Found {len(tables)} existing tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
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
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            managers.append(f"uv {result.stdout.strip()}")
    except FileNotFoundError:
        pass
    
    # Check for pip
    try:
        result = subprocess.run(['pip', '--version'], capture_output=True, text=True)
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
        ("Main Script", lambda: check_file_exists('table_cloner.py', 'Main script')),
        ("Requirements File", lambda: check_file_exists('requirements.txt', 'Requirements file')),
        ("Credentials File", check_credentials_file),
        ("Configuration File", check_config_file),
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
        print(f"\n⚠️  {total - passed} check(s) failed. Please fix the issues above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()