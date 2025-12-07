from __future__ import annotations

import io
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Defer heavy/optional imports so the rest of the app can load even if missing.
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    # moviepy >=2.1 no longer ships the editor convenience module
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    _VIDEO_DEPS_ERROR = None
except Exception as exc:  # pragma: no cover - environment-specific
    np = None
    Image = ImageDraw = ImageFont = None
    AudioFileClip = ImageClip = concatenate_videoclips = None
    _VIDEO_DEPS_ERROR = exc


def generate_video_from_structured_scene(
    scene: Dict,
    background_asset: Optional[Dict] = None,
    music_path: Optional[Path] = None,
    seconds_per_beat: int = 4,
    resolution: Tuple[int, int] = (1280, 720),
    fps: int = 24,
    output_dir: Path = Path("src/output"),
) -> Path:
    """
    Build a simple video from a structured scene by rendering each beat
    onto an image and concatenating them. Optionally layer background
    art and existing music if provided.
    """
    if _VIDEO_DEPS_ERROR:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, and their "
            "system requirements (ffmpeg) are available. Under Docker, rebuild the image "
            "after updating requirements.txt."
        ) from _VIDEO_DEPS_ERROR
    beats: List[Dict] = scene.get("beats") or []
    if not beats:
        raise ValueError("No beats found in structured scene.")

    sorted_beats = sorted(
        beats,
        key=lambda b: b.get("order", 0),
    )

    width, height = resolution
    base_image = _prepare_base_canvas(
        background_bytes=background_asset.get("image_bytes") if background_asset else None,
        resolution=(width, height),
    )
    font_title, font_body = _load_fonts()

    clips: List[ImageClip] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / "generated_video.mp4"

    audio_clip = None
    if music_path and Path(music_path).is_file():
        audio_clip = AudioFileClip(str(music_path))

    try:
        for idx, beat in enumerate(sorted_beats, start=1):
            frame = _render_frame(
                base_image=base_image,
                scene=scene,
                beat=beat,
                index=idx,
                total=len(sorted_beats),
                font_title=font_title,
                font_body=font_body,
            )
            clips.append(ImageClip(np.array(frame)).with_duration(seconds_per_beat))

        video = concatenate_videoclips(clips, method="compose")
        if audio_clip:
            video = video.set_audio(audio_clip)

        video.write_videofile(
            str(final_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None,
        )
    finally:
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
        if audio_clip:
            try:
                audio_clip.close()
            except Exception:
                pass

    return final_path


def _prepare_base_canvas(
    background_bytes: Optional[bytes],
    resolution: Tuple[int, int],
) -> Image.Image:
    width, height = resolution
    if background_bytes:
        try:
            img = Image.open(io.BytesIO(background_bytes)).convert("RGB")
            return img.resize((width, height))
        except Exception:
            pass

    # Fallback: create a subtle gradient backdrop
    base = Image.new("RGB", (width, height), color=(18, 22, 28))
    draw = ImageDraw.Draw(base)
    for y in range(height):
        shade = int(18 + (y / height) * 32)
        draw.line([(0, y), (width, y)], fill=(shade, shade + 4, shade + 8))
    return base


def _load_fonts() -> Tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    try:
        title_font = ImageFont.truetype("arial.ttf", 48)
        body_font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    return title_font, body_font


def _render_frame(
    base_image: Image.Image,
    scene: Dict,
    beat: Dict,
    index: int,
    total: int,
    font_title: ImageFont.ImageFont,
    font_body: ImageFont.ImageFont,
) -> Image.Image:
    img = base_image.copy().convert("RGBA")
    width, height = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Semi-transparent panel for legible text
    panel_top = int(height * 0.55)
    draw.rectangle(
        [(0, panel_top), (width, height)],
        fill=(0, 0, 0, 170),
    )

    padding = 40
    text_x = padding
    text_y = panel_top + padding

    title = f"{scene.get('scene_title', 'Scene')} — Beat {index}/{total}"
    draw.text((text_x, text_y), title, font=font_title, fill=(255, 255, 255, 255))
    text_y += font_title.getbbox(title)[3] + 12

    description = beat.get("description", "No description provided.")
    wrapped = textwrap.wrap(description, width=70) or [""]
    for line in wrapped:
        draw.text(
            (text_x, text_y),
            line,
            font=font_body,
            fill=(230, 230, 230, 255),
        )
        text_y += font_body.getbbox(line)[3] + 6

    composed = Image.alpha_composite(img, overlay)
    return composed.convert("RGB")
