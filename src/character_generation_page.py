from __future__ import annotations

from typing import Dict, List

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow, ProgressHelper
except ImportError:  # Fallback when run as a standalone script context
    from app_state import AppState
    from ui_helpers import ButtonRow, ProgressHelper


class CharacterGenerationPage:
    name = "Character Generation"
    icon = "🧑‍🎨"

    def __init__(self, state: AppState):
        self.state = state

    def render(self) -> None:
        st.header(f"{self.icon} Character & Background Generation")
        st.caption(
            "Generate structured JSON, then create character and background "
            "placeholders. Each asset appears as soon as it is ready."
        )

        if not self.state.session.get("script_text"):
            st.warning("Add a script draft on the Script page first.")
            return

        self._render_structure_controls()
        self._render_asset_generation()

    def _render_structure_controls(self) -> None:
        st.markdown("#### Structured Scene JSON")
        if ButtonRow.single("Mock Generate JSON", key="generate_json"):
            ProgressHelper.run("Generating structured JSON (mock)...")
            structured = self._build_mock_structure(self.state.session["script_text"])
            self.state.set_structured_scene(structured)
            self.state.set_character_assets([])
            self.state.set_background_asset(None)
            st.success("Structured scene updated.")

        structured_scene = self.state.session.get("structured_scene")
        if structured_scene:
            st.json(structured_scene, expanded=True)
        else:
            st.info("No structured output yet. Generate to create one.")

    def _render_asset_generation(self) -> None:
        structured_scene = self.state.session.get("structured_scene")
        if not structured_scene:
            st.stop()

        col_characters, col_background = st.columns([2, 1])
        with col_characters:
            self._render_characters(structured_scene)
        with col_background:
            self._render_background(structured_scene)

    def _render_characters(self, structured_scene: Dict) -> None:
        st.markdown("#### Characters")
        if ButtonRow.single("Mock Generate Character Images", key="generate_characters"):
            ProgressHelper.run("Generating character images (mock)...")
            assets = [
                {
                    "name": character["name"],
                    "status": "ready",
                    "note": f"Placeholder image for {character['name']}.",
                }
                for character in structured_scene.get("characters", [])
            ]
            self.state.set_character_assets(assets)
            st.success("Character placeholders created.")

        assets = self.state.session.get("character_assets", [])
        if assets:
            for character in assets:
                st.success(f"{character['name']} image ready.")
                with st.expander(character["name"], expanded=True):
                    st.write("Status:", character["status"])
                    st.write("Note:", character["note"])
        else:
            st.info("No character images yet. Generate to see placeholders.")

    def _render_background(self, structured_scene: Dict) -> None:
        st.markdown("#### Background")
        if ButtonRow.single("Mock Generate Background", key="generate_background"):
            ProgressHelper.run("Generating background (mock)...")
            background = structured_scene.get("background", {})
            asset = {
                "label": f"{background.get('setting', 'Stage')} - "
                f"{background.get('time_of_day', 'Day')}",
                "status": "ready",
                "note": "Placeholder background image ready for replacement.",
            }
            self.state.set_background_asset(asset)
            st.success("Background placeholder created.")

        asset = self.state.session.get("background_asset")
        if asset:
            st.success(f"Background ready: {asset['label']}")
            st.write("Status:", asset["status"])
            st.write("Note:", asset["note"])
        else:
            st.info("No background yet. Generate to see the placeholder.")

    @staticmethod
    def _build_mock_structure(script_text: str) -> Dict:
        summary = script_text.splitlines()[0] if script_text else "INT. STAGE - DAY"
        characters = CharacterGenerationPage._derive_characters(script_text)
        background = CharacterGenerationPage._derive_background(script_text)

        return {
            "scene_title": "Draft Scene",
            "logline": "A quick mockup built from the latest script draft.",
            "beats": [
                {"order": 1, "description": "Establish setting and mood."},
                {"order": 2, "description": "Introduce main characters."},
                {"order": 3, "description": "Set the conflict and desired outcome."},
            ],
            "characters": characters,
            "background": background,
            "source_excerpt": summary,
        }

    @staticmethod
    def _derive_characters(script_text: str) -> List[Dict[str, str]]:
        names = []
        for line in script_text.splitlines():
            candidate = line.split(":", maxsplit=1)[0].strip()
            if candidate.isalpha() and candidate.istitle() and candidate not in names:
                names.append(candidate)
            if len(names) >= 3:
                break

        if not names:
            names = ["Alex", "Jordan"]

        characters = []
        for name in names:
            characters.append(
                {
                    "name": name,
                    "role": "character",
                    "description": f"Placeholder description for {name}.",
                }
            )
        return characters

    @staticmethod
    def _derive_background(script_text: str) -> Dict[str, str]:
        lower = script_text.lower()
        time_of_day = "Night" if "night" in lower else "Day"
        setting = "Loft" if "loft" in lower else "Studio"
        return {"setting": setting, "time_of_day": time_of_day}
