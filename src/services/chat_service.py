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
        structure_model = (
            os.getenv("OPENAI_STRUCTURE_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4.1-mini"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON describing the scene. Keys: "
                    "scene_title (string), logline (string), art_style (string), "
                    "background (object: description, time_of_day, location), "
                    "characters (array of objects: name, description, style_hint, prompt), "
                    "beats (array of objects: order, description, dialogue, duration_seconds, padded_duration_seconds). "
                    "Each beat.dialogue must be an array of 1-3 short spoken lines labelled with the "
                    "character name (e.g., \"ALEX: Let's move.\"). Keep prompts concise."
                    "Estimate duration_seconds per beat (dialogue+action) and also padded_duration_seconds with ~20-30% extra buffer. "
                    "padded_duration_seconds must be snapped to one of [4, 8, 12] seconds (pick the closest with buffer applied)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Structure this script into JSON for downstream image generation. "
                    "Ensure every beat has a dialogue array with 1-3 short lines of spoken dialogue and both duration_seconds "
                    "and padded_duration_seconds fields (include reasonable buffer). "
                    "Snap padded_duration_seconds to 4, 8, or 12 seconds (nearest, with buffer). "
                    "Script:\n" + script_text
                ),
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=structure_model,
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
