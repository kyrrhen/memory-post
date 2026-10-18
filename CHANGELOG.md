# Changelog

All notable changes to Memory Post are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-10-18

### Added

- Optional 1–8 photos per shared model.
- Shared SIREN trunk with one output head per photo.
- `head_index` support in the bundle manifest and receiver.
- Automatic source-resolution mode with longest-side and pixel-count caps.
- Per-photo source → training resolution display in the GUI.
- Model-group display in the photo list.
- Large-image acceleration mode: render a smaller base image and recover details from the full-resolution residual.
- Hybrid feature cache: precompute Fourier features for small images, sample on demand for large images.
- Vectorized SSIM calculation.
- `--selftest-full` shared-model round-trip test.
- Example images and demo bundle.

### Changed

- Default resolution mode is now `auto` instead of a fixed 512 px.
- Presets now use adaptive resolution: quick 768 px cap, balanced 1024 px cap, high quality 1536 px cap.
- Bundle format version bumped to 2.
- Receiver can read both legacy single-head bundles and new multi-head bundles.

### Performance

- Avoids full-image feature allocation for large photos.
- Uses a 192 MB feature-cache budget for faster small-image training.
- Caps base-image rendering at about 0.9 MP for large images.
- Vectorized SSIM matches the old loop within `1e-7`.

## [1.0.0] - 2026-10-18

### Added

- Unified Windows GUI for sending and receiving.
- PyQt6 Apple-style glass interface.
- Per-image SIREN training in NumPy.
- WebP/PNG residuals with adjustable scale and quality.
- One-click bundle creation and reconstruction.
- Optional inclusion of the executable inside the bundle.
- Background workers, cancellation, progress, and run logs.
- Single-file PyInstaller build.

[1.1.0]: https://github.com/YOUR_GITHUB_USERNAME/memory-post/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/YOUR_GITHUB_USERNAME/memory-post/releases/tag/v1.0.0
