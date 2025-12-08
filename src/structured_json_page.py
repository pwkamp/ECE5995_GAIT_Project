from __future__ import annotations

import streamlit as st

try:
    from .app_state import AppState
    from . import app_utils as au
except ImportError:
    from app_state import AppState
    import app_utils as au


class StructuredJSONPage:
    name = "Structured JSON"
    icon = "🧩"

    def __init__(self, state: AppState, config: dict):
        self.state = state
        self.config = config

    def render(self) -> None:
        st.header(f"{self.icon} Structured JSON")
        st.caption("Auto-generated scene structure based on the current script.")

        structured_scene = au.load_or_init_structured_scene(self.state)

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
            "scene_title": "Factory Prank",
            "logline": "Three men in an early 1900s factory pull a playful prank on one of their own.",
            "art_style": "Friendly cartoon silent-film vibe, black-and-white, cel-shaded with grainy texture",
            "background": {
                "description": (
                    "A cavernous early 20th century factory with brick walls stained by soot, "
                    "rows of iron machines, belts, pistons, scattered wooden crates, "
                    "and hanging filament bulbs casting hard, dramatic shadows through ribbons of steam."
                ),
                "time_of_day": "Day",
                "location": "Industrial factory interior",
            },
            "characters": [
                {
                    "name": "EDWARD",
                    "age": "Mid-30s",
                    "description": (
                        "Tall, lean ringleader with a mischievous glint; grease-smudged face, "
                        "flat cap tilted, rolled sleeves, suspenders over oil-stained overalls, "
                        "fingerless gloves and scuffed boots. Quick, confident posture."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, crisp contrast, rim-lit edges",
                    "image_prompt": "",
                },
                {
                    "name": "HARRY",
                    "age": "Late 20s",
                    "description": (
                        "Stockier accomplice with a broad grin; suspenders, rolled sleeves, patched vest, "
                        "thick moustache dusted with coal, calloused hands, heavy work boots, relaxed stance."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, grainy texture, soft falloff",
                    "image_prompt": "",
                },
                {
                    "name": "GEORGE",
                    "age": "Early 30s",
                    "description": (
                        "Unsuspecting victim; neat cap and vest over a crisp shirt, pocket watch chain visible, "
                        "tidy moustache, cautious eyes; stands straighter, sleeves buttoned, gloves tucked in belt."
                    ),
                    "style_hint": "Silent film, black-and-white portrait, subtle film grain, chiaroscuro lighting",
                    "image_prompt": "",
                },
            ],
            "beats": [
                {
                    "order": 1,
                    "description": (
                        "Wide shot of the bustling factory; machinery thumps in the background as Edward and Harry "
                        "share a conspiratorial grin near a coiled air hose."
                    ),
                    "dialogue": [
                        "EDWARD: If this compressor kicks again, we're blaming George.",
                        "HARRY: He walks in, we trigger it. He'll never see it coming."
                    ],
                    "duration_seconds": 5,
                    "padded_duration_seconds": 8,
                },
                {
                    "order": 2,
                    "description": (
                        "Close on Edward rigging a harmless air blast under George's workbench; Harry watches, "
                        "barely containing laughter."
                    ),
                    "dialogue": [
                        "EDWARD: Hose is hidden. Just nudge that lever when he sits.",
                        "HARRY: Quiet, footsteps—pretend you're actually working."
                    ],
                    "duration_seconds": 5,
                    "padded_duration_seconds": 8,
                },
                {
                    "order": 3,
                    "description": (
                        "George approaches, adjusting his cap; Edward signals; Harry tugs the hidden lever—compressed "
                        "air whooshes and a string pops up; George startles then smirks as the trio chuckles."
                    ),
                    "dialogue": [
                        "GEORGE: What in blazes—was that you two?",
                        "HARRY: Consider it a wake-up call.",
                        "EDWARD: Next round's on you at lunch, friend."
                    ],
                    "duration_seconds": 4,
                    "padded_duration_seconds": 8,
                },
                {
                    "order": 4,
                    "description": (
                        "The trio gathers back at the workbench, sharing a breathless laugh as the machinery clatters on."
                    ),
                    "dialogue": [
                        "GEORGE: Alright, truce until coffee.",
                        "EDWARD: Deal—no more surprises.",
                        "HARRY: For now."
                    ],
                    "duration_seconds": 3,
                    "padded_duration_seconds": 4,
                },
            ],
        }
