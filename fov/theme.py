DARK_MODE = False   # mutable global toggled by MainWindow._toggle_theme

_LIGHT = {
    "bg":          "#f5f5f7",
    "bg2":         "#ffffff",
    "panel":       "#eaeaf0",
    "border":      "#c0c0d0",
    "text":        "#1a1a2e",
    "text2":       "#444466",
    "accent":      "#4040aa",
    "accent2":     "#6060cc",
    "warn":        "#c0392b",
    "info":        "#2471a3",
    "sep":         "#c8c8dc",
    # 2D canvas colours — light
    "canvas_bg":   "#f8f8fc",
    "canvas_bg2":  "#ffffff",
    "grid":        "#dcdce8",
    "grid2":       "#ebebf5",
    "ground":      "#888899",
    "fov_ray":     "#333355",
    "fov_near":    "#888899",
    "tgt_dist":    "#996600",
    "tgt_h":       "#006688",
    "cam_body":    "#333355",
    "cam_pole":    "#555577",
    "axis_lbl":    "#333355",
    "tick":        "#555577",
    "title":       "#1a1a44",
    "divider":     "#c0c0d8",
    # 3D canvas always dark
    "gl_bg":       (0.10, 0.10, 0.16, 1.0),
    "gl_ground":   (0.12, 0.12, 0.20, 0.7),
    "gl_grid":     (0.22, 0.22, 0.38, 0.8),
    "gl_fov":      (0.9,  0.9,  0.9,  0.9),
    "gl_cam":      "#dddddd",
}

_DARK = {
    "bg":          "#1e1e2e",
    "bg2":         "#13131f",
    "panel":       "#2a2a3e",
    "border":      "#3a3a5a",
    "text":        "#e0e0f0",
    "text2":       "#9090b8",
    "accent":      "#6060cc",
    "accent2":     "#8080ee",
    "warn":        "#e74c3c",
    "info":        "#3498db",
    "sep":         "#3a3a5a",
    # 2D canvas colours — dark
    "canvas_bg":   "#0d0d1a",
    "canvas_bg2":  "#111120",
    "grid":        "#1e1e35",
    "grid2":       "#252538",
    "ground":      "#505070",
    "fov_ray":     "#dddddd",
    "fov_near":    "#777799",
    "tgt_dist":    "#cccc00",
    "tgt_h":       "#00cccc",
    "cam_body":    "#dddddd",
    "cam_pole":    "#888899",
    "axis_lbl":    "#aaaacc",
    "tick":        "#666688",
    "title":       "#ccccee",
    "divider":     "#404060",
    # 3D canvas
    "gl_bg":       (0.10, 0.10, 0.16, 1.0),
    "gl_ground":   (0.12, 0.12, 0.20, 0.7),
    "gl_grid":     (0.22, 0.22, 0.38, 0.8),
    "gl_fov":      (0.9,  0.9,  0.9,  0.9),
    "gl_cam":      "#dddddd",
}


def TH(key=None):
    """Return the active theme dict, or a single value if key given."""
    d = _DARK if DARK_MODE else _LIGHT
    return d[key] if key else d
