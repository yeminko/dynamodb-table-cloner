import json
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

from models import AWSSSOConfig


def get_latest_sso_cache_file() -> Path:
    sso_cache_dir = Path.home() / ".aws" / "sso" / "cache"
    if not sso_cache_dir.exists():
        raise FileNotFoundError(
            f"SSO cache directory not found: {sso_cache_dir}")
    json_files = list(sso_cache_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError("No JSON files found in SSO cache directory")
    return max(json_files, key=lambda f: f.stat().st_mtime)


def load_config_from_env() -> AWSSSOConfig:
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(env_path)

    keys = ["AWS_SSO_PROFILE", "AWS_ACCOUNT_ID", "AWS_ROLE_NAME", "AWS_REGION"]
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}")

    return AWSSSOConfig(
        profile=os.environ["AWS_SSO_PROFILE"],
        account_id=os.environ["AWS_ACCOUNT_ID"],
        role_name=os.environ["AWS_ROLE_NAME"],
        region=os.environ["AWS_REGION"],
    )


def get_aws_sso_credentials() -> dict[str, dict[str, str]] | None:
    try:
        config: AWSSSOConfig = load_config_from_env()
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}")
        return None

    print(f"Running AWS SSO login for profile '{config.profile}'...")
    try:
        subprocess.run(["aws", "sso", "login", "--profile",
                       config.profile], check=True)
    except subprocess.CalledProcessError as e:
        print(f"SSO login failed: {e}")
        return None

    print("Waiting for cache to update...")
    time.sleep(3)

    try:
        cache_file = get_latest_sso_cache_file()
        access_token = json.loads(cache_file.read_text()).get("accessToken")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Cache error: {e}")
        return None

    if not access_token:
        print("Error: accessToken not found in cache file")
        return None

    try:
        result = subprocess.run(
            [
                "aws", "sso", "get-role-credentials",
                "--account-id", config.account_id,
                "--role-name", config.role_name,
                "--region", config.region,
                "--access-token", access_token,
            ],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Failed to get role credentials: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse credentials response: {e}")
        return None


def main():
    credentials = get_aws_sso_credentials()
    if credentials:
        print("\n" + "=" * 60)
        print("AWS SSO Credentials:")
        print("=" * 60)
        print(json.dumps(credentials, indent=2))
        print("=" * 60)
    else:
        print("Failed to retrieve credentials")


if __name__ == "__main__":
    main()
