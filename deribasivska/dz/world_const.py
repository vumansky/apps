"""Sun direction shared by the Blender scene and the (bpy-free) post pipeline."""
import math
import numpy as np
SUN_AZ_OFF = math.radians(-6.0)   # mid-November sunrise sits almost on the street axis (bearing ~120 deg)
SUN_EL = math.radians(9.0)
SUN_DIR = np.array([math.sin(SUN_AZ_OFF) * math.cos(SUN_EL), math.cos(SUN_AZ_OFF) * math.cos(SUN_EL), math.sin(SUN_EL)])
