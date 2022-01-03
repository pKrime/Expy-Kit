import os
import shutil

import bpy
from bpy.props import StringProperty

from .ui import AddPresetArmatureRetarget


class ExpyToClipboard(bpy.types.Operator):
    """Copy Expy Kit Preferences to the clipboard"""
    bl_idname = "wm.expy_to_clipboard"
    bl_label = "Copy Stuff to the clipboard"

    clip_text: StringProperty(description="Text to Copy", default="")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        context.window_manager.clipboard = self.clip_text
        return {'FINISHED'}


class ExpyPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        box = column.box()
        col = box.column()

        row = col.row()
        row.label(text="Useful Paths:")

        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()

        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()

        script_path = os.path.dirname(__file__)
        script_path = os.path.join(script_path, 'rig_mapping', 'unreal_mapping.py')
        op = sp_col.operator(ExpyToClipboard.bl_idname, text='Path of "Unreal Mapping" to Clipboard')
        op.clip_text = script_path


def install_presets():
    presets_dir = bpy.utils.user_resource('SCRIPTS', path="presets")
    retarget_dir = os.path.join(presets_dir, AddPresetArmatureRetarget.preset_subdir)
    bundled_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rig_mapping", "presets")

    os.makedirs(retarget_dir, exist_ok=True)
    for f in os.listdir(bundled_dir):
        shutil.copy2(os.path.join(bundled_dir, f), retarget_dir)
