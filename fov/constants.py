# =============================================================================
# SENSOR FORMAT LOOKUP  (optical format → physical sensor width in mm)
# Source: standard imaging sensor dimensions
# =============================================================================
SENSOR_FORMATS = [
    ('1/4"',   3.20),
    ('1/3.6"', 4.00),
    ('1/3"',   4.80),
    ('1/2.9"', 5.12),
    ('1/2.8"', 5.37),
    ('1/2.7"', 5.37),
    ('1/2"',   6.40),
    ('1/1.8"', 7.18),
    ('1/1.7"', 7.60),
    ('1/1.2"', 10.67),
    ('2/3"',   8.80),
    ('1"',     12.80),
    ('4/3"',   17.30),
    ('Custom', 0.0),   # user enters width directly
]
SENSOR_FORMAT_NAMES  = [s[0] for s in SENSOR_FORMATS]
SENSOR_FORMAT_WIDTHS = {s[0]: s[1] for s in SENSOR_FORMATS}

ASPECT_RATIOS = [
    ('4:3',   4/3),
    ('16:9',  16/9),
    ('16:10', 16/10),
    ('3:2',   3/2),
    ('1:1',   1.0),
]
ASPECT_RATIO_NAMES  = [a[0] for a in ASPECT_RATIOS]
ASPECT_RATIO_VALUES = {a[0]: a[1] for a in ASPECT_RATIOS}


# =============================================================================
# CAMERA MODEL  (mutable global — edited via CameraParamsDialog)
# All modules share this single dict object; .update() mutates it in place.
# =============================================================================
CAMERA_MODEL = {
    "name"          : "Varifocal 2.8–12 mm",
    "f_min"         : 2.8,
    "f_max"         : 12.0,
    # Manual datasheet angles (PRIMARY — used when sensor_width == 0)
    "H_max"         : 97.0,   # H-FOV at f_min (widest)
    "H_min"         : 28.0,   # H-FOV at f_max (narrowest)
    "V_max"         : 54.0,   # V-FOV at f_min (widest)
    "V_min"         : 16.0,   # V-FOV at f_max (narrowest)
    # Sensor-based params (FALLBACK — used when sensor_width > 0)
    "sensor_format" : "",
    "sensor_width"  : 0.0,    # 0 = use manual angles above
    "aspect_ratio"  : 16/9,
    "aspect_name"   : "16:9",
    "R_H"           : 2560,
}

# =============================================================================
# DORI standard pixel-density thresholds and display colours
# =============================================================================
DORI_THRESHOLDS = {
    "Identification": 250,
    "Recognition":    125,
    "Observation":     62,
    "Detection":       25,
}
DORI_HEX = {
    "Identification": "#c0392b",
    "Recognition":    "#d35400",
    "Observation":    "#b7950b",
    "Detection":      "#1e8449",
}
DORI_RGBA = {
    "Identification": (0.76, 0.22, 0.17, 0.50),
    "Recognition":    (0.83, 0.33, 0.00, 0.50),
    "Observation":    (0.72, 0.58, 0.04, 0.50),
    "Detection":      (0.12, 0.52, 0.28, 0.50),
}
DORI_SOLID = {k: (v[0], v[1], v[2], 1.0) for k, v in DORI_RGBA.items()}
