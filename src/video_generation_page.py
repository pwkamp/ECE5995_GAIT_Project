from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

try:
    import app_utils as au
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.video_service import (
        generate_video_from_structured_scene,
        generate_video_with_sora,
        mix_music_to_video,
    )
except ImportError:  # Fallback when run as a standalone script context
    import app_utils as au
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.video_service import (
        generate_video_from_structured_scene,
        generate_video_with_sora,
        mix_music_to_video,
    )


class VideoGenerationPage:
    name = "Video Generation"
    icon = "🎬"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config

    def render(self) -> None:
        st.header(f"{self.icon} Final Video Generation")
        st.caption(
            "Bundle the structured scene, background, and (optionally) music into a simple preview video."
        )

        self._maybe_seed_dev_defaults()
        scene = self._load_scene()
        if not scene:
            if self._dev_defaults_available():
                scene = self._dev_placeholder_scene()
                st.info("Dev mode placeholder scene loaded for preview.")
            else:
                st.warning("No structured scene found. Generate the structured JSON first.")
                return

        ready = self._check_requirements()
        if not ready:
            return

        st.session_state.setdefault("video_music_volume", 50)

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
        sanitize_prompts = st.toggle(
            "Sanitize prompts (safe/cartoon tone)",
            value=st.session_state.get("video_sanitize_prompts", False),
            key="video_sanitize_prompts",
            help="When on, softens wording and nudges an animated style to reduce moderation issues.",
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
                music_volume_pct = float(st.session_state.get("video_music_volume", 50))
                music_volume = max(0.0, min(music_volume_pct / 100.0, 1.0))
                music_delay = float(st.session_state.get("video_music_delay", 0.0))
                music_start_offset = float(st.session_state.get("video_music_start_offset", 0.0))
                with st.status("Rendering video...", expanded=True) as status:
                    seconds_per_beat = 4
                    raw_path = None
                    if generator.startswith("Sora"):
                        video_path, raw_path = generate_video_with_sora(
                            scene=scene,
                            music_path=music_path,
                            seconds_per_beat=seconds_per_beat,
                            resolution=resolution,
                            sanitize_prompts=sanitize_prompts,
                            music_volume=music_volume,
                            music_delay_seconds=music_delay,
                            music_start_offset_seconds=music_start_offset,
                            model_id=model_id,
                            image_bytes=ref_image_bytes,
                            image_url=ref_image_url,
                        )
                    else:
                        video_path, raw_path = generate_video_from_structured_scene(
                            scene=scene,
                            background_asset=self.state.session.get("background_asset"),
                            music_path=music_path,
                            seconds_per_beat=seconds_per_beat,
                            resolution=resolution,
                            music_volume=music_volume,
                            music_delay_seconds=music_delay,
                            music_start_offset_seconds=music_start_offset,
                        )
                    video_path = Path(video_path).resolve()
                    raw_path = Path(raw_path).resolve() if raw_path else video_path
                    music_path_str = str(music_path) if music_path else None
                    note = (
                        f"{generator} output ({len(scene.get('beats', []))} beats). "
                        f"Raw (no music): {raw_path}"
                    )
                    if music_path_str:
                        note += f" | Music source: {music_path_str}"
                    self.state.set_video_asset(
                        {
                            "status": "ready",
                            "note": note,
                            "generator": generator,
                            "url": str(video_path),
                            "final_path": str(video_path),
                            "raw_path": str(raw_path),
                            "music_path": music_path_str,
                            "music_volume": music_volume,
                            "music_delay": music_delay,
                            "music_start_offset": music_start_offset,
                        }
                    )
                st.session_state.pop("video_export_path", None)
                st.session_state.pop("video_export_volume", None)
                if music_path_str:
                    st.session_state.pop("video_music_preview_path", None)
                    st.session_state["video_music_preview_volume"] = music_volume
                    st.session_state.pop("video_music_preview_source", None)
                    st.session_state.pop("video_music_preview_music", None)
                    st.session_state.pop("video_music_preview_delay", None)
                    st.session_state.pop("video_music_preview_start_offset", None)
                else:
                    st.session_state.pop("video_music_preview_path", None)
                    st.session_state.pop("video_music_preview_volume", None)
                    st.session_state.pop("video_music_preview_source", None)
                    st.session_state.pop("video_music_preview_music", None)
                    st.session_state.pop("video_music_preview_delay", None)
                    st.session_state.pop("video_music_preview_start_offset", None)
                    st.session_state.pop("video_export_path", None)
                    st.session_state.pop("video_export_volume", None)
                    status.update(label="Video ready.", state="complete")
                st.success(f"Video saved to {video_path}")
            except Exception as exc:
                st.error(f"Video generation failed: {exc}")

        video_asset = self.state.session.get("video_asset")
        if video_asset:
            self._render_playback(video_asset)
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
        # Dev-mode fallback: use default soundtrack if available
        if self.config.get("dev_mode"):
            _, music = self._locate_default_media()
            if music and music.exists():
                return music
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
        if not self.state.session.get("script_text") and not self._dev_defaults_available():
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

    def _render_playback(self, video_asset: dict) -> None:
        st.markdown("#### Playback & Export")
        raw_path = self._resolve_path(video_asset.get("raw_path") or video_asset.get("url"))
        final_path = self._resolve_path(video_asset.get("final_path") or video_asset.get("url"))
        music_path = self._resolve_path(video_asset.get("music_path"))

        if not raw_path or not raw_path.exists():
            fallback_raw = Path("src/output/generated_video_nomusic.mp4")
            if fallback_raw.exists():
                raw_path = fallback_raw
        if not final_path or not final_path.exists():
            fallback_final = Path("src/output/generated_video.mp4")
            if fallback_final.exists():
                final_path = fallback_final

        if (not raw_path or not raw_path.exists()) and self._dev_defaults_available():
            dev_video, dev_music = self._locate_default_media()
            raw_path = dev_video if dev_video and dev_video.exists() else raw_path
            music_path = music_path or (dev_music if dev_music and dev_music.exists() else None)

        st.write("Status:", video_asset.get("status", ""))
        if video_asset.get("note"):
            st.caption(video_asset["note"])

        st.markdown("**Without music**")
        if raw_path and raw_path.exists():
            st.video(str(raw_path))
        else:
            st.info("Raw video not found for preview.")

        if music_path and music_path.exists() and raw_path and raw_path.exists():
            st.markdown("**With music (live volume preview)**")
            default_volume_pct = float(
                st.session_state.get(
                    "video_music_volume",
                    round((video_asset.get("music_volume", 0.25) or 0.25) * 100, 1),
                )
            )
            volume_pct = st.slider(
                "Music volume (0-100%)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                value=default_volume_pct,
                key="video_music_volume",
                help="Adjust backing track loudness relative to the raw video.",
            )
            volume = max(0.0, min(volume_pct / 100.0, 1.0))
            if st.session_state.get("video_export_volume") is not None and st.session_state.get("video_export_volume") != volume:
                st.session_state.pop("video_export_path", None)
            st.session_state["video_export_volume"] = volume

            col_delay, col_offset = st.columns(2)
            with col_delay:
                delay = st.number_input(
                    "Delay before music starts (seconds)",
                    min_value=0.0,
                    max_value=120.0,
                    value=st.session_state.get("video_music_delay", video_asset.get("music_delay", 0.0) or 0.0),
                    step=0.5,
                    key="video_music_delay",
                    help="Play the video for this many seconds before music begins.",
                )
            with col_offset:
                start_offset = st.number_input(
                    "Start music at timestamp within track (seconds)",
                    min_value=0.0,
                    max_value=300.0,
                    value=st.session_state.get("video_music_start_offset", video_asset.get("music_start_offset", 0.0) or 0.0),
                    step=0.5,
                    key="video_music_start_offset",
                    help="Skip ahead in the music track before playback begins (e.g., jump to the chorus).",
                )

            delay = float(st.session_state.get("video_music_delay", video_asset.get("music_delay", 0.0) or 0.0))
            start_offset = float(st.session_state.get("video_music_start_offset", video_asset.get("music_start_offset", 0.0) or 0.0))

            preview_path = self._build_music_preview(raw_path, music_path, volume, delay, start_offset)
            if preview_path and preview_path.exists():
                st.video(str(preview_path))

            export_path = self._resolve_path(st.session_state.get("video_export_path"))
            if ButtonRow.single("Export & Save with music", key="export_with_music"):
                export_path = self._export_with_music(raw_path, music_path, volume, delay, start_offset)
                if export_path:
                    st.session_state["video_export_path"] = str(export_path)
                    st.session_state["video_export_volume"] = volume
                    video_asset.update(
                        {
                            "final_path": str(export_path),
                            "url": str(export_path),
                            "music_volume": volume,
                            "music_delay": delay,
                            "music_start_offset": start_offset,
                        }
                    )
                    self.state.set_video_asset(video_asset)
            if export_path and export_path.exists():
                st.success(f"Export ready at {export_path}")
                st.download_button(
                    label="Download with music",
                    data=export_path.read_bytes(),
                    file_name=export_path.name,
                    mime="video/mp4",
                    key="download_with_music",
                )
        else:
            st.info("No music attached; only the raw preview is available.")
            if final_path and final_path.exists() and (not raw_path or final_path != raw_path):
                st.video(str(final_path))

    def _build_music_preview(self, raw_path: Path, music_path: Path, volume: float, delay: float, start_offset: float) -> Optional[Path]:
        preview_path = self._resolve_path(st.session_state.get("video_music_preview_path"))
        preview_volume = st.session_state.get("video_music_preview_volume")
        preview_source = st.session_state.get("video_music_preview_source")
        preview_music = st.session_state.get("video_music_preview_music")
        preview_delay = st.session_state.get("video_music_preview_delay")
        preview_start_offset = st.session_state.get("video_music_preview_start_offset")
        target_path = Path("src/output/generated_video_with_music_preview.mp4")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        needs_refresh = (
            preview_volume != volume
            or preview_source != str(raw_path)
            or preview_music != str(music_path)
            or preview_delay != delay
            or preview_start_offset != start_offset
            or not (preview_path and preview_path.exists())
        )
        if needs_refresh:
            self._warn_if_music_short(raw_path, music_path, delay, start_offset)
            try:
                with st.spinner("Updating music preview..."):
                    preview_path = mix_music_to_video(
                        raw_video_path=raw_path,
                        music_path=music_path,
                        volume=volume,
                        music_delay_seconds=delay,
                        music_start_offset_seconds=start_offset,
                        output_path=target_path,
                    )
                st.session_state["video_music_preview_path"] = str(preview_path)
                st.session_state["video_music_preview_volume"] = volume
                st.session_state["video_music_preview_source"] = str(raw_path)
                st.session_state["video_music_preview_music"] = str(music_path)
                st.session_state["video_music_preview_delay"] = delay
                st.session_state["video_music_preview_start_offset"] = start_offset
            except Exception as exc:
                st.error(f"Failed to update music preview: {exc}")
                return None
        return preview_path

    def _export_with_music(self, raw_path: Path, music_path: Path, volume: float, delay: float, start_offset: float) -> Optional[Path]:
        try:
            with st.spinner("Exporting video with music..."):
                export_path = mix_music_to_video(
                    raw_video_path=raw_path,
                    music_path=music_path,
                    volume=volume,
                    music_delay_seconds=delay,
                    music_start_offset_seconds=start_offset,
                    output_path=Path("src/output/generated_video_with_music.mp4"),
                )
            return export_path
        except Exception as exc:
            st.error(f"Failed to export video with music: {exc}")
            return None

    def _resolve_path(self, path_str: Optional[str]) -> Optional[Path]:
        if not path_str:
            return None
        path = Path(path_str)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    @staticmethod
    def _probe_video_duration(path: Path) -> float:
        try:
            clip = VideoFileClip(str(path))
            dur = float(getattr(clip, "duration", 0) or 0)
            clip.close()
            return dur
        except Exception:
            return 0.0

    @staticmethod
    def _probe_audio_duration(path: Path) -> float:
        try:
            audio = AudioFileClip(str(path))
            dur = float(getattr(audio, "duration", 0) or 0)
            audio.close()
            return dur
        except Exception:
            pass
        # Fallback via pydub for more robust probing
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(path)
            return float(len(seg) / 1000.0)
        except Exception:
            return 0.0

    def _warn_if_music_short(self, raw_path: Path, music_path: Path, delay: float, start_offset: float) -> None:
        video_duration = self._probe_video_duration(raw_path)
        music_duration = self._probe_audio_duration(music_path)
        remaining_music = max(0.0, music_duration - start_offset)
        needed_music = max(0.0, (video_duration - delay) if video_duration else 0.0)
        if needed_music <= 0:
            return
        if remaining_music <= 0:
            st.warning(
                "Music appears to have no remaining duration after the chosen offset. "
                "Reduce the start offset or pick a longer track."
            )
            return
        if remaining_music < needed_music:
            st.warning(
                f"Music may end early: remaining track after offset is {remaining_music:.1f}s but video needs {needed_music:.1f}s. "
                "Consider a smaller delay or offset."
            )

    def _dev_defaults_available(self) -> bool:
        if not self.config.get("dev_mode"):
            return False
        video, _ = self._locate_default_media()
        return bool(video and video.exists())

    def _maybe_seed_dev_defaults(self) -> None:
        """
        In dev mode, seed a default video + music asset so the page can be tested without new generations.
        """
        if not self.config.get("dev_mode"):
            return
        if self.state.session.get("video_asset"):
            return
        video_path, music_path = self._locate_default_media()
        if not video_path:
            return
        note = "Dev default asset loaded from src/static."
        if music_path:
            note += f" Music: {music_path.name}"
        self.state.set_video_asset(
            {
                "status": "ready",
                "note": note,
                "generator": "Dev default",
                "url": str(video_path),
                "final_path": str(video_path),
                "raw_path": str(video_path),
                "music_path": str(music_path) if music_path else None,
                "music_volume": max(0.0, min(float(st.session_state.get("video_music_volume", 50)) / 100.0, 1.0)),
            }
        )

    def _locate_default_media(self) -> tuple[Optional[Path], Optional[Path]]:
        """
        Find default dev video/music under src/static.
        Returns (video_path, music_path).
        """
        base = Path("src/static")
        video_candidates = [base / "default.mp4"]
        video_candidates.extend(sorted(base.glob("*.mp4")))
        music_candidates = [base / "default.mp3", base / "The_Keystone_Caper.mp3"]
        music_candidates.extend(sorted(base.glob("*.mp3")))

        video_path = next((p for p in video_candidates if p.exists()), None)
        music_path = next((p for p in music_candidates if p.exists()), None)
        return video_path, music_path

    @staticmethod
    def _dev_placeholder_scene() -> dict:
        return {
            "scene_title": "Dev Placeholder",
            "logline": "Placeholder scene for dev testing.",
            "art_style": "friendly 2D animation, cel-shaded, cartoon",
            "background": {"description": "Factory floor placeholder", "time_of_day": "Day", "location": "Factory"},
            "characters": [{"name": "EDWARD", "description": "Placeholder character", "style_hint": ""}],
            "beats": [{"order": 1, "description": "Placeholder beat for preview."}],
        }
