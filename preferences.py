import bpy
from bpy.props import StringProperty

import os


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
        script_path = os.path.join(script_path, 'unreal_mapping.py')
        op = sp_col.operator(ExpyToClipboard.bl_idname, text='Path of "Unreal Mapping" to Clipboard')
        op.clip_text = script_path
