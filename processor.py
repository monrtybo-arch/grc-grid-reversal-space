from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from PIL import Image

GRID_COLS = 16
GRID_ROWS_SCRAMBLED = GRID_COLS + 2
GRID_ROWS_CLEAN = GRID_COLS

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".gif"}


def is_supported_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def is_image_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def is_video_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def build_output_name(filename: str, mode: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    tag = "scrambled" if mode == "encode" else "restored"
    return f"{stem}_{tag}{suffix}"


def process_file(input_path: str, output_path: str, mode: str) -> None:
    if mode not in {"encode", "decode"}:
        raise ValueError("mode must be encode or decode")

    ext = Path(input_path).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        if mode == "encode":
            encode_image_grid(input_path, output_path)
        else:
            decode_image_grid(input_path, output_path)
        return

    if ext in VIDEO_EXTENSIONS:
        if mode == "encode":
            encode_video(input_path, output_path)
        else:
            decode_video(input_path, output_path)
        return

    raise ValueError(f"unsupported file type: {ext}")


def encode_image_grid(input_path: str, output_path: str) -> None:
    img = Image.open(input_path).convert("RGB")
    in_w, in_h = img.size
    tile_w = in_w // GRID_COLS
    tile_h = in_h // GRID_ROWS_CLEAN
    clean_w = tile_w * GRID_COLS
    clean_h = tile_h * GRID_ROWS_CLEAN

    if (in_w, in_h) != (clean_w, clean_h):
        img = img.resize((clean_w, clean_h), Image.LANCZOS)

    out_h = tile_h * GRID_ROWS_SCRAMBLED
    scrambled = Image.new("RGB", (clean_w, out_h), color=(0, 0, 0))

    for row in range(GRID_ROWS_CLEAN):
        for col in range(GRID_COLS):
            scrambled_row = GRID_ROWS_SCRAMBLED - 1 - row
            scrambled_col = GRID_COLS - 1 - col

            left = col * tile_w
            upper = row * tile_h
            tile = img.crop((left, upper, left + tile_w, upper + tile_h))
            scrambled.paste(tile, (scrambled_col * tile_w, scrambled_row * tile_h))

    scrambled.save(output_path, quality=95)


def decode_image_grid(input_path: str, output_path: str) -> None:
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    tile_w = width // GRID_COLS
    tile_h = height // GRID_ROWS_SCRAMBLED

    restored = Image.new("RGB", (width, tile_h * GRID_COLS))
    for row in range(GRID_COLS):
        for col in range(GRID_COLS):
            reversed_row = GRID_ROWS_SCRAMBLED - 1 - row
            reversed_col = GRID_COLS - 1 - col
            left = reversed_col * tile_w
            upper = reversed_row * tile_h
            tile = img.crop((left, upper, left + tile_w, upper + tile_h))
            restored.paste(tile, (col * tile_w, row * tile_h))

    restored.save(output_path, quality=95)


def encode_video(input_path: str, output_path: str) -> None:
    ext = Path(input_path).suffix.lower()
    if ext == ".gif":
        _transform_gif(input_path, output_path, mode="encode")
        return
    _transform_video(input_path, output_path, mode="encode")


def decode_video(input_path: str, output_path: str) -> None:
    ext = Path(input_path).suffix.lower()
    if ext == ".gif":
        _transform_gif(input_path, output_path, mode="decode")
        return
    _transform_video(input_path, output_path, mode="decode")


def _transform_gif(input_path: str, output_path: str, mode: str) -> None:
    img = Image.open(input_path)
    frames = []

    try:
        while True:
            frame = img.copy().convert("RGB")
            frames.append(_transform_image_frame(frame, mode))
            img.seek(img.tell() + 1)
    except EOFError:
        pass

    if not frames:
        raise ValueError("gif contains no frames")

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=img.info.get("duration", 100),
        loop=0,
    )


def _transform_video(input_path: str, output_path: str, mode: str) -> None:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    in_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    in_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if mode == "encode":
        tile_w = in_w // GRID_COLS
        tile_h = in_h // GRID_ROWS_CLEAN
        out_w = tile_w * GRID_COLS
        out_h = tile_h * GRID_ROWS_SCRAMBLED
    else:
        tile_w = in_w // GRID_COLS
        tile_h = in_h // GRID_ROWS_SCRAMBLED
        out_w = in_w
        out_h = tile_h * GRID_COLS

    tmp_dir = Path(tempfile.mkdtemp(prefix="grc-web-"))
    tmp_video = tmp_dir / f"video{Path(output_path).suffix or '.mp4'}"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (out_w, out_h))

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)
            transformed = _transform_image_frame(pil_frame, mode)
            out_frame = cv2.cvtColor(np.array(transformed), cv2.COLOR_RGB2BGR)
            writer.write(out_frame)
    finally:
        cap.release()
        writer.release()

    try:
        original_clip = VideoFileClip(input_path)
        temp_clip = VideoFileClip(str(tmp_video))
        if original_clip.audio is not None:
            temp_clip = temp_clip.set_audio(original_clip.audio)
        temp_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
    except Exception:
        shutil.move(str(tmp_video), output_path)
    finally:
        try:
            original_clip.close()
        except Exception:
            pass
        try:
            temp_clip.close()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _transform_image_frame(frame: Image.Image, mode: str) -> Image.Image:
    frame = frame.convert("RGB")
    width, height = frame.size

    if mode == "encode":
        tile_w = width // GRID_COLS
        tile_h = height // GRID_ROWS_CLEAN
        clean_w = tile_w * GRID_COLS
        clean_h = tile_h * GRID_ROWS_CLEAN
        if (width, height) != (clean_w, clean_h):
            frame = frame.resize((clean_w, clean_h), Image.LANCZOS)
        out = Image.new("RGB", (clean_w, tile_h * GRID_ROWS_SCRAMBLED), color=(0, 0, 0))
        for row in range(GRID_ROWS_CLEAN):
            for col in range(GRID_COLS):
                sr = GRID_ROWS_SCRAMBLED - 1 - row
                sc = GRID_COLS - 1 - col
                left = col * tile_w
                upper = row * tile_h
                tile = frame.crop((left, upper, left + tile_w, upper + tile_h))
                out.paste(tile, (sc * tile_w, sr * tile_h))
        return out

    tile_w = width // GRID_COLS
    tile_h = height // GRID_ROWS_SCRAMBLED
    out = Image.new("RGB", (width, tile_h * GRID_COLS))
    for row in range(GRID_COLS):
        for col in range(GRID_COLS):
            rr = GRID_ROWS_SCRAMBLED - 1 - row
            rc = GRID_COLS - 1 - col
            left = rc * tile_w
            upper = rr * tile_h
            tile = frame.crop((left, upper, left + tile_w, upper + tile_h))
            out.paste(tile, (col * tile_w, row * tile_h))
    return out
