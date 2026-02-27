"""CLI entry point for Gaussian Maker.

Usage:
    gm run video.mp4
    gm run video.mp4 --output ./my_output --trainer nerfstudio --fps 3
    gm info video.mp4
    gm check
"""

from pathlib import Path

import click
from rich.console import Console

from .utils.config import PipelineConfig
from .utils.device import check_ffmpeg, check_colmap, gpu_info
from .video_processor import probe_video

console = Console()


@click.group()
@click.version_option(package_name="gaussian-maker")
def main():
    """Gaussian Maker — convert video into 3D Gaussian splats."""


@main.command()
@click.argument("video", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", default="outputs", show_default=True,
              type=click.Path(path_type=Path), help="Output directory.")
@click.option("--trainer", "-t",
              type=click.Choice(["nerfstudio", "opensplat"]),
              default="nerfstudio", show_default=True,
              help="Training backend.")
@click.option("--sfm-tool", "-s",
              type=click.Choice(["colmap", "glomap", "skip"]),
              default="colmap", show_default=True,
              help="Structure-from-Motion tool (ignored when trainer=nerfstudio).")
@click.option("--fps", "-f", default=2.0, show_default=True,
              help="Frames per second to extract from video.")
@click.option("--max-frames", default=300, show_default=True,
              help="Maximum number of frames to extract.")
@click.option("--iterations", "-i", default=30_000, show_default=True,
              help="Training iterations.")
@click.option("--format", "-F", "export_formats",
              multiple=True, default=["ply"], show_default=True,
              type=click.Choice(["ply", "splat", "ksplat"]),
              help="Output format(s). Pass multiple times for multiple formats.")
@click.option("--quality", "-q",
              type=click.Choice(["low", "medium", "high", "extreme"]),
              default="medium", show_default=True,
              help="COLMAP reconstruction quality.")
def run(video, output, trainer, sfm_tool, fps, max_frames, iterations, export_formats, quality):
    """Convert a VIDEO file into a 3D Gaussian splat.

    \b
    Examples:
        gm run iphone_capture.MOV
        gm run meta_glasses.mp4 --trainer nerfstudio --fps 3
        gm run video.mp4 --format ply --format splat --iterations 10000
    """
    from .pipeline import run_pipeline

    config = PipelineConfig(
        video_path=video,
        output_dir=output,
        fps=fps,
        max_frames=max_frames,
        sfm_tool=sfm_tool,
        colmap_quality=quality,
        trainer=trainer,
        iterations=iterations,
        export_formats=list(export_formats),
    )

    try:
        run_pipeline(config)
    except (EnvironmentError, RuntimeError, FileNotFoundError) as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise SystemExit(1)


@main.command()
@click.argument("video", type=click.Path(exists=True, path_type=Path))
def info(video):
    """Show metadata about a VIDEO file."""
    meta = probe_video(Path(video))
    if not meta:
        console.print("[red]Could not read video metadata. Is ffprobe installed?[/]")
        return
    console.print(f"[bold]{video}[/]")
    for k, v in meta.items():
        console.print(f"  {k}: {v}")


@main.command()
def check():
    """Check that required dependencies are installed."""
    gpu = gpu_info()

    rows = [
        ("ffmpeg", "✓" if check_ffmpeg() else "✗", "Required for frame extraction"),
        ("colmap", "✓" if check_colmap() else "✗ (optional)", "SfM — optional if using nerfstudio"),
        ("GPU", gpu["device"].upper(), f"{gpu['name']} — {gpu['vram_gb']} GB VRAM"),
    ]

    # Optional pip packages
    for pkg in ["torch", "gsplat", "nerfstudio", "open3d"]:
        try:
            __import__(pkg)
            rows.append((pkg, "✓", ""))
        except ImportError:
            rows.append((pkg, "✗ (optional)", f"pip install {pkg}"))

    for name, status, note in rows:
        color = "green" if status.startswith("✓") else "yellow" if "optional" in status else "red"
        console.print(f"  [{color}]{status}[/]  {name:<16} [dim]{note}[/]")


if __name__ == "__main__":
    main()
