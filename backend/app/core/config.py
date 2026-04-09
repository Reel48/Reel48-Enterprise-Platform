from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reel48"
    DATABASE_ECHO: bool = False

    # Redis (rate limiting, caching)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Amazon Cognito
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""
    COGNITO_REGION: str = "us-east-1"

    # Amazon SES (transactional email)
    SES_REGION: str = "us-east-1"
    SES_SENDER_EMAIL: str = "noreply@reel48.com"

    # Frontend (for email links)
    FRONTEND_BASE_URL: str = "https://app.reel48.com"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Application
    DEBUG: bool = False
    APP_NAME: str = "Reel48+ API"
    API_V1_PREFIX: str = "/api/v1"

    @property
    def cognito_issuer(self) -> str:
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}"

    @property
    def cognito_jwks_url(self) -> str:
        return f"{self.cognito_issuer}/.well-known/jwks.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
