# -----------------------------------------------------------------------------
# Blender version utils
# -----------------------------------------------------------------------------

import operator
import bpy

if bpy.app.version >= (2, 80, 0):
    matmul = operator.matmul
else:
    matmul = operator.mul


def make_annotations(cls):
    """Add annotation attribute to fields to avoid Blender 2.8+ warnings"""
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return cls
    if bpy.app.version < (2, 93, 0):
        bl_props = {k: v for k, v in cls.__dict__.items()
                    if isinstance(v, tuple)}
    else:
        bl_props = {k: v for k, v in cls.__dict__.items()
                    if isinstance(v, bpy.props._PropertyDeferred)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls

def layout_split(layout, factor=0.0, align=False):
    """Intermediate method for pre and post blender 2.8 split UI function"""
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return layout.split(percentage=factor, align=align)
    return layout.split(factor=factor, align=align)

def get_preferences(context=None):
    """Intermediate method for pre and post blender 2.8 grabbing the preferences itself"""
    if not context:
        context = bpy.context
    if hasattr(context, "user_preferences"):
        return context.user_preferences
    elif hasattr(context, "preferences"):
        return context.preferences
    return None
