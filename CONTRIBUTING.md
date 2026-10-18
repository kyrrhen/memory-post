# Contributing

Thanks for taking the time to improve Memory Post.

## Development setup

```powershell
git clone <repository-url>
cd memory-post
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Run the app

```powershell
python memory_post.py
```

## Run tests

```powershell
pytest
```

Tests should stay fast. Use tiny synthetic images and low step counts for round-trip checks.

## Build the Windows executable

```powershell
.\build_exe.bat
```

The output is `dist/MemoryPost.exe`.

## Pull request checklist

- Keep changes focused and explain the user-facing impact.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` for user-visible changes.
- Update the bundle-format documentation if manifest fields change.
- Run `pytest` and the executable selftest when packaging changes.
- Do not commit build outputs, local bundles, or generated `received/` directories.

## Code layout

- `memory_post.py` — PyQt6 GUI, unified send/receive pages
- `sender.py` — training, residuals, manifest, ZIP packaging
- `receiver.py` — bundle loading and reconstruction
- `siren_common.py` — Fourier features, NumPy forward pass, shared helpers

## Compatibility

- Keep the receiver able to open legacy bundles where practical.
- When changing the bundle format, bump `manifest.json` version and document it.
- Preserve offline operation: no telemetry or runtime network dependency.

## Style

- Python 3.10+
- Prefer clear names and small functions over clever shortcuts.
- Keep NumPy arrays in `float32` on the hot path.
- Avoid adding heavy dependencies without discussion.
