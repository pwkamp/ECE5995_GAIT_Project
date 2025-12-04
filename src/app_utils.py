
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
    with open(timestamped_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)
    return str(timestamped_path)


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
