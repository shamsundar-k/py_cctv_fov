import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader


def create_shader_program(vertex_src, fragment_src):
    return compileProgram(
        compileShader(vertex_src, GL_VERTEX_SHADER),
        compileShader(fragment_src, GL_FRAGMENT_SHADER)
    )


def perspective(fovy, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fovy) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye, target, up):
    eye = np.array(eye, dtype=np.float32)
    target = np.array(target, dtype=np.float32)
    up = np.array(up, dtype=np.float32)

    f = target - eye
    f /= np.linalg.norm(f)

    s = np.cross(f, up)
    s /= np.linalg.norm(s)

    u = np.cross(s, f)

    m = np.identity(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


def translate(x, y, z):
    m = np.identity(4, dtype=np.float32)
    m[0, 3] = x
    m[1, 3] = y
    m[2, 3] = z
    return m


def rotate_x(angle_deg):
    c = np.cos(np.radians(angle_deg))
    s = np.sin(np.radians(angle_deg))
    m = np.identity(4, dtype=np.float32)
    m[1, 1] = c
    m[1, 2] = -s
    m[2, 1] = s
    m[2, 2] = c
    return m


def rotate_z(angle_deg):
    c = np.cos(np.radians(angle_deg))
    s = np.sin(np.radians(angle_deg))
    m = np.identity(4, dtype=np.float32)
    m[0, 0] = c
    m[0, 1] = -s
    m[1, 0] = s
    m[1, 1] = c
    return m


def project(obj_pos, modelview, projection, viewport):
    # obj_pos: (x, y, z)
    # modelview, projection: 4x4 matrices
    # viewport: (x, y, width, height)
    pos = np.array([obj_pos[0], obj_pos[1], obj_pos[2], 1.0], dtype=np.float32)
    
    # Clip space: P * MV * V
    v_clip = projection @ (modelview @ pos)
    
    if v_clip[3] == 0:
        return None
        
    # Normalized Device Coordinates
    v_ndc = v_clip[:3] / v_clip[3]
    
    # Window coordinates
    x = viewport[0] + viewport[2] * (v_ndc[0] + 1.0) / 2.0
    y = viewport[1] + viewport[3] * (v_ndc[1] + 1.0) / 2.0
    z = (v_ndc[2] + 1.0) / 2.0
    
    return x, y, z
