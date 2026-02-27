"""Export Gaussian splat models to various formats.

Supported output formats:
  - .ply       : Standard point cloud / splat format (Blender, viewers)
  - .splat     : Compressed splat format (web viewers like SuperSplat)
  - .ksplat    : Kevin Kwok's splat format (three-splat viewer)

Uses PlayCanvas splat-transform CLI for format conversion when available.
"""

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def export_ply(source_ply: Path, output_dir: Path) -> Path:
    """Copy/move a .ply file to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / source_ply.name
    shutil.copy2(source_ply, dest)
    console.print(f"[green]✓[/] Exported PLY: [dim]{dest}[/]")
    return dest


def export_splat(source_ply: Path, output_dir: Path) -> Path:
    """Convert .ply to .splat using PlayCanvas splat-transform.

    Install with: npm install -g @playcanvas/splat-transform
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / (source_ply.stem + ".splat")

    if not shutil.which("splat-transform"):
        console.print(
            "[yellow]splat-transform not found. Skipping .splat export.[/]\n"
            "  Install with: npm install -g @playcanvas/splat-transform"
        )
        return out_path

    cmd = ["splat-transform", str(source_ply), str(out_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        console.print(f"[red]splat-transform error:[/] {result.stderr}")
        raise RuntimeError("Failed to convert to .splat format.")

    console.print(f"[green]✓[/] Exported .splat: [dim]{out_path}[/]")
    return out_path


def export_nerfstudio_ply(config_path: Path, output_dir: Path) -> Path:
    """Export .ply from a trained Nerfstudio model using ns-export."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("ns-export"):
        raise EnvironmentError("ns-export not found. Is nerfstudio installed?")

    cmd = [
        "ns-export", "gaussian-splat",
        "--load-config", str(config_path),
        "--output-dir", str(output_dir),
    ]

    console.print("[bold cyan]Exporting PLY[/] from Nerfstudio model...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError("ns-export failed.")

    plys = sorted(output_dir.glob("*.ply"))
    if not plys:
        raise FileNotFoundError("No .ply file found after ns-export.")

    console.print(f"[green]✓[/] Exported: [dim]{plys[-1]}[/]")
    return plys[-1]


def run_exports(
    source: Path,
    output_dir: Path,
    formats: list[str],
    is_nerfstudio_config: bool = False,
) -> dict[str, Path]:
    """Run all requested export formats.

    Args:
        source: Either a .ply file or a Nerfstudio config.yml path.
        output_dir: Directory to write exports.
        formats: List of format strings, e.g. ['ply', 'splat'].
        is_nerfstudio_config: If True, first export .ply from Nerfstudio.

    Returns:
        Dict mapping format name to output path.
    """
    results: dict[str, Path] = {}

    # If source is a nerfstudio config, export .ply first
    ply_path = source
    if is_nerfstudio_config:
        ply_path = export_nerfstudio_ply(source, output_dir)
        results["ply"] = ply_path

    for fmt in formats:
        fmt = fmt.lower().strip(".")
        if fmt == "ply" and "ply" not in results:
            results["ply"] = export_ply(ply_path, output_dir)
        elif fmt == "splat":
            results["splat"] = export_splat(ply_path, output_dir)
        elif fmt == "ksplat":
            # ksplat uses the same splat-transform CLI with a different output extension
            output_dir.mkdir(parents=True, exist_ok=True)
            out = output_dir / (ply_path.stem + ".ksplat")
            if shutil.which("splat-transform"):
                subprocess.run(["splat-transform", str(ply_path), str(out)], check=True)
                results["ksplat"] = out
                console.print(f"[green]✓[/] Exported .ksplat: [dim]{out}[/]")
            else:
                console.print("[yellow]splat-transform not found. Skipping .ksplat.[/]")

    return results
