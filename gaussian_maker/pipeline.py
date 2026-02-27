"""End-to-end pipeline: video file → 3D Gaussian splat.

Orchestrates: video_processor → sfm → trainer → exporter
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .utils.config import PipelineConfig
from .utils.device import check_ffmpeg, check_colmap, gpu_info
from .video_processor import extract_frames, probe_video
from .sfm import run_sfm
from .trainer import train
from .exporter import run_exports

console = Console()


def run_pipeline(config: PipelineConfig) -> dict[str, Path]:
    """Run the full video-to-splat pipeline.

    Args:
        config: PipelineConfig instance with all settings.

    Returns:
        Dict of exported file paths keyed by format name.
    """
    _print_header(config)
    _check_dependencies(config)

    video_path = Path(config.video_path)
    output_dir = Path(config.output_dir)

    # ------------------------------------------------------------------
    # Nerfstudio all-in-one mode (handles frames + SfM internally)
    # ------------------------------------------------------------------
    if config.trainer == "nerfstudio":
        console.print(Panel(
            "[bold]Mode:[/] Nerfstudio all-in-one\n"
            "ns-process-data handles frame extraction + COLMAP automatically.",
            title="Pipeline Mode",
        ))
        train_output = train(
            trainer="nerfstudio",
            data_dir=config.sfm_dir(),
            output_dir=output_dir / "nerfstudio",
            iterations=config.iterations,
            video_path=video_path,
        )
        results = run_exports(
            source=train_output,
            output_dir=config.splat_dir(),
            formats=config.export_formats,
            is_nerfstudio_config=True,
        )

    # ------------------------------------------------------------------
    # Manual mode (step-by-step: extract → SfM → train → export)
    # ------------------------------------------------------------------
    else:
        # Step 1: Extract frames
        console.rule("[bold]Step 1 / 3 — Frame Extraction[/]")
        video_meta = probe_video(video_path)
        if video_meta:
            console.print(
                f"  Video: {video_meta.get('width')}x{video_meta.get('height')} "
                f"@ {video_meta.get('fps')} FPS, "
                f"{video_meta.get('codec')}, "
                f"{video_meta.get('duration_s', 0):.1f}s"
            )
        frames = extract_frames(
            video_path=video_path,
            output_dir=config.frames_dir(),
            fps=config.fps,
            max_frames=config.max_frames,
            fmt=config.frame_format,
            quality=config.frame_quality,
        )

        # Step 2: SfM
        console.rule("[bold]Step 2 / 3 — Structure-from-Motion[/]")
        sparse_dir = run_sfm(
            frames_dir=config.frames_dir(),
            output_dir=config.sfm_dir(),
            tool=config.sfm_tool,
            quality=config.colmap_quality,
        )

        # Step 3: Train
        console.rule("[bold]Step 3 / 3 — Gaussian Splatting Training[/]")
        train_output = train(
            trainer=config.trainer,
            data_dir=sparse_dir,
            output_dir=output_dir / config.trainer,
            iterations=config.iterations,
        )

        # Export
        console.rule("[bold]Exporting[/]")
        is_config = str(train_output).endswith(".yml")
        results = run_exports(
            source=train_output,
            output_dir=config.splat_dir(),
            formats=config.export_formats,
            is_nerfstudio_config=is_config,
        )

    _print_summary(results)
    return results


def _print_header(config: PipelineConfig) -> None:
    gpu = gpu_info()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[cyan]Video[/]", str(config.video_path))
    table.add_row("[cyan]Output[/]", str(config.output_dir))
    table.add_row("[cyan]Trainer[/]", config.trainer)
    table.add_row("[cyan]SfM tool[/]", config.sfm_tool)
    table.add_row("[cyan]Iterations[/]", f"{config.iterations:,}")
    table.add_row("[cyan]Device[/]", f"{gpu['device']} ({gpu['name']}, {gpu['vram_gb']} GB)" if gpu['vram_gb'] else gpu['device'])
    console.print(Panel(table, title="[bold]Gaussian Maker[/]", border_style="cyan"))


def _check_dependencies(config: PipelineConfig) -> None:
    issues = []
    if not check_ffmpeg() and config.trainer != "nerfstudio":
        issues.append("ffmpeg not found on PATH. Install from https://ffmpeg.org/download.html")
    if config.sfm_tool == "colmap" and config.trainer != "nerfstudio" and not check_colmap():
        issues.append("colmap not found on PATH. Install from https://colmap.github.io/install.html")
    if issues:
        for issue in issues:
            console.print(f"[red]✗[/] {issue}")
        raise EnvironmentError("Missing required dependencies. See above.")


def _print_summary(results: dict[str, Path]) -> None:
    console.rule("[bold green]Done[/]")
    for fmt, path in results.items():
        size_mb = path.stat().st_size / 1024**2 if path.exists() else 0
        console.print(f"  [green]✓[/] [bold]{fmt.upper()}[/]: {path}  ({size_mb:.1f} MB)")
