from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from siren_common import (
    features_for_indices,
    generate_base,
    load_npz_weights,
    load_residual,
    make_features,
    parse_freqs,
    resize_base,
)

DEFAULT_MAX_SIDE = 1024
DEFAULT_MAX_PIXELS = 1_600_000


def compute_target_size(width: int, height: int, mode: str, max_side: int, max_pixels: int = DEFAULT_MAX_PIXELS):
    """Return (target_width, target_height, scale).

    auto: preserve the source resolution when it is small, but cap both the
    longest side and the total pixel count. This adapts to each photo instead
    of forcing every image to one fixed size.
    fixed: only downscale when the longest side exceeds max_side.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    longest = max(width, height)
    max_side = max(64, int(max_side))
    if str(mode).lower() == "fixed":
        scale = min(1.0, float(max_side) / longest)
    else:
        pixel_scale = math.sqrt(float(max_pixels) / float(width * height))
        scale = min(1.0, float(max_side) / longest, pixel_scale)
    return max(8, int(round(width * scale))), max(8, int(round(height * scale))), float(scale)


def load_image(path: Path, args):
    image = Image.open(path).convert("RGB")
    source_w, source_h = image.size
    mode = str(getattr(args, "resolution_mode", "auto"))
    max_side = int(getattr(args, "max_side", getattr(args, "size", DEFAULT_MAX_SIDE)))
    max_pixels = int(getattr(args, "max_pixels", DEFAULT_MAX_PIXELS))
    target_w, target_h, scale = compute_target_size(source_w, source_h, mode, max_side, max_pixels)
    if (target_w, target_h) != (source_w, source_h):
        image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    return image, arr, (source_w, source_h, target_w, target_h, scale)


def _init_numpy_weights(in_dim, hidden, num_hidden_layers, num_heads, omega0, rng):
    weights = {}
    bound = math.sqrt(6.0 / in_dim) / omega0
    weights["W0"] = rng.uniform(-bound, bound, (hidden, in_dim)).astype(np.float32)
    weights["b0"] = np.zeros(hidden, dtype=np.float32)
    for i in range(1, num_hidden_layers):
        bound = math.sqrt(6.0 / hidden)
        weights[f"W{i}"] = rng.uniform(-bound, bound, (hidden, hidden)).astype(np.float32)
        weights[f"b{i}"] = np.zeros(hidden, dtype=np.float32)
    bound = math.sqrt(6.0 / hidden)
    for head in range(num_heads):
        weights[f"H{head}_W"] = rng.uniform(-bound, bound, (3, hidden)).astype(np.float32)
        weights[f"H{head}_b"] = np.zeros(3, dtype=np.float32)
    return weights


def _sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def train_siren_group(images, args, log=print, progress=None, cancel_event=None):
    """Train one shared-trunk, multi-head SIREN for one or more images."""
    if not images:
        raise ValueError("no images to train")
    num_heads = len(images)
    first_h, first_w, _ = images[0].shape
    freqs = parse_freqs(args.freqs)
    in_dim = len(freqs) * 4 + 2
    hidden = int(args.hidden)
    num_hidden_layers = int(args.layers)
    omega0 = float(args.omega0)
    rng = np.random.default_rng(int(args.seed))

    weights = _init_numpy_weights(in_dim, hidden, num_hidden_layers, num_heads, omega0, rng)
    m = {k: np.zeros_like(v, dtype=np.float32) for k, v in weights.items()}
    v = {k: np.zeros_like(v, dtype=np.float32) for k, v in weights.items()}
    trunk_keys = [f"{kind}{i}" for i in range(num_hidden_layers) for kind in ("W", "b")]
    head_keys = [
        key
        for head in range(num_heads)
        for key in (f"H{head}_W", f"H{head}_b")
    ]
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    steps = max(1, int(args.steps))
    max_batch = max(64, int(args.batch))
    lr0 = float(args.lr)
    total_pixels = [int(im.shape[0] * im.shape[1]) for im in images]
    cache_budget = int(float(getattr(args, "feature_cache_mb", 192)) * 1024 * 1024)
    feature_cache = []
    cached_bytes = 0
    for image in images:
        h, w, _ = image.shape
        needed = int(h * w * in_dim * 4)
        if cached_bytes + needed <= cache_budget:
            features = np.concatenate(list(make_features(w, h, freqs, batch=None)), axis=0).astype(np.float32)
            feature_cache.append((features, image.reshape(-1, 3)))
            cached_bytes += needed
        else:
            feature_cache.append(None)
    cached_count = sum(1 for item in feature_cache if item is not None)
    log(
        f"shared model: {num_heads} head(s), first {first_w}x{first_h}, "
        f"features {in_dim}, hidden {hidden}, layers {num_hidden_layers}, "
        f"steps/image {steps}, feature cache {cached_count}/{num_heads} "
        f"({cached_bytes / 1024 / 1024:.1f} MB) [NumPy]"
    )
    t0 = time.time()
    for step in range(steps):
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("cancelled")

        trunk_grads = {key: np.zeros_like(weights[key]) for key in trunk_keys}
        head_grads = {key: np.zeros_like(weights[key]) for key in head_keys}
        losses = []

        for head, image in enumerate(images):
            h, w, _ = image.shape
            n = h * w
            batch = min(max_batch, n)
            idx = rng.integers(0, n, size=batch, dtype=np.int64)
            cached = feature_cache[head]
            if cached is not None:
                x = cached[0][idx]
                y = cached[1][idx]
            else:
                x = features_for_indices(w, h, freqs, idx)
                y = image.reshape(-1, 3)[idx]

            a = x
            activations = [a]
            zs = []
            for i in range(num_hidden_layers):
                z = a @ weights[f"W{i}"].T + weights[f"b{i}"]
                zs.append(z)
                a = np.sin(omega0 * z) if i == 0 else np.sin(z)
                activations.append(a)

            head_w = weights[f"H{head}_W"]
            head_b = weights[f"H{head}_b"]
            logits = a @ head_w.T + head_b
            out = _sig(logits)
            dlogits = (out - y) * out * (1.0 - out) * (2.0 / batch)
            head_grads[f"H{head}_W"] += dlogits.T @ a
            head_grads[f"H{head}_b"] += dlogits.sum(axis=0)
            da = dlogits @ head_w

            for i in range(num_hidden_layers - 1, -1, -1):
                if i == 0:
                    dz = da * omega0 * np.cos(omega0 * zs[i])
                else:
                    dz = da * np.cos(zs[i])
                trunk_grads[f"W{i}"] += dz.T @ activations[i]
                trunk_grads[f"b{i}"] += dz.sum(axis=0)
                if i > 0:
                    da = dz @ weights[f"W{i}"]

            losses.append(float(np.mean((out - y) ** 2)))

        inv_heads = 1.0 / float(num_heads)
        for key in trunk_keys:
            trunk_grads[key] *= inv_heads

        t = step + 1
        lr = lr0 * (0.1 + 0.45 * (1.0 + math.cos(math.pi * t / steps)))
        beta1_t = 1.0 - beta1 ** t
        beta2_t = 1.0 - beta2 ** t
        for key, grad in trunk_grads.items():
            m[key] *= beta1
            m[key] += (1.0 - beta1) * grad
            v[key] *= beta2
            v[key] += (1.0 - beta2) * (grad * grad)
            mhat = m[key] / beta1_t
            vhat = v[key] / beta2_t
            weights[key] -= (lr * mhat / (np.sqrt(vhat) + eps)).astype(np.float32)
        for key, grad in head_grads.items():
            m[key] *= beta1
            m[key] += (1.0 - beta1) * grad
            v[key] *= beta2
            v[key] += (1.0 - beta2) * (grad * grad)
            mhat = m[key] / beta1_t
            vhat = v[key] / beta2_t
            weights[key] -= (lr * mhat / (np.sqrt(vhat) + eps)).astype(np.float32)

        if progress is not None:
            progress(t, steps)
        if step == 0 or t % max(1, steps // 10) == 0 or t == steps:
            log(f"  step {t:5d}/{steps}  loss {float(np.mean(losses)):.6f}  elapsed {time.time() - t0:.1f}s")

    return weights, freqs, hidden, num_hidden_layers, num_heads, time.time() - t0


def save_numpy_weights(weights, path: Path, omega0: float, num_hidden_layers: int, num_heads: int):
    saved = {k: np.array(v, copy=True, dtype=np.float32) for k, v in weights.items()}
    saved["W0"] *= float(omega0)
    saved["b0"] *= float(omega0)
    saved["num_hidden"] = np.array(int(num_hidden_layers), dtype=np.int32)
    saved["num_heads"] = np.array(int(num_heads), dtype=np.int32)
    saved["num_layers"] = np.array(int(num_hidden_layers) + 1, dtype=np.int32)
    np.savez_compressed(path, **saved)


def _ssim(original, reconstructed):
    weights = np.array([0.299, 0.587, 0.114], dtype=np.float32)
    a = (original @ weights).astype(np.float32, copy=False)
    b = (reconstructed @ weights).astype(np.float32, copy=False)
    h, w = a.shape
    window, stride = 8, 4
    if h < window or w < window:
        return 0.0
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    wa = np.lib.stride_tricks.sliding_window_view(a, (window, window))[::stride, ::stride]
    wb = np.lib.stride_tricks.sliding_window_view(b, (window, window))[::stride, ::stride]
    mu_a = wa.mean(axis=(-2, -1), dtype=np.float32)
    mu_b = wb.mean(axis=(-2, -1), dtype=np.float32)
    var_a = np.clip((wa * wa).mean(axis=(-2, -1), dtype=np.float32) - mu_a * mu_a, 0.0, None)
    var_b = np.clip((wb * wb).mean(axis=(-2, -1), dtype=np.float32) - mu_b * mu_b, 0.0, None)
    cov = (wa * wb).mean(axis=(-2, -1), dtype=np.float32) - mu_a * mu_b
    value = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / (
        (mu_a * mu_a + mu_b * mu_b + c1) * (var_a + var_b + c2)
    )
    return float(np.mean(value, dtype=np.float64))


def metrics(original, reconstructed):
    mse = float(np.mean((original.astype(np.float32) - reconstructed.astype(np.float32)) ** 2))
    psnr = 99.0 if mse <= 1e-12 else 10.0 * math.log10(1.0 / mse)
    return psnr, float(_ssim(original, reconstructed))


def save_residual(residual: np.ndarray, path: Path, scale: int, quality: int, fmt: str):
    h, w, _ = residual.shape
    if scale == 1:
        low = residual
    else:
        rw, rh = max(1, math.ceil(w / scale)), max(1, math.ceil(h / scale))
        tmp = np.clip(np.rint(residual * 127.5 + 127.5), 0, 255).astype(np.uint8)
        low_u8 = np.asarray(
            Image.fromarray(tmp, "RGB").resize((rw, rh), Image.Resampling.BOX),
            dtype=np.float32,
        )
        low = (low_u8 / 255.0 - 0.5) * 2.0
    multiplier = max(1e-4, float(np.max(np.abs(low))))
    encoded = np.clip(low / (2.0 * multiplier) + 0.5, 0.0, 1.0)
    arr = np.clip(np.rint(encoded * 255.0), 0, 255).astype(np.uint8)
    image = Image.fromarray(arr, "RGB")
    if fmt.lower() == "png":
        image.save(path, format="PNG", optimize=True)
    else:
        image.save(path, format="WEBP", quality=int(quality), method=6)
    return multiplier




def choose_base_render_size(width: int, height: int, enabled: bool, max_pixels: int = 900_000):
    if not enabled or width * height <= int(max_pixels):
        return int(width), int(height)
    scale = math.sqrt(float(max_pixels) / float(width * height))
    return max(8, int(round(width * scale))), max(8, int(round(height * scale)))


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def build_bundle(images, args, output: Path, log=print, progress=None, cancel_event=None):
    script_dir = Path(__file__).resolve().parent
    tmp = Path(tempfile.mkdtemp(prefix="siren_bundle_"))
    try:
        (tmp / "models").mkdir()
        (tmp / "residuals").mkdir()
        image_paths = [Path(p) for p in images]
        group_size = max(1, int(getattr(args, "model_group_size", 1)))
        groups = [image_paths[i:i + group_size] for i in range(0, len(image_paths), group_size)]
        total_images = len(image_paths)
        manifest = {
            "format": "siren-image-bundle",
            "version": 2,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "settings": {
                "model_group_size": group_size,
                "resolution_mode": str(getattr(args, "resolution_mode", "auto")),
                "max_side": int(getattr(args, "max_side", getattr(args, "size", DEFAULT_MAX_SIDE))),
                "max_pixels": int(getattr(args, "max_pixels", DEFAULT_MAX_PIXELS)),
                "large_image_fast": bool(getattr(args, "large_image_fast", True)),
                "base_render_pixels": int(getattr(args, "base_render_pixels", 900_000)),
            },
            "groups": [],
            "images": [],
        }
        total_start = time.time()
        used_names: set[str] = set()
        done_before_group = 0

        for group_number, group_paths in enumerate(groups, 1):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("cancelled")
            log(f"\n=== 模型组 {group_number}/{len(groups)} · {len(group_paths)} 张照片 ===")
            prepared = []
            for path in group_paths:
                image, arr, info = load_image(path, args)
                source_w, source_h, target_w, target_h, scale = info
                prepared.append((path, arr, info))
                log(
                    f"  {path.name}: {source_w}x{source_h} -> {target_w}x{target_h} "
                    f"(scale {scale:.3f})"
                )

            def on_step(step, total, group_number=group_number, group_len=len(group_paths), done_before=done_before_group):
                if progress is not None:
                    overall = (done_before + (step / max(1, total)) * group_len) / max(1, total_images)
                    progress(
                        overall,
                        f"训练模型组 {group_number}/{len(groups)} · {step}/{total} 步",
                    )

            model_weights, freqs, hidden, num_hidden, num_heads, train_seconds = train_siren_group(
                [item[1] for item in prepared],
                args,
                log=log,
                progress=on_step,
                cancel_event=cancel_event,
            )
            model_name = f"model_{group_number:03d}.npz"
            model_path = tmp / "models" / model_name
            save_numpy_weights(model_weights, model_path, args.omega0, num_hidden, num_heads)
            weights = load_npz_weights(model_path)
            model_bytes = int(model_path.stat().st_size)
            manifest["groups"].append({
                "group": group_number,
                "model": f"models/{model_name}",
                "num_heads": num_heads,
                "num_hidden": num_hidden,
                "hidden": hidden,
                "train_seconds": float(train_seconds),
                "model_bytes": model_bytes,
            })
            log(
                f"  模型已保存：{model_name} · {num_heads} 个输出头 · "
                f"{model_bytes / 1024:.1f} KB · 训练 {train_seconds:.1f}s"
            )

            for head_index, (image_path, arr, info) in enumerate(prepared):
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError("cancelled")
                source_w, source_h, target_w, target_h, scale = info
                h, w, _ = arr.shape
                stem = image_path.stem.replace(" ", "_")
                if stem in used_names:
                    stem = f"{stem}_{group_number}_{head_index + 1}"
                used_names.add(stem)

                base_w, base_h = choose_base_render_size(
                    w,
                    h,
                    bool(getattr(args, "large_image_fast", True)),
                    int(getattr(args, "base_render_pixels", 900_000)),
                )
                base = generate_base(
                    weights,
                    base_w,
                    base_h,
                    freqs,
                    batch=args.batch,
                    head_index=head_index,
                )
                if (base_w, base_h) != (w, h):
                    base = resize_base(base, w, h)
                    log(
                        f"  大图加速：基础图 {base_w}x{base_h} -> {w}x{h}，" 
                        "高分辨率细节由残差补回"
                    )
                base_psnr, base_ssim = metrics(arr, base)
                residual = arr - base
                residual_path = tmp / "residuals" / f"{stem}.{args.residual_format}"
                multiplier = save_residual(
                    residual,
                    residual_path,
                    args.residual_scale,
                    args.residual_quality,
                    args.residual_format,
                )
                decoded_residual = load_residual(
                    residual_path,
                    w,
                    h,
                    args.residual_scale,
                    multiplier,
                )
                final = np.clip(base + decoded_residual, 0.0, 1.0)
                final_psnr, final_ssim = metrics(arr, final)

                manifest["images"].append({
                    "name": stem,
                    "source_name": image_path.name,
                    "source_width": source_w,
                    "source_height": source_h,
                    "width": w,
                    "height": h,
                    "resolution_scale": float(scale),
                    "base_render_width": int(base_w),
                    "base_render_height": int(base_h),
                    "model": f"models/{model_name}",
                    "model_type": "siren_shared_trunk_multihead",
                    "model_group": group_number,
                    "model_group_size": num_heads,
                    "head_index": head_index,
                    "num_heads": num_heads,
                    "num_hidden": num_hidden,
                    "residual": f"residuals/{stem}.{args.residual_format}",
                    "residual_scale": int(args.residual_scale),
                    "residual_multiplier": float(multiplier),
                    "residual_format": args.residual_format,
                    "freqs": freqs,
                    "hidden": int(hidden),
                    "omega_0": float(args.omega0),
                    "output_activation": "sigmoid",
                    "base_psnr": float(base_psnr),
                    "base_ssim": base_ssim,
                    "final_psnr": float(final_psnr),
                    "final_ssim": final_ssim,
                    "train_seconds": float(train_seconds),
                    "model_bytes": model_bytes,
                    "residual_bytes": int(residual_path.stat().st_size),
                })
                log(
                    f"  head {head_index + 1}/{num_heads} · {image_path.name}: "
                    f"base PSNR {base_psnr:.2f} dB -> final PSNR {final_psnr:.2f} dB · "
                    f"residual {residual_path.stat().st_size / 1024:.1f} KB"
                )
                if progress is not None:
                    progress(
                        (done_before_group + head_index + 1) / max(1, total_images),
                        f"已完成 {done_before_group + head_index + 1}/{total_images} 张",
                    )
            done_before_group += len(group_paths)

        write_text(tmp / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        include_exe = bool(
            getattr(args, "include_receiver_exe", False)
            or getattr(args, "include_app_exe", False)
        )
        app_exe = None
        if getattr(sys, "frozen", False):
            app_exe = Path(sys.executable)
        else:
            for candidate_name in (
                "记忆邮局.exe",
                "MemoryPost.exe",
                "dist/记忆邮局.exe",
                "dist/MemoryPost.exe",
            ):
                candidate = script_dir / candidate_name
                if candidate.exists():
                    app_exe = candidate
                    break

        bundled_exe_name = ""
        if include_exe and app_exe is not None and app_exe.exists():
            bundled_exe_name = app_exe.name
            shutil.copy2(app_exe, tmp / bundled_exe_name)
            log(f"已把 {bundled_exe_name} 一起打进包裹。")
        elif include_exe:
            log("警告：当前没有可打包的程序 exe，包裹只包含模型与残差。")

        if bundled_exe_name:
            receiver_help = (
                f"1. 解压本 ZIP。\n"
                f"2. 双击里面的 {bundled_exe_name}。\n"
                f"3. 切换到“接收”，选择本 ZIP，点击“还原完整照片”。\n"
            )
        else:
            receiver_help = (
                "本包裹没有内置接收程序。\n"
                "请向发送者索取“记忆邮局.exe”。\n"
                "运行后切换到“接收”，选择本 ZIP 即可还原照片。\n"
            )
        write_text(
            tmp / "使用说明.txt",
            "记忆邮局 · 接收说明\n"
            "====================\n\n"
            + receiver_help
            + "\n包裹中包含：模型、残差、图片清单。\n"
            + "同一组照片可能共用一个模型文件，但每张照片仍有自己的输出头与残差。\n"
            + "所有重建均在本机完成，不需要联网。\n",
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(tmp.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(tmp).as_posix())

        log(f"\nBundle: {output.resolve()}")
        log(f"Bundle size: {output.stat().st_size / 1024 / 1024:.2f} MB")
        log(f"Total sender time: {time.time() - total_start:.1f}s")
        log("Send this ZIP to your friend. Receiver instructions are inside.")
        if progress is not None:
            progress(1.0, "打包完成")
        return {
            "bundle": str(output.resolve()),
            "bundle_bytes": int(output.stat().st_size),
            "images": manifest["images"],
            "groups": manifest["groups"],
            "total_seconds": float(time.time() - total_start),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Train SIREN memory bundles for photos.")
    parser.add_argument("images", nargs="+", help="Image files to send")
    parser.add_argument("-o", "--output", default="bundle.zip", help="Output bundle ZIP")
    parser.add_argument("--resolution-mode", choices=["auto", "fixed"], default="auto")
    parser.add_argument("--max-side", type=int, default=DEFAULT_MAX_SIDE)
    parser.add_argument("--max-pixels", type=int, default=DEFAULT_MAX_PIXELS)
    parser.add_argument("--size", type=int, default=DEFAULT_MAX_SIDE, help="Compatibility alias for --max-side")
    parser.add_argument("--model-group-size", type=int, default=1, help="Photos per shared model")
    parser.add_argument("--no-fast-large-images", dest="large_image_fast", action="store_false", help="Disable low-resolution base rendering for large photos")
    parser.add_argument("--base-render-pixels", type=int, default=900_000, help="Maximum pixels used to render a base image before residual correction")
    parser.set_defaults(large_image_fast=True)
    parser.add_argument("--steps", type=int, default=800, help="Training steps per image/head")
    parser.add_argument("--batch", type=int, default=8192)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--freqs", default="1,2,4,8")
    parser.add_argument("--omega0", type=float, default=30.0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--residual-scale", type=int, default=1, choices=[1, 2, 4])
    parser.add_argument("--residual-quality", type=int, default=95)
    parser.add_argument("--residual-format", choices=["webp", "png"], default="webp")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--include-receiver-exe", action="store_true")
    args = parser.parse_args()
    np.random.seed(args.seed)
    build_bundle(args.images, args, Path(args.output))


if __name__ == "__main__":
    main()
