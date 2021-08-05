import bpy

from . import operators
from importlib import reload
reload(operators)


def menu_header(layout):
    row = layout.row()
    row.separator()

    row = layout.row()
    row.label(text="Charigty Tools")


def pose_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.ConstraintStatus.bl_idname)

    row = layout.row()
    row.operator(operators.RevertDotBoneNames.bl_idname)

    row = layout.row()
    row.operator(operators.ConvertBoneNaming.bl_idname)

    row = layout.row()
    row.operator(operators.ExtractMetarig.bl_idname)

    row = layout.row()
    row.operator(operators.ConvertGameFriendly.bl_idname)


def armature_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.MergeHeadTails.bl_idname)


def action_header_buttons(self, context):
    st = context.space_data

    if st.mode == 'ACTION':
        layout = self.layout

        row = layout.row()
        row.operator(operators.ActionRangeToScene.bl_idname, icon='PREVIEW_RANGE', text='To Scene Range')
