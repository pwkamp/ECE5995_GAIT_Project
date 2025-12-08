"""
Streamlit multi-page interface for the GAIT idea-to-video workflow.
"""

from __future__ import annotations

import os
from typing import List, Protocol

import streamlit as st

try:
    from .app_state import AppState
    from .character_generation_page import CharacterGenerationPage
    from .music_generation_page import MusicGenerationPage
    from .script_page import ScriptPage
    from .structured_json_page import StructuredJSONPage
    from .video_generation_page import VideoGenerationPage
except ImportError:
    from app_state import AppState
    from character_generation_page import CharacterGenerationPage
    from music_generation_page import MusicGenerationPage
    from script_page import ScriptPage
    from structured_json_page import StructuredJSONPage
    from video_generation_page import VideoGenerationPage


class Page(Protocol):
    name: str
    icon: str
    def render(self) -> None: ...


class GAITApp:
    """Coordinator for the Streamlit app and page routing."""

    def __init__(self, config: dict):
        self.state = AppState()
        self.state.bind()
        self.config = config

        self.pages: List[Page] = [
            ScriptPage(self.state, self.config),
            CharacterGenerationPage(self.state, self.config),
            MusicGenerationPage(self.state, self.config),
            VideoGenerationPage(self.state),
            StructuredJSONPage(self.state, self.config),
        ]

    def render(self) -> None:
        st.set_page_config(
            page_title="GAIT Story Builder",
            page_icon="GAIT",
            layout="wide",
        )
        st.title("GAIT Story Builder")
        st.markdown(
            "Design a scene, mock the AI handoffs, and see how assets move through "
            "the pipeline. Replace the placeholders with live AI calls when ready."
        )
        st.markdown("---")
        self._maybe_seed_dev_script()
        selected_page = self._sidebar_nav()
        selected_page.render()

    def _maybe_seed_dev_script(self) -> None:
        if not self.config.get("dev_mode"):
            return
        sample_script = (
            "**Title: Factory Prank**\n\n"
            "**Characters:**\n"
            "- **EDWARD** (mid-30s, tall, lean, mischievous ringleader in grease-stained overalls and flat cap)\n"
            "- **HARRY** (late 20s, stockier, jovial accomplice with suspenders and rolled sleeves)\n"
            "- **GEORGE** (early 30s, unsuspecting victim, neat cap and vest, cautious demeanor)\n\n"
            "**Scene Description:**\n"
            "*Time: Day. Place: A gritty early 1900s factory floor with machinery, pipes, and hanging lamps casting stark shadows. "
            "Mood: Playful silent-film prank. Art Style: Black-and-white, grainy silent film.*\n\n"
            "---\n\n"
            "**(EDWARD and HARRY exchange sly glances on the factory floor.)**\n\n"
            "**EDWARD**\n(whispering)\nReady? When George gets here, lift the lever.\n\n"
            "**HARRY**\n(grinning)\nHe'll never see it coming.\n\n"
            "**(GEORGE walks over, adjusting his cap. Edward nods; Harry pulls the lever. A puff of air startles George; a harmless string dangles.)**\n\n"
            "**GEORGE**\n(startled, then smirking)\nVery funny.\n\n"
            "**EDWARD**\n(laughing)\nJust a bit of fun to lighten the shift.\n\n"
            "---\n\n"
            "**(End scene.)**"
        )
        if not st.session_state.get("dev_script_loaded") and not self.state.session.get("script_text"):
            self.state.set_script(sample_script)
            st.session_state["script_editor"] = sample_script
            st.session_state["dev_script_loaded"] = True

    def _sidebar_nav(self) -> Page:
        page_names = [f"{page.icon} {page.name}" for page in self.pages]
        choice = st.sidebar.radio("Workflow", page_names, key="nav_radio")
        index = page_names.index(choice)
        return self.pages[index]


def main() -> None:
    dev_mode = st.sidebar.toggle("Dev mode: preload sample script", value=True)
    secrets_api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    secrets_model = st.secrets.get("OPENAI_MODEL") if hasattr(st, "secrets") else None
    secrets_eleven = st.secrets.get("ELEVENLABS_API_KEY") if hasattr(st, "secrets") else None
    api_key = secrets_api_key or os.getenv("OPENAI_API_KEY", "")
    model = secrets_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    eleven_key = secrets_eleven or os.getenv("ELEVENLABS_API_KEY", "")
    eleven_length_ms = int(os.getenv("ELEVENLABS_MUSIC_LENGTH_MS", "45000"))

    masked_key = f"...{api_key[-4:]}" if api_key else "MISSING"
    masked_music = f"...{eleven_key[-4:]}" if eleven_key else "MISSING"
    debug_message = (
        f"ENV DEBUG - OPENAI_API_KEY: {masked_key}, OPENAI_MODEL: {model}, "
        f"ELEVENLABS_API_KEY: {masked_music}, ELEVENLABS_MUSIC_LENGTH_MS: {eleven_length_ms}"
    )
    print(debug_message)
    st.sidebar.info(debug_message)
    app = GAITApp(
        config={
            "api_key": api_key,
            "model": model,
            "dev_mode": dev_mode,
            "elevenlabs_api_key": eleven_key,
            "elevenlabs_music_length_ms": eleven_length_ms,
        }
    )
    app.render()


if __name__ == "__main__":
    main()

