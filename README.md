# py-fov

A CCTV camera Field-of-View (FOV) visualizer built with PySide6 and PyOpenGL for analyzing and understanding camera coverage areas.

## Overview

py-fov is a desktop application that provides real-time visualization of camera fields-of-view in three dimensions. It displays:

- **3D OpenGL View** (center panel) — Interactive 3D rendering of the camera FOV
- **2D Top-Down View** (right upper) — Bird's-eye perspective of coverage area
- **2D Side-Elevation View** (right lower) — Side profile of coverage
- **Control Panel** (left) — Sliders, camera parameters, and DORI (Detection, Observation, Recognition, Identification) legend

## Features

- Multiple camera sensor format support
- Adjustable focal length, height, tilt, and pan angles
- Real-time interactive visualization
- DORI distance indicators for camera performance benchmarking
- Dark/light theme toggle
- Support for various camera models with pre-configured specifications
- Ground-plane footprint visualization

## Requirements

- Python 3.12 or higher
- `uv` package manager

## Installation

1. Clone or download this repository:
   ```bash
   cd py_fov
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

## Running the Application

```bash
uv run python main.py
```

The application will launch with the 3D FOV visualizer and interactive controls.

## Usage

### Controls

- **Focal Length** — Adjust camera zoom (in mm)
- **Height** — Camera mounting height above ground (in meters)
- **Distance** — Target distance for auto-tilt calculation
- **Height (target)** — Target height for auto-tilt
- **Tilt/Pan** — Camera rotation angles
- **Sliders** — Fine-tune all parameters in real-time

### Theme Toggle

Use the menu or keyboard shortcut to switch between dark and light themes.

### DORI Legend

The DORI indicators show distance ranges for:
- **Detection** — Detect movement
- **Observation** — Observe activity
- **Recognition** — Recognize face/object
- **Identification** — Identify specific details

## Project Structure

```
fov/
├── theme.py          # Theme management (dark/light mode)
├── constants.py      # Camera models, sensor formats, DORI tables
├── geometry.py       # FOV geometry calculations and math
├── dialogs.py        # Camera parameters dialog
├── gl_view.py        # 3D OpenGL rendering
├── views2d.py        # 2D top-down and side-elevation views
├── control_panel.py  # Left control panel with sliders
└── main_window.py    # Main application window (assembles all panels)
main.py               # Application entry point
```

## Architecture

### Data Flow

`MainWindow._refresh()` retrieves slider values from the control panel, computes camera geometry, and pushes results to the 3D and 2D views with a 40ms debounce timer to prevent redundant redraws.

### Key Functions

- `compute_geometry()` — Master calculation function returning geometry dict
- `interpolate_angles()` — Computes horizontal and vertical FOV angles
- `compute_tilt()` — Auto-calculates camera tilt for target coverage
- `trapezoid_corners()` — Calculates ground-plane FOV footprint

## Development

### Adding Features

1. Add pure calculation logic to `geometry.py` (no Qt imports)
2. Create a widget module in `fov/` with necessary imports
3. Wire the new widget into `MainWindow`

### Global State

The project uses two mutable globals:
- `DARK_MODE` in `theme.py` — Access via `theme.DARK_MODE` (module attribute lookup)
- `CAMERA_MODEL` in `constants.py` — Can be mutated in place with `.update()`

## License

[Add your license here]

## Contributing

[Contribution guidelines if applicable]
