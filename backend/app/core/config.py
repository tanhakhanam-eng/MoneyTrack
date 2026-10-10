from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HisabFlow"
    database_url: str = "sqlite:///./hisabflow.db"
    secret_key: str = "dev-secret-key-change-me"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
