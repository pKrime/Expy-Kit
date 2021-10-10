import bpy
from bpy.props import StringProperty

from . import operators
from importlib import reload
reload(operators)


def menu_header(layout):
    row = layout.row()
    row.separator()

    row = layout.row()
    row.label(text="Expy Kit", icon='ARMATURE_DATA')


def object_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.CreateTransformOffset.bl_idname)


def pose_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.ConstrainToArmature.bl_idname)

    row = layout.row()
    row.operator(operators.ConstraintStatus.bl_idname)

    row = layout.row()
    row.operator(operators.SelectConstrainedControls.bl_idname)

    layout.separator()

    row = layout.row()
    row.operator(operators.RevertDotBoneNames.bl_idname)

    row = layout.row()
    row.operator(operators.ConvertBoneNaming.bl_idname)

    layout.separator()

    row = layout.row()
    row.operator(operators.ExtractMetarig.bl_idname)

    row = layout.row()
    row.operator(operators.ConvertGameFriendly.bl_idname)

    layout.separator()

    row = layout.row()
    row.operator(operators.ActionRangeToScene.bl_idname)

    row = layout.row()
    row.operator(operators.BakeConstrainedActions.bl_idname)

    row = layout.row()
    row.operator_context = 'INVOKE_DEFAULT'
    row.operator(operators.RenameActionsFromFbxFiles.bl_idname)

    row = layout.row()
    row.operator(operators.AddRootMotion.bl_idname)

    row = layout.row()
    row.operator(operators.CreateTransformOffset.bl_idname)


def armature_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.MergeHeadTails.bl_idname)


def action_header_buttons(self, context):
    layout = self.layout
    row = layout.row()
    row.operator(operators.ActionRangeToScene.bl_idname, icon='PREVIEW_RANGE', text='To Scene Range')


class ActionRenameSimple(bpy.types.Operator):
    """Rename Current Action"""
    bl_idname = "object.expykit_rename_action_simple"
    bl_label = "Expy Action Rename"

    new_name: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        if not context.object:
            return None
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.animation_data:
            return False
        if not context.object.animation_data.action:
            return False

        return True

    def execute(self, context):
        action = context.object.animation_data.action
        if self.new_name and action:
            action.name = self.new_name

        # remove candidate from other actions
        for other_action in bpy.data.actions:
            if other_action == action:
                continue
            idx = other_action.expykit_name_candidates.find(self.new_name)
            if idx > -1:
                other_action.expykit_name_candidates.remove(idx)
            if len(other_action.expykit_name_candidates) == 1:
                other_action.name = other_action.expykit_name_candidates[0].name

        action.expykit_name_candidates.clear()
        return {'FINISHED'}


class DATA_PT_expy_buttons(bpy.types.Panel):
    bl_label = "Expy Utilities"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.animation_data:
            return False
        action = context.object.animation_data.action
        if not action:
            return False

        return len(action.expykit_name_candidates) > 0

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Candidate Names")

        action = context.object.animation_data.action
        for candidate in action.expykit_name_candidates:
            if candidate.name in bpy.data.actions:
                # that name has been taken
                continue

            row = layout.row()
            op = row.operator(ActionRenameSimple.bl_idname, text=candidate.name)
            op.new_name = candidate.name
