from __future__ import annotations

import os
from typing import Optional, Tuple

import requests
from openai import OpenAI


class OpenAIImageService:
    """Wrapper for OpenAI image generation; returns image bytes and URL."""

    def __init__(self, api_key: Optional[str] = None, model: str = "dall-e-3"):
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set for image generation.")
        self.client = OpenAI(api_key=key)
        self.model = os.getenv("OPENAI_IMAGE_MODEL", model)

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        reference_note: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """
        Generate an image. Returns (image_bytes, image_url_or_b64).
        If reference_note is provided, append it to the prompt to keep style continuity.
        """
        full_prompt = prompt
        if reference_note:
            full_prompt = f"{prompt}\nReference note: {reference_note}"

        response = self.client.images.generate(
            model=self.model,
            prompt=full_prompt,
            size=size,
        )
        data = response.data[0]
        url = getattr(data, "url", None)
        b64_json = getattr(data, "b64_json", None)

        if url:
            image_bytes = self._download(url)
            return image_bytes, url
        if b64_json:
            import base64

            image_bytes = base64.b64decode(b64_json)
            return image_bytes, "embedded_base64"

        raise RuntimeError("Image generation returned no url or base64 data.")

    @staticmethod
    def _download(url: str) -> bytes:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
