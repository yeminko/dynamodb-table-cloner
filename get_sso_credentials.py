#!/usr/bin/env python3
import subprocess
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


def get_latest_sso_cache_file():
    """Find the latest JSON file in the AWS SSO cache directory."""
    sso_cache_dir = Path.home() / ".aws" / "sso" / "cache"

    if not sso_cache_dir.exists():
        raise FileNotFoundError(
            f"SSO cache directory not found: {sso_cache_dir}")

    json_files = list(sso_cache_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError("No JSON files found in SSO cache directory")

    # Get the most recently modified file
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    return latest_file


def load_config_from_env() -> Dict[str, str]:
    """Load configuration from .env file."""
    # Load .env file from the script's directory
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(env_path)

    # Get required configuration
    required_vars = {
        "AWS_SSO_PROFILE": os.getenv("AWS_SSO_PROFILE"),
        "AWS_ACCOUNT_ID": os.getenv("AWS_ACCOUNT_ID"),
        "AWS_ROLE_NAME": os.getenv("AWS_ROLE_NAME"),
        "AWS_REGION": os.getenv("AWS_REGION")
    }

    # Check for missing variables
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}")

    return required_vars


def get_aws_sso_credentials() -> Optional[Dict[str, Any]]:
    """
    Automate AWS SSO login and credential retrieval.

    Returns:
        dict: Formatted credentials dictionary or None if failed
    """

    # Load configuration from .env
    try:
        config = load_config_from_env()
        profile = config["AWS_SSO_PROFILE"]
        account_id = config["AWS_ACCOUNT_ID"]
        role_name = config["AWS_ROLE_NAME"]
        region = config["AWS_REGION"]
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"Error loading configuration: {e}")
        return None

    # Step 1: Run aws sso login
    print(f"Running AWS SSO login for profile '{profile}'...")
    try:
        subprocess.run(
            ["aws", "sso", "login", "--profile", profile],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during SSO login: {e}")
        return None

    # Step 2: Wait for 3 seconds
    print("Waiting 3 seconds for cache to update...")
    time.sleep(3)

    # Step 3: Get the latest JSON file from SSO cache
    print("Finding latest SSO cache file...")
    try:
        latest_cache_file = get_latest_sso_cache_file()
        print(f"Found: {latest_cache_file}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None

    # Step 4: Read and extract accessToken
    print("Reading access token...")
    with open(latest_cache_file, 'r') as f:
        cache_data = json.load(f)

    access_token = cache_data.get("accessToken")

    if not access_token:
        print("Error: accessToken not found in cache file")
        return None

    # Step 5: Get role credentials
    print("Fetching role credentials...")
    try:
        result = subprocess.run(
            [
                "aws", "sso", "get-role-credentials",
                "--account-id", account_id,
                "--role-name", role_name,
                "--region", region,
                "--access-token", access_token
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the response
        response_data = json.loads(result.stdout)

        # Step 6: Format the output
        formatted_credentials = {
            "roleCredentials": {
                "accessKeyId": response_data["roleCredentials"]["accessKeyId"],
                "secretAccessKey": response_data["roleCredentials"]["secretAccessKey"],
                "sessionToken": response_data["roleCredentials"]["sessionToken"],
                "expiration": response_data["roleCredentials"]["expiration"]
            }
        }

        return formatted_credentials

    except subprocess.CalledProcessError as e:
        print(f"Error getting role credentials: {e}")
        print(f"stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None


def main():
    """Main function to get and print AWS SSO credentials."""
    credentials = get_aws_sso_credentials()

    if credentials:
        print("\n" + "="*60)
        print("AWS SSO Credentials:")
        print("="*60)
        print(json.dumps(credentials, indent=2))
        print("="*60)
    else:
        print("Failed to retrieve credentials")


if __name__ == "__main__":
    main()
