from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "automated-posting"
    post_timeout_seconds: float = 15.0

    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    bluesky_pds_url: str = "https://bsky.social"

    mastodon_base_url: str | None = None
    mastodon_access_token: str | None = None

    devto_api_key: str | None = None

    wordpress_site_url: str | None = None
    wordpress_username: str | None = None
    wordpress_app_password: str | None = None

    hf_token: str | None = None
    hf_repo: str | None = None


settings = Settings()
