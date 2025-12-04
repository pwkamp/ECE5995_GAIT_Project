from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow, ProgressHelper
except ImportError:  # Fallback when run as a standalone script context
    from app_state import AppState
    from ui_helpers import ButtonRow, ProgressHelper


class VideoGenerationPage:
    name = "Video Generation"
    icon = "🎬"

    def __init__(self, state: AppState):
        self.state = state

    def render(self) -> None:
        st.header(f"{self.icon} Final Video Generation")
        st.caption(
            "Bundle script, characters, and background into a final render. "
            "Progress and playback are mocked for now."
        )

        ready = self._check_requirements()
        if not ready:
            return

        if ButtonRow.single("Mock Generate Video", key="generate_video"):
            ProgressHelper.run("Generating video (mock)...", steps=6, delay=0.25)
            self.state.set_video_asset(
                {
                    "status": "ready",
                    "note": "Video generated in the cloud (placeholder).",
                    "url": "path/to/generated_video.mp4",
                }
            )
            st.success("Video generation complete.")

        video_asset = self.state.session.get("video_asset")
        if video_asset:
            st.markdown("#### Playback")
            st.info("Playback placeholder: swap with st.video using the real file/URL.")
            st.write("Status:", video_asset["status"])
            st.write("Note:", video_asset["note"])
            st.code(video_asset["url"], language="text")
        else:
            st.info("No video yet. Generate to see the playback placeholder.")

    def _check_requirements(self) -> bool:
        missing = []
        if not self.state.session.get("script_text"):
            missing.append("Script")
        if not self.state.session.get("character_assets"):
            missing.append("Characters")
        if not self.state.session.get("background_asset"):
            missing.append("Background")

        if missing:
            st.warning(
                "Complete earlier steps before rendering the video: "
                + ", ".join(missing)
            )
            return False
        return True
