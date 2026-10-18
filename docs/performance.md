# Performance Notes

Memory Post uses NumPy only for training and inference. The design favors predictable CPU behavior and small model files over GPU peak throughput.

## Target resolution

Default mode:

```text
auto · source resolution
```

The sender computes:

```text
scale = min(
  1.0,
  max_side / longest_side,
  sqrt(max_pixels / total_pixels)
)
```

Defaults:

- `max_side = 1024`
- `max_pixels = 1_600_000`
- small images are never upscaled

This avoids forcing every image to 512 px and prevents very large photos from causing excessive inference time or memory use.

## Feature caching

Fourier feature arrays are large: approximately `pixels × feature_dim × 4 bytes`.

Strategy:

- accumulate a feature cache budget, default 192 MB
- precompute features for images that fit
- generate features for only the sampled batch when an image does not fit

This restores fast indexing for normal photos while keeping large photos memory-safe.

## Vectorized SSIM

The old implementation looped over every 8×8 window in Python. The current implementation uses `sliding_window_view` with stride 4 and vectorized means, variances, and covariance.

Measured difference from the old loop on a test image: `< 1e-7`.

## Large-image base render

For images above about 0.9 MP, the base image is rendered at a reduced resolution and upscaled before residual correction.

Why:

- SIREN base images are smooth
- the residual already stores high-frequency detail
- rendering fewer pixels is substantially faster
- receiver behavior is deterministic because the render dimensions are stored in the manifest

## Reference results

### Two photos, shared model

- 512×341 each
- 120 steps, 3×64
- one model file, two heads
- bundle: ~98.6 KB
- final PSNR: ~42.5 dB each

### Large photo

- source: 3000×2000
- target: 1024×683
- accelerated base render: 671×447
- 40 training steps
- build/train/package: ~2.84 s
- receiver reconstruction: ~1.35 s
- final PSNR: 42.36 dB

### Default-quality single photo

- 512×341
- 800 steps, 4×128
- bundle: ~226.9 KB
- final PSNR: 43.64 dB
- SSIM: 0.9913

Wall-clock times vary significantly with CPU and system load.
