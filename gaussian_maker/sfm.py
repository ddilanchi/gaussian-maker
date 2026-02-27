"""Structure-from-Motion (SfM) — camera pose estimation from frames.

Supported backends:
  - colmap  : Gold standard, widely supported (default)
  - glomap  : 10-50x faster than COLMAP, drop-in replacement
  - skip    : Use pre-existing COLMAP output (for power users)
"""

import subprocess
import shutil
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def run_colmap(
    frames_dir: Path,
    output_dir: Path,
    quality: str = "medium",
    use_gpu: bool = True,
) -> Path:
    """Run COLMAP automatic_reconstructor on a directory of frames.

    Args:
        frames_dir: Directory containing extracted JPEG/PNG frames.
        output_dir: Directory to write COLMAP workspace (sparse/, database.db).
        quality: One of 'low', 'medium', 'high', 'extreme'.
        use_gpu: Use GPU for feature extraction/matching when available.

    Returns:
        Path to the COLMAP sparse/0 directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    gpu_flag = "1" if use_gpu else "0"

    cmd = [
        "colmap", "automatic_reconstructor",
        "--workspace_path", str(output_dir),
        "--image_path", str(frames_dir),
        "--quality", quality,
        "--use_gpu", gpu_flag,
        "--single_camera", "1",  # assume one camera (iPhone / glasses)
    ]

    console.print(f"[bold cyan]Running COLMAP[/] ({quality} quality)...")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as p:
        p.add_task("SfM in progress — this may take a few minutes...", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        console.print(f"[red]COLMAP error:[/]\n{result.stderr[-1000:]}")
        raise RuntimeError("COLMAP reconstruction failed.")

    sparse_dir = output_dir / "sparse" / "0"
    if not sparse_dir.exists():
        # Try without the "0" subfolder
        sparse_dir = output_dir / "sparse"

    console.print(f"[green]✓[/] COLMAP finished. Sparse model: [dim]{sparse_dir}[/]")
    return sparse_dir


def run_glomap(frames_dir: Path, output_dir: Path) -> Path:
    """Run GLOMAP (faster COLMAP alternative) on a directory of frames.

    GLOMAP must be installed separately: https://github.com/colmap/glomap
    Falls back to COLMAP if GLOMAP is not found.
    """
    if not shutil.which("glomap"):
        console.print("[yellow]GLOMAP not found, falling back to COLMAP.[/]")
        return run_colmap(frames_dir, output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "database.db"

    # Step 1: Feature extraction
    subprocess.run([
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(frames_dir),
        "--ImageReader.single_camera", "1",
        "--SiftExtraction.use_gpu", "1",
    ], check=True, capture_output=True)

    # Step 2: Feature matching
    subprocess.run([
        "colmap", "exhaustive_matcher",
        "--database_path", str(db_path),
        "--SiftMatching.use_gpu", "1",
    ], check=True, capture_output=True)

    # Step 3: GLOMAP mapping (replaces COLMAP mapper)
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(exist_ok=True)
    subprocess.run([
        "glomap", "mapper",
        "--database_path", str(db_path),
        "--image_path", str(frames_dir),
        "--output_path", str(sparse_dir),
    ], check=True)

    result = sparse_dir / "0"
    console.print(f"[green]✓[/] GLOMAP finished. Sparse model: [dim]{result}[/]")
    return result


def run_sfm(
    frames_dir: Path,
    output_dir: Path,
    tool: str = "colmap",
    quality: str = "medium",
) -> Path:
    """Dispatch to the correct SfM backend."""
    if tool == "glomap":
        return run_glomap(frames_dir, output_dir)
    elif tool == "colmap":
        return run_colmap(frames_dir, output_dir, quality=quality)
    elif tool == "skip":
        sparse_dir = output_dir / "sparse" / "0"
        if not sparse_dir.exists():
            raise FileNotFoundError(f"Expected pre-existing COLMAP sparse model at {sparse_dir}")
        console.print(f"[yellow]Skipping SfM — using existing model at {sparse_dir}[/]")
        return sparse_dir
    else:
        raise ValueError(f"Unknown SfM tool: {tool}. Choose from: colmap, glomap, skip")
