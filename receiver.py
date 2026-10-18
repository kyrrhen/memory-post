from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from siren_common import (
    generate_base,
    image_to_uint8,
    load_npz_weights,
    load_residual,
    read_manifest,
    resize_base,
)


def resolve_bundle(input_path: str | None):
    script_dir = Path(__file__).resolve().parent
    if not input_path:
        if (script_dir / "manifest.json").exists():
            return script_dir, None
        raise SystemExit("No bundle given. Drag bundle.zip onto receive.bat, or run: python receiver.py bundle.zip")
    path = Path(input_path)
    if path.is_dir():
        return path, None
    if path.suffix.lower() != ".zip":
        raise SystemExit(f"Unsupported bundle: {path}")
    tmp = Path(tempfile.mkdtemp(prefix="siren_receive_"))
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(tmp)
    return tmp, tmp


def reconstruct_bundle(bundle, output, log=print, progress=None, fmt="png", quality=95, cancel_event=None):
    root, cleanup = resolve_bundle(str(bundle) if bundle else None)
    outputs = []
    try:
        manifest = read_manifest(root)
        out_dir = Path(output)
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        log(f"bundle: {root}")
        log(f"output: {out_dir}")
        entries = manifest.get("images", [])
        if not entries:
            raise RuntimeError("bundle 中没有图片")
        for i, entry in enumerate(entries, 1):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("cancelled")
            name = entry["name"]
            width = int(entry["width"])
            height = int(entry["height"])
            group_text = f", model group {entry.get('model_group')}/{entry.get('num_heads')}" if entry.get("model_group_size", 1) > 1 else ""
            log(f"[{i}/{len(entries)}] reconstructing {name} ({width}x{height}){group_text}...")
            if progress is not None:
                progress((i - 0.5) / len(entries), f"重建 {i}/{len(entries)} · 网络推理")
            weights = load_npz_weights(root / entry["model"])
            base_width = int(entry.get("base_render_width", width))
            base_height = int(entry.get("base_render_height", height))
            base = generate_base(
                weights,
                base_width,
                base_height,
                entry["freqs"],
                batch=65536,
                head_index=int(entry.get("head_index", 0)),
            )
            if (base_width, base_height) != (width, height):
                base = resize_base(base, width, height)
                log(f"  base render {base_width}x{base_height} -> {width}x{height}")
            residual = load_residual(
                root / entry["residual"],
                width,
                height,
                int(entry["residual_scale"]),
                float(entry["residual_multiplier"]),
            )
            final = np.clip(base + residual, 0.0, 1.0)
            out_path = out_dir / f"{name}.{fmt}"
            image = Image.fromarray(image_to_uint8(final), "RGB")
            if fmt == "jpg":
                image.save(out_path, format="JPEG", quality=quality, optimize=True)
            else:
                image.save(out_path, format="PNG", optimize=True)
            outputs.append(str(out_path))
            log(f"  -> {out_path}")
            if progress is not None:
                progress(i / len(entries), f"完成 {i}/{len(entries)}")
        log("done.")
        return outputs
    finally:
        if cleanup is not None:
            shutil.rmtree(cleanup, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Reconstruct images from a SIREN bundle.")
    parser.add_argument("bundle", nargs="?", help="bundle.zip or an unpacked bundle directory")
    parser.add_argument("-o", "--output", default="received", help="Output directory")
    parser.add_argument("--format", choices=["png", "jpg"], default="png")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality if --format jpg")
    args = parser.parse_args()
    reconstruct_bundle(args.bundle, args.output, fmt=args.format, quality=args.quality)


if __name__ == "__main__":
    main()
