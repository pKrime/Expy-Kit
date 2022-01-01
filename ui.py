import bpy
from bpy.props import StringProperty

from bpy.types import Operator, Menu
from bl_operators.presets import AddPresetBase

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


class BindingsMenu(bpy.types.Menu):
    bl_label = "Binding"
    bl_idname = "object.expykit_binding_menu"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ConstrainToArmature.bl_idname)

        row = layout.row()
        row.operator(operators.ConstraintStatus.bl_idname)

        row = layout.row()
        row.operator(operators.SelectConstrainedControls.bl_idname)


class ConvertMenu(bpy.types.Menu):
    bl_label = "Conversion"
    bl_idname = "object.expykit_convert_menu"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ConvertGameFriendly.bl_idname)

        row = layout.row()
        row.operator(operators.RevertDotBoneNames.bl_idname)

        row = layout.row()
        row.operator(operators.ConvertBoneNaming.bl_idname)

        row = layout.row()
        row.operator(operators.ExtractMetarig.bl_idname)

        row = layout.row()
        row.operator(operators.CreateTransformOffset.bl_idname)


class AnimMenu(bpy.types.Menu):
    bl_label = "Animation"
    bl_idname = "object.expykit_anim_menu"

    def draw(self, context):
        layout = self.layout

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
        op = row.operator(operators.SelectConstrainedControls.bl_idname, text="Select Animated Controls")
        op.select_type = 'anim'


def pose_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    # use an operator enum property to populate a sub-menu
    layout.menu(BindingsMenu.bl_idname)
    layout.menu(ConvertMenu.bl_idname)
    layout.menu(AnimMenu.bl_idname)

    layout.separator()


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


class AddPresetArmatureRetarget(AddPresetBase, Operator):
    """Add a Bone Retarget Preset"""
    bl_idname = "object.expy_kit_armature_preset_add"
    bl_label = "Add Bone Retarget Preset"
    preset_menu = "DATA_MT_retarget_presets"

    # variable used for all preset values
    preset_defines = [
        "skeleton = bpy.context.object.data.expykit_retarget"
    ]

    # properties to store in the preset
    preset_values = [
        "skeleton.spine.head",
        "skeleton.spine.neck",
        "skeleton.spine.spine2",
        "skeleton.spine.spine1",
        "skeleton.spine.spine",
        "skeleton.spine.hips",

        "skeleton.right_arm.shoulder",
        "skeleton.right_arm.arm",
        "skeleton.right_arm.arm_twist",
        "skeleton.right_arm.forearm",
        "skeleton.right_arm.forearm_twist",
        "skeleton.right_arm.hand",

        "skeleton.left_arm.shoulder",
        "skeleton.left_arm.arm",
        "skeleton.left_arm.arm_twist",
        "skeleton.left_arm.forearm",
        "skeleton.left_arm.forearm_twist",
        "skeleton.left_arm.hand",

        "skeleton.right_leg.upleg",
        "skeleton.right_leg.upleg_twist",
        "skeleton.right_leg.leg",
        "skeleton.right_leg.leg_twist",

        "skeleton.left_leg.upleg",
        "skeleton.left_leg.upleg_twist",
        "skeleton.left_leg.leg",
        "skeleton.left_leg.leg_twist",

        "skeleton.left_fingers.thumb",
        "skeleton.left_fingers.index",
        "skeleton.left_fingers.middle",
        "skeleton.left_fingers.ring",
        "skeleton.left_fingers.pinky",

        "skeleton.right_fingers.thumb",
        "skeleton.right_fingers.index",
        "skeleton.right_fingers.middle",
        "skeleton.right_fingers.ring",
        "skeleton.right_fingers.pinky",

        "skeleton.right_arm.shoulder",
        "skeleton.right_arm.arm",
        "skeleton.right_arm.arm_twist",
        "skeleton.right_arm.forearm",
        "skeleton.right_arm.forearm_twist",
        "skeleton.right_arm.hand",

        "skeleton.left_arm_ik.shoulder",
        "skeleton.left_arm_ik.arm",
        "skeleton.left_arm_ik.arm_twist",
        "skeleton.left_arm_ik.forearm",
        "skeleton.left_arm_ik.forearm_twist",
        "skeleton.left_arm_ik.hand",

        "skeleton.right_leg_ik.upleg",
        "skeleton.right_leg_ik.upleg_twist",
        "skeleton.right_leg_ik.leg",
        "skeleton.right_leg_ik.leg_twist",

        "skeleton.left_leg_ik.upleg",
        "skeleton.left_leg_ik.upleg_twist",
        "skeleton.left_leg_ik.leg",
        "skeleton.left_leg_ik.leg_twist",
    ]

    # where to store the preset
    preset_subdir = "armature/retarget"


class DATA_MT_retarget_presets(Menu):
    bl_label = "Retarget Presets"
    preset_subdir = "armature/retarget"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class DATA_PT_expy_retarget(bpy.types.Panel):
    bl_label = "Expy Retargeting"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def sided_rows(self, ob, limbs, bone_names, suffix=""):
        split = self.layout.split()

        labels = None
        for group in limbs:
            col = split.column()
            row = col.row()
            if not labels:
                row.label(text='Right')
                labels = split.column()
                row = labels.row()
                row.label(text="")
            else:
                row.label(text='Left')

            for k in bone_names:
                row = col.row()
                row.prop_search(group, k, ob.data, "bones", text="")

        for k in bone_names:
            row = labels.row()
            row.label(text=(k + suffix).title())

    def draw(self, context):
        ob = context.object
        layout = self.layout

        row = layout.row(align=True)
        row.menu(DATA_MT_retarget_presets.__name__, text=DATA_MT_retarget_presets.bl_label)
        row.operator(AddPresetArmatureRetarget.bl_idname, text="", icon='ZOOM_IN')
        row.operator(AddPresetArmatureRetarget.bl_idname, text="", icon='ZOOM_OUT').remove_active = True

        skeleton = ob.data.expykit_retarget

        row = layout.row()
        row.prop(skeleton, "advanced_on", text="Show All", toggle=True)

        if skeleton.advanced_on:
            sides = "right", "left"
            split = layout.split()
            finger_bones = ('a', 'b', 'c')
            for side, group in zip(sides, [skeleton.right_fingers, skeleton.left_fingers]):
                col = split.column()

                for k in group.keys():
                    row = col.row()
                    row.label(text=" ".join((side, k)).title())
                    finger = getattr(group, k)
                    for slot in finger_bones:
                        row = col.row()
                        row.prop_search(finger, slot, ob.data, "bones", text="")
            layout.separator()

        if skeleton.advanced_on:
            arm_bones = ('shoulder', 'arm', 'arm_twist', 'forearm', 'forearm_twist', 'hand')
            self.sided_rows(ob, (skeleton.right_arm_ik, skeleton.left_arm_ik), arm_bones, suffix=" IK")
        else:
            arm_bones = ('shoulder', 'arm', 'forearm', 'hand')
        self.sided_rows(ob, (skeleton.right_arm, skeleton.left_arm), arm_bones)

        layout.separator()
        for slot in ('head', 'neck', 'spine2', 'spine1', 'spine', 'hips'):
            row = layout.row()
            row.prop_search(ob.data.expykit_retarget.spine, slot, ob.data, "bones", text=slot.title())

        layout.separator()
        if skeleton.advanced_on:
            leg_bones = ('upleg', 'upleg_twist', 'leg', 'leg_twist', 'foot', 'toe')
            self.sided_rows(ob, (skeleton.right_leg_ik, skeleton.left_leg_ik), leg_bones, suffix=" IK")
        else:
            leg_bones = ('upleg', 'leg', 'foot', 'toe')
        self.sided_rows(ob, (skeleton.right_leg, skeleton.left_leg), leg_bones)


def register_properties():
    bpy.utils.register_class(DATA_MT_retarget_presets)
    bpy.utils.register_class(AddPresetArmatureRetarget)

def unregister_properties():
    bpy.utils.unregister_class(DATA_MT_retarget_presets)
    bpy.utils.unregister_class(AddPresetArmatureRetarget)
