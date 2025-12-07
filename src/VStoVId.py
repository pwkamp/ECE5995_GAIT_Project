#!/usr/bin/env python3
"""
Generate a video using fal.ai from a text/JSON script file and a directory of images.

Features:
- Supports .txt and .json script files.
- Uploads images to fal.ai, calls an image-to-video model per scene.
- Downloads each generated clip.
- Optionally concatenates all clips into a single video (moviepy).

Usage examples:

# JSON script (recommended)
python fal_video_from_dir.py \
    --script script.json \
    --images-dir ./images \
    --output-dir ./clips \
    --final-video ./output.mp4 \
    --fal-key YOUR_FAL_KEY

# Plain text script: one prompt per line, matched to images by filename order
python fal_video_from_dir.py \
    --script script.txt \
    --images-dir ./images \
    --output-dir ./clips \
    --final-video ./output.mp4
"""

import argparse
import json
import os
import sys
from pathlib import Path
import urllib.request

import tomllib

import fal_client  # pip install fal-client
from moviepy.editor import VideoFileClip, concatenate_videoclips  # pip install moviepy

# Default fal.ai image-to-video model (MiniMax Video 01) :contentReference[oaicite:1]{index=1}
DEFAULT_MODEL_ID = "fal-ai/minimax/video-01/image-to-video"

# Allowed image extensions
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")


def debug(msg: str) -> None:
    print(f"[fal-video] {msg}", flush=True)


def load_fal_key_from_secrets() -> str | None:
    """
    Try to load FAL_KEY from a .streamlit/secrets.toml file.
    Supports top-level FAL_KEY or a [fal] section with FAL_KEY/key.
    """
    repo_root_candidate = Path(__file__).resolve().parent.parent
    candidate_paths = [
        Path.cwd() / ".streamlit" / "secrets.toml",
        repo_root_candidate / ".streamlit" / "secrets.toml",
    ]

    for path in candidate_paths:
        if not path.is_file():
            continue
        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except Exception as exc:
            debug(f"Could not read secrets from {path}: {exc}")
            continue

        if not isinstance(data, dict):
            continue

        # Top-level FAL_KEY
        key = data.get("FAL_KEY")

        # Or nested under [fal]
        if not key:
            fal_section = data.get("fal")
            if isinstance(fal_section, dict):
                key = fal_section.get("FAL_KEY") or fal_section.get("key")

        if key:
            debug(f"Loaded FAL_KEY from {path}")
            return str(key)

    return None


def resolve_fal_key(provided_key: str | None) -> str:
    """
    Resolve fal.ai API key from (in order):
    1) Explicit CLI argument
    2) FAL_KEY environment variable
    3) .streamlit/secrets.toml (top-level FAL_KEY or [fal].FAL_KEY/key)
    """
    if provided_key:
        return provided_key

    env_key = os.getenv("FAL_KEY")
    if env_key:
        return env_key

    secrets_key = load_fal_key_from_secrets()
    if secrets_key:
        return secrets_key

    raise RuntimeError(
        "fal.ai API key not provided. Use --fal-key, set FAL_KEY env var, "
        "or add FAL_KEY to .streamlit/secrets.toml"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a video using fal.ai from a script file and image directory."
    )
    parser.add_argument(
        "--script",
        required=True,
        help="Path to script file (.json or .txt).",
    )
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directory containing input images.",
    )
    parser.add_argument(
        "--output-dir",
        default="./fal_clips",
        help="Directory to store generated clip files (default: ./fal_clips).",
    )
    parser.add_argument(
        "--final-video",
        default="./final_output.mp4",
        help="Path for concatenated final video (default: ./final_output.mp4).",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"fal.ai model ID to use (default: {DEFAULT_MODEL_ID}).",
    )
    parser.add_argument(
        "--fal-key",
        default=None,
        help="fal.ai API key (if not set, will use FAL_KEY env variable).",
    )
    parser.add_argument(
        "--no-concat",
        action="store_true",
        help="If set, do NOT concatenate clips into a final video.",
    )
    return parser.parse_args()


def list_images(images_dir: str) -> list[Path]:
    p = Path(images_dir)
    if not p.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    files = sorted(
        f for f in p.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not files:
        raise RuntimeError(f"No image files found in {images_dir}")
    return files


def load_scenes_from_json(script_path: Path, images_dir: Path) -> list[dict]:
    """
    JSON formats supported:

    1) Array of scenes:
       [
         {"image": "frame1.png", "prompt": "Scene 1 prompt", "duration": 6},
         {"image": "frame2.png", "prompt": "Scene 2 prompt"}
       ]

    2) Object with "scenes" field:
       { "scenes": [ ...same as above... ] }
    """
    with script_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "scenes" in data:
        scenes = data["scenes"]
    elif isinstance(data, list):
        scenes = data
    else:
        raise ValueError(
            "JSON script must be either an array of scenes or an object with a 'scenes' array."
        )

    result = []
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene #{idx} is not an object: {scene!r}")
        image_name = scene.get("image")
        if not image_name:
            raise ValueError(f"Scene #{idx} missing 'image' field")

        image_path = Path(image_name)
        if not image_path.is_absolute():
            image_path = images_dir / image_name
        if not image_path.exists():
            raise FileNotFoundError(
                f"Scene #{idx} image not found: {image_path}"
            )

        prompt = scene.get("prompt", "").strip()
        duration = scene.get("duration")  # optional, not all models use it

        result.append(
            {
                "image_path": image_path,
                "prompt": prompt,
                "duration": duration,
            }
        )

    return result


def load_scenes_from_text(script_path: Path, images_dir: Path) -> list[dict]:
    """
    Text format:

    - Each non-empty line is a prompt.
    - Images are sorted by filename.
    - If there's ONE prompt line, it's reused for all images.
    - If prompt count == image count, lines map 1:1 to images.
    """
    with script_path.open("r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if not lines:
        raise ValueError("Text script has no non-empty lines (no prompts).")

    images = list_images(str(images_dir))

    if len(lines) == 1:
        prompts = [lines[0]] * len(images)
    elif len(lines) == len(images):
        prompts = lines
    else:
        raise ValueError(
            f"Text script line count ({len(lines)}) must be 1 or equal to number of images ({len(images)})."
        )

    scenes = []
    for img_path, prompt in zip(images, prompts):
        scenes.append(
            {
                "image_path": img_path,
                "prompt": prompt,
                "duration": None,
            }
        )
    return scenes


def load_scenes(script_path: str, images_dir: str) -> list[dict]:
    script_p = Path(script_path)
    images_p = Path(images_dir)
    if not script_p.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    ext = script_p.suffix.lower()
    if ext == ".json":
        return load_scenes_from_json(script_p, images_p)
    else:
        # treat everything else (.txt, .md, etc.) as a plain text script
        return load_scenes_from_text(script_p, images_p)


def download_file(url: str, dest_path: Path) -> None:
    debug(f"Downloading video from {url}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, dest_path.open("wb") as out_file:
        out_file.write(response.read())
    debug(f"Saved video to {dest_path}")


def extract_video_url(result: dict) -> str:
    """
    fal_client responses for video models typically include either:
      - result["video"]["url"], or
      - result["data"]["video"]["url"]
    We try both. :contentReference[oaicite:2]{index=2}
    """
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected response type: {type(result)}")

    video_url = None

    # Common pattern: result["video"]["url"]
    video_obj = result.get("video")
    if isinstance(video_obj, dict):
        video_url = video_obj.get("url")

    # Alternative: result["data"]["video"]["url"]
    if not video_url:
        data = result.get("data")
        if isinstance(data, dict):
            video_obj = data.get("video")
            if isinstance(video_obj, dict):
                video_url = video_obj.get("url")

    if not video_url:
        raise RuntimeError(
            f"Could not find video URL in fal.ai response: {result.keys()}"
        )

    return video_url


def generate_clip_for_scene(
    scene: dict,
    model_id: str,
    output_dir: Path,
) -> Path:
    image_path: Path = scene["image_path"]
    prompt: str = scene.get("prompt", "")
    duration = scene.get("duration")

    debug(f"Uploading image: {image_path}")
    image_url = fal_client.upload_file(str(image_path))  # :contentReference[oaicite:3]{index=3}

    arguments = {
        "image_url": image_url,
        "prompt": prompt,
    }
    # Some models accept duration (e.g., seconds); if present in JSON we pass it through.
    if duration is not None:
        arguments["duration"] = duration

    debug(f"Requesting video generation via {model_id}")
    result = fal_client.subscribe(
        model_id,
        arguments=arguments,
        with_logs=True,  # prints server logs to stdout as they stream
    )

    video_url = extract_video_url(result)

    clip_name = f"{image_path.stem}.mp4"
    clip_path = output_dir / clip_name
    download_file(video_url, clip_path)
    return clip_path


def concat_videos(video_paths: list[Path], final_path: Path) -> None:
    debug("Concatenating clips into final video...")
    clips = []
    try:
        for p in video_paths:
            clips.append(VideoFileClip(str(p)))
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
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
    debug(f"Final video written to {final_path}")


def main() -> None:
    args = parse_args()

    try:
        fal_key = resolve_fal_key(args.fal_key)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Configure fal_client global API key :contentReference[oaicite:4]{index=4}
    fal_client.api_key = fal_key

    # Prepare dirs
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    debug("Loading scenes from script...")
    scenes = load_scenes(args.script, args.images_dir)
    debug(f"Loaded {len(scenes)} scene(s).")

    clip_paths: list[Path] = []

    for idx, scene in enumerate(scenes, start=1):
        debug(f"--- Scene {idx}/{len(scenes)} ---")
        clip_path = generate_clip_for_scene(
            scene=scene,
            model_id=args.model_id,
            output_dir=output_dir,
        )
        clip_paths.append(clip_path)

    if not args.no_concat:
        final_path = Path(args.final_video)
        concat_videos(clip_paths, final_path)
    else:
        debug("Skipping concatenation (--no-concat set).")

    debug("Done.")


if __name__ == "__main__":
    main()
