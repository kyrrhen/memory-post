from pathlib import Path
from types import SimpleNamespace

from sender import build_bundle


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    examples = root / "examples"
    images = [examples / "images" / "sunset.png", examples / "images" / "aurora.png"]
    args = SimpleNamespace(
        max_side=640,
        size=640,
        max_pixels=1_600_000,
        resolution_mode="auto",
        model_group_size=2,
        steps=120,
        batch=4096,
        hidden=64,
        layers=3,
        freqs="1,2,4,8",
        omega0=30.0,
        lr=1e-3,
        residual_scale=1,
        residual_quality=95,
        residual_format="webp",
        large_image_fast=True,
        base_render_pixels=900_000,
        feature_cache_mb=192,
        seed=1234,
        include_receiver_exe=False,
    )
    build_bundle([str(path) for path in images], args, examples / "demo-bundle.zip")


if __name__ == "__main__":
    main()
