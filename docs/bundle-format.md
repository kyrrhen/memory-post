# Bundle Format

A bundle is a ZIP archive. Version 1.1 uses bundle format version 2 while the receiver remains compatible with legacy format version 1.

## Layout

```text
bundle.zip
├─ manifest.json
├─ models/
│  └─ model_001.npz
├─ residuals/
│  ├─ photo_a.webp
│  └─ photo_b.webp
├─ 使用说明.txt
└─ 记忆邮局.exe          # optional, when “include this tool” is checked
```

## manifest.json

Example:

```json
{
  "format": "siren-image-bundle",
  "version": 2,
  "created": "2026-10-18 12:00:00",
  "settings": {
    "model_group_size": 2,
    "resolution_mode": "auto",
    "max_side": 1024,
    "max_pixels": 1600000,
    "large_image_fast": true,
    "base_render_pixels": 900000
  },
  "groups": [
    {
      "group": 1,
      "model": "models/model_001.npz",
      "num_heads": 2,
      "num_hidden": 4,
      "hidden": 128,
      "train_seconds": 120.0,
      "model_bytes": 200000
    }
  ],
  "images": [
    {
      "name": "photo_a",
      "source_name": "photo_a.jpg",
      "source_width": 3000,
      "source_height": 2000,
      "width": 1024,
      "height": 683,
      "resolution_scale": 0.341,
      "base_render_width": 671,
      "base_render_height": 447,
      "model": "models/model_001.npz",
      "model_type": "siren_shared_trunk_multihead",
      "model_group": 1,
      "model_group_size": 2,
      "head_index": 0,
      "num_heads": 2,
      "num_hidden": 4,
      "residual": "residuals/photo_a.webp",
      "residual_scale": 1,
      "residual_multiplier": 0.42,
      "residual_format": "webp",
      "freqs": [1.0, 2.0, 4.0, 8.0],
      "hidden": 128,
      "omega_0": 30.0,
      "output_activation": "sigmoid",
      "base_psnr": 26.0,
      "base_ssim": 0.81,
      "final_psnr": 43.0,
      "final_ssim": 0.99,
      "train_seconds": 120.0,
      "model_bytes": 200000,
      "residual_bytes": 30000
    }
  ]
}
```

## Model file

The model is a compressed NumPy `.npz` file.

New multi-head model keys:

```text
W0, b0, W1, b1, ...          # shared hidden trunk
H0_W, H0_b, H1_W, H1_b, ...  # output heads
num_hidden                    # number of sine hidden layers
num_heads                     # number of output heads
num_layers                    # legacy compatibility metadata
```

The first-layer `omega_0` is folded into `W0` and `b0` before export, so the receiver uses ordinary `sin()` for every hidden layer.

Legacy format version 1 models use `W0..Wn`, `b0..bn`, and `num_layers` without heads. The receiver detects the format from `num_heads`.

## Residual file

The residual is stored as an RGB image:

1. Compute `residual = source - base`.
2. Optionally downsample the residual by 2 or 4.
3. Find `multiplier = max(abs(residual))`.
4. Encode to `[0, 1]` as `residual / (2 * multiplier) + 0.5`.
5. Save as WebP or PNG.
6. At reconstruction, load and reverse the mapping.
7. Upscale if needed and add to the base image.

The `residual_multiplier` value in the manifest must be used by the receiver.

## Base-render dimensions

For large images, the sender may render the network at a smaller size:

```json
"base_render_width": 671,
"base_render_height": 447
```

The receiver must render at those dimensions first, then resize to `width × height` with the same bicubic path before adding the residual. This keeps the residual mathematically consistent with the sender.

## Compatibility rules

- Unknown manifest fields should be ignored when possible.
- Do not remove `version`, `images`, `model`, `residual`, or `freqs`.
- A new incompatible format should increment `version`.
- Receivers should validate model paths to avoid arbitrary file access when opening untrusted bundles.
