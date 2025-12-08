from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import streamlit as st
import app_utils as au

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.music_service import MusicService
except ImportError:
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.music_service import MusicService


class MusicGenerationPage:
    name = "Music Generation"
    icon = "🎵"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config

    def render(self) -> None:
        st.header(f"{self.icon} Music Generation")
        st.caption("Analyze the scene mood, generate a backing track, refine it, and save the final audio.")

        scene = self._load_scene()
        if not scene:
            st.warning("No structured scene found. Generate the script + structured JSON first.")
            return

        sentiment = self._get_sentiment(scene)
        st.markdown("#### Scene sentiment & direction")
        st.info(sentiment or "Sentiment pending analysis.")

        self._render_generation_controls(scene, sentiment)
        self._render_existing_asset()
        self._render_save_controls()

    def _load_scene(self) -> Optional[Dict]:
        """
        Try pulling the structured scene from session, then disk (src/output/structured_scene.json).
        """
        scene = self.state.session.get("structured_scene")
        if scene:
            return scene
        return au.load_or_init_structured_scene(self.state)

    def _get_sentiment(self, scene: Dict) -> str:
        """
        Derives sentiment via LLM today; to switch to a direct JSON field,
        replace this call with `scene.get("sentiment", "")`.
        """
        signature = json.dumps(scene, sort_keys=True)
        cached_sig = st.session_state.get("music_sentiment_signature")
        if cached_sig == signature and st.session_state.get("music_sentiment"):
            return st.session_state["music_sentiment"]

        try:
            service = self._get_music_service()
        except Exception as exc:
            st.error(f"Cannot analyze sentiment: {exc}")
            return ""

        with st.spinner("Analyzing scene mood..."):
            try:
                sentiment = service.extract_sentiment(scene)
                st.session_state["music_sentiment"] = sentiment
                st.session_state["music_sentiment_signature"] = signature
                return sentiment
            except Exception as exc:
                st.error(f"Sentiment analysis failed: {exc}")
                return ""

    def _render_generation_controls(self, scene: Dict, sentiment: str) -> None:
        st.markdown("#### Generate or refine music")

        col_len, col_vocals = st.columns([2, 1])
        with col_len:
            length_seconds = st.slider(
                "Length (seconds)",
                min_value=10,
                max_value=90,
                value=st.session_state.get("music_length_seconds", 45),
                step=5,
                key="music_length_seconds",
            )
        with col_vocals:
            include_vocals = st.toggle(
                "Include vocals",
                value=st.session_state.get("music_include_vocals", False),
                key="music_include_vocals",
                help="Toggle to request sung/voiced elements in the track.",
            )

        col_tempo, col_energy = st.columns(2)
        with col_tempo:
            tempo = st.selectbox(
                "Tempo",
                options=["slow", "moderate", "fast"],
                index=["slow", "moderate", "fast"].index(
                    st.session_state.get("music_tempo", "moderate")
                ),
                key="music_tempo",
            )
        with col_energy:
            energy = st.selectbox(
                "Energy",
                options=["chill", "balanced", "intense"],
                index=["chill", "balanced", "intense"].index(
                    st.session_state.get("music_energy", "balanced")
                ),
                key="music_energy",
            )

        direction_default = (
            "Old-timey silent-film piano underscore: playful, bouncy, with clear melody and period feel."
        )
        user_direction = st.text_area(
            "Additional music direction",
            value=st.session_state.get("music_direction", direction_default),
            height=120,
            key="music_direction",
        )

        music_asset = self.state.session.get("music_asset")
        mode = st.radio(
            "Generation mode",
            options=["Start fresh", "Refine current output"],
            index=1 if music_asset else 0,
            help="Refine reuses the last track as a style baseline (prompt-level for now).",
            key="music_generation_mode",
        )

        col_generate, col_reset = st.columns([3, 1])
        with col_generate:
            if ButtonRow.single("Generate music", key="generate_music"):
                self._trigger_generation(
                    scene=scene,
                    sentiment=sentiment,
                    user_direction=user_direction,
                    use_baseline=mode == "Refine current output",
                    length_seconds=length_seconds,
                    include_vocals=include_vocals,
                    tempo=tempo,
                    energy=energy,
                )
        with col_reset:
            if ButtonRow.single("Clear current track", key="clear_music", disabled=not music_asset):
                self.state.set_music_asset(None)
                st.session_state.pop("music_refinement_notes", None)
                st.success("Cleared music output. Generate again to create a new track.")

        st.markdown("#### Refinement notes")
        st.text_area(
            "What should change?",
            value=st.session_state.get("music_refinement_notes", ""),
            height=120,
            key="music_refinement_notes",
            placeholder="Example: Make it slower after the midpoint; add a brief crescendo for the punchline.",
        )
        if ButtonRow.single("Apply changes", key="regenerate_music", disabled=not music_asset):
            self._trigger_generation(
                scene=scene,
                sentiment=sentiment,
                user_direction=st.session_state.get("music_refinement_notes", ""),
                use_baseline=mode == "Refine current output",
                length_seconds=length_seconds,
                include_vocals=include_vocals,
                tempo=tempo,
                energy=energy,
            )

    def _render_existing_asset(self) -> None:
        music_asset = self.state.session.get("music_asset")
        if not music_asset:
            st.info("No music yet. Generate to hear a preview.")
            return

        st.markdown("#### Preview")
        st.audio(music_asset["audio_bytes"], format=music_asset.get("mime_type", "audio/mpeg"))
        st.write("Sentiment basis:", music_asset.get("sentiment", ""))
        st.write("Prompt used:", music_asset.get("prompt", ""))
        st.caption(music_asset.get("note", ""))

    def _render_save_controls(self) -> None:
        music_asset = self.state.session.get("music_asset")
        if not music_asset:
            return
        output_path = Path("src/output/scene_music.mp3")
        if ButtonRow.single("Confirm & Save music", key="save_music"):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(music_asset["audio_bytes"])
            st.success(f"Saved music to {output_path}")

    def _trigger_generation(
        self,
        scene: Dict,
        sentiment: str,
        user_direction: str,
        use_baseline: bool,
        length_seconds: int,
        include_vocals: bool,
        tempo: str,
        energy: str,
    ) -> None:
        if not sentiment:
            st.error("Sentiment is missing; cannot build a music prompt.")
            return
        try:
            service = self._get_music_service()
        except Exception as exc:
            st.error(f"Cannot generate music: {exc}")
            return

        baseline_prompt = ""
        if use_baseline and self.state.session.get("music_asset"):
            baseline_prompt = self.state.session["music_asset"].get("prompt", "")
        prompt = self._build_composition_prompt(
            scene=scene,
            sentiment=sentiment,
            user_direction=user_direction,
            use_baseline=use_baseline,
            baseline_prompt=baseline_prompt,
            length_seconds=length_seconds,
            include_vocals=include_vocals,
            tempo=tempo,
            energy=energy,
        )

        with st.status("Generating music via ElevenLabs...", expanded=True) as status:
            try:
                audio_bytes, mime_type = service.generate_music(
                    prompt=prompt,
                    use_baseline=use_baseline,
                    music_length_ms=length_seconds * 1000,
                )
                asset = {
                    "status": "ready",
                    "note": "Track generated via ElevenLabs",
                    "prompt": prompt,
                    "sentiment": sentiment,
                    "length_seconds": length_seconds,
                    "include_vocals": include_vocals,
                    "tempo": tempo,
                    "energy": energy,
                    "audio_bytes": audio_bytes,
                    "mime_type": mime_type,
                }
                self.state.set_music_asset(asset)
                status.update(label="Music ready for playback.", state="complete")
                st.success("Music generated.")
            except Exception as exc:
                status.update(label=f"Generation failed: {exc}", state="error")
                st.error(f"Music generation failed: {exc}")

    @st.cache_resource(show_spinner=False)
    def _get_music_service(_self) -> MusicService:
        return MusicService(
            openai_api_key=_self.config.get("api_key"),
            openai_model=_self.config.get("model", "gpt-4o-mini"),
            elevenlabs_api_key=_self.config.get("elevenlabs_api_key"),
            music_length_ms=_self.config.get("elevenlabs_music_length_ms", 45000),
        )

    @staticmethod
    def _build_composition_prompt(
        scene: Dict,
        sentiment: str,
        user_direction: str,
        use_baseline: bool,
        baseline_prompt: str = "",
        length_seconds: int = 45,
        include_vocals: bool = False,
        tempo: str = "moderate",
        energy: str = "balanced",
    ) -> str:
        logline = scene.get("logline", "")
        art_style = scene.get("art_style", "")
        background = scene.get("background", {})
        location = background.get("location", "")
        time_of_day = background.get("time_of_day", "")
        beats = scene.get("beats", [])
        beat_summary = "; ".join([beat.get("description", "") for beat in beats[:6]])

        prompt_parts = [
            f"Scene mood/sentiment: {sentiment}",
            f"Logline: {logline}",
            f"Art style: {art_style}",
            f"Setting: {location} at {time_of_day}",
            f"Key beats: {beat_summary}",
            f"Target length: ~{length_seconds} seconds",
            f"Vocals: {'include vocals/humming' if include_vocals else 'instrumental only'}",
            f"Tempo: {tempo}",
            f"Energy: {energy}",
            f"User direction: {user_direction or 'None provided.'}",
        ]
        if use_baseline:
            prompt_parts.append("Refine the previous track while keeping core motifs.")
            if baseline_prompt:
                prompt_parts.append(f"Previous track guidance: {baseline_prompt}")
        return "\n".join(prompt_parts)
