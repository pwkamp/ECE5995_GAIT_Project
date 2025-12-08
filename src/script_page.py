from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.chat_service import OpenAIChatService
    from . import app_utils as au
except ImportError:  # Fallback when run as a standalone script context
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.chat_service import OpenAIChatService
    import app_utils as au


class ScriptPage:
    name = "Script"
    icon = "🖋️"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config

    def render(self) -> None:
        st.header(f"{self.icon} Script Workspace")
        st.caption("Capture the scene idea, chat through it, and refine the draft.")
        # Ensure dev preset JSON exists in dev mode without hitting the API
        if self.config.get("dev_mode") and not self.state.session.get("structured_scene"):
            self.state.set_structured_scene(self._dev_structured_scene())
        # Sync editor with stored script when first loading
        if "script_editor" not in st.session_state and self.state.session.get("script_text"):
            st.session_state["script_editor"] = self.state.session.get("script_text")
        self._render_chat()
        self._render_script_tools()

    def _render_chat(self) -> None:
        chat_container = st.container()
        for message in self.state.session["chat_history"]:
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])
        prompt = st.chat_input("Describe the scene, characters, and vibe.")
        if prompt:
            self.state.add_chat("user", prompt)
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            with chat_container.chat_message("assistant"), st.spinner("Thinking..."):
                reply = self._call_model()
                st.markdown(reply)
            self.state.add_chat("assistant", reply)
            self.state.set_script(reply)
            st.session_state["script_editor"] = reply
            self._maybe_regenerate_structure(reply)
            st.rerun()

    def _render_script_tools(self) -> None:
        st.markdown("#### Quick Actions")
        if ButtonRow.single("Load Sample Script (LLM)", key="load_sample_script"):
            with st.spinner("Generating a short comedy scene via LLM..."):
                sample = self._generate_sample_script()
            self.state.set_script(sample)
            st.session_state["script_editor"] = sample
            self.state.add_chat("assistant", sample)
            self._maybe_regenerate_structure(sample)
            st.success("Sample script loaded.")
            st.rerun()
        st.markdown("#### Draft Script")
        current_text = self.state.session.get("script_text", "")
        updated_text = st.text_area(
            "Scene script",
            value=current_text,
            height=280,
            key="script_editor",
            placeholder="INT. LOCATION - TIME\nCharacter: Dialogue...",
        )
        if updated_text != current_text:
            self.state.set_script(updated_text)
            self._maybe_regenerate_structure(updated_text)
        if st.button("Confirm & Generate Structured JSON", key="confirm_generate_json"):
            with st.spinner("Generating structured JSON from script..."):
                try:
                    client = self._get_structure_client()
                    structured = client.generate_structured_scene(self.state.session.get("script_text", ""))
                    self.state.set_structured_scene(structured)
                    self.state.set_character_assets([])
                    self.state.set_background_asset(None)
                    st.session_state["structured_scene_source_text"] = self.state.session.get("script_text", "")
                    au.save_structured_scene(self.state)
                    st.success("Structured JSON updated.")
                except Exception as exc:
                    st.error(f"Failed to generate structured JSON: {exc}")

    def _call_model(self) -> str:
        @st.cache_resource(show_spinner=False)
        def _get_client() -> OpenAIChatService:
            return OpenAIChatService(
                api_key=self.config.get("api_key"),
                model=self.config.get("model"),
            )

        client = _get_client()
        try:
            return client.generate_reply(self.state.session["chat_history"])
        except Exception as exc:
            st.error(f"Chat request failed: {exc}")
            return "I'm having trouble reaching the model right now."

    def _generate_sample_script(self) -> str:
        @st.cache_resource(show_spinner=False)
        def _get_client() -> OpenAIChatService:
            return OpenAIChatService(
                api_key=self.config.get("api_key"),
                model=self.config.get("model"),
            )

        client = _get_client()
        try:
            prompt_history = [
                {
                    "role": "system",
                    "content": (
                        "You write short, funny scene scripts (~20 seconds) with 2-3 characters. "
                        "Always include: character names with clear descriptions, background "
                        "description, and a specific art style tag (realistic, 3d, watercolor, anime, "
                        "comic, painterly, etc.)."
                    ),
                },
                {
                    "role": "user",
                    "content": "Give me a ~20 second comedy scene with 2-3 characters, light banter, and a quick punchline.",
                },
            ]
            return client.generate_reply(prompt_history)
        except Exception as exc:
            st.error(f"Sample script generation failed: {exc}")
            return self._sample_script()

    def _maybe_regenerate_structure(self, script_text: str) -> None:
        if not script_text.strip():
            return
        last = st.session_state.get("structured_scene_source_text", "")
        if script_text == last and self.state.session.get("structured_scene"):
            return
        if self.config.get("dev_mode"):
            structured = self._dev_structured_scene()
            self.state.set_structured_scene(structured)
            self.state.set_character_assets([])
            self.state.set_background_asset(None)
            st.session_state["structured_scene_source_text"] = script_text
            au.save_structured_scene(self.state)
            return
        with st.spinner("Updating structured JSON from script..."):
            try:
                client = self._get_structure_client()
                structured = client.generate_structured_scene(script_text)
                self.state.set_structured_scene(structured)
                self.state.set_character_assets([])
                self.state.set_background_asset(None)
                st.session_state["structured_scene_source_text"] = script_text
                au.save_structured_scene(self.state)
            except Exception as exc:
                st.error(f"Failed to update structured JSON: {exc}")

    @st.cache_resource(show_spinner=False)
    def _get_structure_client(_self=None) -> OpenAIChatService:
        return OpenAIChatService(
            api_key=st.session_state.get("api_key_override") or _self.config.get("api_key"),  # type: ignore[attr-defined]
            model=st.session_state.get("model_override") or _self.config.get("model"),  # type: ignore[attr-defined]
        )

    @staticmethod
    def _dev_structured_scene() -> dict:
        return {
            "scene_title": "Factory Prank",
            "logline": "Three men in an early 1900s factory pull a playful prank on one of their own.",
            "art_style": "Black and white, silent-film style with grainy texture",
            "background": {
                "description": (
                    "A cavernous early 20th century factory with brick walls stained by soot, "
                    "rows of iron machines, belts, pistons, scattered wooden crates, and hanging "
                    "filament bulbs casting hard, dramatic shadows through ribbons of steam."
                ),
                "time_of_day": "Day",
                "location": "Industrial factory interior",
            },
            "characters": [
                {
                    "name": "EDWARD",
                    "age": "Mid-30s",
                    "description": (
                        "Tall, lean ringleader with a mischievous glint; grease-smudged face, flat cap tilted, "
                        "rolled sleeves, suspenders over oil-stained overalls, fingerless gloves and scuffed boots. "
                        "Quick, confident posture."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, crisp contrast, rim-lit edges",
                    "image_prompt": "",
                },
                {
                    "name": "HARRY",
                    "age": "Late 20s",
                    "description": (
                        "Stockier accomplice with a broad grin; suspenders, rolled sleeves, patched vest, thick moustache "
                        "dusted with coal, calloused hands, heavy work boots, relaxed stance."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, grainy texture, soft falloff",
                    "image_prompt": "",
                },
                {
                    "name": "GEORGE",
                    "age": "Early 30s",
                    "description": (
                        "Unsuspecting victim; neat cap and vest over a crisp shirt, pocket watch chain visible, tidy moustache, "
                        "cautious eyes; stands straighter, sleeves buttoned, gloves tucked in belt."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, subtle film grain, chiaroscuro lighting",
                    "image_prompt": "",
                },
            ],
            "beats": [
                {
                    "order": 1,
                    "description": (
                        "Wide shot of the bustling factory; machinery thumps in the background as Edward and Harry share "
                        "a conspiratorial grin near a coiled air hose."
                    ),
                },
                {
                    "order": 2,
                    "description": (
                        "Close on Edward rigging a harmless air blast under George's workbench; Harry watches, barely containing laughter."
                    ),
                },
                {
                    "order": 3,
                    "description": (
                        "George approaches, adjusting his cap; Edward signals; Harry tugs the hidden lever—compressed air whooshes "
                        "and a string pops up; George startles then smirks as the trio chuckles."
                    ),
                },
            ],
        }

    @staticmethod
    def _draft_script_from_prompt(prompt: str) -> str:
        return (
            "INT. STUDIO - EVENING\n"
            f"Host: {prompt}\n"
            "Camera pans across the set as the team prepares the scene."
        )

    @staticmethod
    def _sample_script() -> str:
        return (
            "INT. CITY LOFT - NIGHT\n"
            "Alex: Another late night, Jordan. The skyline still looks alive.\n"
            "Jordan: We need one last shot before sunrise.\n"
            "Riley (voiceover): Time is running out for the perfect take.\n"
            "Lights flicker as the camera tilts toward the window."
        )
