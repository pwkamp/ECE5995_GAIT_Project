from __future__ import annotations

import io
import os
import tempfile
import textwrap
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Defer heavy imports so other pages can load without video deps present.
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy import AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips
    import fal_client

    _VIDEO_DEPS_ERROR = None
except Exception as exc:  # pragma: no cover - environment-specific
    np = None
    Image = ImageDraw = ImageFont = None
    AudioFileClip = ImageClip = VideoFileClip = concatenate_videoclips = None
    fal_client = None
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

    sorted_beats = sorted(beats, key=lambda b: b.get("order", 0))

    width, height = resolution
    base_image = _prepare_base_canvas(
        background_bytes=background_asset.get("image_bytes") if background_asset else None,
        resolution=(width, height),
    )
    font_title, font_body = _load_fonts()

    clips: List[ImageClip] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = (output_dir / "generated_video.mp4").resolve()

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
            # MoviePy 2.x uses with_audio instead of set_audio
            video = video.with_audio(audio_clip)

        # moviepy 2.x removed verbose/logger params
        video.write_videofile(
            str(final_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
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


# ---------- fal.ai (Pika) generator ----------

def generate_video_with_pika(
    scene: Dict,
    background_asset: Optional[Dict],
    character_assets: List[Dict],
    music_path: Optional[Path] = None,
    seconds_per_beat: int = 4,
    resolution: Tuple[int, int] = (1280, 720),
    model_id: str = None,
    fal_key: Optional[str] = None,
    output_dir: Path = Path("src/output"),
) -> Path:
    """
    Generate a real video by sending composed frames to fal.ai Pika image-to-video.
    Concatenates clips and optionally layers music.
    """
    if _VIDEO_DEPS_ERROR:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, `fal-client`, "
            "and ffmpeg are available. Rebuild the image after updating requirements.txt."
        ) from _VIDEO_DEPS_ERROR
    if fal_client is None:
        raise ImportError("fal_client is required for Pika generation.")

    fal_client.api_key = _resolve_fal_key(fal_key)
    model = model_id or os.getenv("PIKA_MODEL_ID", "fal-ai/pika/video")

    beats: List[Dict] = scene.get("beats") or []
    if not beats:
        raise ValueError("No beats found in structured scene.")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="pika_inputs_", dir=output_dir))
    clips_dir = output_dir / "pika_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    base_image = _compose_scene_image(
        background_asset=background_asset,
        character_assets=character_assets,
        resolution=resolution,
    )

    clip_paths: List[Path] = []
    try:
        for idx, beat in enumerate(beats, start=1):
            frame_path = tmp_dir / f"beat_{idx:02d}.png"
            frame = _render_frame(
                base_image=base_image,
                scene=scene,
                beat=beat,
                index=idx,
                total=len(beats),
                font_title=_load_fonts()[0],
                font_body=_load_fonts()[1],
            )
            frame.save(frame_path)

            prompt = _build_pika_prompt(scene, beat, character_assets, seconds_per_beat)
            clip_path = _generate_clip_via_pika(
                image_path=frame_path,
                prompt=prompt,
                model_id=model,
                output_dir=clips_dir,
                idx=idx,
                fal_key=fal_key,
                resolution=resolution,
                duration=seconds_per_beat,
            )
            clip_paths.append(clip_path)

        final_path = (output_dir / "generated_video.mp4").resolve()
        _concat_and_optionally_add_audio(
            clip_paths=clip_paths,
            final_path=final_path,
            music_path=music_path,
        )
        return final_path
    finally:
        # Best-effort cleanup of temp frames
        for p in tmp_dir.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass


def _build_pika_prompt(
    scene: Dict,
    beat: Dict,
    character_assets: List[Dict],
    seconds_per_beat: int,
) -> str:
    names = ", ".join(c.get("name", "") for c in character_assets) or "characters"
    art_style = scene.get("art_style", "")
    background = scene.get("background", {})
    setting = background.get("location", background.get("description", "scene"))
    return "\n".join(
        [
            f"Create a cinematic shot for this beat: {beat.get('description', '')}",
            f"Art style: {art_style}",
            f"Characters present: {names}",
            f"Setting: {setting}",
            f"Duration target: ~{seconds_per_beat} seconds.",
            "No subtitles, no on-screen text, no watermarks. No audio.",
        ]
    )


# ----------- fal.ai REST helpers -----------

def call_fal_pika(
    image_path: str,
    prompt: str,
    *,
    duration: float | None = None,
    resolution: str | None = None,
    model_id: str | None = None,
    fal_key: str | None = None,
) -> str:
    """
    Submit an image-to-video job to fal.ai Pika and return the final video URL.
    Uses fal_client to handle queue/polling.
    """
    if fal_client is None:
        raise ImportError("fal_client is required for Pika integration.")

    api_key = fal_key or os.getenv("FAL_KEY")
    if not api_key:
        raise RuntimeError("FAL_KEY environment variable not set.")

    model = model_id or os.getenv("PIKA_MODEL_ID") or "fal-ai/pika/v2-turbo/image-to-video"
    fal_client.api_key = api_key

    image_url = fal_client.upload_file(image_path)
    arguments: dict = {
        "image_url": image_url,
        "prompt": prompt,
    }
    if duration is not None:
        arguments["duration"] = duration
    if resolution:
        arguments["resolution"] = resolution

    result = fal_client.subscribe(model, arguments=arguments, with_logs=True)
    video_url = _extract_video_url(result)
    if not video_url:
        raise RuntimeError(f"fal.ai response missing video url: {result}")
    return video_url


def download_video(url: str, output_path: Path) -> Path:
    """
    Stream a video from URL to disk.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed ({resp.status_code}): {resp.text[:200]}")
    with output_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return output_path


def _generate_clip_via_pika(
    image_path: Path,
    prompt: str,
    model_id: str,
    output_dir: Path,
    idx: int,
    fal_key: Optional[str],
    resolution: Tuple[int, int],
    duration: int,
) -> Path:
    video_url = call_fal_pika(
        image_path=str(image_path),
        prompt=prompt,
        duration=duration,
        resolution=f"{resolution[0]}x{resolution[1]}",
        model_id=model_id,
        fal_key=fal_key,
    )
    clip_path = output_dir / f"clip_{idx:02d}.mp4"
    download_video(video_url, clip_path)
    return clip_path


def _extract_video_url(result: dict) -> str:
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected response type: {type(result)}")
    video_url = None
    video_obj = result.get("video")
    if isinstance(video_obj, dict):
        video_url = video_obj.get("url")
    if not video_url:
        data = result.get("data")
        if isinstance(data, dict):
            video_obj = data.get("video")
            if isinstance(video_obj, dict):
                video_url = video_obj.get("url")
    if not video_url:
        raise RuntimeError("Could not find video URL in fal.ai response.")
    return video_url


def _download_file(url: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, dest_path.open("wb") as out_file:
        out_file.write(response.read())


def _concat_and_optionally_add_audio(
    clip_paths: List[Path],
    final_path: Path,
    music_path: Optional[Path],
) -> None:
    clips = []
    audio_clip = None
    try:
        for p in clip_paths:
            clips.append(VideoFileClip(str(p)))
        video = concatenate_videoclips(clips, method="compose")
        if music_path and Path(music_path).is_file():
            audio_clip = AudioFileClip(str(music_path))
            video = video.with_audio(audio_clip)
        video.write_videofile(
            str(final_path),
            codec="libx264",
            audio_codec="aac",
        )
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        if audio_clip:
            try:
                audio_clip.close()
            except Exception:
                pass


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


def _compose_scene_image(
    background_asset: Optional[Dict],
    character_assets: List[Dict],
    resolution: Tuple[int, int],
) -> Image.Image:
    """
    Compose a simple frame combining background + character images (if available).
    Characters are laid along the bottom in a row.
    """
    width, height = resolution
    base = _prepare_base_canvas(
        background_bytes=background_asset.get("image_bytes") if background_asset else None,
        resolution=resolution,
    ).convert("RGBA")

    chars = [c for c in character_assets or [] if c.get("image_bytes")]
    if not chars:
        return base.convert("RGB")

    max_chars = min(len(chars), 3)
    chars = chars[:max_chars]
    padding = 20
    avail_width = width - padding * (max_chars + 1)
    slot_w = avail_width // max_chars
    max_h = int(height * 0.45)
    y_bottom = height - padding

    for idx, char in enumerate(chars):
        try:
            img = Image.open(io.BytesIO(char["image_bytes"])).convert("RGBA")
        except Exception:
            continue
        w, h = img.size
        scale = min(slot_w / w, max_h / h)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.LANCZOS)
        x = padding + idx * (slot_w + padding) + (slot_w - new_size[0]) // 2
        y = y_bottom - new_size[1]
        base.alpha_composite(img, dest=(x, y))

    return base.convert("RGB")


def _resolve_fal_key(provided_key: Optional[str]) -> str:
    if provided_key:
        return provided_key
    env_key = os.getenv("FAL_KEY")
    if env_key:
        return env_key
    # Try secrets file
    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        try:
            import tomllib

            with secrets_path.open("rb") as f:
                data = tomllib.load(f)
            if isinstance(data, dict):
                key = data.get("FAL_KEY")
                if not key:
                    fal_section = data.get("fal")
                    if isinstance(fal_section, dict):
                        key = fal_section.get("FAL_KEY") or fal_section.get("key")
                if key:
                    return str(key)
        except Exception:
            pass
    raise RuntimeError("FAL_KEY not found. Set FAL_KEY env var or add it to .streamlit/secrets.toml.")
