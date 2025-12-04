

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

    