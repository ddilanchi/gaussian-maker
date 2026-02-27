"""Gaussian splatting training backends.

Supported trainers:
  - nerfstudio : Uses `ns-train splatfacto` (recommended, pip-installable)
  - gsplat     : Direct gsplat training via its example scripts
  - opensplat  : OpenSplat binary (cross-platform, no Python GPU needed)
"""

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# Nerfstudio / Splatfacto
# ---------------------------------------------------------------------------

def train_nerfstudio(
    data_dir: Path,
    output_dir: Path,
    iterations: int = 30_000,
    save_every: int = 5_000,
) -> Path:
    """Train a 3D Gaussian splat using Nerfstudio's splatfacto method.

    Args:
        data_dir: Directory containing COLMAP output (with transforms.json or
                  sparse/ subdirectory). If it contains frames + COLMAP sparse,
                  use ns-process-data first.
        output_dir: Root directory for Nerfstudio outputs.
        iterations: Number of training iterations (default 30k).
        save_every: Checkpoint interval.

    Returns:
        Path to the trained config YAML.
    """
    if not shutil.which("ns-train"):
        raise EnvironmentError(
            "Nerfstudio not found. Install with: pip install nerfstudio"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ns-train", "splatfacto",
        "--data", str(data_dir),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(iterations),
        "--steps-per-save", str(save_every),
        "--pipeline.model.cull-alpha-thresh", "0.005",
        "--pipeline.model.continue-cull-post-densification", "True",
        "--vis", "wandb",  # use 'viewer' to open the web viewer
    ]

    console.print(f"[bold cyan]Training Gaussian splat[/] with Nerfstudio splatfacto ({iterations:,} iters)...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError("Nerfstudio training failed.")

    # Find the config file
    configs = sorted(output_dir.rglob("config.yml"))
    if not configs:
        raise FileNotFoundError("Could not find Nerfstudio config.yml after training.")

    config_path = configs[-1]
    console.print(f"[green]✓[/] Training complete. Config: [dim]{config_path}[/]")
    return config_path


def preprocess_nerfstudio(video_path: Path, output_dir: Path) -> Path:
    """Use ns-process-data to handle frame extraction + COLMAP in one step.

    This is the easiest path: give it a video, it handles everything.

    Returns:
        Path to the processed data directory (ready for ns-train).
    """
    if not shutil.which("ns-process-data"):
        raise EnvironmentError(
            "Nerfstudio not found. Install with: pip install nerfstudio"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ns-process-data", "video",
        "--data", str(video_path),
        "--output-dir", str(output_dir),
        "--num-frames-target", "150",
        "--sfm-tool", "colmap",
        "--matching-method", "sequential",  # best for video (sequential frames)
    ]

    console.print(f"[bold cyan]Preprocessing video[/] with Nerfstudio (FFmpeg + COLMAP)...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError("ns-process-data failed.")

    console.print(f"[green]✓[/] Preprocessing complete: [dim]{output_dir}[/]")
    return output_dir


# ---------------------------------------------------------------------------
# OpenSplat (binary-based, cross-platform)
# ---------------------------------------------------------------------------

def train_opensplat(
    colmap_dir: Path,
    output_dir: Path,
    num_points: int = 100_000,
) -> Path:
    """Train using the OpenSplat binary.

    OpenSplat must be installed: https://github.com/pierotofy/OpenSplat
    Accepts COLMAP workspace as input.

    Returns:
        Path to the output .ply file.
    """
    if not shutil.which("OpenSplat") and not shutil.which("opensplat"):
        raise EnvironmentError(
            "OpenSplat not found. Download from: https://github.com/pierotofy/OpenSplat/releases"
        )

    binary = shutil.which("OpenSplat") or shutil.which("opensplat")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_ply = output_dir / "splat.ply"

    cmd = [
        binary,
        str(colmap_dir),
        "-n", str(num_points),
        "-o", str(out_ply),
    ]

    console.print(f"[bold cyan]Training Gaussian splat[/] with OpenSplat ({num_points:,} points)...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError("OpenSplat training failed.")

    console.print(f"[green]✓[/] OpenSplat done: [dim]{out_ply}[/]")
    return out_ply


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def train(
    trainer: str,
    data_dir: Path,
    output_dir: Path,
    iterations: int = 30_000,
    video_path: Path | None = None,
) -> Path:
    """Dispatch to the correct training backend.

    Args:
        trainer: One of 'nerfstudio', 'opensplat'.
        data_dir: Input data directory (COLMAP workspace or processed data).
        output_dir: Output directory.
        iterations: Training iterations (nerfstudio only).
        video_path: Original video (used by nerfstudio all-in-one mode).

    Returns:
        Path to the trained model or config file.
    """
    if trainer == "nerfstudio":
        if video_path is not None:
            # All-in-one: let nerfstudio handle frame extraction + COLMAP
            processed = preprocess_nerfstudio(video_path, data_dir)
            return train_nerfstudio(processed, output_dir, iterations)
        return train_nerfstudio(data_dir, output_dir, iterations)
    elif trainer == "opensplat":
        return train_opensplat(data_dir, output_dir)
    else:
        raise ValueError(f"Unknown trainer: {trainer}. Choose from: nerfstudio, opensplat")
