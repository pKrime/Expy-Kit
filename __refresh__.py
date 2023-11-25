import os
from importlib import reload
from . import *

def _reload_modules():
    from importlib import reload
    from . import operators
    from . import bone_utils
    from . import preferences
    from . import preset_handler
    from . import properties
    from . import ui

    from .rig_mapping import bone_mapping
    from . import _extra_

    reload(operators)
    reload(bone_utils)
    reload(preferences)
    reload(preset_handler)
    reload(properties)
    reload(ui)
    reload(bone_mapping)
    reload(_extra_)

_DEV_MODE = bool(os.environ.get('BLENDER_DEV_MODE', 0))
reload_modules = _reload_modules if _DEV_MODE else lambda: None
