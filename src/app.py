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
    from .script_page import ScriptPage
    from .structured_json_page import StructuredJSONPage
    from .video_generation_page import VideoGenerationPage
except ImportError:
    from app_state import AppState
    from character_generation_page import CharacterGenerationPage
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
            CharacterGenerationPage(self.state, self.config),
            ScriptPage(self.state, self.config),
            VideoGenerationPage(self.state),
            StructuredJSONPage(self.state, self.config)
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
            "**Title: Smoothie Showdown**\n\n"
            "**Characters:**\n"
            "- **JAKE** (mid-20s, laid-back, always wearing a goofy hat, loves trying new things)\n"
            "- **SARAH** (early 30s, health-conscious, sarcastic, always prepared with a witty comeback)\n"
            "- **MIKE** (late 20s, overly enthusiastic, the “smoothie expert,” a bit clueless)\n\n"
            "**Scene Description:**\n"
            "*Time: Late morning. Place: A bright, colorful kitchen filled with fresh fruits and a blender. "
            "Mood: Light-hearted and playful. Art Style: Comic.*\n\n"
            "---\n\n"
            "**(JAKE stands by the blender, holding a banana with a mischievous grin.)**\n\n"
            "**JAKE**\n(cheerfully)\nI’m making the ultimate smoothie! Banana, spinach, and... (holds up a handful of gummy bears) these!\n\n"
            "**SARAH**\n(rolling her eyes)\nGummy bears? You do know this is a health thing, right?\n\n"
            "**(MIKE bounces in, excited.)**\n\n"
            "**MIKE**\nCan I add chocolate syrup? I read it’s a superfood!\n\n"
            "**JAKE**\n(grinning)\nSure, let’s just call it a “dessert smoothie.”\n\n"
            "**SARAH**\n(smirking)\nMore like a “regret smoothie.”\n\n"
            "**(JAKE presses the blender button; it sputters and sprays smoothie everywhere.)**\n\n"
            "**JAKE**\n(laughing)\nGuess it’s a “splat-er smoothie!”\n\n"
            "**(All three burst into laughter.)**\n\n"
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

    api_key = secrets_api_key or os.getenv("OPENAI_API_KEY", "")
    model = secrets_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    masked_key = f"...{api_key[-4:]}" if api_key else "MISSING"
    debug_message = f"ENV DEBUG - OPENAI_API_KEY: {masked_key}, OPENAI_MODEL: {model}"
    print(debug_message)
    st.sidebar.info(debug_message)

    app = GAITApp(config={"api_key": api_key, "model": model, "dev_mode": dev_mode})
    app.render()


if __name__ == "__main__":
    main()
