import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from receiver import reconstruct_bundle
from sender import build_bundle


def _make_image(path: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:48, 0:48]
    arr = np.zeros((48, 48, 3), dtype=np.uint8)
    arr[..., 0] = ((xx + seed) * 5 % 256).astype(np.uint8)
    arr[..., 1] = ((yy + seed) * 7 % 256).astype(np.uint8)
    arr[..., 2] = rng.integers(0, 256, size=(48, 48), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def _args():
    return SimpleNamespace(
        size=64,
        max_side=64,
        max_pixels=1_600_000,
        resolution_mode="auto",
        model_group_size=2,
        steps=6,
        batch=512,
        hidden=16,
        layers=2,
        freqs="1,2,4,8",
        omega0=30.0,
        lr=1e-3,
        residual_scale=1,
        residual_quality=92,
        residual_format="webp",
        large_image_fast=True,
        base_render_pixels=1_000,
        feature_cache_mb=32,
        seed=1234,
        include_receiver_exe=False,
    )


def test_shared_model_roundtrip(tmp_path: Path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_image(first, 1)
    _make_image(second, 2)

    bundle = tmp_path / "bundle.zip"
    build_bundle([str(first), str(second)], _args(), bundle, log=lambda _line: None)

    outputs = reconstruct_bundle(str(bundle), str(tmp_path / "received"), log=lambda _line: None)
    assert len(outputs) == 2
    assert all(Path(path).exists() for path in outputs)

    with zipfile.ZipFile(bundle) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["version"] == 2
    assert len(manifest["groups"]) == 1
    assert manifest["groups"][0]["num_heads"] == 2
    assert len([name for name in names if name.startswith("models/") and name.endswith(".npz")]) == 1
    assert len([name for name in names if name.startswith("residuals/")]) == 2
    assert [entry["head_index"] for entry in manifest["images"]] == [0, 1]
    assert all(entry["base_render_width"] < entry["width"] for entry in manifest["images"])
