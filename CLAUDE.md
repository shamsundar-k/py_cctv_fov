# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`py-fov` is a CCTV camera Field-of-View (FOV) visualiser built with PySide6 and PyOpenGL. It renders a 3-panel GUI: a 3D OpenGL view (centre), a 2D top-down view (right upper), and a 2D side-elevation view (right lower), with a slider/controls panel on the left.

## Commands

This project uses `uv` for dependency management (Python 3.12 required).

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py
```

## Package Structure

```
fov/
├── theme.py          # DARK_MODE global, _LIGHT/_DARK dicts, TH() accessor
├── constants.py      # SENSOR_FORMATS, ASPECT_RATIOS, CAMERA_MODEL, DORI_* tables
├── geometry.py       # Pure-math FOV/geometry functions
├── dialogs.py        # CameraParamsDialog (QDialog)
├── gl_view.py        # GLView (QOpenGLWidget) — 3D FOV render
├── views2d.py        # Views2D (QWidget) — 2D top + side elevation views
├── control_panel.py  # ControlPanel (QWidget) — sliders, stats, DORI legend
└── main_window.py    # MainWindow (QMainWindow) — assembles all panels
main.py               # Entry point
```

## Architecture

### Data flow

`MainWindow._refresh()` reads slider values from `ControlPanel`, calls `compute_geometry()`, then pushes the resulting `geo` dict to `GLView.set_geometry()` and `Views2D.set_geometry()`. A 40 ms debounce timer prevents redundant redraws during slider drag.

### Key geometry functions (`fov/geometry.py`)

- `compute_geometry(f, H, target_dist, target_h, model)` — master function; returns a `geo` dict consumed by all views.
- `interpolate_angles(f, model)` — returns `(H_angle, V_angle)`. Uses manual datasheet angles (primary) or sensor-physics formula (fallback, when `sensor_width > 0`).
- `compute_tilt()` — auto-calculates camera tilt so the top FOV ray hits `target_height` at `target_distance`.
- `trapezoid_corners()` — ground-plane FOV footprint corners, used by both 3D and 2D renderers.

### Mutable globals and import rules

There are two mutable module-level globals:

| Global | Module | Type | Pattern |
|---|---|---|---|
| `DARK_MODE` | `fov.theme` | `bool` (rebound on toggle) | Always access as `theme.DARK_MODE` via module ref |
| `CAMERA_MODEL` | `fov.constants` | `dict` (mutated in place) | `from .constants import CAMERA_MODEL` then `.update()` is safe |

**Critical:** `DARK_MODE` is a scalar that gets rebound (`theme.DARK_MODE = not theme.DARK_MODE` in `MainWindow._toggle_theme`). Any module that does `from fov.theme import DARK_MODE` will hold a stale reference after the toggle. The two places in `views2d.py` that read `DARK_MODE` directly use `_theme.DARK_MODE` (module-attribute lookup) to stay live. `TH()` is always safe to import by name because it re-reads `DARK_MODE` from its own module globals at call time.

### Adding a new view or feature

1. Add pure logic to `geometry.py` (no Qt imports).
2. Create a new widget module in `fov/` importing from `theme`, `constants`, and `geometry`.
3. Wire it into `MainWindow` in `main_window.py`.
