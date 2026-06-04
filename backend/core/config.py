from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    jwt_private_key: SecretStr
    jwt_public_key: str
    jwt_expiry_seconds: int = 86400
    jwt_issuer: str

    allowed_origins: list[str] = []

    google_client_id: str
    google_client_secret: SecretStr
    github_client_id: str
    github_client_secret: SecretStr

    csrf_secret_key: SecretStr
    app_base_url: str
    log_level: str = "INFO"
    disable_docs: bool = False


settings = Settings()  # type: ignore[call-arg]
