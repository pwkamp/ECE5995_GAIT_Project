import json
from pathlib import Path
from datetime import datetime


def append_beat(state, description: str) -> None:
    """Append a beat to the current structured scene in session state."""
    scene = state.session.get("structured_scene")
    if not scene:
        return
    beats = scene.setdefault("beats", [])
    new_order = len(beats) + 1
    beats.append({"order": new_order, "description": description})
    state.set_structured_scene(scene)


def save_structured_scene(state):
    """Persist the current structured scene to src/output/structured_scene.json."""
    scene = state.session.get("structured_scene")
    if not scene:
        return None
    output_dir = Path("src/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_path = output_dir / "structured_scene.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)
    return latest_path


def load_structured_scene(state):
    """Load structured scene from disk into session state, if present."""
    file_path = Path("src/output/structured_scene.json")
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            scene = json.load(f)
    except json.JSONDecodeError:
        return None
    state.set_structured_scene(scene)
    return scene


def load_or_init_structured_scene(state):
    """
    Load from disk if it exists; otherwise return the current in-memory scene.
    Useful when starting a new session.
    """
    loaded = load_structured_scene(state)
    if loaded is not None:
        return loaded
    return state.session.get("structured_scene")


def _dev_get_default_structured_scene() -> dict:
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
                "name": "Character_1",
                "age": "01, recently born",
                "description": "likes, dislikes, career, and disposition",
                "style_hint": "Goofy, playful, leadership",
                "image_prompt": "A young man with a goofy hat, holding a banana and gummy bears, grinning mischievously.",
            },
            {
                "name": "Character_2",
                "age": "25, mid-twenties",
                "description": "likes, dislikes, career, and disposition",
                "style_hint": "Witty, sharp",
                "image_prompt": "A woman in her early 30s, rolling her eyes, with a sarcastic expression.",
            },
            {
                "name": "Character_3",
                "age": "01, recently born",
                "description": "likes, dislikes, career, and disposition",
                "style_hint": "Enthusiastic, clueless",
                "image_prompt": "A young man in his late 20s, bouncing in excitedly, with a big smile.",
            },
        ],
        "beats": [
            {"order": 1, "description": "Establish the setting."},
            {"order": 2, "description": "Introduce the characters."},
            {"order": 3, "description": "Present the initial conflict or goal."},
        ],
    }
