import bpy

from . import operators
from importlib import reload
reload(operators)


def pose_context_options(self, context):
    layout = self.layout

    row = layout.row()
    row.separator()

    row = layout.row()
    row.label(text="Charetee Tools")

    row = layout.row()
    row.operator(operators.ConstraintStatus.bl_idname)

    row = layout.row()
    row.operator(operators.RevertDotBoneNames.bl_idname)

    row = layout.row()
    row.operator(operators.ConvertBoneNaming.bl_idname)


class ARMATURE_PT_charetee_buttons(bpy.types.Panel):
    bl_label = "Charetee Tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'ARMATURE'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ConstraintStatus.bl_idname)
