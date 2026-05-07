from dataclasses import dataclass


@dataclass
class RoleCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: str
