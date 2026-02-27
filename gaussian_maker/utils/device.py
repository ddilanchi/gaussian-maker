"""GPU/CPU device detection and info."""

import subprocess
import sys


def get_device() -> str:
    """Return 'cuda', 'mps', or 'cpu' based on availability."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def gpu_info() -> dict:
    """Return basic GPU info as a dict."""
    info = {"device": get_device(), "name": "N/A", "vram_gb": None}
    try:
        import torch
        if torch.cuda.is_available():
            info["name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024**3, 1
            )
    except ImportError:
        pass
    return info


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def check_colmap() -> bool:
    """Return True if colmap is on PATH."""
    try:
        subprocess.run(
            ["colmap", "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False
