# Architecture

Memory Post is a local photo-to-model pipeline built around SIREN-style implicit neural representations.

## High-level pipeline

```text
source photos
  → target-size selection
  → Fourier coordinate features
  → SIREN training
  → base image generation
  → residual compression
  → manifest + model(s) + residuals → ZIP
```

Receiver:

```text
bundle.zip
  → manifest.json
  → NumPy forward pass
  → base image
  → residual decode + upscale
  → PNG/JPG output
```

## Modules

### `memory_post.py`

PyQt6 application entry point.

- Frameless rounded glass-style window
- Shared title bar with Send / Receive tabs
- Sender and receiver pages
- QThread workers for training and reconstruction
- Drag-and-drop zones
- Progress, cancellation, logs, and toast notifications

### `sender.py`

Training and packaging backend.

- Adaptive target-size calculation
- SIREN initialization and NumPy backpropagation
- Multi-head shared-model training
- Residual encoding
- Manifest generation
- ZIP packaging
- `--selftest-full` support

### `receiver.py`

Bundle reconstruction backend.

- ZIP or directory bundle resolution
- Manifest validation
- Model loading
- Multi-head selection through `head_index`
- Base-image generation and optional low-resolution base render
- Residual upscaling and addition
- PNG/JPG export

### `siren_common.py`

Shared NumPy utilities.

- Fourier features for full images or selected pixels
- Legacy single-head and new multi-head forward passes
- Base-image resizing
- Residual loading
- Manifest reading

## Model architecture

### Single photo per model

```text
(x, y)
→ Fourier features
→ N sine hidden layers
→ output head
→ RGB
```

### Multiple photos per model

```text
(x, y)
→ Fourier features
→ shared sine hidden trunk
→ one output head per photo
→ RGB for the selected photo
```

Each manifest entry stores:

- model file path
- `head_index`
- `num_heads`
- target width and height
- frequency list
- residual metadata

The shared trunk is trained with gradients from all heads in the group. Every head receives one update per training step, so a group of N photos costs roughly N times the compute of a single head.

## Why residuals

A small SIREN captures low-frequency structure well but tends to soften high-frequency detail. The residual stores the difference between the source and the network base image. This gives a strong quality/size trade-off:

- model: tens to hundreds of KB
- residual: often tens of KB at WebP q95
- bundle: commonly 0.1–0.3 MB

The network remains a visible “memory” component while the residual keeps the final result close to the original.

## Threading

Training and reconstruction run in `QThread` workers. The GUI remains responsive and can cancel long tasks. NumPy releases the GIL for most matrix operations, so the UI can repaint while training runs.

## Offline guarantees

The app performs no runtime network requests. All images, models, and residuals stay on the local machine unless the user manually sends a bundle.
