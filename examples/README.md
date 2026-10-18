# Examples

This directory contains a small self-contained demo.

## Files

- `images/sunset.png`
- `images/aurora.png`
- `demo-bundle.zip`

The demo bundle contains:

- one shared model with two output heads
- two residuals
- a manifest
- receiver instructions

## Try the receiver

1. Open Memory Post.
2. Switch to “接收”.
3. Select `examples/demo-bundle.zip`.
4. Choose an output folder.
5. Click “还原完整照片”.

## Rebuild the demo bundle

From the repository root:

```powershell
python scripts/build_demo_bundle.py
```

The script uses 120 training steps per head and a 640 px maximum side, so it completes quickly on a CPU.
