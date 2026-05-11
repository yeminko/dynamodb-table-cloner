import os
from dotenv import load_dotenv
from pathlib import Path
from models.environment_config import EnvironmentConfig


def load_config_from_env() -> EnvironmentConfig:
    """Load AWS SSO configuration from the .env file and return it as an EnvironmentConfig instance."""
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(env_path)

    keys = [
        "AWS_SSO_PROFILE",
        "AWS_ACCOUNT_ID",
        "AWS_ROLE_NAME",
        "AWS_REGION",
        "LOCAL_DYNAMODB_ENDPOINT",
        "LOCAL_TABLE_PREFIX",
        "BATCH_SIZE"
    ]

    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}")

    return EnvironmentConfig(
        aws_sso_profile=os.environ["AWS_SSO_PROFILE"],
        aws_account_id=os.environ["AWS_ACCOUNT_ID"],
        aws_role_name=os.environ["AWS_ROLE_NAME"],
        aws_region=os.environ["AWS_REGION"],
        local_dynamodb_endpoint=os.environ["LOCAL_DYNAMODB_ENDPOINT"],
        local_table_prefix=os.environ["LOCAL_TABLE_PREFIX"],
        batch_size=int(os.environ["BATCH_SIZE"]),
    )
