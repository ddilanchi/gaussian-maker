"""Gaussian splatting training backends.

Supported trainers:
  - nerfstudio : Uses nerfstudio.scripts (recommended, pip-installable)
  - opensplat  : OpenSplat binary (cross-platform, no Python GPU needed)
"""

import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()

# Always use the same Python executable that is running this script.
# This ensures nerfstudio's scripts are found even when ns-train / ns-process-data
# are not on PATH (common on Windows with user-level pip installs).
PY = sys.executable


def _nerfstudio_available() -> bool:
    """Return True if nerfstudio is importable."""
    try:
        import importlib.util
        return importlib.util.find_spec("nerfstudio") is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Nerfstudio / Splatfacto
# ---------------------------------------------------------------------------

def train_nerfstudio(
    data_dir: Path,
    output_dir: Path,
    iterations: int = 30_000,
    save_every: int = 5_000,
) -> Path:
    """Train a 3D Gaussian splat using Nerfstudio's splatfacto method."""
    if not _nerfstudio_available():
        raise EnvironmentError("Nerfstudio not found. Install with: pip install nerfstudio")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PY, "-m", "nerfstudio.scripts.train", "splatfacto",
        "--data", str(data_dir),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(iterations),
        "--steps-per-save", str(save_every),
        "--pipeline.model.cull-alpha-thresh", "0.005",
        "--pipeline.model.continue-cull-post-densification", "True",
        "--vis", "viewer+wandb",
    ]

    console.print(f"[bold cyan]Training Gaussian splat[/] with Nerfstudio splatfacto ({iterations:,} iters)...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError("Nerfstudio training failed.")

    configs = sorted(output_dir.rglob("config.yml"))
    if not configs:
        raise FileNotFoundError("Could not find Nerfstudio config.yml after training.")

    config_path = configs[-1]
    console.print(f"[green]✓[/] Training complete. Config: [dim]{config_path}[/]")
    return config_path


def preprocess_nerfstudio(video_path: Path, output_dir: Path) -> Path:
    """Use ns-process-data to handle frame extraction + COLMAP in one step."""
    if not _nerfstudio_available():
        raise EnvironmentError("Nerfstudio not found. Install with: pip install nerfstudio")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PY, "-m", "nerfstudio.scripts.process_data", "video",
        "--data", str(video_path),
        "--output-dir", str(output_dir),
        "--num-frames-target", "150",
        "--sfm-tool", "colmap",
        "--matching-method", "sequential",
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
    """Train using the OpenSplat binary."""
    binary = shutil.which("OpenSplat") or shutil.which("opensplat")
    if not binary:
        raise EnvironmentError(
            "OpenSplat not found. Download from: https://github.com/pierotofy/OpenSplat/releases"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_ply = output_dir / "splat.ply"

    cmd = [binary, str(colmap_dir), "-n", str(num_points), "-o", str(out_ply)]

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
    if trainer == "nerfstudio":
        if video_path is not None:
            processed = preprocess_nerfstudio(video_path, data_dir)
            return train_nerfstudio(processed, output_dir, iterations)
        return train_nerfstudio(data_dir, output_dir, iterations)
    elif trainer == "opensplat":
        return train_opensplat(data_dir, output_dir)
    else:
        raise ValueError(f"Unknown trainer: {trainer}. Choose from: nerfstudio, opensplat")
