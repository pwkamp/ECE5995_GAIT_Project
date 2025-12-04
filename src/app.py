"""
Streamlit multi-page mock interface for the GAIT idea-to-video workflow.

Each workflow step is defined in its own module to keep implementations
clean and reusable. AI calls remain mocked for now.
"""

from __future__ import annotations

from typing import List, Protocol

import streamlit as st

try:
    from .app_state import AppState
    from .character_generation_page import CharacterGenerationPage
    from .script_page import ScriptPage
    from .video_generation_page import VideoGenerationPage
except ImportError:  # Fallback when run as a standalone script (e.g., streamlit run src/app.py)
    from app_state import AppState
    from character_generation_page import CharacterGenerationPage
    from script_page import ScriptPage
    from video_generation_page import VideoGenerationPage


class Page(Protocol):
    name: str
    icon: str

    def render(self) -> None:
        ...


class GAITApp:
    """Coordinator for the Streamlit app and page routing."""

    def __init__(self):
        self.state = AppState()
        self.state.bind()

        self.pages: List[Page] = [
            ScriptPage(self.state),
            CharacterGenerationPage(self.state),
            VideoGenerationPage(self.state),
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

        selected_page = self._sidebar_nav()
        selected_page.render()

    def _sidebar_nav(self) -> Page:
        page_names = [f"{page.icon} {page.name}" for page in self.pages]
        choice = st.sidebar.radio("Workflow", page_names, key="nav_radio")
        index = page_names.index(choice)
        return self.pages[index]


def main() -> None:
    app = GAITApp()
    app.render()


if __name__ == "__main__":
    main()
