#!/usr/bin/env python3
"""
Example usage of the DynamoDB Table Cloner.

This script demonstrates how to use the table cloner to clone
specific tables commonly used in development environments.
"""

import subprocess
import sys
import json
import os

def run_cloner(table_name, credentials_file='credentials.json', config_file='config.json'):
    """
    Run the table cloner for a specific table.
    
    Args:
        table_name (str): Name of the table to clone
        credentials_file (str): Path to credentials file
        config_file (str): Path to config file
    """
    try:
        cmd = [
            'python', 'table_cloner.py', 
            table_name,
            '--credentials', credentials_file,
            '--config', config_file
        ]
        
        print(f"\n{'='*60}")
        print(f"Cloning table: {table_name}")
        print(f"{'='*60}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error cloning table {table_name}:")
        print(e.stdout)
        print(e.stderr)
        return False
    
    return True

def main():
    """Main function to demonstrate table cloning."""
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json file not found!")
        print("Please create a credentials.json file with your AWS credentials.")
        print("\nExample:")
        print(json.dumps({
            "roleCredentials": {
                "accessKeyId": "YOUR_ACCESS_KEY_ID",
                "secretAccessKey": "YOUR_SECRET_ACCESS_KEY",
                "sessionToken": "YOUR_SESSION_TOKEN",
                "expiration": 1759523091000
            }
        }, indent=2))
        sys.exit(1)
    
    # List of tables to clone (update with your actual table names)
    tables_to_clone = [
        'dev_users',
        'qa_products', 
        'stg_orders',
        'test_data'
    ]
    
    print("🚀 Starting batch table cloning process...")
    print(f"📋 Tables to clone: {', '.join(tables_to_clone)}")
    
    successful_clones = []
    failed_clones = []
    
    for table in tables_to_clone:
        if run_cloner(table):
            successful_clones.append(table)
        else:
            failed_clones.append(table)
    
    # Summary
    print(f"\n{'='*60}")
    print("CLONING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully cloned: {len(successful_clones)} tables")
    for table in successful_clones:
        # Show the actual target name that would be generated
        if table.startswith(('dev_', 'qa_', 'stg_', 'test_')):
            env_prefixes = ['dev_', 'qa_', 'stg_', 'test_']
            for prefix in env_prefixes:
                if table.startswith(prefix):
                    target = f"local_{table[len(prefix):]}"
                    break
        else:
            target = f"local_{table}"
        print(f"   - {table} → {target}")
    
    if failed_clones:
        print(f"\n❌ Failed to clone: {len(failed_clones)} tables")
        for table in failed_clones:
            print(f"   - {table}")
    
    print(f"\n🎉 Batch cloning process completed!")

if __name__ == "__main__":
    main()