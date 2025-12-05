
import json
from pathlib import Path
from datetime import datetime


def append_beat(self, description: str) -> None:
    scene = self.state.session.get("structured_scene")
    if not scene:
        return
    beats = scene.setdefault("beats", [])
    new_order = len(beats) + 1
    beats.append({
        "order": new_order,
        "description": description
    })
    self.state.set_structured_scene(scene)


def save_structured_scene(self):
    scene = self.state.session.get("structured_scene")
    if not scene:
        return None
    output_dir = Path("src/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_path = output_dir / f"structured_scene_{timestamp}.json"
    latest_path = output_dir / "structured_scene.json"
    # with open(timestamped_path, "w", encoding="utf-8") as f:
    #     json.dump(scene, f, indent=2)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)


def load_structured_scene(self):
    file_path = Path("src/output/structured_scene.json")
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            scene = json.load(f)
    except json.JSONDecodeError:
        return None
    self.state.set_structured_scene(scene)
    return scene


def load_or_init_structured_scene(self):
    """
    Load from disk if it exists; otherwise return the current memory scene.
    Useful when starting a new session.
    """
    loaded = self.load_structured_scene()
    if loaded is not None:
        return loaded

    return self.state.session.get("structured_scene")

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
        ]
    }
    
