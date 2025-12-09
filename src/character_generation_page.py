from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import app_utils as au

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow, ProgressHelper
    from .services.chat_service import OpenAIChatService
    from .services.image_service import OpenAIImageService
except ImportError:
    from app_state import AppState
    from ui_helpers import ButtonRow, ProgressHelper
    from services.chat_service import OpenAIChatService
    from services.image_service import OpenAIImageService


class CharacterGenerationPage:
    name = "Character Generation"
    icon = "🧑‍🎨"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config


    def render(self) -> None:
        st.header(f"{self.icon} Character & Background Generation")
        st.caption(
            "Work with the structured scene, edit character inputs, and generate/refine assets."
        )
        if not self.state.session.get("script_text"):
            st.warning("Add a script draft on the Script page first.")
            return
        # Ensure structured JSON is current when entering this page
        self._sync_structure_with_script()
        self._render_asset_generation()


    def _render_asset_generation(self) -> None:
        structured_scene = self.state.session.get("structured_scene")
        if not structured_scene:
            st.info("No structured output yet. Update the script to auto-generate JSON.")
            st.stop()
        # Simplify: skip per-character/background generation and only produce a single composite image.
        self._render_image_quality_slider()
        self._render_scene_composite(structured_scene)


    # Quality of generated portraits
    def _render_image_quality_slider(self) -> None:
        st.markdown("#### Image Quality")
        st.select_slider(
            "Image size",
            options=["1024x1024", "1024x1792", "1792x1024"],
            value=st.session_state.get("image_size", "1024x1024"),
            key="image_size",
            help="Higher sizes look better but cost more.",
        )


    def _render_chars_and_background_columns(self, structured_scene: Dict) -> None:
        col_characters, col_background = st.columns([2, 1])
        with col_characters:
            self._render_characters(structured_scene)
        with col_background:
            self._render_background(structured_scene)


    def _render_media_characters(self, structured_scene: Dict) -> None:
        st.markdown("#### Story Characters")
        updated_chars: List[Dict] = []
        for character in structured_scene.get("characters", []):
            with st.expander(character.get("name", "Character"), expanded=False):
                name = st.text_input(
                    "Name",
                    value=character.get("name", ""),
                    key=f"name_{character.get('name')}",
                )
                age = st.text_area(
                    "Age",
                    value=character.get("age", ""),
                    key=f"age_{character.get('name')}",
                )
                description = st.text_area(
                    "Description",
                    value=character.get("description", ""),
                    key=f"desc_{character.get('name')}",
                )
                style_hint = st.text_input(
                    "Style hint",
                    value=character.get("style_hint", structured_scene.get("art_style", "")),
                    key=f"style_{character.get('name')}",
                )
                prompt = st.text_area(
                    "Prompt",
                    value=character.get("image_prompt", ""),
                    key=f"prompt_{character.get('name')}",
                )
                updated_chars.append(
                    {
                        "name": name,
                        "age": age,
                        "description": description,
                        "style_hint": style_hint,
                        "image_prompt": prompt,
                    }
                )
        if updated_chars:
            structured_scene["characters"] = updated_chars
            self.state.set_structured_scene(structured_scene)
            au.save_structured_scene(self.state)

    
    # Character avatars
    def _render_character_avatar_uploads(self, structured_scene: Dict) -> None:
        st.markdown("#### Optional: Upload Existing Avatars")
        uploads = st.session_state.setdefault("character_uploads", {})
        for character in structured_scene.get("characters", []):
            name = character.get("name")
            file = st.file_uploader(
                f"Upload avatar for {name}",
                type=["png", "jpg", "jpeg"],
                key=f"upload_{name}",
            )
            if file:
                uploads[name] = file.read()
                st.success(f"Avatar uploaded for {name}")


    def _render_characters(self, structured_scene: Dict) -> None:
        st.markdown("#### Characters")
        if ButtonRow.single("Generate Characters", key="generate_characters"):
            characters = structured_scene.get("characters", [])
            art_style = structured_scene.get("art_style", "realistic")
            assets: List[Dict[str, str]] = []

            for character in characters:
                style_hint = art_style
                prev_style = assets[-1].get("style", art_style) if assets else art_style
                prompt = self._build_character_prompt(character, style_hint, prev_style)
                entry = {
                    "name": character["name"],
                    "status": "pending",
                    "note": character.get("description", "Generated image"),
                    "style": style_hint,
                    "prompt": prompt,
                    "refinement": "",
                    "image_bytes": None,
                    "image_url": None,
                    "use_reference": True,
                    "error": None,
                }

                uploads = st.session_state.get("character_uploads", {})
                uploaded = uploads.get(character["name"])
                if uploaded:
                    entry["status"] = "ready"
                    entry["image_bytes"] = uploaded
                    entry["note"] = "Uploaded avatar used."
                else:
                    with st.status(f"Generating {character['name']}...", expanded=True) as status:
                        try:
                            image_bytes, url = self._generate_image(prompt)
                            entry["status"] = "ready"
                            entry["image_bytes"] = image_bytes
                            entry["image_url"] = url
                            status.update(label=f"{character['name']} generated.", state="complete")
                        except Exception as exc:
                            entry["status"] = "error"
                            entry["error"] = str(exc)
                            status.update(label=f"{character['name']} failed: {exc}", state="error")
                assets.append(entry)

            self.state.set_character_assets(assets)
            st.success("Character images created in sequence.")
        assets = self.state.session.get("character_assets", [])
        if assets:
            for character in assets:
                st.success(f"{character['name']} image {character.get('status')}.")
                with st.expander(character["name"], expanded=True):
                    st.write("Status:", character["status"])
                    st.write("Art style:", character.get("style", ""))
                    st.write("Prompt:", character.get("image_prompt", ""))
                    st.write("Note:", character["note"])
                    if character.get("error"):
                        st.error(character["error"])
                    if character.get("image_bytes"):
                        st.image(character["image_bytes"], caption=character["name"])
                        st.download_button(
                            label=f"Download {character['name']}",
                            data=character["image_bytes"],
                            file_name=f"{character['name']}.png",
                            mime="image/png",
                        )
                    character["use_reference"] = st.checkbox(
                        f"Use current image as reference for {character['name']}",
                        value=character.get("use_reference", True),
                        key=f"use_ref_{character['name']}",
                    )
                    refinement = st.text_area(
                        f"Refinement for {character['name']}",
                        value=character.get("refinement", ""),
                        key=f"refine_{character['name']}",
                        help="Add a prompt tweak to regenerate this character.",
                    )
                    if st.button(f"Refine {character['name']}", key=f"apply_{character['name']}"):
                        with st.status(f"Refining {character['name']}...", expanded=True) as status:
                            prompt = character["prompt"]
                            if refinement:
                                prompt = prompt + "\nRefine: " + refinement
                            use_ref = character.get("use_reference")
                            ref_note = (
                                "Keep close to current image for consistency on a white background."
                                if use_ref
                                else "Reimagine from scratch on a white background while keeping core description."
                            )
                            image_bytes, url = self._generate_image(prompt, reference_note=ref_note if use_ref else None)
                            status.update(label=f"{character['name']} updated.", state="complete")
                        character["refinement"] = refinement
                        character["status"] = "updated"
                        character["image_prompt"] = prompt
                        character["image_bytes"] = image_bytes
                        character["image_url"] = url
                        character["error"] = None
                        self.state.set_character_assets(assets)
                        st.rerun()
        else:
            st.info("No character images yet. Generate to see placeholders.")


    def _render_background(self, structured_scene: Dict) -> None:
        st.markdown("#### Background")
        uploaded_bg = st.file_uploader(
            "Upload background image (optional)",
            type=["png", "jpg", "jpeg"],
            key="upload_background",
        )
        if uploaded_bg:
            bg_bytes = uploaded_bg.read()
            asset = {
                "label": "Uploaded background",
                "status": "ready",
                "note": "User-uploaded background",
                "image_bytes": bg_bytes,
                "image_url": None,
            }
            self.state.set_background_asset(asset)
            st.success("Background uploaded.")
        if ButtonRow.single("Generate Background", key="generate_background"):
            background = structured_scene.get("background", {})
            art_style = structured_scene.get("art_style", "realistic")
            character_summaries = ", ".join(
                [f"{c.get('name')} ({c.get('description','')})" for c in structured_scene.get("characters", [])]
            )
            prompt = self._build_background_prompt(background, art_style, character_summaries)
            with st.spinner("Rendering background..."):
                image_bytes, url = self._generate_image(prompt)
            asset = {
                "label": f"{background.get('location', background.get('setting', 'Stage'))} - "
                f"{background.get('time_of_day', 'Day')}",
                "status": "ready",
                "note": (
                    f"Background matches style '{art_style}'. "
                    f"Characters considered: {character_summaries}. "
                    f"Description: {background.get('description', '')}"
                ),
                "image_bytes": image_bytes,
                "image_url": url,
            }
            self.state.set_background_asset(asset)
            st.success("Background created using all characters.")
        asset = self.state.session.get("background_asset")
        if asset:
            st.success(f"Background ready: {asset['label']}")
            st.write("Status:", asset["status"])
            st.write("Note:", asset["note"])
            if asset.get("image_bytes"):
                st.image(asset["image_bytes"], caption=asset["label"])
                st.download_button(
                    label="Download Background",
                    data=asset["image_bytes"],
                    file_name="background.png",
                    mime="image/png",
                )
            refine_bg = st.text_area(
                "Refine background",
                value=asset.get("refinement", ""),
                key="refine_background",
                help="Adjust the background prompt and regenerate.",
            )
            use_ref_bg = st.checkbox(
                "Use current background as reference",
                value=asset.get("use_reference", True),
                key="use_ref_background",
            )
            if st.button("Refine Background", key="apply_background"):
                with st.status("Refining background...", expanded=True) as status:
                    prompt = self._build_background_prompt(
                        structured_scene.get("background", {}),
                        structured_scene.get("art_style", "realistic"),
                        ", ".join([c.get("name") for c in structured_scene.get("characters", [])]),
                    )
                    if refine_bg:
                        prompt = prompt + "\nRefine: " + refine_bg
                    ref_note = (
                        "Keep layout and mood consistent, no characters, white backdrop for compositing."
                        if use_ref_bg
                        else "Reimagine from scratch: no characters, white backdrop for compositing."
                    )
                    image_bytes, url = self._generate_image(prompt, reference_note=ref_note if use_ref_bg else None)
                    status.update(label="Background updated.", state="complete")
                asset["refinement"] = refine_bg
                asset["use_reference"] = use_ref_bg
                asset["image_bytes"] = image_bytes
                asset["image_url"] = url
                self.state.set_background_asset(asset)
                st.rerun()
        else:
            st.info("No background yet. Generate or upload one.")

    def _render_scene_composite(self, structured_scene: Dict) -> None:
        st.markdown("#### Composite Scene Image")
        st.caption("Generate one high-quality frame with all characters in the described background (no separate portraits).")
        if ButtonRow.single("Generate composite scene", key="generate_scene_composite"):
            prompt = self._build_scene_composite_prompt(structured_scene)
            size = st.session_state.get("image_size", "1792x1024")
            with st.status("Rendering composite scene...", expanded=True) as status:
                try:
                    img_bytes, url = self._get_image_client().generate_image(prompt=prompt, size=size)
                    status.update(label="Composite scene generated.", state="complete")
                except Exception as exc:
                    status.update(label=f"Failed: {exc}", state="error")
                    st.error(f"Composite generation failed: {exc}")
                    return

            st.image(img_bytes, caption="Composite scene")
            output_path = Path("src/output/scene_composite.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(img_bytes)
            st.success(f"Saved composite scene to {output_path}")
            st.download_button(
                label="Download composite",
                data=img_bytes,
                file_name="scene_composite.png",
                mime="image/png",
            )
            # Cache in session for downstream use
            st.session_state["scene_composite"] = {
                "image_bytes": img_bytes,
                "url": url,
                "note": "Composite scene with characters and background.",
            }


    def _sync_structure_with_script(self) -> None:
        """Refresh structured JSON when entering the page if the script changed."""
        script_text = self.state.session.get("script_text", "")
        if not script_text.strip():
            return
        last = st.session_state.get("structured_scene_source_text", "")
        needs_update = script_text != last or not self.state.session.get("structured_scene")
        if not needs_update:
            return
        if self.config.get("dev_mode"):
            structured = au._dev_get_default_structured_scene()
            self.state.set_structured_scene(structured)
            st.session_state["structured_scene_source_text"] = script_text
            return
        try:
            client = self._get_client()
            structured = client.generate_structured_scene(script_text)
            self.state.set_structured_scene(structured)
            st.session_state["structured_scene_source_text"] = script_text
        except Exception as exc:
            st.error(f"Failed to refresh structured JSON: {exc}")


    def _generate_image(self, prompt: str, reference_note: Optional[str] = None):
        client = self._get_image_client()
        size = st.session_state.get("image_size", "1024x1024")
        return client.generate_image(prompt=prompt, reference_note=reference_note, size=size)


    @staticmethod
    def _build_character_prompt(character: Dict, style_hint: str, prev_style: str) -> str:
        return (
            f"Single, centered, full-body portrait of {character.get('name')} in {style_hint} illustration style "
            f"with clean lines, bold colors, and light shading. "
            f"Description: {character.get('description','')}. "
            f"Plain white background only; no props, no panels, no collage, no text, no extra poses, no duplicates. "
            f"Consistent style across all characters; maintain continuity with previous: {prev_style}. "
            f"High-quality, detailed rendering suitable for compositing."
        )


    @staticmethod
    def _build_background_prompt(background: Dict, art_style: str, character_summaries: str) -> str:
        return (
            f"Scene background in {art_style} style. "
            f"Location: {background.get('location', background.get('setting', 'Stage'))}. "
            f"Time of day: {background.get('time_of_day', 'Day')}. "
            f"Description: {background.get('description','')}. "
            f"No characters, no people, no text, no word balloons. "
            f"Leave clean negative space for compositing foreground characters. "
            f"Ensure stylistic consistency with characters: {character_summaries}."
        )

    @staticmethod
    def _build_scene_composite_prompt(structured_scene: Dict) -> str:
        base_style = structured_scene.get("art_style", "friendly 2D animation, cel-shaded, cartoon")
        art_style = base_style if any(k in base_style.lower() for k in ["cartoon", "animation", "anime", "comic"]) else f"{base_style}; friendly 2D animation, cel-shaded, cartoon, non-realistic"
        background = structured_scene.get("background", {})
        characters = structured_scene.get("characters", [])
        plot_elements = [elem for elem in structured_scene.get("important_plot_elements", []) if elem]
        char_lines = "; ".join(
            [
                f"{c.get('name','')}: {c.get('description','')}"
                for c in characters
            ]
        )
        beats = structured_scene.get("beats", [])
        beat_text = "; ".join([b.get("description", "") for b in beats[:4]])
        plot_text = "; ".join(plot_elements)
        plot_line = f"Important plot elements to show clearly: {plot_text}. " if plot_text else ""
        return (
            f"One cinematic, high-resolution illustration in {art_style} style showing all main characters together. "
            f"Setting: {background.get('location', background.get('description', ''))}, "
            f"time: {background.get('time_of_day', 'Day')}. "
            f"Characters: {char_lines}. "
            f"Mood and action: {beat_text}. "
            f"{plot_line}"
            f"Full scene in one frame, cohesive lighting, consistent style across characters and environment. "
            f"No text, no captions, no watermarks."
        )


    @staticmethod
    def _fallback_structure(script_text: str) -> Dict:
        summary = script_text.splitlines()[0] if script_text else "INT. STAGE - DAY"
        characters = [{"name": "Alex", "description": "Protagonist", "style_hint": "realistic", "prompt": "Alex portrait"}]
        background = {
            "description": "Interior set",
            "time_of_day": "Day",
            "location": "Studio",
        }
        return {
            "scene_title": "Draft Scene",
            "logline": "Fallback structure from heuristic parser.",
            "art_style": "realistic",
            "important_plot_elements": [
                "A single prop or visual cue critical to the scene (e.g., a mysterious package on the table)."
            ],
            "beats": [
                {"order": 1, "description": "Establish setting and mood."},
                {"order": 2, "description": "Introduce main characters."},
                {"order": 3, "description": "Set the conflict and desired outcome."},
            ],
            "characters": characters,
            "background": background,
            "source_excerpt": summary,
        }


    @st.cache_resource(show_spinner=False)
    def _get_client(_self=None) -> OpenAIChatService:
        return OpenAIChatService()


    @st.cache_resource(show_spinner=False)
    def _get_image_client(_self=None) -> OpenAIImageService:
        return OpenAIImageService()
