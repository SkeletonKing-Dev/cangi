"""Temporary LLM-backed guide. Replaced later by the deterministic analysis engine.

The rest of cangi only sees GuideService; everything LLM specific lives in this package.
"""
from .llm import ChatClient, LLMConfig, LLMError, OpenAICompatClient
from .service import GuideService

__all__ = ["ChatClient", "GuideService", "LLMConfig", "LLMError", "OpenAICompatClient"]
