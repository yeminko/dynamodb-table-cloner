from dataclasses import dataclass


@dataclass
class AWSSSOConfig:
    profile: str
    account_id: str
    role_name: str
    region: str
