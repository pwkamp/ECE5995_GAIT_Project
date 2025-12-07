from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow
    from .services.chat_service import OpenAIChatService
except ImportError:  # Fallback when run as a standalone script context
    from app_state import AppState
    from ui_helpers import ButtonRow
    from services.chat_service import OpenAIChatService


class ScriptPage:
    name = "Script"
    icon = "📝"


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
            # Echo user message immediately
            self.state.add_chat("user", prompt)
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            # Assistant reply with spinner
            with chat_container.chat_message("assistant"), st.spinner("Thinking..."):
                reply = self._call_model()
                st.markdown(reply)
            self.state.add_chat("assistant", reply)
            # Always keep the draft script and structure in sync with the latest assistant reply
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
            # Add to chat history so it appears in the conversation log
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
        # Keep state synchronized with the text area edits
        if updated_text != current_text:
            self.state.set_script(updated_text)
            self._maybe_regenerate_structure(updated_text)
        # Explicit confirm to generate/update structured JSON via LLM
        if st.button("Confirm & Generate Structured JSON", key="confirm_generate_json"):
            with st.spinner("Generating structured JSON from script..."):
                try:
                    client = self._get_structure_client()
                    structured = client.generate_structured_scene(self.state.session.get("script_text", ""))
                    self.state.set_structured_scene(structured)
                    self.state.set_character_assets([])
                    self.state.set_background_asset(None)
                    st.session_state["structured_scene_source_text"] = self.state.session.get("script_text", "")
                    st.success("Structured JSON updated.")
                except Exception as exc:
                    st.error(f"Failed to generate structured JSON: {exc}")


    def _call_model(self) -> str:
        """Call OpenAI with the current chat history."""
        # Cache the client to avoid re-instantiation on each interaction.
        @st.cache_resource(show_spinner=False)
        def _get_client() -> OpenAIChatService:
            return OpenAIChatService(
                api_key=self.config.get("api_key"),
                model=self.config.get("model"),
            )
        client = _get_client()
        try:
            return client.generate_reply(self.state.session["chat_history"])
        except Exception as exc:  # Broad catch to surface errors in UI
            st.error(f"Chat request failed: {exc}")
            return "I'm having trouble reaching the model right now."


    def _generate_sample_script(self) -> str:
        """Generate a short (~20s) comedy script via the LLM."""
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
        """Auto-regenerate structured JSON when script changes (unless dev mode)."""
        if not script_text.strip():
            return
        last = st.session_state.get("structured_scene_source_text", "")
        if script_text == last and self.state.session.get("structured_scene"):
            return
        # In dev mode, use the preset to avoid API calls
        if self.config.get("dev_mode"):
            structured = self._dev_structured_scene()
            self.state.set_structured_scene(structured)
            self.state.set_character_assets([])
            self.state.set_background_asset(None)
            st.session_state["structured_scene_source_text"] = script_text
            return
        with st.spinner("Updating structured JSON from script..."):
            try:
                client = self._get_structure_client()
                structured = client.generate_structured_scene(script_text)
                self.state.set_structured_scene(structured)
                self.state.set_character_assets([])
                self.state.set_background_asset(None)
                st.session_state["structured_scene_source_text"] = script_text
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
                    "image_prompt": "A young man with a goofy hat, holding a banana and gummy bears, grinning mischievously.",
                },
                {
                    "name": "SARAH",
                    "description": "Early 30s, health-conscious, sarcastic, always prepared with a witty comeback.",
                    "style_hint": "Witty, sharp",
                    "image_prompt": "A woman in her early 30s, rolling her eyes, with a sarcastic expression.",
                },
                {
                    "name": "MIKE",
                    "description": "Late 20s, overly enthusiastic, the 'smoothie expert,' a bit clueless.",
                    "style_hint": "Enthusiastic, clueless",
                    "image_prompt": "A young man in his late 20s, bouncing in excitedly, with a big smile.",
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
