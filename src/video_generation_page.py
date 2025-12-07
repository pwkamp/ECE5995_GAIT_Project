from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    import app_utils as au
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.video_service import generate_video_from_structured_scene
except ImportError:  # Fallback when run as a standalone script context
    import app_utils as au
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.video_service import generate_video_from_structured_scene


class VideoGenerationPage:
    name = "Video Generation"
    icon = "🎬"

    def __init__(self, state: AppState):
        self.state = state

    def render(self) -> None:
        st.header(f"{self.icon} Final Video Generation")
        st.caption(
            "Bundle the structured scene, background, and (optionally) music into a simple preview video."
        )

        scene = self._load_scene()
        if not scene:
            st.warning("No structured scene found. Generate the structured JSON first.")
            return

        ready = self._check_requirements()
        if not ready:
            return

        st.markdown("#### Options")
        seconds_per_beat = st.slider(
            "Seconds per beat",
            min_value=2,
            max_value=10,
            value=4,
            step=1,
            help="How long each beat card stays on screen.",
            key="video_seconds_per_beat",
        )
        resolution_label = st.selectbox(
            "Resolution",
            options=["1280x720", "1920x1080"],
            index=0,
            help="Resolution for the generated video.",
            key="video_resolution",
        )
        use_music = st.toggle(
            "Attach saved music (if available)",
            value=True,
            key="video_use_music",
            help="Uses src/output/scene_music.mp3 or the last generated track in memory.",
        )

        music_path = self._resolve_music_path() if use_music else None
        if use_music and not music_path:
            st.info("No saved music found. Generate music first or save a track to src/output/scene_music.mp3.")

        if ButtonRow.single("Generate video from structured JSON", key="generate_video"):
            try:
                resolution = self._parse_resolution(resolution_label)
                with st.status("Rendering video...", expanded=True) as status:
                    video_path = generate_video_from_structured_scene(
                        scene=scene,
                        background_asset=self.state.session.get("background_asset"),
                        music_path=music_path,
                        seconds_per_beat=seconds_per_beat,
                        resolution=resolution,
                    )
                    self.state.set_video_asset(
                        {
                            "status": "ready",
                            "note": f"Built locally from structured_scene.json ({len(scene.get('beats', []))} beats).",
                            "url": str(video_path),
                        }
                    )
                    status.update(label="Video ready.", state="complete")
                st.success(f"Video saved to {video_path}")
            except Exception as exc:
                st.error(f"Video generation failed: {exc}")

        video_asset = self.state.session.get("video_asset")
        if video_asset:
            st.markdown("#### Playback")
            st.video(video_asset["url"])
            st.write("Status:", video_asset.get("status", ""))
            st.write("Note:", video_asset.get("note", ""))
            st.code(video_asset["url"], language="text")
        else:
            st.info("No video yet. Generate to see the playback.")

    def _load_scene(self):
        scene = self.state.session.get("structured_scene")
        if scene:
            return scene
        return au.load_or_init_structured_scene(self.state)

    def _resolve_music_path(self) -> Path | None:
        """
        Return a path to music to use, writing in-memory audio if present.
        """
        output_path = Path("src/output/scene_music.mp3")
        music_asset = self.state.session.get("music_asset")
        if music_asset and music_asset.get("audio_bytes"):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(music_asset["audio_bytes"])
            return output_path
        if output_path.exists():
            return output_path
        return None

    @staticmethod
    def _parse_resolution(label: str) -> tuple[int, int]:
        try:
            width_str, height_str = label.lower().split("x")
            return int(width_str), int(height_str)
        except Exception:
            return (1280, 720)

    def _check_requirements(self) -> bool:
        missing = []
        if not self.state.session.get("script_text"):
            missing.append("Script text")

        if missing:
            st.warning(
                "Complete earlier steps before rendering the video: "
                + ", ".join(missing)
            )
            return False

        if not self.state.session.get("background_asset"):
            st.info("No background image found; using a simple gradient backdrop.")
        if not self.state.session.get("character_assets"):
            st.info("No character images found; beats will be rendered as text cards only.")
        return True
