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

    _VIDEO_DEPS_ERROR = None
except Exception as exc:  # pragma: no cover - environment-specific
    np = None
    Image = ImageDraw = ImageFont = None
    AudioFileClip = ImageClip = VideoFileClip = concatenate_videoclips = CompositeAudioClip = None
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
) -> Path:
    """
    Generate a video via OpenAI's Sora (or compatible video) endpoint.
    This uses a single prompt distilled from the structured scene and beats.
    """
    if _VIDEO_DEPS_ERROR:
        raise ImportError(
            "Video dependencies not installed. Please ensure `moviepy`, `pillow`, and ffmpeg are available."
        ) from _VIDEO_DEPS_ERROR

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    beats = scene.get("beats") or []

    # Optional: derive a visual description from a reference image.
    # Only attempt vision if we have a real HTTP(S) URL; skip data URLs / raw bytes.
    image_desc = None
    if image_url and image_url.startswith(("http://", "https://")):
        image_desc = describe_image_with_vision(image_url)
    # If we only have image_bytes (no hosted URL), we currently skip vision
    # and just rely on the text prompt. This avoids invalid_image_url errors.

    # If we have beats, render one ~4s clip per beat and stitch.
    if beats:
        segments = [[b] for b in beats]
        segment_dir = output_dir / "sora_segments"
        segment_dir.mkdir(parents=True, exist_ok=True)
        clip_paths: List[Path] = []
        try:
            for idx, beat_slice in enumerate(segments, start=1):
                seg_prompt = _build_sora_prompt_segment(scene, beat_slice, image_desc)
                video_result = call_sora_video(
                    prompt=seg_prompt,
                    duration=4,  # aim for ~4s per segment
                    resolution=None,
                    model_id=model_id,
                )
                seg_path = segment_dir / f"segment_{idx:02}.mp4"
                _store_video_result(video_result, seg_path)
                clip_paths.append(seg_path)

            final_path = output_dir / "generated_video.mp4"
            _concat_and_optionally_add_audio(
                clip_paths=clip_paths,
                final_path=final_path,
                music_path=music_path,
                trim_audio=True,
            )
            return final_path
        finally:
            for p in segment_dir.glob("segment_*.mp4"):
                try:
                    p.unlink()
                except Exception:
                    pass
    # Fallback: single call
    prompt = _build_sora_prompt(scene, image_desc)
    target_duration = max(1, len(beats) * seconds_per_beat)
    target_duration = min(target_duration, 12)
    video_result = call_sora_video(
        prompt=prompt,
        duration=target_duration,
        resolution=None,
        model_id=model_id,
    )
    clip_path = output_dir / "generated_video.mp4"
    _store_video_result(video_result, clip_path)
    if music_path and Path(music_path).is_file():
        _overlay_music_to_video(clip_path, Path(music_path))
    return clip_path


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
) -> Union[str, bytes]:
    """
    Submit a video generation job to OpenAI (Sora-compatible) and return the video URL.
    This uses the experimental /v1/videos endpoint shape.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    model = model_id or os.getenv("SORA_MODEL_ID") or "sora-2-pro"
    url = "https://api.openai.com/v1/videos"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "prompt": prompt,
    }
    if duration is not None:
        payload["duration"] = duration
    if resolution:
        payload["resolution"] = resolution

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 300:
        # Fallback: retry without duration/resolution if server rejects those fields
        text = resp.text.lower()
        if duration is not None and ("duration" in text or "unknown_parameter" in text or "invalid_parameter" in text):
            payload.pop("duration", None)
            payload.pop("resolution", None)
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 300:
            raise RuntimeError(f"Sora submit failed ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"Sora response missing job id: {data}")

    # Poll for completion
    status_url = f"{url}/{job_id}"
    for _ in range(120):  # up to ~2 minutes
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
            # Try data array
            items = pdata.get("data") or []
            if items and isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        candidate = item.get("url") or item.get("download_url")
                        if candidate:
                            return candidate
            # Try files endpoint
            file_url = _fetch_sora_download_url(job_id, headers)
            if file_url:
                return file_url
            file_bytes = _fetch_sora_file_content(job_id, headers)
            if file_bytes:
                return file_bytes
            # Final fallback: try direct content endpoint
            direct_bytes = _fetch_sora_job_content(job_id, headers)
            if direct_bytes:
                return direct_bytes
            raise RuntimeError(f"Sora completed but no video url: {pdata}")
        if state in {"failed", "error"}:
            raise RuntimeError(f"Sora job failed: {pdata}")
        time.sleep(2)

    raise RuntimeError("Sora job timed out waiting for completion.")


def _build_sora_prompt(scene: Dict, image_description: Optional[str] = None) -> str:
    beats = scene.get("beats", [])
    beat_lines = "; ".join(b.get("description", "") for b in beats)
    art_style = scene.get("art_style", "")
    background = scene.get("background", {})
    setting = background.get("location", background.get("description", ""))
    background_desc = background.get("description", "")
    characters = scene.get("characters", []) or []
    character_lines = "; ".join(
        f"{c.get('name','Character')}: {c.get('description','')}" for c in characters
    )
    image_line = f"Visual reference: {image_description}. " if image_description else ""
    return (
        f"Create a coherent cinematic sequence in {art_style} style. "
        f"Setting: {setting}. Environment detail: {background_desc}. "
        f"Characters: {character_lines}. "
        f"Story beats: {beat_lines}. "
        f"{image_line}"
        f"Include natural spoken dialogue and ambient factory sounds; avoid on-screen text or subtitles."
    )


def _build_sora_prompt_segment(
    scene: Dict, beats_slice: List[Dict], image_description: Optional[str] = None
) -> str:
    art_style = scene.get("art_style", "")
    background = scene.get("background", {})
    setting = background.get("location", background.get("description", ""))
    background_desc = background.get("description", "")
    characters = scene.get("characters", []) or []
    character_lines = "; ".join(
        f"{c.get('name','Character')}: {c.get('description','')}" for c in characters
    )
    beat_lines = "; ".join(b.get("description", "") for b in beats_slice)
    image_line = f"Visual reference: {image_description}. " if image_description else ""
    return (
        f"Create a coherent cinematic sequence in {art_style} style. "
        f"Setting: {setting}. Environment detail: {background_desc}. "
        f"Characters: {character_lines}. "
        f"Story beats: {beat_lines}. "
        f"{image_line}"
        f"Include natural spoken dialogue and ambient factory sounds; avoid on-screen text or subtitles."
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
    music_path: Optional[Path],
    trim_audio: bool = False,
) -> None:
    clips = []
    audio_clip = None
    mixed_audio = None
    try:
        for p in clip_paths:
            clips.append(VideoFileClip(str(p)))
        video = concatenate_videoclips(clips, method="compose")
        concat_duration = sum((getattr(c, "duration", 0) or 0) for c in clips)
        target_duration = max(concat_duration, getattr(video, "duration", concat_duration) or concat_duration)
        if music_path and Path(music_path).is_file():
            audio_clip = AudioFileClip(str(music_path))
            if trim_audio:
                duration = min(getattr(audio_clip, "duration", target_duration) or target_duration, target_duration)
                if hasattr(audio_clip, "with_duration"):
                    audio_clip = audio_clip.with_duration(duration)
                else:
                    audio_clip = audio_clip.set_duration(duration)
            # Lower background music to ~20% volume
            try:
                audio_clip = audio_clip.volumex(0.2)
            except Exception:
                try:
                    audio_clip = audio_clip * 0.2
                except Exception:
                    pass
            base_audio = getattr(video, "audio", None)
            if base_audio and CompositeAudioClip:
                mixed_audio = CompositeAudioClip([base_audio, audio_clip])
                video = video.with_audio(mixed_audio)
            else:
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
        for c in (audio_clip, mixed_audio):
            try:
                if c:
                    c.close()
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


def _overlay_music_to_video(video_path: Path, music_path: Path) -> None:
    """
    Overlay music onto video, trimming audio to video duration.
    """
    clips = []
    video = None
    audio = None
    mixed_audio = None
    temp_out = video_path.with_suffix(".tmp.mp4")
    try:
        video = VideoFileClip(str(video_path))
        video_duration = getattr(video, "duration", 0) or 0
        audio = AudioFileClip(str(music_path))
        trimmed_duration = min(getattr(audio, "duration", video_duration) or video_duration, video_duration)
        # MoviePy 2.x uses with_duration; fall back to set_duration if needed
        if hasattr(audio, "with_duration"):
            audio = audio.with_duration(trimmed_duration)
        else:
            audio = audio.set_duration(trimmed_duration)
        # Lower background music to ~20% volume
        try:
            audio = audio.volumex(0.2)
        except Exception:
            try:
                audio = audio * 0.2
            except Exception:
                pass
        base_audio = getattr(video, "audio", None)
        if base_audio and CompositeAudioClip:
            mixed_audio = CompositeAudioClip([base_audio, audio])
            final = video.with_audio(mixed_audio)
        else:
            final = video.with_audio(audio)
        final.write_videofile(
            str(temp_out),
            codec="libx264",
            audio_codec="aac",
        )
        video_path.unlink(missing_ok=True)
        temp_out.replace(video_path)
    finally:
        for c in (audio, video, mixed_audio):
            try:
                if c:
                    c.close()
            except Exception:
                pass
        if temp_out.exists() and not video_path.exists():
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

