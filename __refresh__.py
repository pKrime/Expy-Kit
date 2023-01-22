import os
from importlib import reload
from . import *
from .thirdparty import bone_gizmos

def _reload_modules():
    reload(operators)
    reload(bone_utils)
    reload(preferences)
    reload(preset_handler)
    reload(properties)
    reload(bone_gizmos)
    reload(ui)

_DEV_MODE = bool(os.environ.get('BLENDER_DEV_MODE', 0))
reload_modules = _reload_modules if _DEV_MODE else lambda: None
