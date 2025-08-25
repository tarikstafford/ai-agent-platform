"""
Message Inspector Configuration

This module provides configuration management for the A2A Message Inspector feature.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field

from ..a2a.message_store import MessageStoreConfig


class MessageInspectorConfig(BaseModel):
    """Configuration for A2A Message Inspector"""
    
    # Message Store Configuration
    max_messages: int = Field(
        default=int(os.getenv("A2A_MSG_MAX_MESSAGES", "5000")),
        gt=0,
        description="Maximum messages in memory"
    )
    max_age_hours: int = Field(
        default=int(os.getenv("A2A_MSG_MAX_AGE_HOURS", "24")),
        gt=0,
        description="Maximum message age in hours"
    )
    payload_summary_length: int = Field(
        default=int(os.getenv("A2A_MSG_PAYLOAD_SUMMARY_LENGTH", "512")),
        gt=0,
        description="Length of payload summary"
    )
    allow_full_payload: bool = Field(
        default=os.getenv("A2A_MSG_ALLOW_FULL_PAYLOAD", "false").lower() == "true",
        description="Store full payloads (security risk)"
    )
    persistent_storage: bool = Field(
        default=os.getenv("A2A_MSG_PERSISTENT_STORAGE", "true").lower() == "true",
        description="Enable SQLite persistence"
    )
    sqlite_path: str = Field(
        default=os.getenv("A2A_MSG_SQLITE_PATH", "data/a2a_messages.db"),
        description="SQLite database path"
    )
    enable_sampling: bool = Field(
        default=os.getenv("A2A_MSG_ENABLE_SAMPLING", "false").lower() == "true",
        description="Enable message sampling under load"
    )
    sampling_rate: float = Field(
        default=float(os.getenv("A2A_MSG_SAMPLING_RATE", "0.1")),
        ge=0.0,
        le=1.0,
        description="Sampling rate when enabled"
    )
    
    # Security Configuration
    require_auth: bool = Field(
        default=os.getenv("A2A_MSG_REQUIRE_AUTH", "true").lower() == "true",
        description="Require authentication for message inspector"
    )
    admin_role_required: bool = Field(
        default=os.getenv("A2A_MSG_ADMIN_ROLE", "true").lower() == "true",
        description="Require admin role for full payload access"
    )
    
    # Export Configuration
    export_enabled: bool = Field(
        default=os.getenv("A2A_MSG_EXPORT_ENABLED", "true").lower() == "true",
        description="Enable message export functionality"
    )
    max_export_messages: int = Field(
        default=int(os.getenv("A2A_MSG_MAX_EXPORT", "10000")),
        gt=0,
        description="Maximum messages per export"
    )
    
    # Replay Configuration
    replay_enabled: bool = Field(
        default=os.getenv("A2A_MSG_REPLAY_ENABLED", "true").lower() == "true",
        description="Enable message replay functionality"
    )
    replay_rate_limit: int = Field(
        default=int(os.getenv("A2A_MSG_REPLAY_RATE_LIMIT", "10")),
        gt=0,
        description="Maximum replays per minute per user"
    )
    
    # Real-time Stream Configuration
    stream_enabled: bool = Field(
        default=os.getenv("A2A_MSG_STREAM_ENABLED", "true").lower() == "true",
        description="Enable real-time message streaming"
    )
    stream_buffer_size: int = Field(
        default=int(os.getenv("A2A_MSG_STREAM_BUFFER", "100")),
        gt=0,
        description="Buffer size for real-time streaming"
    )
    
    def to_message_store_config(self) -> MessageStoreConfig:
        """Convert to MessageStoreConfig"""
        return MessageStoreConfig(
            max_messages=self.max_messages,
            max_age_hours=self.max_age_hours,
            payload_summary_length=self.payload_summary_length,
            allow_full_payload=self.allow_full_payload,
            persistent_storage=self.persistent_storage,
            sqlite_path=self.sqlite_path,
            enable_sampling=self.enable_sampling,
            sampling_rate=self.sampling_rate
        )


def load_config() -> MessageInspectorConfig:
    """Load configuration from environment variables and defaults"""
    return MessageInspectorConfig()


# Global configuration instance
_config: Optional[MessageInspectorConfig] = None


def get_config() -> MessageInspectorConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> MessageInspectorConfig:
    """Reload configuration from environment"""
    global _config
    _config = load_config()
    return _config