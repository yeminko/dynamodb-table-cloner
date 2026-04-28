from dataclasses import dataclass


@dataclass
class AWSSSOConfig:
    profile: str
    account_id: str
    role_name: str
    region: str


@dataclass
class AppConfig:
    aws_region: str
    local_dynamodb_endpoint: str
    local_table_prefix: str
    batch_size: int
