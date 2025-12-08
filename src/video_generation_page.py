from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    import app_utils as au
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.video_service import (
        generate_video_from_structured_scene,
        generate_video_with_sora,
    )
except ImportError:  # Fallback when run as a standalone script context
    import app_utils as au
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.video_service import (
        generate_video_from_structured_scene,
        generate_video_with_sora,
    )


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
        generator = st.selectbox(
            "Video generator",
            options=["Sora (OpenAI)", "Local placeholder"],
            index=0,
            help="Sora uses OpenAI video; Local renders static beats.",
            key="video_generator",
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
        model_id = st.text_input(
            "Model id",
            value=st.session_state.get("video_model_id", "sora-2"),
            key="video_model_id_input",
            help="OpenAI video model id (e.g., sora-2 or sora-2-pro).",
        )

        music_path = self._resolve_music_path() if use_music else None
        if use_music and not music_path:
            st.info("No saved music found. Generate music first or save a track to src/output/scene_music.mp3.")

        ref_image_bytes, ref_image_url = self._resolve_reference_image()
        if generator.startswith("Sora") and not (ref_image_bytes or ref_image_url):
            st.info("No composite reference image found; Sora will rely on text prompts only.")

        if ButtonRow.single("Generate video from structured JSON", key="generate_video"):
            try:
                resolution = self._parse_resolution(resolution_label)
                with st.status("Rendering video...", expanded=True) as status:
                    seconds_per_beat = 4
                    raw_path = None
                    if generator.startswith("Sora"):
                        video_path, raw_path = generate_video_with_sora(
                            scene=scene,
                            music_path=music_path,
                            seconds_per_beat=seconds_per_beat,
                            resolution=resolution,
                            model_id=model_id,
                            image_bytes=ref_image_bytes,
                            image_url=ref_image_url,
                        )
                    else:
                        video_path = generate_video_from_structured_scene(
                            scene=scene,
                            background_asset=self.state.session.get("background_asset"),
                            music_path=music_path,
                            seconds_per_beat=seconds_per_beat,
                            resolution=resolution,
                        )
                    video_path = Path(video_path).resolve()
                    raw_path = Path(raw_path).resolve() if raw_path else None
                    self.state.set_video_asset(
                        {
                            "status": "ready",
                            "note": (
                                f"Built locally from structured_scene.json ({len(scene.get('beats', []))} beats). "
                                f"Raw (no music): {raw_path if raw_path else 'n/a'}"
                            ),
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
            video_path = Path(video_asset.get("url", ""))
            if not video_path.is_absolute():
                video_path = (Path.cwd() / video_path).resolve()
            if video_path.exists():
                st.video(str(video_path))
                st.write("Status:", video_asset.get("status", ""))
                st.write("Note:", video_asset.get("note", ""))
                st.code(str(video_path), language="text")
            else:
                st.error(f"Video file not found at {video_path}")
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

        return True

    def _resolve_reference_image(self) -> tuple[bytes | None, str | None]:
        """
        Return in-memory or saved composite scene image for Sora reference.
        """
        composite = self.state.session.get("scene_composite") or {}
        image_bytes = composite.get("image_bytes")
        image_url = composite.get("url")
        if not image_bytes:
            path = Path("src/output/scene_composite.png")
            if path.exists():
                image_bytes = path.read_bytes()
        return image_bytes, image_url
