from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
except ImportError:
    from app_state import AppState


class StructuredJSONPage:
    name = "Structured JSON"
    icon = "📄"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config

    def render(self) -> None:
        st.header(f"{self.icon} Structured JSON")
        st.caption("Auto-generated scene structure based on the current script.")

        if self.config.get("dev_mode") and not self.state.session.get("structured_scene"):
            self.state.set_structured_scene(self._dev_structured_scene())

        structured_scene = self.state.session.get("structured_scene")
        if structured_scene:
            st.json(structured_scene, expanded=True)
        else:
            st.info("No structured output yet. Edit the script to auto-generate JSON.")

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
