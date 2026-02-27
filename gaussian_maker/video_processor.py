"""Extract frames from video files using FFmpeg.

Supports iPhone .MOV, Meta glasses .mp4, and any FFmpeg-readable format.
"""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: float = 2.0,
    max_frames: int = 300,
    fmt: str = "jpg",
    quality: int = 95,
) -> list[Path]:
    """Extract frames from a video at a given FPS.

    Args:
        video_path: Path to the input video file.
        output_dir: Directory to write extracted frames into.
        fps: Frames per second to extract (2-5 recommended for static scenes).
        max_frames: Cap total frames to avoid VRAM overflow.
        fmt: Output image format ('jpg' or 'png').
        quality: JPEG quality (1-95). Ignored for PNG.

    Returns:
        Sorted list of extracted frame paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(output_dir / f"%04d.{fmt}")

    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # overwrite existing
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-vframes", str(max_frames),
    ]

    if fmt == "jpg":
        cmd += ["-qscale:v", "1", "-qmin", "1", f"-q:v", str(max(1, int((100 - quality) / 5)))]
    else:
        cmd += ["-compression_level", "1"]

    cmd.append(pattern)

    console.print(f"[bold cyan]Extracting frames[/] from [yellow]{video_path.name}[/] at {fps} FPS...")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        progress.add_task("Running FFmpeg...", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        console.print(f"[red]FFmpeg error:[/]\n{result.stderr}")
        raise RuntimeError(f"Frame extraction failed: {result.stderr[-500:]}")

    frames = sorted(output_dir.glob(f"*.{fmt}"))
    console.print(f"[green]✓[/] Extracted {len(frames)} frames to [dim]{output_dir}[/]")
    return frames


def probe_video(video_path: Path) -> dict:
    """Return basic metadata about a video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}

    import json
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            fps_str = stream.get("r_frame_rate", "0/1")
            num, den = fps_str.split("/")
            return {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": round(int(num) / int(den), 2) if int(den) else 0,
                "codec": stream.get("codec_name"),
                "duration_s": float(stream.get("duration", 0)),
            }
    return {}
