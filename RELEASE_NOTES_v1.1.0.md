# Memory Post 1.1.0

This release focuses on flexible model grouping and large-image performance.

## Highlights

- Default behavior remains one model per photo.
- New “photos per model” option: 1–8.
- Shared models use one SIREN trunk with one output head per photo.
- Automatic source-resolution mode: small photos are not upscaled; large photos are capped by longest side and total pixels.
- Large-image acceleration: render a smaller base image, then recover detail from the full-resolution residual.
- Hybrid feature caching: fast precomputed features for small photos, on-demand sampling for large photos.
- Vectorized SSIM for faster quality evaluation.
- New sample images and demo bundle.

## Tested

- Two photos sharing one model: one `.npz`, two heads, two residuals, successful reconstruction.
- Mixed resolutions in one shared model: successful reconstruction.
- 3000×2000 source → 1024×683 training size → 671×447 accelerated base render.
- Full exe selftest with bundled executable and two-photo shared model.

## Notes

- The Windows executable is unsigned; SmartScreen may show an unknown-publisher warning.
- The result is visually near-lossless with residuals, not mathematically lossless.
