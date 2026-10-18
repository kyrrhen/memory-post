"""Shared SIREN helpers used by both sender and receiver.

The receiver only needs numpy + pillow. No PyTorch is required on the
receiving side.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def parse_freqs(value):
    if isinstance(value, str):
        return [float(x.strip()) for x in value.split(",") if x.strip()]
    return [float(x) for x in value]


def make_features(width: int, height: int, freqs, batch: int | None = None):
    """Yield Fourier features for pixel centers in row-major order.

    Each row is [x, y, sin(pi*f*x), cos(pi*f*x), sin(pi*f*y), cos(pi*f*y), ...].
    Coordinates are normalized to [-1, 1].
    """
    freqs = parse_freqs(freqs)
    total = width * height
    step = total if batch is None else max(1, int(batch))
    ys, xs = np.mgrid[0:height, 0:width]
    x_all = ((xs.reshape(-1) + 0.5) / width * 2.0 - 1.0).astype(np.float32)
    y_all = ((ys.reshape(-1) + 0.5) / height * 2.0 - 1.0).astype(np.float32)

    for start in range(0, total, step):
        end = min(total, start + step)
        x = x_all[start:end]
        y = y_all[start:end]
        cols = [x, y]
        for f in freqs:
            cols.extend([
                np.sin(np.pi * f * x),
                np.cos(np.pi * f * x),
                np.sin(np.pi * f * y),
                np.cos(np.pi * f * y),
            ])
        yield np.stack(cols, axis=1).astype(np.float32)


def features_for_indices(width: int, height: int, freqs, indices: np.ndarray) -> np.ndarray:
    """Build Fourier features only for selected row-major pixel indices."""
    freqs = parse_freqs(freqs)
    idx = np.asarray(indices, dtype=np.int64)
    ys = idx // int(width)
    xs = idx - ys * int(width)
    x = ((xs.astype(np.float32) + 0.5) / float(width) * 2.0 - 1.0)
    y = ((ys.astype(np.float32) + 0.5) / float(height) * 2.0 - 1.0)
    cols = [x, y]
    for f in freqs:
        cols.extend([
            np.sin(np.pi * f * x),
            np.cos(np.pi * f * x),
            np.sin(np.pi * f * y),
            np.cos(np.pi * f * y),
        ])
    return np.stack(cols, axis=1).astype(np.float32, copy=False)


def load_npz_weights(path: str | Path):
    data = np.load(str(path), allow_pickle=False)
    return {k: data[k] for k in data.files}


def forward_numpy(weights, features: np.ndarray, head_index: int = 0) -> np.ndarray:
    """Run the saved SIREN in NumPy.

    Supports both the legacy single-head format and the multi-head format used
    for several photos sharing one model. The first-layer omega_0 is folded
    into the exported weights, so hidden layers all use sin() and the output
    uses sigmoid().
    """
    h = features.astype(np.float32, copy=False)
    if "num_heads" in weights:
        num_hidden = int(np.asarray(weights["num_hidden"]).reshape(-1)[0])
        num_heads = int(np.asarray(weights["num_heads"]).reshape(-1)[0])
        head_index = int(head_index)
        if not 0 <= head_index < num_heads:
            raise ValueError(f"head_index {head_index} outside 0..{num_heads - 1}")
        for i in range(num_hidden):
            w = weights[f"W{i}"]
            b = weights[f"b{i}"]
            h = np.sin(h @ w.T + b)
        logits = h @ weights[f"H{head_index}_W"].T + weights[f"H{head_index}_b"]
        return (1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))).astype(np.float32, copy=False)

    num_layers = int(np.asarray(weights["num_layers"]).reshape(-1)[0])
    for i in range(num_layers):
        w = weights[f"W{i}"]
        b = weights[f"b{i}"]
        h = h @ w.T + b
        if i < num_layers - 1:
            h = np.sin(h)
        else:
            h = 1.0 / (1.0 + np.exp(-np.clip(h, -30.0, 30.0)))
    return h.astype(np.float32, copy=False)


def generate_base(weights, width: int, height: int, freqs, batch: int = 65536, head_index: int = 0):
    total = width * height
    out = np.empty((total, 3), dtype=np.float32)
    offset = 0
    for features in make_features(width, height, freqs, batch=batch):
        pred = forward_numpy(weights, features, head_index=head_index)
        n = pred.shape[0]
        out[offset:offset + n] = pred
        offset += n
    return out.reshape(height, width, 3)


def load_residual(path: str | Path, width: int, height: int, scale: int, multiplier: float):
    image = Image.open(path).convert("RGB")
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.BICUBIC)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    return (arr - 0.5) * 2.0 * float(multiplier)


def image_to_uint8(image: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8)


def resize_base(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize a float RGB base image, preserving the same quantization path."""
    if image.shape[1] == int(width) and image.shape[0] == int(height):
        return image.astype(np.float32, copy=False)
    source = Image.fromarray(image_to_uint8(image), "RGB")
    resized = source.resize((int(width), int(height)), Image.Resampling.BICUBIC)
    return np.asarray(resized, dtype=np.float32) / 255.0


def read_manifest(bundle_root: str | Path):
    root = Path(bundle_root)
    with open(root / "manifest.json", "r", encoding="utf-8") as f:
        return json.load(f)
