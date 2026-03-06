from pydantic import BaseModel, Field


class AgentSettings(BaseModel):
    """Main agent behavior settings."""
    
    timeout_seconds: int = Field(
        default=1800,
        description="Maximum interview duration in seconds (default: 30 minutes)"
    )
    
    language: str = Field(
        default="vi",
        description="Agent language code (vi for Vietnamese)"
    )
    
    preemptive_generation: bool = Field(
        default=True,
        description="Enable preemptive response generation"
    )


class STTSettings(BaseModel):
    """Speech-to-Text configuration."""
    
    model: str = Field(
        default="elevenlabs/scribe_v2_realtime",
        description="STT model identifier"
    )
    
    language: str = Field(
        default="vi",
        description="STT language code"
    )


class LLMSettings(BaseModel):
    """Large Language Model configuration."""
    
    model: str = Field(
        default="openai/gpt-4.1-mini",
        description="LLM model identifier"
    )

    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model identifier for summary/scoring generation"
    )


class TTSSettings(BaseModel):
    """Text-to-Speech configuration."""
    
    model: str = Field(
        default="cartesia/sonic-3",
        description="TTS model identifier"
    )
    
    voice: str = Field(
        default="935a9060-373c-49e4-b078-f4ea6326987a",
        description="Voice ID for TTS"
    )
    
    language: str = Field(
        default="vi",
        description="TTS language code"
    )


class StorageSettings(BaseModel):
    """Data storage configuration."""
    
    data_dir: str = Field(
        default="./interview_data",
        description="Directory for storing interview session data"
    )


class WebhookSettings(BaseModel):
    """Webhook configuration for sending interview results."""
    
    url: str = Field(
        default="",
        description="Webhook URL to POST interview results (optional, can be set via HR_WEBHOOK_URL env var)"
    )
    
    timeout_seconds: int = Field(
        default=30,
        description="Timeout for webhook requests"
    )
    
    retry_count: int = Field(
        default=3,
        description="Number of retries on webhook failure"
    )
    
    retry_delay_seconds: float = Field(
        default=1.0,
        description="Delay between webhook retries in seconds"
    )
