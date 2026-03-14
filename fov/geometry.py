import math

from .constants import DORI_THRESHOLDS


def fov_from_sensor(focal_mm: float, sensor_dim_mm: float) -> float:
    """Physics-based FOV: 2 * atan(sensor_dim / (2 * focal_length))"""
    if focal_mm <= 0 or sensor_dim_mm <= 0:
        return 0.0
    return math.degrees(2 * math.atan(sensor_dim_mm / (2 * focal_mm)))


def sensor_vwidth(sensor_width_mm: float, aspect_ratio: float) -> float:
    return sensor_width_mm / aspect_ratio


def interpolate_angles(f, model):
    """
    Compute H and V FOV angles for focal length f.

    Priority:
      1. Manual datasheet angles (H_max/H_min/V_max/V_min) — most accurate.
         Uses manufacturer measured values that include real lens distortion.
         Active when sensor_width == 0  (manual mode in dialog).
      2. Sensor physics fallback: 2*atan(sensor_dim / 2f).
         Assumes ideal thin lens. Active when sensor_width > 0.

    Both paths linearly interpolate at intermediate focal lengths.
    """
    f = max(model["f_min"], min(model["f_max"], f))
    sw = model.get("sensor_width", 0.0)

    if sw == 0.0:
        # PRIMARY — datasheet angles
        denom = model["f_max"] - model["f_min"]
        if denom == 0:
            return model["H_max"], model["V_max"]
        t  = (f - model["f_min"]) / denom
        Ha = model["H_max"] - t * (model["H_max"] - model["H_min"])
        Va = model["V_max"] - t * (model["V_max"] - model["V_min"])
    else:
        # FALLBACK — physics from sensor size
        ar = model.get("aspect_ratio", 16/9)
        Ha = fov_from_sensor(f, sw)
        Va = fov_from_sensor(f, sw / ar)
    return Ha, Va


def compute_tilt(H_cam, target_dist, target_h, V_angle_deg):
    delta = H_cam - target_h
    if delta <= 0 or target_dist <= 0:
        return None
    top_angle = math.degrees(math.atan(delta / target_dist))
    tilt = top_angle + V_angle_deg / 2
    if tilt <= 0 or tilt >= 90:
        return None
    return tilt


def compute_geometry(f, H, target_dist, target_h, model):
    H_angle, V_angle = interpolate_angles(f, model)
    tilt = compute_tilt(H, target_dist, target_h, V_angle)
    warnings = []

    if tilt is None:
        return None, "⚠ Cannot compute tilt — check height / target height / distance."

    theta  = math.radians(tilt)
    half_v = math.radians(V_angle / 2)
    half_h = math.radians(H_angle / 2)

    if tilt <= V_angle / 2:
        return None, (f"⚠ Computed tilt ({tilt:.1f}°) ≤ V_angle/2 ({V_angle/2:.1f}°). "
                      f"Increase target distance or reduce target height.")

    D_near     = H / math.tan(theta + half_v)
    D_far      = H / math.tan(theta - half_v)
    render_far = min(D_far, target_dist)

    if D_near > target_dist:
        warnings.append(
            f"⚠ D_near ({D_near:.1f}m) > target distance ({target_dist:.0f}m) "
            f"— near-field starts beyond target!")
    if D_far > target_dist:
        warnings.append(
            f"ℹ FOV extends to {D_far:.1f}m, clipped at target {target_dist:.0f}m.")

    W_near   = 2 * D_near     * math.tan(half_h)
    W_render = 2 * render_far * math.tan(half_h)
    W_far    = 2 * D_far      * math.tan(half_h)
    area     = (0.5 * (W_near + W_render) * (render_far - D_near)
                if render_far > D_near else 0)

    R_H  = model["R_H"]
    dori = {}
    for level, ppm in DORI_THRESHOLDS.items():
        D_slant = R_H / (2 * ppm * math.tan(half_h))
        disc    = D_slant**2 - H**2
        D_horiz = math.sqrt(disc) if disc > 0 else 0.0
        D_eff   = min(D_horiz, render_far)
        dori[level] = {
            "D_horiz":       D_horiz,
            "D_effective":   D_eff,
            "within_fov":    D_horiz <= D_far,
            "within_render": D_horiz <= render_far,
        }

    return {
        "f": f, "H": H, "tilt": tilt,
        "target_dist": target_dist, "target_h": target_h,
        "H_angle": H_angle, "V_angle": V_angle,
        "D_near": D_near, "D_far": D_far, "render_far": render_far,
        "W_near": W_near, "W_far": W_far, "W_render": W_render,
        "area": area, "dori": dori,
        "half_h": half_h, "half_v": half_v,
        "bearing": 0.0,
    }, "\n".join(warnings)


def trapezoid_corners(d_inner, d_outer, half_h, bearing_deg=0.0):
    b      = math.radians(bearing_deg)
    cb, sb = math.cos(b), math.sin(b)
    th     = math.tan(half_h)
    def pt(d, side):
        lat = side * d * th
        return (lat*cb + d*sb, -lat*sb + d*cb, 0.0)
    return [pt(d_inner, -1), pt(d_inner, +1),
            pt(d_outer, +1), pt(d_outer, -1)]
