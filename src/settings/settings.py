from __future__ import annotations

from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from .models import (
    AgentSettings,
    LLMSettings,
    StorageSettings,
    STTSettings,
    TTSSettings,
    WebhookSettings,
)

# Load .env file first (for secrets)
load_dotenv(find_dotenv(".env.local"), override=True)


class Settings(BaseSettings):
    """
    Application settings.

    Priority order (highest to lowest):
    1. Init settings
    2. Environment variables
    3. .env file
    4. File secrets
    5. YAML config file
    """

    # API Keys and Secrets (from .env)
    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    hr_webhook_url: str | None = None

    # Functional configuration (from settings.yaml)
    agent: AgentSettings = AgentSettings()
    stt: STTSettings = STTSettings()
    llm: LLMSettings = LLMSettings()
    tts: TTSSettings = TTSSettings()
    storage: StorageSettings = StorageSettings()
    webhook: WebhookSettings = WebhookSettings()

    # Deployment settings
    deployment_env: str = "development"

    class Config:
        env_nested_delimiter = "__"
        yaml_file = str(Path(__file__).parent.parent.parent / "settings.yaml")
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources priority.

        Order: init > env > dotenv > file_secret > yaml
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )


def get_settings() -> Settings:
    """Create and return settings instance.

    Keep initialization explicit at application entrypoints (e.g. agent.py)
    to match project convention.
    """
    s = Settings()

    # If HR_WEBHOOK_URL is set via env, override webhook.url
    if s.hr_webhook_url:
        s.webhook.url = s.hr_webhook_url

    return s
