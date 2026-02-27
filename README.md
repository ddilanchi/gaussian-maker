# Gaussian Maker

Convert iPhone, Meta glasses, and other video files into 3D Gaussian splats — fast.

## Pipeline

```
Video (.MOV / .mp4 / any FFmpeg format)
   → Frame Extraction (FFmpeg)
   → Structure-from-Motion (COLMAP or GLOMAP)
   → Gaussian Splatting Training (Nerfstudio splatfacto / OpenSplat)
   → Export (.ply / .splat / .ksplat)
```

The default backend is **Nerfstudio** using **gsplat** under the hood — the fastest
pip-installable CUDA rasterizer available as of 2026.

---

## Quick Start

### 1. Install system dependencies

| Dependency | Link |
|---|---|
| Python ≥ 3.10 | https://python.org |
| FFmpeg | https://ffmpeg.org/download.html |
| COLMAP | https://colmap.github.io/install.html |
| CUDA ≥ 11.8 (NVIDIA GPU recommended) | https://developer.nvidia.com/cuda-downloads |

### 2. Install Python packages

```bash
# Clone and install
git clone https://github.com/ddilanchi/gaussian-maker
cd gaussian-maker
pip install -e .

# Install PyTorch (match your CUDA version — example for CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install training backend
pip install nerfstudio   # Recommended: includes gsplat + ns-train CLI
# OR
pip install gsplat       # Lower-level API
```

### 3. Convert a video

```bash
# Simplest: let Nerfstudio handle everything
gm run iphone_capture.MOV

# With options
gm run meta_glasses.mp4 \
    --trainer nerfstudio \
    --fps 3 \
    --iterations 20000 \
    --format ply \
    --format splat

# Check what's installed
gm check

# Show video metadata
gm info video.mp4
```

---

## CLI Reference

```
gm run VIDEO [OPTIONS]

  --output, -o       Output directory           [default: outputs]
  --trainer, -t      nerfstudio | opensplat     [default: nerfstudio]
  --sfm-tool, -s     colmap | glomap | skip     [default: colmap]
  --fps, -f          Frames per second           [default: 2.0]
  --max-frames       Max frames to extract       [default: 300]
  --iterations, -i   Training iterations         [default: 30000]
  --format, -F       ply | splat | ksplat        [default: ply]
  --quality, -q      low|medium|high|extreme     [default: medium]
```

---

## Trainers

| Trainer | Speed | GPU | Notes |
|---|---|---|---|
| **nerfstudio** | Fast | NVIDIA (CUDA) | `pip install nerfstudio`. All-in-one: handles frames + SfM. |
| **opensplat** | Fast | NVIDIA / AMD / Apple | Needs binary install. Cross-platform. |

## SfM Tools (camera pose estimation)

| Tool | Speed | Notes |
|---|---|---|
| **colmap** | Standard | Gold standard. Most compatible. |
| **glomap** | 10-50x faster | Drop-in replacement. Needs separate install. |
| **skip** | — | Use pre-existing COLMAP output. |

---

## Output Formats

| Format | Viewer |
|---|---|
| `.ply` | Blender (Gaussian Splatting addon), SuperSplat |
| `.splat` | [SuperSplat](https://supersplat.dev), three-splat |
| `.ksplat` | [three-splat viewer](https://github.com/mkkellogg/GaussianSplats3D) |

Convert between formats:
```bash
npm install -g @playcanvas/splat-transform
splat-transform input.ply output.splat
```

---

## Hardware Requirements

| VRAM | Capability |
|---|---|
| 8 GB | Low quality (≤ 150 frames) |
| 12 GB | Medium quality (≤ 300 frames) — recommended minimum |
| 24 GB | High quality / large scenes |

CPU-only is supported by OpenSplat but training will be very slow.

---

## Advanced: Speed Tips

- Use **GLOMAP** instead of COLMAP for 10-50x faster SfM: `--sfm-tool glomap`
- Reduce `--fps` to 1-2 for large scenes to stay within VRAM
- Use `--iterations 10000` for a quick preview draft
- For dynamic scenes (moving people/objects), see [4DGaussians](https://github.com/hustvl/4DGaussians)
- For COLMAP-free instant reconstruction, see [InstantSplat](https://github.com/NVlabs/InstantSplat)

---

## Roadmap

- [ ] InstantSplat backend (COLMAP-free, seconds to init)
- [ ] LongSplat backend (designed for casual iPhone/Meta video)
- [ ] 4D Gaussian splatting for dynamic scenes
- [ ] Web UI / drag-and-drop interface
- [ ] Watch folder mode (auto-process new videos)
- [ ] Cloud GPU support (RunPod / Lambda)

---

## References

- [gsplat](https://github.com/nerfstudio-project/gsplat) — CUDA rasterization backend
- [Nerfstudio splatfacto](https://docs.nerf.studio/nerfology/methods/splat.html)
- [OpenSplat](https://github.com/pierotofy/OpenSplat)
- [InstantSplat (NVIDIA)](https://github.com/NVlabs/InstantSplat)
- [LongSplat (NVIDIA, ICCV 2025)](https://github.com/NVlabs/LongSplat)
- [GLOMAP](https://github.com/colmap/glomap)
