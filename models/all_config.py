from dataclasses import dataclass


@dataclass
class AllConfig:
    aws_sso_profile: str
    aws_account_id: str
    aws_role_name: str
    aws_region: str
    local_dynamodb_endpoint: str
    local_table_prefix: str
    batch_size: int
