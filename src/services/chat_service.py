from __future__ import annotations

import os
from typing import Dict, List, Optional
from openai import OpenAI, OpenAIError


class OpenAIChatService:
    """Simple wrapper for OpenAI chat completions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = "gpt-4o-mini"):
        api_key = self._resolve_api_key(api_key)
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Set it in your environment, .env, or Streamlit secrets."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", model) if model is None else model

    def generate_reply(self, history: List[Dict[str, str]]) -> str:
        """Send chat history to OpenAI and return assistant reply."""
        messages = [{"role": "system", "content": self._system_prompt()}]
        messages.extend(history)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
        except OpenAIError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        return response.choices[0].message.content

    def generate_structured_scene(self, script_text: str) -> Dict:
        """Generate structured JSON from freeform script text."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON describing the scene. Keys: "
                    "scene_title (string), logline (string), art_style (string), "
                    "background (object: description, time_of_day, location), "
                    "characters (array of objects: name, description, style_hint, prompt), "
                    "beats (array of objects: order, description). Keep prompts concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Structure this script into JSON for downstream image generation. "
                    "Script:\n" + script_text
                ),
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            import json

            return json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"Failed to generate structured scene: {exc}") from exc

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a screenwriting assistant. Always return a concise, film-ready script "
            "that includes: (1) character names with clear descriptions/personality cues, "
            "(2) scene background description (time, place, mood), (3) an explicit art style "
            "tag such as realistic, 3d, watercolor, anime, comic, or painterly, and "
            "(4) brief, production-friendly dialogue/action beats. Keep it ~20-40 seconds "
            "of content unless the user asks otherwise."
        )

    @staticmethod
    def _resolve_api_key(self, provided_key: Optional[str] = None) -> Optional[str]:
        """Find API key from provided value, Streamlit secrets, or environment."""
        if provided_key:
            return provided_key

        # Streamlit secrets (works in Docker via .streamlit/secrets.toml)
        try:
            import streamlit as st

            if hasattr(st, "secrets"):
                secret_key = st.secrets.get("OPENAI_API_KEY")
                if secret_key:
                    return secret_key
        except Exception:
            pass

        # Try env next
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key

        # Streamlit secrets fallback
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None

        return api_key
