import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from models.aws_sso_config import AWSSSOConfig
from models.role_credentials import RoleCredentials


def get_latest_sso_cache_file() -> Path:
    """Return the most recently modified JSON file from the AWS SSO cache directory."""
    sso_cache_dir = Path.home() / ".aws" / "sso" / "cache"

    if not sso_cache_dir.exists():
        raise FileNotFoundError(
            f"SSO cache directory not found: {sso_cache_dir}")

    json_files = list(sso_cache_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError("No JSON files found in SSO cache directory")

    return max(json_files, key=lambda f: f.stat().st_mtime)


def load_config_from_env() -> AWSSSOConfig:
    """Load AWS SSO configuration from the .env file and return it as an AWSSSOConfig instance."""
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


def _ensure_valid_sso_token(config: AWSSSOConfig) -> bool:
    """Check SSO token expiry and trigger login if needed. Returns False on unrecoverable error."""
    try:
        cache_file = get_latest_sso_cache_file()
        sso_cache_data = json.loads(cache_file.read_text())
        if is_token_expired(sso_cache_data.get("expiresAt")):
            print(
                "⏰ SSO access token has expired! Starting SSO Login to refresh credentials.")
            run_sso_login(config)
    except FileNotFoundError:
        print(
            "🔍 No SSO cache files found! Start running SSO Login to generate credentials.")
        run_sso_login(config)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse SSO cache file: {e}")
        return False
    return True


def _read_access_token() -> str | None:
    """Read the access token from the SSO cache, or return None on failure."""
    try:
        cache_file = get_latest_sso_cache_file()
        sso_cache_data = json.loads(cache_file.read_text())
        return sso_cache_data.get("accessToken")
    except FileNotFoundError:
        print("🔍 No SSO cache files found after login! Cannot retrieve credentials.")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse SSO cache file after login: {e}")
        return None


def _fetch_role_credentials(config: AWSSSOConfig, access_token: str) -> RoleCredentials | None:
    """Call the AWS CLI to fetch role credentials and return them."""
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
        credentials_data = json.loads(result.stdout).get("roleCredentials")
        if not credentials_data:
            print("❌ Error: roleCredentials not found in response")
            return None
        return RoleCredentials(
            access_key_id=credentials_data["accessKeyId"],
            secret_access_key=credentials_data["secretAccessKey"],
            session_token=credentials_data["sessionToken"],
            expiration=credentials_data["expiration"],
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get role credentials: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse credentials response: {e}")
        return None


def get_aws_sso_credentials() -> RoleCredentials | None:
    """Authenticate via AWS SSO and return temporary role credentials, or None on failure."""
    try:
        config: AWSSSOConfig = load_config_from_env()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Configuration error: {e}")
        return None

    if not _ensure_valid_sso_token(config):
        return None

    access_token = _read_access_token()
    if not access_token:
        print("❌ Error: accessToken not found in cache file")
        return None

    return _fetch_role_credentials(config, access_token)


def run_sso_login(config: AWSSSOConfig) -> None:
    print(f"🔐 Running AWS SSO login for profile '{config.profile}'...")
    try:
        subprocess.run(["aws", "sso", "login", "--profile",
                       config.profile], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ SSO login failed: {e}")
        return None


def is_token_expired(expires_at: str | None) -> bool:
    """Check if the SSO access token has expired based on the expiresAt timestamp."""

    if not expires_at:
        return False

    try:
        expires_at_dt = datetime.strptime(
            expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return expires_at_dt.timestamp() < time.time()

    except ValueError as e:
        print(f"⚠️  Invalid expiresAt format: {e}")
        return True  # Assume expired if we can't parse the timestamp


def main():
    """Retrieve and print AWS SSO credentials to stdout."""
    credentials: RoleCredentials | None = get_aws_sso_credentials()
    if credentials:
        print("\n" + "=" * 60)
        print("🔑 AWS SSO Credentials:")
        print("=" * 60)
        print(json.dumps(credentials.__dict__, indent=2))
        print("=" * 60)
    else:
        print("❌ Failed to retrieve credentials")


if __name__ == "__main__":
    main()
