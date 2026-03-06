from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple


_ENCODER_CACHE: Optional[List[Tuple[str, str]]] = None


def detect_gpu_encoders() -> List[Tuple[str, str]]:
    """
    Return encoders: list of (name, description) for hardware encoders.
    """
    global _ENCODER_CACHE

    if _ENCODER_CACHE is not None:
        return _ENCODER_CACHE

    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout or ""
    except (FileNotFoundError, OSError):
        output = ""
    gpu_keywords = ["_nvenc", "_qsv", "_amf", "_vaapi"]
    encoders: List[Tuple[str, str]] = []

    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[1]
        if any(name.endswith(kw) for kw in gpu_keywords):
            desc = " ".join(parts[2:]) if len(parts) > 2 else name
            encoders.append((name, desc))

    _ENCODER_CACHE = encoders
    return encoders


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    is_video: bool,
    is_convert: bool,
    gpu_choice: str,
    available_gpu_encoders: Iterable[str],
    target_size_mb: Optional[float] = None,
    target_resolution: Optional[str] = None,
) -> Sequence[str]:
    if is_video:
        return build_video_command(
            input_path=input_path,
            output_path=output_path,
            is_convert=is_convert,
            gpu_choice=gpu_choice,
            available_gpu_encoders=set(available_gpu_encoders),
            target_size_mb=target_size_mb,
            target_resolution=target_resolution,
        )
    return build_image_command(
        input_path=input_path,
        output_path=output_path,
        is_convert=is_convert,
    )


def build_video_command(
    input_path: Path,
    output_path: Path,
    is_convert: bool,
    gpu_choice: str,
    available_gpu_encoders: Set[str],
    target_size_mb: Optional[float] = None,
    target_resolution: Optional[str] = None,
) -> Sequence[str]:
    cmd: List[str] = ["ffmpeg", "-y", "-hide_banner", "-i", str(input_path)]

    video_bitrate = "2500k" if is_convert else "1800k"
    audio_bitrate = "128k"

    if target_size_mb is not None and target_size_mb > 0:
        duration = get_video_duration_seconds(input_path)
        if duration and duration > 0:
            total_bits = target_size_mb * 1024 * 1024 * 8
            total_kbits = total_bits / 1000.0
            target_total_kbps = total_kbits / duration
            audio_kbps = 128.0
            video_kbps = max(300.0, target_total_kbps - audio_kbps)
            video_bitrate = f"{int(video_kbps)}k"

    vcodec = "libx264"

    if gpu_choice and gpu_choice not in ("auto", "cpu_only"):
        vcodec = gpu_choice

    if gpu_choice == "auto":
        preferred_gpu_codecs = ["h264_nvenc", "hevc_nvenc", "h264_qsv", "h264_amf"]
        for codec in preferred_gpu_codecs:
            if codec in available_gpu_encoders:
                vcodec = codec
                break

    if target_resolution:
        cmd += ["-vf", f"scale={target_resolution}:flags=lanczos"]

    cmd += ["-c:v", vcodec, "-b:v", video_bitrate, "-preset", "medium"]
    cmd += ["-c:a", "aac", "-b:a", audio_bitrate]
    cmd.append(str(output_path))
    return cmd


def get_video_duration_seconds(path: Path) -> Optional[float]:
    """
    Ask ffprobe for the duration in seconds. Returns None on failure.
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        return None

    output = (proc.stdout or "").strip()
    try:
        return float(output)
    except ValueError:
        return None


def build_image_command(
    input_path: Path,
    output_path: Path,
    is_convert: bool,
) -> Sequence[str]:
    cmd: List[str] = ["ffmpeg", "-y", "-hide_banner", "-i", str(input_path)]

    ext = output_path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        quality = "2" if is_convert else "4"
        cmd += ["-q:v", quality]
    elif ext == ".png":
        level = "3" if is_convert else "5"
        cmd += ["-compression_level", level]

    cmd.append(str(output_path))
    return cmd

