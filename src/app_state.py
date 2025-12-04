from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import streamlit as st


@dataclass
class AppState:
    """Thin wrapper around Streamlit session_state for clearer intent."""

    chat_history: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {
                "role": "assistant",
                "content": "Tell me about the scene you want to create.",
            }
        ]
    )
    script_text: str = ""
    structured_scene: Optional[Dict] = None
    character_assets: List[Dict[str, str]] = field(default_factory=list)
    background_asset: Optional[Dict[str, str]] = None
    assembly_notes: List[str] = field(default_factory=list)
    video_asset: Optional[Dict[str, str]] = None

    def bind(self) -> None:
        """Ensure session_state has initialized values."""
        session = st.session_state
        session.setdefault("chat_history", self.chat_history)
        session.setdefault("script_text", self.script_text)
        session.setdefault("structured_scene", self.structured_scene)
        session.setdefault("character_assets", self.character_assets)
        session.setdefault("background_asset", self.background_asset)
        session.setdefault("assembly_notes", self.assembly_notes)
        session.setdefault("video_asset", self.video_asset)

    @property
    def session(self):
        return st.session_state

    # Convenience helpers for cleaner downstream code
    def add_chat(self, role: str, content: str) -> None:
        self.session["chat_history"].append({"role": role, "content": content})

    def set_script(self, text: str) -> None:
        self.session["script_text"] = text

    def set_structured_scene(self, data: Dict) -> None:
        self.session["structured_scene"] = data

    def set_character_assets(self, assets: List[Dict[str, str]]) -> None:
        self.session["character_assets"] = assets

    def set_background_asset(self, asset: Dict[str, str]) -> None:
        self.session["background_asset"] = asset

    def set_assembly_notes(self, notes: List[str]) -> None:
        self.session["assembly_notes"] = notes

    def set_video_asset(self, asset: Dict[str, str]) -> None:
        self.session["video_asset"] = asset
