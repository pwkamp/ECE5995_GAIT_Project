
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
        return

    output_dir = Path("src/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / "structured_scene.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)

    return str(file_path)
