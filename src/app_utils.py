
import json
from pathlib import Path


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
    latest_path = output_dir / "structured_scene.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)


def update_app_cache():
    save_structured_scene()


def load_structured_scene(self):
    file_path = Path("src/output/structured_scene.json")
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            scene = json.load(f)
    except json.JSONDecodeError:
        return None
    self.state.session["structured_scene"] = scene
    return scene


def load_or_init_structured_scene(self):
    load_structured_scene(self)
    return self.state.session.get("structured_scene")


def get_current_script(self):
    structured_scene = load_or_init_structured_scene(self)
    if not structured_scene:
        return ""
    formatted_c = get_formatted_characters(structured_scene)
    plot_to_pt = get_plot_to_pt(structured_scene)
    return formatted_c + "\n******************************\n" + plot_to_pt


def get_formatted_characters(structured_scene: dict) -> str:
    if not structured_scene:
        return ""
    beats = structured_scene.get("characters", [])
    if not beats:
        return ""
    characters = structured_scene.get("characters", [])
    if not characters:
        return ""
    formatted_characters = []
    for c in characters:
        lines = []
        name = c.get("name", "")
        lines.append(f"Character: {name}")
        for key, value in c.items():
            if key == "name":
                continue
            if value is None:
                continue
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        formatted_characters.append("\n".join(lines))
    return "\n\n".join(formatted_characters)


def get_plot_to_pt(structured_scene: dict) -> str:
    if not structured_scene:
        return ""
    beats = structured_scene.get("beats", [])
    if not beats:
        return ""
    beats_sorted = sorted(beats, key=lambda b: b.get("order", 0))
    descriptions = [b.get("description", "").strip() for b in beats_sorted]
    return "\n".join(descriptions)


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
            {"order": 1, "description": "Establish the setting. Your journey begins here."},
        ]
    }
    
