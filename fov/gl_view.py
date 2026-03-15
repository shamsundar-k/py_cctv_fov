import math
import numpy as np

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *

from .constants import DORI_RGBA, DORI_SOLID, DORI_HEX, BLIND_SPOT_RGBA, BLIND_SPOT_HEX, BLIND_SPOT_SOLID
from .gl_utils import create_shader_program, perspective, look_at, translate, rotate_x, rotate_z, project


VERTEX_SHADER_SRC = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec4 aColor;

uniform mat4 uMVP;
out vec4 vColor;

void main() {
    gl_Position = uMVP * vec4(aPos, 1.0);
    vColor = aColor;
}
"""

FRAGMENT_SHADER_SRC = """
#version 330 core
in vec4 vColor;
out vec4 FragColor;

void main() {
    FragColor = vColor;
}
"""


class GLView(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.geo     = None
        self.bearing = 0.0
        self._rx     = 35.0
        self._rz     = -30.0
        self._zoom   = 1.0
        self._px     = 0.0
        self._py     = 0.0
        self._last   = QPoint()
        self._labels = []
        self._mv = self._pj = self._vp = None
        self._shader_program = None
        self._vao = None
        self._vbo = None
        self.setMinimumSize(500, 480)

    def set_geometry(self, geo, bearing):
        self.geo          = geo
        self.bearing      = bearing
        geo["bearing"]    = bearing
        self.update()

    def mousePressEvent(self, e): self._last = e.position().toPoint()
    def mouseMoveEvent(self, e):
        dx = e.position().x() - self._last.x()
        dy = e.position().y() - self._last.y()
        if   e.buttons() & Qt.LeftButton:
            self._rz += dx*0.5; self._rx += dy*0.5
        elif e.buttons() & Qt.RightButton:
            self._zoom = max(0.1, min(10, self._zoom*(1+dy*0.005)))
        elif e.buttons() & Qt.MiddleButton:
            self._px += dx*0.05; self._py -= dy*0.05
        self._last = e.position().toPoint()
        self.update()

    def wheelEvent(self, e):
        self._zoom = max(0.1, min(10, self._zoom*(1+e.angleDelta().y()*0.001)))
        self.update()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # GL_LINE_SMOOTH is NOT enabled globally: on Ubuntu/Mesa it implicitly
        # activates polygon-smooth coverage which overrides glColor4f alpha for
        # filled quads and causes all DORI zones to render as the first zone's
        # colour (green).  We enable it only locally around actual line draws.
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.10, 0.10, 0.16, 1.0)
        
        self._shader_program = create_shader_program(VERTEX_SHADER_SRC, FRAGMENT_SHADER_SRC)
        self._vao = glGenVertexArrays(1)
        self._vbo = glGenBuffers(1)

    def resizeGL(self, w, h): glViewport(0, 0, w, max(h, 1))

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        geo = self.geo
        D_ref = geo["render_far"] if geo else 20.0
        cd    = D_ref * 2.5 / self._zoom

        # 1. Projection matrix
        proj = perspective(45, self.width()/max(self.height(), 1), 0.1, 2000)
        
        # 2. View/Model matrix
        view = look_at((0, -cd, cd*0.8), (0, 0, 0), (0, 0, 1))
        model = translate(self._px, self._py, 0) @ rotate_x(self._rx) @ rotate_z(self._rz)
        mv = view @ model

        self._mv = mv
        self._pj = proj
        self._vp = [0, 0, self.width(), self.height()]

        if not geo: return
        self._labels = []
        b = self.bearing

        glUseProgram(self._shader_program)
        glBindVertexArray(self._vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        
        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 7 * 4, ctypes.c_void_p(0))
        # Color attribute
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 7 * 4, ctypes.c_void_p(3 * 4))

        # Combined MVP
        mvp = proj @ mv
        mvp_loc = glGetUniformLocation(self._shader_program, "uMVP")
        glUniformMatrix4fv(mvp_loc, 1, GL_TRUE, mvp)

        self._ground(geo)
        self._grid(geo)
        self._blind_spot_3d(geo, b)
        self._dori_zones_3d(geo, b)
        self._fov_outline_3d(geo, b)
        self._target_line(geo, b)
        self._camera_body(geo, b)
        self._north(geo)
        self._axes(geo)

        glBindVertexArray(0)
        glUseProgram(0)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _draw_elements(self, vertices, mode=GL_TRIANGLES):
        """Helper to draw vertex data using VBO."""
        data = np.array(vertices, dtype=np.float32)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)
        glDrawArrays(mode, 0, len(data) // 7)

    def _frustum_3d_corners(self, d, geo, b):
        tilt_rad = math.radians(geo["tilt"])
        half_v   = geo["half_v"]
        half_h   = geo["half_h"]
        H        = geo["H"]
        brad     = math.radians(b)
        cb, sb   = math.cos(brad), math.sin(brad)
        w        = d * math.tan(half_h)
        z_top    = max(0.0, H - d * math.tan(tilt_rad - half_v))
        bl = (d*sb - w*cb,  d*cb + w*sb,  0.0)
        br = (d*sb + w*cb,  d*cb - w*sb,  0.0)
        tr = (d*sb + w*cb,  d*cb - w*sb,  z_top)
        tl = (d*sb - w*cb,  d*cb + w*sb,  z_top)
        return [bl, br, tr, tl]

    def _dashed_line3d(self, p0, p1, color, dash=0.4, gap=0.25):
        dx = p1[0]-p0[0]; dy = p1[1]-p0[1]; dz = p1[2]-p0[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 0.01: return
        nx, ny, nz = dx/dist, dy/dist, dz/dist
        t = 0.0; drawing = True
<<<<<<< Updated upstream
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
=======
        vertices = []
>>>>>>> Stashed changes
        while t < dist:
            seg = dash if drawing else gap
            t2  = min(t + seg, dist)
            if drawing:
                vertices.extend([p0[0]+nx*t,  p0[1]+ny*t,  p0[2]+nz*t, *color])
                vertices.extend([p0[0]+nx*t2, p0[1]+ny*t2, p0[2]+nz*t2, *color])
            t = t2; drawing = not drawing
<<<<<<< Updated upstream
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
        if vertices:
            self._draw_elements(vertices, GL_LINES)
>>>>>>> Stashed changes

    # ── Scene elements ─────────────────────────────────────────────────────────

    def _ground(self, geo):
        s = max(geo["render_far"]*2.2, 20)
        c = (0.12, 0.12, 0.20, 0.7)
        v = [
            -s, -s, 0, *c,  s, -s, 0, *c,  s,  s, 0, *c,
            -s, -s, 0, *c,  s,  s, 0, *c, -s,  s, 0, *c
        ]
        self._draw_elements(v, GL_TRIANGLES)

    def _grid(self, geo):
        s    = max(geo["render_far"]*2.2, 20)
        step = max(1.0, round(s/15))
<<<<<<< Updated upstream
        glColor4f(0.22, 0.22, 0.38, 0.8); glLineWidth(0.5)
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
=======
        c    = (0.22, 0.22, 0.38, 0.8)
        v    = []
>>>>>>> Stashed changes
        x = -s
        while x <= s+.01:
            v.extend([x, -s, .002, *c, x, s, .002, *c])
            x += step
        y = -s
        while y <= s+.01:
<<<<<<< Updated upstream
            glVertex3f(-s, y, .002); glVertex3f(s, y, .002); y += step
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
            v.extend([-s, y, .002, *c, s, y, .002, *c])
            y += step
        if v:
            self._draw_elements(v, GL_LINES)
>>>>>>> Stashed changes

    def _blind_spot_3d(self, geo, b):
        dn = geo["D_near"]
        H  = geo["H"]
        if dn <= 0.1: return

        n = self._frustum_3d_corners(dn, geo, b)
        cam = (0.0, 0.0, H)
        pole_base = (0.0, 0.0, 0.0)
        c = BLIND_SPOT_RGBA
        
        glDepthMask(GL_FALSE)
        v_tri = [
            *pole_base, *c, *n[0], *c, *n[1], *c, # Ground
            *cam, *c, *pole_base, *c, *n[0], *c,  # Left
            *cam, *c, *pole_base, *c, *n[1], *c,  # Right
            *cam, *c, *n[0], *c, *n[1], *c        # Back
        ]
        self._draw_elements(v_tri, GL_TRIANGLES)
        glDepthMask(GL_TRUE)

        cs = BLIND_SPOT_SOLID
        v_line = [
            *pole_base, *cs, *n[0], *cs,
            *n[0], *cs, *n[1], *cs,
            *n[1], *cs, *pole_base, *cs,
            *cam, *cs, *n[0], *cs,
            *cam, *cs, *n[1], *cs
        ]
        self._draw_elements(v_line, GL_LINES)

        mx = (n[0][0]+n[1][0])/4; my = (n[0][1]+n[1][1])/4
        self._labels.append((mx, my, 0.0, "Blind Spot", BLIND_SPOT_HEX))

    def _dori_zones_3d(self, geo, b):
        dn   = geo["D_near"]
        df   = geo["render_far"]
        dori = geo["dori"]
        order = [
            ("Detection", dori["Observation"]["D_effective"], dori["Detection"]["D_effective"]),
            ("Observation", dori["Recognition"]["D_effective"], dori["Observation"]["D_effective"]),
            ("Recognition", dori["Identification"]["D_effective"], dori["Recognition"]["D_effective"]),
            ("Identification", dn, dori["Identification"]["D_effective"]),
        ]

        glDepthMask(GL_FALSE)
        for level, di, do in order:
            di2 = max(di, dn);  do2 = min(do, df)
            if do2 <= di2 + 0.01: continue
            n = self._frustum_3d_corners(di2, geo, b)
            f = self._frustum_3d_corners(do2, geo, b)
            r, g, bv, a = DORI_RGBA[level]
            c = (r, g, bv, a)
            cg = (r, g, bv, a * 0.55)
            ct = (min(r*1.15, 1), min(g*1.15, 1), min(bv*1.15, 1), a * 0.65)
            cn = (r, g, bv, a * 0.80)
            cf = (min(r*1.2, 1), min(g*1.2, 1), min(bv*1.2, 1), a * 0.90)
            cs = (r*0.80, g*0.80, bv*0.80, a * 0.65)

            v_fill = [
                # Ground
                *n[0], *cg, *n[1], *cg, *f[1], *cg, *n[0], *cg, *f[1], *cg, *f[0], *cg,
                # Top
                *n[3], *ct, *n[2], *ct, *f[2], *ct, *n[3], *ct, *f[2], *ct, *f[3], *ct,
                # Near
                *n[0], *cn, *n[1], *cn, *n[2], *cn, *n[0], *cn, *n[2], *cn, *n[3], *cn,
                # Far
                *f[0], *cf, *f[1], *cf, *f[2], *cf, *f[0], *cf, *f[2], *cf, *f[3], *cf,
                # Left
                *n[0], *cs, *n[3], *cs, *f[3], *cs, *n[0], *cs, *f[3], *cs, *f[0], *cs,
                # Right
                *n[1], *cs, *n[2], *cs, *f[2], *cs, *n[1], *cs, *f[2], *cs, *f[1], *cs,
            ]
            self._draw_elements(v_fill, GL_TRIANGLES)

        # Region beyond Detection
        d_det = dori["Detection"]["D_effective"]
        if df > d_det + 0.01:
            nd = self._frustum_3d_corners(d_det, geo, b)
            fd = self._frustum_3d_corners(df,    geo, b)
            r2, g2, b2, a2 = 0.35, 0.38, 0.52, 0.28
            c = (r2, g2, b2, a2)
            v_det = [
                *nd[0], *(r2,g2,b2,a2*0.7), *nd[1], *(r2,g2,b2,a2*0.7), *fd[1], *(r2,g2,b2,a2*0.7),
                *nd[0], *(r2,g2,b2,a2*0.7), *fd[1], *(r2,g2,b2,a2*0.7), *fd[0], *(r2,g2,b2,a2*0.7),
                *nd[3], *(r2,g2,b2,a2*0.8), *nd[2], *(r2,g2,b2,a2*0.8), *fd[2], *(r2,g2,b2,a2*0.8),
                *nd[3], *(r2,g2,b2,a2*0.8), *fd[2], *(r2,g2,b2,a2*0.8), *fd[3], *(r2,g2,b2,a2*0.8),
                *nd[0], *c, *nd[1], *c, *nd[2], *c, *nd[0], *c, *nd[2], *c, *nd[3], *c,
                *fd[0], *c, *fd[1], *c, *fd[2], *c, *fd[0], *c, *fd[2], *c, *fd[3], *c,
                *nd[0], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *nd[3], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[3], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7),
                *nd[0], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[3], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[0], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7),
                *nd[1], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *nd[2], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[2], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7),
                *nd[1], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[2], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7), *fd[1], *(r2*0.8,g2*0.8,b2*0.8,a2*0.7),
            ]
            self._draw_elements(v_det, GL_TRIANGLES)
        glDepthMask(GL_TRUE)

<<<<<<< Updated upstream
        # ── DORI zone boundary lines and labels ───────────────────────────────
        glEnable(GL_LINE_SMOOTH)
=======
>>>>>>> Stashed changes
        for level, info in dori.items():
            de = info["D_effective"]
            if de <= dn + .01: continue
            c  = self._frustum_3d_corners(de, geo, b)
            cl = DORI_SOLID[level]
            self._draw_elements([*c[0], *cl, *c[1], *cl], GL_LINES)
            self._draw_elements([*c[0], *cl, *c[3], *cl, *c[1], *cl, *c[2], *cl], GL_LINES)
            mx = (c[0][0]+c[1][0])/2; my = (c[0][1]+c[1][1])/2
            sfx = "" if info["within_render"] else "*"
<<<<<<< Updated upstream
            self._labels.append((mx, my, 0.0,
                f"{level[:5]}. {de:.1f}m{sfx}", DORI_HEX[level]))
        glDisable(GL_LINE_SMOOTH)
=======
            self._labels.append((mx, my, 0.0, f"{level[:5]}. {de:.1f}m{sfx}", DORI_HEX[level]))
>>>>>>> Stashed changes

    def _fov_outline_3d(self, geo, b):
        dn  = geo["D_near"]
        df  = geo["render_far"]
        H   = geo["H"]
        cam = (0.0, 0.0, H)
        n = self._frustum_3d_corners(dn, geo, b)
        f = self._frustum_3d_corners(df, geo, b)
        c_cyan = (0.0, 0.85, 0.85, 1.0)
        
        v_rays = [
            *cam, *c_cyan, *f[3], *c_cyan, *cam, *c_cyan, *f[2], *c_cyan,
            *cam, *c_cyan, *f[0], *c_cyan, *cam, *c_cyan, *f[1], *c_cyan
        ]
        self._draw_elements(v_rays, GL_LINES)

<<<<<<< Updated upstream
        n = self._frustum_3d_corners(dn, geo, b)   # near: [BL, BR, TR, TL]
        f = self._frustum_3d_corners(df, geo, b)   # far:  [BL, BR, TR, TL]

        glEnable(GL_LINE_SMOOTH)

        # ── 4 corner rays: camera → far corners (solid cyan) ──────────────────
        glColor4f(0.0, 0.85, 0.85, 1.0); glLineWidth(1.8)
        glBegin(GL_LINES)
        glVertex3f(*cam); glVertex3f(*f[3])   # → far top-left
        glVertex3f(*cam); glVertex3f(*f[2])   # → far top-right
        glVertex3f(*cam); glVertex3f(*f[0])   # → far bottom-left
        glVertex3f(*cam); glVertex3f(*f[1])   # → far bottom-right
        glEnd()

        # ── Dashed optical axis: camera → far face centre ─────────────────────
=======
>>>>>>> Stashed changes
        fc_x = (f[0][0]+f[1][0])/2; fc_y = (f[0][1]+f[1][1])/2
        fc_z = (f[2][2]+f[3][2])/2
        self._dashed_line3d(cam, (fc_x, fc_y, fc_z), (0.0, 0.85, 0.85, 0.75))

        c_white = (1.0, 1.0, 1.0, 0.85)
        v_near = [*n[0], *c_white, *n[1], *c_white, *n[1], *c_white, *n[2], *c_white,
                  *n[2], *c_white, *n[3], *c_white, *n[3], *c_white, *n[0], *c_white]
        self._draw_elements(v_near, GL_LINES)

        c_green = (0.20, 1.00, 0.35, 1.0)
        v_far = [*f[0], *c_green, *f[1], *c_green, *f[1], *c_green, *f[2], *c_green,
                 *f[2], *c_green, *f[3], *c_green, *f[3], *c_green, *f[0], *c_green]
        self._draw_elements(v_far, GL_LINES)

        c_gray = (0.85, 0.85, 0.85, 0.75)
        self._draw_elements([*n[3], *c_gray, *f[3], *c_gray, *n[2], *c_gray, *f[2], *c_gray], GL_LINES)

        glDisable(GL_LINE_SMOOTH)

    def _target_line(self, geo, b):
        td = geo["target_dist"]; th = geo["target_h"]
<<<<<<< Updated upstream
        c  = self._frustum_3d_corners(td, geo, b)
        glEnable(GL_LINE_SMOOTH)
        # Yellow ground line at target distance
        glColor4f(1, 1, 0, 0.9); glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex3f(*c[0]); glVertex3f(*c[1])
        glEnd()
        # Cyan vertical target-height pole
        brad = math.radians(b)
        cx = td*math.sin(brad); cy = td*math.cos(brad)
        glColor4f(0, 1, 1, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(cx, cy, 0); glVertex3f(cx, cy, th)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
        c = self._frustum_3d_corners(td, geo, b)
        cl_y = (1, 1, 0, 0.9)
        self._draw_elements([*c[0], *cl_y, *c[1], *cl_y], GL_LINES)
        
        brad = math.radians(b)
        cx = td*math.sin(brad); cy = td*math.cos(brad)
        cl_c = (0, 1, 1, 1)
        self._draw_elements([cx, cy, 0, *cl_c, cx, cy, th, *cl_c], GL_LINES)
>>>>>>> Stashed changes
        self._labels.append((cx+0.2, cy, 0.0, f"Tgt H {th:.1f}m", "#00dddd"))
        self._labels.append((c[0][0], c[0][1], 0.0, f"Tgt D {td:.0f}m", "#dddd00"))

    def _camera_body(self, geo, b):
        H    = geo["H"]
        brad = math.radians(b)
        fx   = math.sin(brad); fy = math.cos(brad)
        c_gray = (0.55, 0.55, 0.55, 1)
        self._draw_elements([0, 0, 0, *c_gray, 0, 0, H, *c_gray], GL_LINES)

<<<<<<< Updated upstream
        # Mounting pole
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0.55, 0.55, 0.55, 1); glLineWidth(2.5)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0); glVertex3f(0, 0, H)
        glEnd()
        glDisable(GL_LINE_SMOOTH)

        # Camera body — slightly elongated box oriented along bearing
        s = 0.20   # half-size
        lx = -math.cos(brad); ly = math.sin(brad)   # lateral direction
        fwd = (fx*s*2, fy*s*2, 0)                    # forward extent (lens side)

        # 8 corners of an elongated camera box
=======
        s = 0.20
        lx = -math.cos(brad); ly = math.sin(brad)
>>>>>>> Stashed changes
        def cv(sf, sl, sz):
            return (sf*fx*s*1.8 + sl*lx*s, sf*fy*s*1.8 + sl*ly*s, H + sz*s)

        corners = [cv(f, l, z) for f in (-1, 1) for l in (-1, 1) for z in (-1, 1)]
        faces = [(0,1,3,2),(4,5,7,6),(0,2,6,4),(1,3,7,5),(0,1,5,4),(2,3,7,6)]
        c_body = (0.82, 0.82, 0.82, 1.0)
        v_body = []
        for face in faces:
<<<<<<< Updated upstream
            for i in face: glVertex3f(*corners[i])
        glEnd()
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0.4, 0.4, 0.4, 1); glLineWidth(1.2)
        glBegin(GL_LINE_LOOP)
        for i in faces[0]:  glVertex3f(*corners[i])
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
            v_body.extend([*corners[face[0]], *c_body, *corners[face[1]], *c_body, *corners[face[2]], *c_body,
                           *corners[face[0]], *c_body, *corners[face[2]], *c_body, *corners[face[3]], *c_body])
        self._draw_elements(v_body, GL_TRIANGLES)
        
        c_outline = (0.4, 0.4, 0.4, 1)
        f0 = faces[0]
        v_outline = [*corners[f0[0]], *c_outline, *corners[f0[1]], *c_outline, *corners[f0[1]], *c_outline, *corners[f0[2]], *c_outline,
                     *corners[f0[2]], *c_outline, *corners[f0[3]], *c_outline, *corners[f0[3]], *c_outline, *corners[f0[0]], *c_outline]
        self._draw_elements(v_outline, GL_LINES)
>>>>>>> Stashed changes

        ns = 0.09
<<<<<<< Updated upstream
        lc = (fx*s*1.8 + 0, fy*s*1.8 + 0, H)
        glColor4f(0.20, 0.20, 0.20, 1.0)
        self._box(lc[0] + fx*ns, lc[1] + fy*ns, lc[2], ns)

        # Bearing direction indicator (teal line)
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0, 0.85, 0.85, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, H); glVertex3f(fx*.6, fy*.6, H)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
        lc = (fx*s*1.8, fy*s*1.8, H)
        self._box(lc[0] + fx*ns, lc[1] + fy*ns, lc[2], ns, (0.2, 0.2, 0.2, 1.0))
>>>>>>> Stashed changes

        c_teal = (0, 0.85, 0.85, 1)
        self._draw_elements([0, 0, H, *c_teal, fx*.6, fy*.6, H, *c_teal], GL_LINES)
        self._labels.append((0.3, 0, 0.0, f"H={H:.1f}m", "#dddddd"))

    def _box(self, cx, cy, cz, s, color):
        v = [(cx+dx, cy+dy, cz+dz) for dx in (-s, s) for dy in (-s, s) for dz in (-s, s)]
        faces = [(0,1,3,2),(4,5,7,6),(0,2,6,4),(1,3,7,5),(0,1,5,4),(2,3,7,6)]
        v_tri = []
        for f in faces:
            v_tri.extend([*v[f[0]], *color, *v[f[1]], *color, *v[f[2]], *color,
                          *v[f[0]], *color, *v[f[2]], *color, *v[f[3]], *color])
        self._draw_elements(v_tri, GL_TRIANGLES)

    def _north(self, geo):
        d = min(geo["render_far"]*.2, 6)
<<<<<<< Updated upstream
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0, 0.9, 0.5, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, .05); glVertex3f(0, d, .05)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
        self._labels.append((0, d+.4, 0.0, "N", "#00ee88"))

    def _axes(self, geo):
        L = min(geo["render_far"]*.1, 3); glLineWidth(2)
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
        glColor4f(1, 0.3, 0.3, 1); glVertex3f(0, 0, 0); glVertex3f(L, 0, 0)
        glColor4f(0.3, 1, 0.3, 1); glVertex3f(0, 0, 0); glVertex3f(0, L, 0)
        glColor4f(0.3, 0.3, 1, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, L)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
=======
        c = (0, 0.9, 0.5, 1)
        self._draw_elements([0, 0, .05, *c, 0, d, .05, *c], GL_LINES)
        self._labels.append((0, d+.4, 0.0, "N", "#00ee88"))

    def _axes(self, geo):
        L = min(geo["render_far"]*.1, 3)
        c_r, c_g, c_b = (1, 0.3, 0.3, 1), (0.3, 1, 0.3, 1), (0.3, 0.3, 1, 1)
        self._draw_elements([0,0,0, *c_r, L,0,0, *c_r, 0,0,0, *c_g, 0,L,0, *c_g, 0,0,0, *c_b, 0,0,L, *c_b], GL_LINES)
>>>>>>> Stashed changes

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._labels or self._mv is None or self._pj is None or self._vp is None: return
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(QFont("Arial", 9, QFont.Bold))
        fm, dpr = p.fontMetrics(), self.devicePixelRatio()
        for (wx, wy, wz, txt, col) in self._labels:
            res = project((wx, wy, wz), self._mv, self._pj, self._vp)
            if not res: continue
            sx, sy, sz = res
            if sz < 0 or sz > 1: continue
            px, py = int(sx / dpr), int(self.height() - sy / dpr)
            br = fm.boundingRect(txt)
            p.fillRect(px-2, py-br.height(), br.width()+6, br.height()+4, QColor(0, 0, 0, 180))
            p.setPen(QColor(col)); p.drawText(px, py, txt)
        p.end()
