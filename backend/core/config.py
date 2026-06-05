from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str

    # Cognito
    cognito_region: str = "eu-west-1"
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_client_secret: SecretStr
    cognito_domain: str  # e.g. "expense-splitter-dev" (without .auth.region.amazoncognito.com)
    jwt_expiry_seconds: int = 86400  # must match Cognito ID token validity

    allowed_origins: list[str] = []

    csrf_secret_key: SecretStr
    app_base_url: str
    log_level: str = "INFO"
    disable_docs: bool = False

    @property
    def cognito_base_url(self) -> str:
        return f"https://{self.cognito_domain}.auth.{self.cognito_region}.amazoncognito.com"

    @property
    def cognito_jwks_url(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com"
            f"/{self.cognito_user_pool_id}/.well-known/jwks.json"
        )

    @property
    def cognito_issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com"
            f"/{self.cognito_user_pool_id}"
        )


settings = Settings()  # type: ignore[call-arg]
