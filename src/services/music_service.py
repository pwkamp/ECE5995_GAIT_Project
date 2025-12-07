from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

import requests
from openai import OpenAI, OpenAIError


class MusicService:
    """
    Handles sentiment extraction (via OpenAI) and music generation (via ElevenLabs).

    To switch to using a pre-computed sentiment field from the scene JSON instead of the LLM,
    adjust `_sentiment_via_llm` or short-circuit `_extract_sentiment` to read `scene.get("sentiment")`.
    """

    def __init__(
        self,
        openai_api_key: Optional[str],
        openai_model: str = "gpt-4o-mini",
        elevenlabs_api_key: Optional[str] = None,
        music_length_ms: int = 45000,
    ):
        try:
            from elevenlabs.client import ElevenLabs  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "elevenlabs package not installed. Rebuild the container or pip install -r requirements.txt."
            ) from exc

        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_model = openai_model
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for sentiment analysis.")
        if not self.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is required for music generation.")
        self._openai_client = OpenAI(api_key=self.openai_api_key)
        self._eleven_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        self.music_length_ms = music_length_ms

    def extract_sentiment(self, scene: Dict) -> str:
        """
        Derive music direction from the structured scene JSON.
        Currently uses an LLM; swap to a direct scene["sentiment"] read if/when provided.
        """
        return self._sentiment_via_llm(scene)

    def _sentiment_via_llm(self, scene: Dict) -> str:
        try:
            response = self._openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a music director. Given structured scene JSON, "
                            "return a concise mood and musical direction for a short score. "
                            "Focus on tempo, intensity, genre cues, and instrumentation. "
                            "Keep it under 75 words."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Scene JSON:\n{json.dumps(scene, indent=2)}",
                    },
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content
        except OpenAIError as exc:
            raise RuntimeError(f"Failed to analyze sentiment: {exc}") from exc

    def generate_music(
        self,
        prompt: str,
        use_baseline: bool = False,
        music_length_ms: Optional[int] = None,
    ) -> Tuple[bytes, str]:
        """
        Call ElevenLabs music generation via composition plan + compose.
        Returns (audio_bytes, mime_type).
        """
        if use_baseline:
            prompt = f"[Refine existing track] {prompt}"

        length_ms = music_length_ms or self.music_length_ms

        try:
            plan = self._eleven_client.music.composition_plan.create(
                prompt=prompt,
                music_length_ms=length_ms,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to create composition plan: {exc}") from exc

        try:
            raw = self._eleven_client.music.compose(composition_plan=plan)
        except Exception as exc:
            raise RuntimeError(f"Music compose failed: {exc}") from exc

        audio_bytes = self._extract_audio(raw)
        return audio_bytes, "audio/mpeg"

    @staticmethod
    def _extract_audio(composition) -> bytes:
        """
        Handle different return types from the ElevenLabs SDK.
        """
        if composition is None:
            raise RuntimeError("Music compose returned no data.")
        # Generators/iterables yielding chunks
        if hasattr(composition, "__iter__") and not isinstance(composition, (dict, bytes, bytearray, str)):
            try:
                chunks = list(composition)
                if chunks:
                    return b"".join(
                        [bytes(c) if isinstance(c, (bytes, bytearray)) else bytes(str(c), "utf-8") for c in chunks]
                    )
            except Exception:
                pass
        if isinstance(composition, (bytes, bytearray)):
            return bytes(composition)
        if isinstance(composition, str):
            try:
                return base64.b64decode(composition)
            except Exception:
                pass
        if isinstance(composition, (list, tuple)) and all(isinstance(c, int) for c in composition):
            return bytes(composition)
        # Some SDK versions may return dicts with 'audio' base64
        if isinstance(composition, dict):
            audio_b64 = composition.get("audio") or composition.get("audio_base64")
            if audio_b64:
                return base64.b64decode(audio_b64)
            audio_url = composition.get("audio_url") or composition.get("url")
            if audio_url:
                return MusicService._download(audio_url)
        # Fallback: attempt to access .audio or .output
        audio_attr = getattr(composition, "audio", None) or getattr(composition, "output", None)
        if audio_attr:
            if isinstance(audio_attr, (bytes, bytearray)):
                return bytes(audio_attr)
            try:
                return base64.b64decode(audio_attr)
            except Exception:
                pass
        # requests.Response style
        content_attr = getattr(composition, "content", None)
        if content_attr:
            try:
                return bytes(content_attr)
            except Exception:
                pass
        url_attr = getattr(composition, "url", None) or getattr(composition, "audio_url", None)
        if url_attr:
            return MusicService._download(url_attr)

        raise RuntimeError(
            f"Unrecognized music compose response format (type={type(composition)}). "
            "Check ElevenLabs SDK version and response shape."
        )

    @staticmethod
    def _download(url: str) -> bytes:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
