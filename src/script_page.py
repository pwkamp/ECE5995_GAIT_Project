from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
    from .ui_helpers import ButtonRow
except ImportError:  # Fallback when run as a standalone script context
    from app_state import AppState
    from ui_helpers import ButtonRow


class ScriptPage:
    name = "Script"
    icon = "📝"

    def __init__(self, state: AppState):
        self.state = state

    def render(self) -> None:
        st.header(f"{self.icon} Script Workspace")
        st.caption("Capture the scene idea, chat through it, and refine the draft.")

        self._render_chat()
        self._render_script_editor()

    def _render_chat(self) -> None:
        for message in self.state.session["chat_history"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input("Describe the scene, characters, and vibe.")
        if prompt:
            self.state.add_chat("user", prompt)
            self.state.add_chat(
                "assistant",
                "Draft updated. Review or edit the script, then move to generation.",
            )
            if not self.state.session.get("script_text"):
                self.state.set_script(self._draft_script_from_prompt(prompt))
                st.info("Draft script seeded from your idea.")

    def _render_script_editor(self) -> None:
        st.markdown("#### Draft Script")
        default_text = self.state.session.get("script_text", "")
        new_text = st.text_area(
            "Scene script",
            value=default_text,
            height=280,
            key="script_editor",
            placeholder="INT. LOCATION - TIME\nCharacter: Dialogue...",
        )

        actions = ButtonRow.two(
            "Save Script Draft",
            "Load Sample Script",
            keys=["save_script", "load_sample_script"],
        )
        if actions["left"]:
            self.state.set_script(new_text)
            st.success("Script draft updated.")
        if actions["right"]:
            sample = self._sample_script()
            self.state.set_script(sample)
            st.session_state["script_editor"] = sample
            st.info("Sample script loaded for quick testing.")

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
