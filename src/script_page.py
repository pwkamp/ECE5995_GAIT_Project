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

            # Always keep the draft script in sync with the latest assistant reply
            self.state.set_script(reply)
            st.session_state["script_editor"] = reply

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
            st.session_state["script_editor"] = updated_text

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
