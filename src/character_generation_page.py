from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow, ProgressHelper
    from .services.chat_service import OpenAIChatService
    from .services.image_service import OpenAIImageService
except ImportError:  # Fallback when run as a standalone script context
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
            "Generate structured JSON from the latest script, then walk through "
            "sequential character creation and a consistent background."
        )

        if not self.state.session.get("script_text"):
            st.warning("Add a script draft on the Script page first.")
            return

        self._render_structure_controls()
        self._render_asset_generation()

    def _render_structure_controls(self) -> None:
        st.markdown("#### Structured Scene JSON")
        if ButtonRow.single("Generate JSON", key="generate_json"):
            if self.config.get("dev_mode"):
                structured = self._dev_structured_scene()
                self.state.set_structured_scene(structured)
                self.state.set_character_assets([])
                self.state.set_background_asset(None)
                st.success("Structured scene loaded from dev preset.")
            else:
                status = st.status("Generating structured JSON...", expanded=True)
                try:
                    structured = self._build_structure_from_llm(self.state.session["script_text"])
                    self.state.set_structured_scene(structured)
                    self.state.set_character_assets([])
                    self.state.set_background_asset(None)
                    status.update(label="Structured scene updated.", state="complete")
                except Exception as exc:
                    status.update(label=f"JSON generation failed: {exc}", state="error")

        structured_scene = self.state.session.get("structured_scene")
        if structured_scene:
            st.json(structured_scene, expanded=True)
        else:
            st.info("No structured output yet. Generate to create one.")

    def _render_asset_generation(self) -> None:
        structured_scene = self.state.session.get("structured_scene")
        if not structured_scene:
            st.stop()

        # Optional: allow uploads of pre-made avatars before generation
        st.markdown("#### Optional: Upload Existing Avatars")
        uploads = st.session_state.setdefault("character_uploads", {})
        for character in structured_scene.get("characters", []):
            file = st.file_uploader(
                f"Upload avatar for {character.get('name')}",
                type=["png", "jpg", "jpeg"],
                key=f"upload_{character.get('name')}",
            )
            if file:
                uploads[character.get("name")] = file.read()
                st.success(f"Avatar uploaded for {character.get('name')}")

        # Image quality/size selector
        st.markdown("#### Image Quality")
        size_option = st.select_slider(
            "Image size",
            options=["1024x1024", "1024x1792", "1792x1024"],
            value=st.session_state.get("image_size", "1024x1024"),
            key="image_size",
            help="Higher sizes look better but cost more.",
        )

        col_characters, col_background = st.columns([2, 1])
        with col_characters:
            self._render_characters(structured_scene)
        with col_background:
            self._render_background(structured_scene)

    def _render_characters(self, structured_scene: Dict) -> None:
        st.markdown("#### Characters")
        if ButtonRow.single("Generate Characters", key="generate_characters"):
            characters = structured_scene.get("characters", [])
            art_style = structured_scene.get("art_style", "realistic")
            assets: List[Dict[str, str]] = []

            for idx, character in enumerate(characters):
                style_hint = art_style  # enforce consistent style across characters
                prev_style = art_style if not assets else assets[-1].get("style", art_style)
                prompt = self._build_character_prompt(character, style_hint, prev_style, structured_scene)
                entry = {
                    "name": character["name"],
                    "status": "pending",
                    "note": character.get("description", "Generated image"),
                    "style": style_hint,
                    "prompt": prompt,
                    "refinement": "",
                    "image_b64": None,
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
                status_text = "ready" if character.get("status") == "ready" else character.get("status")
                st.success(f"{character['name']} image {status_text}.")
                with st.expander(character["name"], expanded=True):
                    st.write("Status:", character["status"])
                    st.write("Art style:", character.get("style", ""))
                    st.write("Prompt:", character.get("prompt", ""))
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
                        help="Add a prompt tweak to regenerate this character before moving on.",
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
                        character["prompt"] = prompt
                        character["image_b64"] = None
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
                "image_b64": None,
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
                "image_b64": None,
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
            st.info("No background yet. Generate to see the placeholder.")

    def _build_structure_from_llm(self, script_text: str) -> Dict:
        """Use LLM to produce structured JSON; fallback to simple heuristic on failure."""
        try:
            client = self._get_client()
            return client.generate_structured_scene(script_text)
        except Exception as exc:
            st.error(f"LLM JSON generation failed, using heuristic fallback: {exc}")
            return self._fallback_structure(script_text)

    @staticmethod
    def _dev_structured_scene() -> Dict:
        return {
            "scene_title": "Smoothie Showdown",
            "logline": "Three friends compete to create the ultimate smoothie, leading to hilarious mishaps and playful banter in a colorful kitchen.",
            "art_style": "Comic, clean lines, bold colors, minimal shading",
            "background": {
                "description": "A bright, colorful kitchen filled with fresh fruits and a blender.",
                "time_of_day": "Late morning",
                "location": "Kitchen",
            },
            "characters": [
                {
                    "name": "JAKE",
                    "description": "Mid-20s, laid-back, always wearing a goofy hat, loves trying new things.",
                    "style_hint": "Goofy, playful",
                    "prompt": "A young man with a goofy hat, holding a banana and gummy bears, grinning mischievously.",
                },
                {
                    "name": "SARAH",
                    "description": "Early 30s, health-conscious, sarcastic, always prepared with a witty comeback.",
                    "style_hint": "Witty, sharp",
                    "prompt": "A woman in her early 30s, rolling her eyes, with a sarcastic expression.",
                },
                {
                    "name": "MIKE",
                    "description": "Late 20s, overly enthusiastic, the 'smoothie expert,' a bit clueless.",
                    "style_hint": "Enthusiastic, clueless",
                    "prompt": "A young man in his late 20s, bouncing in excitedly, with a big smile.",
                },
            ],
            "beats": [
                {"order": 1, "description": "JAKE stands by the blender, holding a banana with a mischievous grin."},
                {"order": 2, "description": "JAKE cheerfully announces his smoothie ingredients, including gummy bears."},
                {"order": 3, "description": "SARAH rolls her eyes at JAKE's choice of gummy bears."},
                {"order": 4, "description": "MIKE bounces in, excitedly suggesting chocolate syrup."},
                {"order": 5, "description": "JAKE agrees to call it a 'dessert smoothie.'"},
                {"order": 6, "description": "SARAH smirks, calling it a 'regret smoothie.'"},
                {"order": 7, "description": "JAKE presses the blender button, causing a smoothie explosion."},
                {"order": 8, "description": "JAKE laughs and calls it a 'splat-er smoothie,' leading to laughter from all."},
            ],
        }

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
        """Cache OpenAI client; ignore self in hashing to avoid cache errors."""
        return OpenAIChatService()

    @st.cache_resource(show_spinner=False)
    def _get_image_client(_self=None) -> OpenAIImageService:
        """Cache OpenAI image client; ignore self in hashing."""
        return OpenAIImageService()

    def _generate_image(self, prompt: str, reference_note: Optional[str] = None):
        client = self._get_image_client()
        size = st.session_state.get("image_size", "768x768")
        return client.generate_image(prompt=prompt, reference_note=reference_note, size=size)

    @staticmethod
    def _build_character_prompt(character: Dict, style_hint: str, prev_style: str, structured_scene: Dict) -> str:
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
