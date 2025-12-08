from __future__ import annotations

import io
import os
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import base64

import requests

# Defer heavy imports so other pages can load without video deps present.
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy import AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips
    from moviepy.audio.AudioClip import CompositeAudioClip
    from moviepy.audio.fx import audio_loop

    _VIDEO_DEPS_ERROR = None
except Exception as exc:  # pragma: no cover - environment-specific
    np = None
    Image = ImageDraw = ImageFont = None
    AudioFileClip = ImageClip = VideoFileClip = concatenate_videoclips = CompositeAudioClip = None
    audio_loop = None
    _VIDEO_DEPS_ERROR = exc


def _ensure_video_deps() -> Optional[Exception]:
    """
    Lazily re-attempt loading video dependencies in case they were installed after module import.
    Returns the last error if still failing, otherwise None.
    """
    global np, Image, ImageDraw, ImageFont, AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips, CompositeAudioClip, audio_loop, _VIDEO_DEPS_ERROR
    if _VIDEO_DEPS_ERROR is None:
        return None
    try:
        import numpy as _np
        from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
        from moviepy import (
            AudioFileClip as _AudioFileClip,
            ImageClip as _ImageClip,
            VideoFileClip as _VideoFileClip,
            concatenate_videoclips as _concatenate_videoclips,
        )
        from moviepy.audio.AudioClip import CompositeAudioClip as _CompositeAudioClip
        try:
            from moviepy.audio.fx import audio_loop as _audio_loop
        except Exception:
            _audio_loop = None

        np = _np
        Image = _Image
        ImageDraw = _ImageDraw
        ImageFont = _ImageFont
        AudioFileClip = _AudioFileClip
        ImageClip = _ImageClip
        VideoFileClip = _VideoFileClip
        concatenate_videoclips = _concatenate_videoclips
        CompositeAudioClip = _CompositeAudioClip
        audio_loop = _audio_loop
        _VIDEO_DEPS_ERROR = None
    except Exception as exc:  # pragma: no cover - environment-specific
        _VIDEO_DEPS_ERROR = exc
    return _VIDEO_DEPS_ERROR


def _ensure_video_deps() -> Optional[Exception]:
    """
    Lazily re-attempt loading video dependencies in case they were installed after module import.
    Returns the last error if still failing, otherwise None.
    """
    global np, Image, ImageDraw, ImageFont, AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips, CompositeAudioClip, audio_loop, _VIDEO_DEPS_ERROR
    if _VIDEO_DEPS_ERROR is None:
        return None
    try:
        import numpy as _np
        from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
        from moviepy import (
            AudioFileClip as _AudioFileClip,
            ImageClip as _ImageClip,
            VideoFileClip as _VideoFileClip,
            concatenate_videoclips as _concatenate_videoclips,
        )
        from moviepy.audio.AudioClip import CompositeAudioClip as _CompositeAudioClip
        try:
            from moviepy.audio.fx import audio_loop as _audio_loop
        except Exception:
            _audio_loop = None

        np = _np
        Image = _Image
        ImageDraw = _ImageDraw
        ImageFont = _ImageFont
        AudioFileClip = _AudioFileClip
        ImageClip = _ImageClip
        VideoFileClip = _VideoFileClip
        concatenate_videoclips = _concatenate_videoclips
        CompositeAudioClip = _CompositeAudioClip
        audio_loop = _audio_loop
        _VIDEO_DEPS_ERROR = None
    except Exception as exc:  # pragma: no cover - environment-specific
        _VIDEO_DEPS_ERROR = exc
    return _VIDEO_DEPS_ERROR


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
    err = _ensure_video_deps()
    if err:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, and ffmpeg are available. "
            "If you just installed them, restart or rebuild the container. "
            f"Root cause: {err}"
        ) from err

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
    *args, **kwargs
) -> Path:
    raise NotImplementedError("Pika/fal.ai generation has been removed. Use Sora/OpenAI or Local placeholder.")


def generate_video_with_sora(
    scene: Dict,
    music_path: Optional[Path] = None,
    seconds_per_beat: int = 4,
    resolution: Tuple[int, int] = (1280, 720),
    model_id: Optional[str] = None,
    image_url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    output_dir: Path = Path("src/output"),
) -> Tuple[Path, Optional[Path]]:
    """
    Generate a video via OpenAI's Sora (or compatible video) endpoint.
    This uses a single prompt distilled from the structured scene and beats.
    """
    err = _ensure_video_deps()
    if err:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, and ffmpeg are available. "
            "If you just installed them, restart or rebuild the container. "
            f"Root cause: {err}"
        ) from err

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    beats = scene.get("beats") or []

    reference_image_bytes = image_bytes
    if reference_image_bytes is None:
        for candidate in [Path("src/output/scene_composite.png"), output_dir / "scene_composite.png"]:
            if candidate.exists():
                reference_image_bytes = candidate.read_bytes()
                break
    # Resize reference to match target video size to avoid inpaint size errors.
    resolution_str = _normalize_resolution(resolution)
    reference_image_bytes = _resize_reference_image(reference_image_bytes, resolution_str) if reference_image_bytes else None
    reference_image_data_url = _encode_image_to_data_url(reference_image_bytes) if reference_image_bytes else None

    # Optional: derive a visual description from a reference image.
    # Only attempt vision if we have a real HTTP(S) URL; skip data URLs / raw bytes.
    vision_image_url = image_url if image_url and image_url.startswith(("http://", "https://")) else None
    image_desc = None
    if vision_image_url:
        image_desc = describe_image_with_vision(vision_image_url)
    if not image_desc and reference_image_bytes:
        image_desc = "Use the attached reference image to match framing, lighting, and character positions."

    # If we have beats, render one clip per beat and stitch.
    if beats:
        segments = [[b] for b in beats]
        segment_dir = output_dir / "sora_segments"
        segment_dir.mkdir(parents=True, exist_ok=True)
        clip_paths: List[Path] = []
        segment_durations: List[float] = []
        seed_image_bytes = reference_image_bytes
        seed_image_data_url = reference_image_data_url or image_url
        try:
            for idx, beat_slice in enumerate(segments, start=1):
                duration_hint = _beat_duration_with_buffer(beat_slice[0], seconds_per_beat)
                seg_prompt = _build_sora_prompt_segment(scene, beat_slice, image_desc, duration_hint)
                video_result = call_sora_video(
                    prompt=seg_prompt,
                    duration=duration_hint,
                    resolution=resolution_str,
                    model_id=model_id,
                    image_url=seed_image_data_url,
                    image_bytes=seed_image_bytes,
                )
                seg_path = segment_dir / f"segment_{idx:02}.mp4"
                _store_video_result(video_result, seg_path)
                clip_paths.append(seg_path)
                segment_durations.append(duration_hint)
                # Seed next clip with the last frame of the previous segment for continuity.
                seed_image_bytes = _extract_last_frame_as_png(seg_path) or seed_image_bytes
                seed_image_data_url = _encode_image_to_data_url(seed_image_bytes) if seed_image_bytes else seed_image_data_url

            final_path = output_dir / "generated_video.mp4"
            raw_path = output_dir / "generated_video_nomusic.mp4"
            _concat_and_optionally_add_audio(
                clip_paths=clip_paths,
                final_path=final_path,
                raw_path=raw_path,
                music_path=music_path,
                trim_audio=True,
                expected_duration=sum(segment_durations) if segment_durations else None,
            )
            return final_path, raw_path
        finally:
            for p in segment_dir.glob("segment_*.mp4"):
                try:
                    p.unlink()
                except Exception:
                    pass
    # Fallback: single call
    target_duration = _total_duration_with_buffer(beats, seconds_per_beat)
    target_duration = min(target_duration, 60)
    prompt = _build_sora_prompt(scene, image_desc, target_duration)
    video_result = call_sora_video(
        prompt=prompt,
        duration=target_duration,
        resolution=resolution_str,
        model_id=model_id,
        image_url=reference_image_data_url or image_url,
        image_bytes=reference_image_bytes,
    )
    raw_path = output_dir / "generated_video_nomusic.mp4"
    final_path = output_dir / "generated_video.mp4"
    _store_video_result(video_result, raw_path)
    if music_path and Path(music_path).is_file():
        _overlay_music_to_video(raw_path, Path(music_path), expected_duration=target_duration, output_path=final_path)
    else:
        raw_path.replace(final_path)
    return final_path, raw_path


def _build_pika_prompt(
    scene: Dict,
    beat: Dict,
    character_assets: List[Dict],
    seconds_per_beat: int,
) -> str:
    raise NotImplementedError("Pika/fal.ai prompts removed. Use Sora/OpenAI.")


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
    raise NotImplementedError("Pika/fal.ai generation removed. Use Sora/OpenAI.")


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


def _store_video_result(video_result: Union[str, bytes, bytearray], output_path: Path) -> None:
    """
    Persist a video result that may be a URL or raw bytes.
    """
    if isinstance(video_result, (bytes, bytearray)):
        output_path.write_bytes(video_result)
    else:
        download_video(str(video_result), output_path)


def describe_image_with_vision(image_url: str, vision_model: Optional[str] = None) -> str:
    """
    Send an image URL to a vision-capable chat model to get a description.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set for vision description.")
    model = vision_model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this image in rich visual detail. "
                            "Focus on people, environment, style, lighting, and color."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ],
            }
        ],
    }
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"Vision describe failed ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return _extract_text_from_message(message)


def _extract_text_from_message(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") in ("output_text", "text")]
        if texts:
            return " ".join(texts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


# ----------- OpenAI Sora helpers -----------

def call_sora_video(
    prompt: str,
    *,
    duration: float | None = None,
    resolution: str | None = None,
    model_id: str | None = None,
    image_url: str | None = None,
    image_bytes: bytes | None = None,
) -> Union[str, bytes]:
    """
    Submit a video generation job to OpenAI Sora and return the video URL/bytes.
    Uses multipart form-data to support reference images and the `seconds` field.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    model = model_id or os.getenv("SORA_MODEL_ID") or "sora-2-pro"
    url = "https://api.openai.com/v1/videos"

    headers = {"Authorization": f"Bearer {api_key}"}
    files = {}
    if image_bytes:
        files["input_reference"] = ("reference.png", image_bytes, "image/png")
    data: dict = {
        "prompt": prompt,
        "model": model,
    }
    if duration is not None:
        data["seconds"] = int(duration)
    if resolution:
        data["size"] = _normalize_resolution(resolution)
    if image_url and not image_bytes:
        data["image_url"] = image_url

    resp = requests.post(url, headers=headers, data=data, files=files or None, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"Sora submit failed ({resp.status_code}): {resp.text[:500]}")

    resp_data = resp.json()
    direct_url = None
    if isinstance(resp_data.get("data"), list):
        for item in resp_data["data"]:
            if isinstance(item, dict):
                direct_url = item.get("download_url") or item.get("url")
                if direct_url:
                    break
    if direct_url:
        return direct_url

    job_id = resp_data.get("id")
    if not job_id:
        raise RuntimeError(f"Sora response missing job id: {resp_data}")

    return _poll_sora_job(job_id, headers, url)


def _build_sora_prompt(
    scene: Dict, image_description: Optional[str] = None, target_duration: Optional[float] = None
) -> str:
    beats = scene.get("beats", [])
    beat_lines = "; ".join(_safe_text(b.get("description", "")) for b in beats)
    dialogue_lines = _dialogue_lines(beats)
    art_style = _cartoonize_style(scene.get("art_style", ""))
    background = scene.get("background", {})
    setting = background.get("location", background.get("description", ""))
    background_desc = background.get("description", "")
    characters = scene.get("characters", []) or []
    character_lines = "; ".join(
        f"{c.get('name','Character')}: {_safe_text(c.get('description',''))}" for c in characters
    )
    image_line = f"Visual reference: {image_description}. " if image_description else ""
    dialogue_prompt = f"Dialogue beats: {dialogue_lines}. " if dialogue_lines else ""
    duration_line = f"Target overall length: ~{target_duration:.1f} seconds with a little breathing room. " if target_duration else ""
    return (
        f"Create a coherent cinematic sequence in {art_style} style. "
        f"Setting: {setting}. Environment detail: {background_desc}. "
        f"Characters: {character_lines}. "
        f"Story beats: {beat_lines}. "
        f"{dialogue_prompt}"
        f"{duration_line}"
        f"{image_line}"
        "Tone: lighthearted, playful, family-friendly; no harm, no violence, no injuries, no weapons. "
        f"Include natural spoken dialogue and ambient factory sounds; avoid on-screen text or subtitles."
    )


def _build_sora_prompt_segment(
    scene: Dict, beats_slice: List[Dict], image_description: Optional[str] = None, duration_hint: Optional[float] = None
) -> str:
    art_style = _cartoonize_style(scene.get("art_style", ""))
    background = scene.get("background", {})
    setting = background.get("location", background.get("description", ""))
    background_desc = background.get("description", "")
    characters = scene.get("characters", []) or []
    character_lines = "; ".join(
        f"{c.get('name','Character')}: {_safe_text(c.get('description',''))}" for c in characters
    )
    beat_lines = "; ".join(_safe_text(b.get("description", "")) for b in beats_slice)
    dialogue_lines = _dialogue_lines(beats_slice)
    image_line = f"Visual reference: {image_description}. " if image_description else ""
    dialogue_prompt = f"Dialogue beats: {dialogue_lines}. " if dialogue_lines else ""
    duration_line = f"Target clip length: ~{duration_hint:.1f} seconds with a small buffer. " if duration_hint else ""
    return (
        f"Create a coherent cinematic sequence in {art_style} style. "
        f"Setting: {setting}. Environment detail: {background_desc}. "
        f"Characters: {character_lines}. "
        f"Story beats: {beat_lines}. "
        f"{dialogue_prompt}"
        f"{duration_line}"
        f"{image_line}"
        "Tone: lighthearted, playful, family-friendly; no harm, no violence, no injuries, no weapons. "
        f"Use natural, flowing dialogue that fits the action; avoid robotic pacing. "
        f"Include ambient factory sounds; avoid on-screen text or subtitles."
    )


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
    raise NotImplementedError("Pika/fal.ai generation removed. Use Sora/OpenAI.")


def _concat_and_optionally_add_audio(
    clip_paths: List[Path],
    final_path: Path,
    raw_path: Optional[Path],
    music_path: Optional[Path],
    trim_audio: bool = False,
    expected_duration: Optional[float] = None,
) -> None:
    clips = []
    video = None
    total_duration = 0.0
    raw_path = raw_path or final_path.with_name(f"{final_path.stem}_nomusic{final_path.suffix}")
    try:
        for p in clip_paths:
            clip = VideoFileClip(str(p))
            clips.append(clip)
            try:
                total_duration += float(getattr(clip, "duration", 0) or 0)
            except Exception:
                pass
        video = concatenate_videoclips(clips, method="compose")
        try:
            total_duration = max(total_duration, float(getattr(video, "duration", 0) or 0))
        except Exception:
            pass
        video.write_videofile(
            str(raw_path),
            codec="libx264",
            audio_codec="aac",
        )
        try:
            if video:
                video.close()
                video = None
        except Exception:
            video = None
        if music_path and Path(music_path).is_file():
            target_duration = expected_duration if expected_duration and expected_duration > 0 else total_duration
            _overlay_music_to_video(raw_path, Path(music_path), trim_audio=trim_audio, expected_duration=target_duration, output_path=final_path)
        else:
            if final_path != raw_path:
                final_path.write_bytes(Path(raw_path).read_bytes())
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        try:
            if video:
                video.close()
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


def _split_beats(beats: List[Dict], parts: int) -> List[List[Dict]]:
    """
    Split beats into up to `parts` groups, preserving order.
    """
    if parts <= 1 or len(beats) <= 1:
        return [beats]
    chunk_size = max(1, (len(beats) + parts - 1) // parts)
    return [beats[i : i + chunk_size] for i in range(0, len(beats), chunk_size)]


def _dialogue_lines(beats: List[Dict]) -> str:
    """Flatten dialogue lines across beats."""
    lines: List[str] = []
    for idx, beat in enumerate(beats, start=1):
        dialogue = beat.get("dialogue") or []
        if isinstance(dialogue, str):
            dialogue = [dialogue]
        for line in dialogue:
            text = _safe_text(str(line).strip())
            if not text:
                continue
            label = beat.get("order", idx)
            lines.append(f"Beat {label}: {text}")
    return "; ".join(lines)


def _beat_duration_with_buffer(beat: Dict, fallback: float) -> float:
    """
    Return a padded duration for a beat, adding extra buffer to avoid early cutoffs.
    """
    has_padded = "padded_duration_seconds" in beat and beat.get("padded_duration_seconds") is not None
    raw = beat.get("padded_duration_seconds")
    if raw is None:
        raw = beat.get("duration_seconds")
    try:
        base = float(raw)
    except Exception:
        base = float(fallback)
    if not has_padded:
        base = base + max(1.0, base * 0.25)
    return float(_quantize_sora_duration(base))


def _total_duration_with_buffer(beats: List[Dict], fallback_per_beat: float) -> float:
    if not beats:
        return float(fallback_per_beat)
    total = 0.0
    for beat in beats:
        total += _beat_duration_with_buffer(beat, fallback_per_beat)
    total = max(total, float(len(beats) * fallback_per_beat))
    return float(_quantize_sora_duration(total))


def _quantize_sora_duration(duration: float) -> float:
    """
    Sora currently accepts only discrete durations (commonly 4, 8, 12s). Snap to nearest.
    """
    if duration <= 6:
        return 4
    if duration <= 10:
        return 8
    return 12


def _normalize_resolution(resolution: Union[str, Tuple[int, int], List[int], None]) -> Optional[str]:
    if resolution is None:
        return None
    if isinstance(resolution, str):
        return resolution
    try:
        w, h = resolution
        return f"{int(w)}x{int(h)}"
    except Exception:
        return None


_SAFE_REPLACEMENTS = {
    "victim": "friend",
    "prank": "harmless joke",
    "conspiratorial": "playful",
    "threat": "teasing",
    "attack": "playful move",
    "injury": "laugh",
    "danger": "safe fun",
}


def _safe_text(text: str) -> str:
    t = text
    for bad, good in _SAFE_REPLACEMENTS.items():
        t = t.replace(bad, good).replace(bad.capitalize(), good.capitalize())
    return t


def _cartoonize_style(style: str) -> str:
    """
    Bias style toward a safe, non-realistic, animated look to reduce moderation risk.
    """
    if not style:
        style = "friendly 2D animation, cel-shaded, cartoon"
    markers = ["cartoon", "animation", "anime", "comic", "cel"]
    if any(m.lower() in style.lower() for m in markers):
        return style
    return f"{style}; stylized cartoon, friendly 2D animation, non-realistic"


def _fetch_sora_download_url(job_id: str, headers: dict) -> Optional[str]:
    files_url = f"https://api.openai.com/v1/videos/{job_id}/files"
    resp = requests.get(files_url, headers=headers, timeout=30)
    if resp.status_code >= 300:
        return None
    data = resp.json()
    items = data.get("data") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        mime = item.get("mime_type", "")
        name = item.get("filename", "")
        if "video" in mime or name.endswith(".mp4"):
            return item.get("download_url") or item.get("url")
    return None


def _fetch_sora_file_content(job_id: str, headers: dict) -> Optional[bytes]:
    files_url = f"https://api.openai.com/v1/videos/{job_id}/files"
    resp = requests.get(files_url, headers=headers, timeout=30)
    if resp.status_code >= 300:
        return None
    data = resp.json()
    items = data.get("data") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        mime = item.get("mime_type", "")
        name = item.get("filename", "")
        if "video" in mime or name.endswith(".mp4"):
            file_id = item.get("id")
            if not file_id:
                continue
            content_url = f"https://api.openai.com/v1/videos/{job_id}/files/{file_id}/content"
            content = requests.get(content_url, headers=headers, timeout=60)
            if content.status_code == 200:
                return content.content
    return None


def _fetch_sora_job_content(job_id: str, headers: dict) -> Optional[bytes]:
    content_url = f"https://api.openai.com/v1/videos/{job_id}/content"
    resp = requests.get(content_url, headers=headers, timeout=60)
    if resp.status_code == 200:
        return resp.content
    return None


def _poll_sora_job(job_id: str, headers: dict, base_url: str) -> Union[str, bytes]:
    status_url = f"{base_url}/{job_id}"
    for _ in range(180):  # up to ~6 minutes
        poll = requests.get(status_url, headers=headers, timeout=30)
        if poll.status_code >= 300:
            raise RuntimeError(f"Sora poll failed ({poll.status_code}): {poll.text[:500]}")
        pdata = poll.json()
        state = pdata.get("status") or pdata.get("state")
        if state in {"succeeded", "completed", "ready"}:
            video = pdata.get("video") or pdata.get("result") or {}
            if isinstance(video, dict):
                video_url = video.get("url") or video.get("download_url")
                if video_url:
                    return video_url
            items = pdata.get("data") or []
            if items and isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        candidate = item.get("url") or item.get("download_url")
                        if candidate:
                            return candidate
            file_url = _fetch_sora_download_url(job_id, headers)
            if file_url:
                return file_url
            file_bytes = _fetch_sora_file_content(job_id, headers)
            if file_bytes:
                return file_bytes
            direct_bytes = _fetch_sora_job_content(job_id, headers)
            if direct_bytes:
                return direct_bytes
            raise RuntimeError(f"Sora completed but no video url: {pdata}")
        if state in {"failed", "error"}:
            raise RuntimeError(f"Sora job failed: {pdata}")
        time.sleep(2)
    raise RuntimeError("Sora job timed out waiting for completion.")


def _build_reference_payload(image_url: Optional[str], image_bytes: Optional[bytes]) -> Dict[str, str]:
    """
    Prepare reference image fields for the Sora payload.
    """
    payload: Dict[str, str] = {}
    if image_url:
        payload["image_url"] = image_url
    if image_bytes:
        payload["image"] = _encode_image_to_data_url(image_bytes)
    return payload


def _encode_image_to_data_url(image_bytes: Optional[bytes]) -> Optional[str]:
    if not image_bytes:
        return None
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _resize_reference_image(image_bytes: Optional[bytes], resolution: Optional[str]) -> Optional[bytes]:
    """
    Resize the reference image to match the requested video resolution to avoid inpaint size errors.
    Keeps aspect ratio with letterboxing.
    """
    if not image_bytes or not resolution or not Image:
        return image_bytes
    try:
        width, height = [int(x) for x in str(resolution).lower().replace("x", " ").split() if x.isdigit()][:2]
        if not width or not height:
            return image_bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_width = width
            new_height = int(width / img_ratio)
        else:
            new_height = height
            new_width = int(height * img_ratio)
        resized = img.resize((max(1, new_width), max(1, new_height)), Image.LANCZOS)
        canvas = Image.new("RGB", (width, height), color=(0, 0, 0))
        offset = ((width - resized.width) // 2, (height - resized.height) // 2)
        canvas.paste(resized, offset)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return image_bytes


def _extract_last_frame_as_png(video_path: Path) -> Optional[bytes]:
    """
    Grab the last frame from a video file and return PNG bytes for continuity seeding.
    """
    if not VideoFileClip or not Image:
        return None
    try:
        with VideoFileClip(str(video_path)) as clip:
            duration = getattr(clip, "duration", 0) or 0
            fps = getattr(clip, "fps", 24) or 24
            timestamp = max(0, duration - (1.0 / max(fps, 1)))
            frame = clip.get_frame(timestamp if duration > 0 else 0)
            image = Image.fromarray(frame)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception:
        return None


def _overlay_music_to_video(
    video_path: Path,
    music_path: Path,
    trim_audio: bool = True,
    expected_duration: Optional[float] = None,
    output_path: Optional[Path] = None,
) -> None:
    """
    Overlay music onto video, trimming audio to video duration.
    """
    err = _ensure_video_deps()
    if err:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, and ffmpeg are available. "
            f"Root cause: {err}"
        ) from err
    clips = []
    video = None
    audio = None
    mixed_audio = None
    output_path = output_path or video_path
    temp_out = output_path.with_suffix(".tmp.mp4")
    try:
        video = VideoFileClip(str(video_path))
        video_duration = getattr(video, "duration", 0) or 0
        audio = AudioFileClip(str(music_path))
        audio_duration = getattr(audio, "duration", video_duration) or video_duration
        target_duration = max(video_duration, expected_duration or 0, 0.1)
        trimmed_duration = target_duration if trim_audio else audio_duration
        if audio_loop and (audio_duration < target_duration):
            try:
                audio = audio_loop(audio, duration=target_duration)
            except Exception:
                pass
        # Force music to exact target duration for continuity
        if hasattr(audio, "with_duration"):
            audio = audio.with_duration(trimmed_duration)
        else:
            audio = audio.set_duration(trimmed_duration)
        # Lower background music to ~25% volume for headroom
        try:
            audio = audio.volumex(0.25)
        except Exception:
            try:
                audio = audio * 0.25
            except Exception:
                pass
        final = video.with_audio(audio)
        final.write_videofile(
            str(temp_out),
            codec="libx264",
            audio_codec="aac",
        )
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
        temp_out.replace(output_path)
    finally:
        for c in (audio, video, mixed_audio):
            try:
                if c:
                    c.close()
            except Exception:
                pass
        if temp_out.exists() and not output_path.exists():
            try:
                temp_out.unlink()
            except Exception:
                pass

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
    title = f"{scene.get('scene_title', 'Scene')} - Beat {index}/{total}"

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
