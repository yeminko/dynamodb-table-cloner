from dataclasses import dataclass


@dataclass
class SSOConfig:
    aws_sso_profile: str
    aws_account_id: str
    aws_role_name: str
    aws_region: str
