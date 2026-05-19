from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_password: str = ""

    monarch_email: str = ""
    monarch_password: str = ""
    monarch_mfa_secret: str = ""
    mm_session_file: str = "secrets/mm_session.pickle"

    google_client_secrets_file: str = "secrets/client_secrets.json"
    google_token_file: str = "secrets/token.json"
    sheet_id: str = ""

    cache_ttl_accounts: int = 300
    cache_ttl_transactions: int = 60

    sheets_tab_assumptions: str = "Assumptions"
    sheets_tab_targets: str = "Targets"
    sheets_tab_accounts: str = "Accounts"
    sheets_tab_holdings: str = "Holdings"
    sheets_tab_projections: str = "Projections"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
