# CCTV Camera Field-of-View: Algorithm Reference

A language-agnostic description of every calculation involved in computing a
CCTV camera's field of view, ground footprint, and DORI coverage zones.
All units are **millimetres** for optical dimensions and **metres** for
real-world distances unless stated otherwise.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Inputs & Parameters](#2-inputs--parameters)
3. [Camera FOV Angles](#3-camera-fov-angles)
4. [Auto-Tilt Calculation](#4-auto-tilt-calculation)
5. [Ground Distance Bounds](#5-ground-distance-bounds-d_near-and-d_far)
6. [Horizontal Coverage Width](#6-horizontal-coverage-width)
7. [Coverage Area](#7-coverage-area)
8. [DORI Zone Calculations](#8-dori-zone-calculations)
9. [Ground Footprint Corners (Top-Down View)](#9-ground-footprint-corners-top-down-view)
10. [Full Algorithm Pseudocode](#10-full-algorithm-pseudocode)
11. [Reference Tables](#11-reference-tables)

---

## 1. Overview

A CCTV camera mounted on a wall or pole looks out at an angle (its *tilt*) and
sweeps a cone-shaped region of space.  Where that cone intersects the ground
plane it creates a **trapezoid** — wide at the far end, narrow at the near end.

The goal of these calculations is to answer:

- What **horizontal and vertical angles** does the lens produce?
- What **tilt** is needed so the top of the FOV cone grazes the top of a
  target object at a given distance?
- How **far** along the ground does the cone reach, and how **wide** is it?
- Up to what distance can the camera achieve each DORI quality level?

```
Side-elevation view
════════════════════════════════════════════════════════════

  Camera ──────────────────────────────────────  Height H
     \  ↑ tilt angle (from horizontal)
      \
  top  \___________________________ target top (target_h)   ← top ray
  ray   \
         \
  bottom  \______________________________  ground (0 m)     ← bottom ray
   ray     \
             \
              ↓ (continues below ground — unused)

              |<--- D_near --->|<------  D_far  ------>|
```

The camera is tilted **downward** from horizontal by the `tilt` angle.
The vertical FOV cone spans `V_angle` degrees total, so the top ray is at
`tilt − V_angle/2` below horizontal, and the bottom ray is at
`tilt + V_angle/2` below horizontal.

---

## 2. Inputs & Parameters

### 2a. Camera / Lens Parameters

| Symbol     | Description                              | Typical unit |
|------------|------------------------------------------|--------------|
| `f`        | Focal length                             | mm           |
| `f_min`    | Minimum focal length of zoom lens        | mm           |
| `f_max`    | Maximum focal length of zoom lens        | mm           |
| `H_max`    | Horizontal FOV at `f_min` (widest)       | degrees      |
| `H_min`    | Horizontal FOV at `f_max` (narrowest)    | degrees      |
| `V_max`    | Vertical FOV at `f_min` (widest)         | degrees      |
| `V_min`    | Vertical FOV at `f_max` (narrowest)      | degrees      |
| `sw`       | Sensor width (horizontal)                | mm           |
| `ar`       | Aspect ratio (width ÷ height)            | dimensionless|
| `R_H`      | Sensor horizontal pixel resolution       | pixels       |

> **Fixed vs. varifocal lenses**: A fixed lens has `f_min = f_max = f` so
> `H_max = H_min` and `V_max = V_min`. The interpolation step still works —
> it just always returns the single known angle.

### 2b. Scene Parameters

| Symbol        | Description                              | Unit |
|---------------|------------------------------------------|------|
| `H`           | Camera mounting height above ground      | m    |
| `target_dist` | Horizontal distance to target            | m    |
| `target_h`    | Target object height above ground        | m    |

### 2c. Derived / Computed

| Symbol      | Description                              |
|-------------|------------------------------------------|
| `H_angle`   | Horizontal FOV angle for current `f`     |
| `V_angle`   | Vertical FOV angle for current `f`       |
| `tilt`      | Camera tilt below horizontal             |
| `D_near`    | Horizontal distance to near edge of FOV  |
| `D_far`     | Horizontal distance to far edge of FOV   |
| `W_near`    | Width of FOV at `D_near`                 |
| `W_far`     | Width of FOV at `D_far`                  |
| `area`      | Ground coverage area                     |

---

## 3. Camera FOV Angles

FOV angles can be obtained in two ways.  **Method A (datasheet)** is preferred
when manufacturer-measured angles are available because it accounts for real
lens distortion.  **Method B (physics)** is a fallback using the thin-lens
model.

### Method A — Linear Interpolation from Datasheet Angles

Most manufacturers publish the horizontal and vertical FOV at the wide end
(`f_min`) and the telephoto end (`f_max`) of a varifocal lens.  Angles at
intermediate focal lengths are computed by linear interpolation.

```
t = (f − f_min) / (f_max − f_min)        // 0.0 at widest, 1.0 at narrowest

H_angle = H_max − t × (H_max − H_min)
V_angle = V_max − t × (V_max − V_min)
```

**Clamp `f`** to `[f_min, f_max]` before computing `t`.

> **Why the minus sign?** A longer focal length gives a **narrower** FOV, so
> as `t` goes from 0→1, the angle decreases from `H_max` → `H_min`.

**Worked example — varifocal 2.8–12 mm lens at f = 7.4 mm**

| Parameter | Value     |
|-----------|-----------|
| f_min     | 2.8 mm    |
| f_max     | 12.0 mm   |
| H_max     | 97.0°     |
| H_min     | 28.0°     |
| V_max     | 54.0°     |
| V_min     | 16.0°     |
| f         | 7.4 mm    |

```
t = (7.4 − 2.8) / (12.0 − 2.8) = 4.6 / 9.2 = 0.500

H_angle = 97.0 − 0.500 × (97.0 − 28.0) = 97.0 − 34.5 = 62.5°
V_angle = 54.0 − 0.500 × (54.0 − 16.0) = 54.0 − 19.0 = 35.0°
```

---

### Method B — Physics (Thin-Lens Formula)

When sensor dimensions are known but datasheet angles are not:

```
FOV = 2 × atan( sensor_dim / (2 × f) )       // result in radians → convert to degrees
```

- For **horizontal** FOV use `sensor_dim = sensor_width` (mm)
- For **vertical** FOV use `sensor_dim = sensor_width / aspect_ratio`

```
ASCII: sensor plane geometry

    ←── sensor_width ───→
    ┌─────────────────────┐
    │                     │     ← sensor plane
    └──────────┬──────────┘
               │  f (focal length)
               │
             [LENS]
               │   ╲
               │    ╲  half-angle = atan(sensor_width/2 / f)
               ↓     ╲
             scene
```

**Worked example — 1/2.8" sensor (5.37 mm wide), 16:9, f = 4 mm**

```
V_width  = 5.37 / (16/9) = 5.37 / 1.778 = 3.02 mm

H_angle  = 2 × atan(5.37 / (2 × 4.0))
         = 2 × atan(0.671)
         = 2 × 33.87°
         = 67.7°

V_angle  = 2 × atan(3.02 / (2 × 4.0))
         = 2 × atan(0.378)
         = 2 × 20.64°
         = 41.3°
```

---

## 4. Auto-Tilt Calculation

**Goal**: find the tilt angle so that the *top edge* of the vertical FOV
passes exactly through the point `(target_dist, target_h)` — i.e. the top of
the subject at the specified distance.

```
Side-elevation diagram (not to scale)
══════════════════════════════════════════════════════════

  Camera @ height H
    ╲
     ╲  ← tilt angle (θ) below horizontal
      ╲
       ╲──────────────── top ray (θ − V/2 below horizontal)
        ╲
         ╲
          ◉ ← target top: (target_dist, target_h)
          │
    ──────┼───────────────────────────────────── ground
          │
      target_dist
```

**Step 1**: Compute the angular elevation from the camera to the target top.

```
delta      = H − target_h              // vertical drop from camera to target top
top_angle  = atan( delta / target_dist )   // angle below horizontal to reach target top
```

**Step 2**: The top ray of the FOV is `V_angle/2` above the camera's pointing
direction.  For the top ray to hit the target, the pointing direction must be
`V_angle/2` further downward:

```
tilt = top_angle + V_angle / 2
```

**Validity checks** (return an error if either fails):

| Condition          | Reason                                                    |
|--------------------|-----------------------------------------------------------|
| `delta > 0`        | Camera must be above the target top                       |
| `target_dist > 0`  | Target must be at a positive distance                     |
| `tilt > V_angle/2` | Bottom ray must point at or below horizontal              |
| `tilt < 90°`       | Camera cannot point straight down                         |

**Worked example**

Camera height `H = 4 m`, target height `target_h = 1.8 m` (person),
target distance `target_dist = 12 m`, `V_angle = 35°`.

```
delta      = 4.0 − 1.8 = 2.2 m
top_angle  = atan(2.2 / 12.0) = atan(0.1833) = 10.4°

tilt       = 10.4 + 35/2 = 10.4 + 17.5 = 27.9°

Check: tilt (27.9°) > V_angle/2 (17.5°)  ✓
Check: tilt (27.9°) < 90°                ✓
```

---

## 5. Ground Distance Bounds (D_near and D_far)

Once tilt is known, we can find where the top and bottom rays of the vertical
FOV hit the ground (`z = 0`).

```
Side-elevation — rays hitting ground
══════════════════════════════════════════════════════════

  Camera
    ╲  ← θ = tilt
  top ╲
  ray  ╲─────────────────────────────── ← hits ground at D_near
        ╲
         ╲  ← pointing direction (θ below horiz)
          ╲
  bottom   ╲──────────────────────────────────────── ← hits ground at D_far
   ray       ╲
              ↓ (would continue underground — clipped)

              |<-- D_near -->|<----------  D_far  ---------->|
```

The top ray makes an angle of `(tilt + V_angle/2)` below horizontal, and the
bottom ray makes `(tilt − V_angle/2)` below horizontal.

```
half_v = V_angle / 2                      // in degrees (convert to radians for trig)

D_near = H / tan( tilt + half_v )
D_far  = H / tan( tilt − half_v )
```

> All `tan` calls expect angles in **radians**. Convert: `radians = degrees × π/180`.

**Clipping**: The far distance may extend past the scene of interest.  Clip it:

```
render_far = min(D_far, target_dist)
```

**Worked example** (continuing from Section 4)

`H = 4 m`, `tilt = 27.9°`, `half_v = 17.5°`, `target_dist = 12 m`

```
tilt + half_v = 27.9 + 17.5 = 45.4°  →  tan(45.4°) = 1.012
tilt − half_v = 27.9 − 17.5 = 10.4°  →  tan(10.4°) = 0.1835

D_near = 4.0 / 1.012 = 3.95 m
D_far  = 4.0 / 0.1835 = 21.8 m

render_far = min(21.8, 12.0) = 12.0 m   (clipped at target distance)
```

---

## 6. Horizontal Coverage Width

The width of the FOV at any ground distance `d` is determined by the
**horizontal half-angle**:

```
half_h = H_angle / 2                      // degrees → convert to radians for trig

W(d) = 2 × d × tan( half_h )
```

```
Top-down diagram
══════════════════════════════════════════════════════════

               Camera
               /│╲
              / │ ╲
             /  │  ╲   ← half_h on each side
            /   │   ╲
           /    │    ╲
          ╱─────┼─────╲  ← W_near at D_near
         ╱      │      ╲
        ╱       │       ╲
       ╱────────┼────────╲  ← W_render at render_far
      ╱         │         ╲
```

**Worked example** (`H_angle = 62.5°`, `half_h = 31.25°`)

```
tan(31.25°) = 0.6066

W_near   = 2 × 3.95  × 0.6066 = 4.79 m
W_render = 2 × 12.0  × 0.6066 = 14.56 m
W_far    = 2 × 21.8  × 0.6066 = 26.45 m   (unclipped, for reference)
```

---

## 7. Coverage Area

The ground footprint between `D_near` and `render_far` is a **trapezoid**.
Its area is:

```
area = 0.5 × (W_near + W_render) × (render_far − D_near)
```

**Worked example**

```
area = 0.5 × (4.79 + 14.56) × (12.0 − 3.95)
     = 0.5 × 19.35 × 8.05
     = 77.9 m²
```

---

## 8. DORI Zone Calculations

**DORI** (Detection, Observation, Recognition, Identification) is an industry
standard (EN 62676-4 / IEC 62676-4) that classifies the *quality* of coverage
a camera provides at any given distance, based on **pixel density** — how many
image pixels cover one metre of the real scene.

### 8a. Threshold Table

| Level          | Min pixels-per-metre (ppm) | Typical task                              |
|----------------|---------------------------|-------------------------------------------|
| Detection      | 25                        | Detect presence of an object              |
| Observation    | 62                        | Observe movement / gross features         |
| Recognition    | 125                       | Distinguish individuals by appearance     |
| Identification | 250                       | Positively identify a face or number plate|

### 8b. Pixel Density at a Distance

For a camera with horizontal resolution `R_H` pixels and horizontal FOV angle
`H_angle`, the **width of the scene visible in one pixel** at slant distance
`D_slant` is:

```
pixel_width = (2 × D_slant × tan(half_h)) / R_H
```

Pixels-per-metre (pixel density) is the reciprocal:

```
pixel_density = R_H / (2 × D_slant × tan(half_h))
```

### 8c. DORI Distance Formula

To find the **maximum slant distance** at which the camera still achieves at
least `ppm` pixels-per-metre, set `pixel_density = ppm` and solve for
`D_slant`:

```
ppm = R_H / (2 × D_slant × tan(half_h))

D_slant = R_H / (2 × ppm × tan(half_h))
```

`D_slant` is measured along the direct line of sight from the camera to the
point on the ground.  Convert to **horizontal ground distance** using
Pythagoras (camera is at height `H`):

```
discriminant = D_slant² − H²

if discriminant > 0:
    D_horiz = sqrt(discriminant)
else:
    D_horiz = 0          // camera cannot achieve this ppm at any ground point
```

```
Side view — slant vs horizontal distance
══════════════════════════════════════════════════════════

  Camera @ H
    ╲
     ╲  D_slant (line of sight)
      ╲
       ◉─────────────────── ground
       ↑
       D_horiz

  D_slant² = D_horiz² + H²   (Pythagoras)
  D_horiz  = sqrt(D_slant² − H²)
```

### 8d. Effective DORI Distance

Clip the ideal DORI distance at the rendered far boundary:

```
D_effective = min(D_horiz, render_far)
```

Also record two boolean flags:

```
within_fov    = (D_horiz <= D_far)       // achievable within the optical FOV
within_render = (D_horiz <= render_far)  // achievable within the clipped scene
```

### 8e. Worked Example

Camera: `R_H = 2560 px`, `H_angle = 62.5°` → `half_h = 31.25°` → `tan(31.25°) = 0.6066`
Camera height `H = 4 m`, `render_far = 12 m`, `D_far = 21.8 m`.

| Level          | ppm | D_slant = 2560/(2×ppm×0.6066)       | D_horiz = √(D_slant²−16) | D_eff         |
|----------------|-----|--------------------------------------|---------------------------|---------------|
| Detection      | 25  | 2560 / (50 × 0.6066) = **84.4 m**   | √(7123−16) = **84.3 m**   | 12.0 m        |
| Observation    | 62  | 2560 / (124 × 0.6066) = **34.1 m**  | √(1163−16) = **33.9 m**   | 12.0 m        |
| Recognition    | 125 | 2560 / (250 × 0.6066) = **16.9 m**  | √(285.6−16) = **16.4 m**  | 12.0 m        |
| Identification | 250 | 2560 / (500 × 0.6066) = **8.44 m**  | √(71.2−16)  = **7.43 m**  | 7.43 m ✓      |

Interpretation: the camera achieves Identification quality only up to ~7.4 m,
which is within the scene.  Detection, Observation, and Recognition extend well
beyond the target distance of 12 m, so their effective distance is capped.

---

## 9. Ground Footprint Corners (Top-Down View)

The trapezoidal FOV footprint has **four corners**.  To support cameras pointing
in different directions, the corners are computed in a coordinate system where:

- **+Y** = forward (camera pointing direction)
- **+X** = right
- **Z** = 0 (ground plane)

Then optionally rotated by a **bearing** angle `b` (clockwise from north /
forward axis):

```
For each (distance d, side s) where side s = −1 (left) or +1 (right):

    lateral = s × d × tan(half_h)      // horizontal offset left/right

    // Rotate by bearing b (in radians):
    x =  lateral × cos(b) + d × sin(b)
    y = −lateral × sin(b) + d × cos(b)
    z = 0
```

The four corners are:

| Corner index | distance    | side |
|--------------|-------------|------|
| 0            | `D_near`    | left (−1)  |
| 1            | `D_near`    | right (+1) |
| 2            | `D_far`     | right (+1) |
| 3            | `D_far`     | left (−1)  |

### Worked Example A — bearing = 0°

`D_near = 3.95 m`, `D_far = 12.0 m` (render_far), `half_h = 31.25°`,
`tan(31.25°) = 0.6066`, `bearing = 0°` → `cos(0) = 1`, `sin(0) = 0`.

```
Lateral at D_near = ±3.95 × 0.6066 = ±2.40 m
Lateral at D_far  = ±12.0 × 0.6066 = ±7.28 m

Corners (x, y):
  [0]  (−2.40,  3.95)   left-near
  [1]  (+2.40,  3.95)   right-near
  [2]  (+7.28, 12.00)   right-far
  [3]  (−7.28, 12.00)   left-far
```

```
Top-down diagram (bearing = 0°, forward = up):

         ↑ Y (forward)
         │
  [3] ───────── [2]
  −7.28  12m   +7.28
    ╲             ╱
     ╲           ╱
      ╲         ╱
  [0]──────────[1]
  −2.40  3.95m +2.40
         │
      [Camera]──────→ X (right)
```

### Worked Example B — bearing = 45°

Same distances, `b = 45°` → `cos(45°) = sin(45°) = 0.7071`.

Near-left corner (d = 3.95, lateral = −2.40):
```
x =  (−2.40) × 0.7071 + 3.95 × 0.7071 = (3.95 − 2.40) × 0.7071 =  1.55 × 0.7071 =  1.10 m
y = −(−2.40) × 0.7071 + 3.95 × 0.7071 = (3.95 + 2.40) × 0.7071 =  6.35 × 0.7071 =  4.49 m
```

Far-right corner (d = 12.0, lateral = +7.28):
```
x =   7.28  × 0.7071 + 12.0 × 0.7071 = (7.28 + 12.0) × 0.7071 = 19.28 × 0.7071 = 13.63 m
y = −(7.28) × 0.7071 + 12.0 × 0.7071 = (12.0 − 7.28) × 0.7071 =  4.72 × 0.7071 =  3.34 m
```

The whole trapezoid is rotated 45° clockwise relative to Example A.

---

## 10. Full Algorithm Pseudocode

```
FUNCTION compute_fov(f, H, target_dist, target_h, model):

    // ── Step 1: Clamp focal length ──────────────────────────────────────
    f = clamp(f, model.f_min, model.f_max)

    // ── Step 2: Get FOV angles ──────────────────────────────────────────
    IF model.sensor_width == 0:
        // Method A: datasheet interpolation
        t       = (f - model.f_min) / (model.f_max - model.f_min)
        H_angle = model.H_max - t * (model.H_max - model.H_min)
        V_angle = model.V_max - t * (model.V_max - model.V_min)
    ELSE:
        // Method B: thin-lens physics
        H_angle = 2 * degrees( atan(model.sensor_width / (2 * f)) )
        V_angle = 2 * degrees( atan(model.sensor_width / model.aspect_ratio / (2 * f)) )
    END IF

    // ── Step 3: Compute tilt ─────────────────────────────────────────────
    delta     = H - target_h
    IF delta <= 0 OR target_dist <= 0:
        RETURN error("invalid geometry")
    END IF

    top_angle = degrees( atan(delta / target_dist) )
    tilt      = top_angle + V_angle / 2

    IF tilt <= V_angle / 2 OR tilt >= 90:
        RETURN error("tilt out of range")
    END IF

    // ── Step 4: Convert angles to radians ────────────────────────────────
    theta  = radians(tilt)
    half_v = radians(V_angle / 2)
    half_h = radians(H_angle / 2)

    // ── Step 5: Ground distance bounds ───────────────────────────────────
    D_near     = H / tan(theta + half_v)
    D_far      = H / tan(theta - half_v)
    render_far = min(D_far, target_dist)

    // ── Step 6: Widths ───────────────────────────────────────────────────
    W_near   = 2 * D_near     * tan(half_h)
    W_render = 2 * render_far * tan(half_h)
    W_far    = 2 * D_far      * tan(half_h)

    // ── Step 7: Coverage area ────────────────────────────────────────────
    IF render_far > D_near:
        area = 0.5 * (W_near + W_render) * (render_far - D_near)
    ELSE:
        area = 0
    END IF

    // ── Step 8: DORI zones ───────────────────────────────────────────────
    DORI_THRESHOLDS = { Detection: 25, Observation: 62,
                        Recognition: 125, Identification: 250 }
    dori = {}

    FOR EACH (level, ppm) IN DORI_THRESHOLDS:
        D_slant      = model.R_H / (2 * ppm * tan(half_h))
        discriminant = D_slant^2 - H^2
        IF discriminant > 0:
            D_horiz = sqrt(discriminant)
        ELSE:
            D_horiz = 0
        END IF
        D_effective   = min(D_horiz, render_far)
        within_fov    = (D_horiz <= D_far)
        within_render = (D_horiz <= render_far)

        dori[level] = { D_horiz, D_effective, within_fov, within_render }
    END FOR

    // ── Step 9: Footprint corners ────────────────────────────────────────
    corners = trapezoid_corners(D_near, render_far, half_h, bearing=0)

    // ── Return all results ───────────────────────────────────────────────
    RETURN {
        H_angle, V_angle, tilt,
        D_near, D_far, render_far,
        W_near, W_far, W_render,
        area, dori, corners
    }

END FUNCTION


FUNCTION trapezoid_corners(d_inner, d_outer, half_h, bearing_deg):
    b   = radians(bearing_deg)
    cb  = cos(b)
    sb  = sin(b)
    th  = tan(half_h)

    FUNCTION point(d, side):           // side = -1 (left) or +1 (right)
        lateral = side * d * th
        x = lateral * cb + d * sb
        y = -lateral * sb + d * cb
        RETURN (x, y, 0)
    END FUNCTION

    RETURN [
        point(d_inner, -1),   // left-near
        point(d_inner, +1),   // right-near
        point(d_outer, +1),   // right-far
        point(d_outer, -1),   // left-far
    ]
END FUNCTION
```

---

## 11. Reference Tables

### Sensor Format → Physical Width

| Format   | Width (mm) |
|----------|------------|
| 1/4"     | 3.20       |
| 1/3.6"   | 4.00       |
| 1/3"     | 4.80       |
| 1/2.9"   | 5.12       |
| 1/2.8"   | 5.37       |
| 1/2.7"   | 5.37       |
| 1/2"     | 6.40       |
| 1/1.8"   | 7.18       |
| 1/1.7"   | 7.60       |
| 2/3"     | 8.80       |
| 1/1.2"   | 10.67      |
| 1"       | 12.80      |
| 4/3"     | 17.30      |

> Source: Standard imaging sensor dimensions used across the CCTV industry.

### Common Aspect Ratios

| Name   | Value (w÷h) |
|--------|-------------|
| 4:3    | 1.333       |
| 16:9   | 1.778       |
| 16:10  | 1.600       |
| 3:2    | 1.500       |
| 1:1    | 1.000       |

### DORI Thresholds

| Level          | Min ppm | Standard reference  |
|----------------|---------|---------------------|
| Detection      | 25      | EN 62676-4 / IEC 62676-4 |
| Observation    | 62      | EN 62676-4 / IEC 62676-4 |
| Recognition    | 125     | EN 62676-4 / IEC 62676-4 |
| Identification | 250     | EN 62676-4 / IEC 62676-4 |

---

*End of document.*
