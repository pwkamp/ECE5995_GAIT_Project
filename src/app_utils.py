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
        "scene_title": "Factory Prank",
        "logline": "Three men in an early 1900s factory pull a playful prank on one of their own.",
        "art_style": "Black and white, silent-film style with grainy texture",
        "background": {
            "description": (
                "A cavernous early 20th century factory with brick walls stained by soot, rows of iron machines, belts, "
                "pistons, scattered wooden crates, and hanging filament bulbs casting hard, dramatic shadows through "
                "ribbons of steam."
            ),
            "time_of_day": "Day",
            "location": "Industrial factory interior",
        },
        "characters": [
            {
                "name": "EDWARD",
                "age": "Mid-30s",
                "description": (
                    "Tall, lean ringleader with a mischievous glint; grease-smudged face, flat cap tilted, rolled sleeves, "
                    "suspenders over oil-stained overalls, fingerless gloves and scuffed boots. Quick, confident posture."
                ),
                "style_hint": "Silent film, black-and-white portrait, crisp contrast, rim-lit edges",
                "image_prompt": "",
            },
            {
                "name": "HARRY",
                "age": "Late 20s",
                "description": (
                    "Stockier accomplice with a broad grin; suspenders, rolled sleeves, patched vest, thick moustache dusted "
                    "with coal, calloused hands, heavy work boots, relaxed stance."
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
                    "Wide shot of the bustling factory; machinery thumps in the background as Edward and Harry share a "
                    "conspiratorial grin near a coiled air hose."
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
