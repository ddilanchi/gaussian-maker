"""Configuration management for Gaussian Maker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class PipelineConfig:
    # Input
    video_path: Path = Path("input.mp4")
    output_dir: Path = Path("outputs")

    # Frame extraction
    fps: float = 2.0
    max_frames: int = 300
    frame_format: Literal["jpg", "png"] = "jpg"
    frame_quality: int = 95  # JPEG quality 1-95

    # SfM
    sfm_tool: Literal["colmap", "glomap", "instantsplat"] = "colmap"
    colmap_quality: Literal["low", "medium", "high", "extreme"] = "medium"

    # Training
    trainer: Literal["gsplat", "nerfstudio", "opensplat"] = "nerfstudio"
    iterations: int = 30_000
    save_every: int = 5_000

    # Export
    export_formats: list[str] = field(default_factory=lambda: ["ply"])

    # Hardware
    device: str = "cuda"

    def frames_dir(self) -> Path:
        return self.output_dir / "frames"

    def sfm_dir(self) -> Path:
        return self.output_dir / "sfm"

    def splat_dir(self) -> Path:
        return self.output_dir / "splats"
