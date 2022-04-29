import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Menu
from bl_operators.presets import AddPresetBase

from . import operators
from . import preset_handler
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
    bl_idname = "OBJECT_MT_expykit_binding_menu"

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
    bl_idname = "OBJECT_MT_expykit_convert_menu"

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
    bl_idname = "OBJECT_MT_expykit_anim_menu"

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


class ExecutePresetArmatureRetarget(Operator):
    """Apply a Bone Retarget Preset"""
    bl_idname = "object.expy_kit_armature_preset_apply"
    bl_label = "Apply Bone Retarget Preset"

    filepath: StringProperty(
        subtype='FILE_PATH',
        options={'SKIP_SAVE'},
    )
    menu_idname: StringProperty(
        name="Menu ID Name",
        description="ID name of the menu this was called from",
        options={'SKIP_SAVE'},
    )

    @staticmethod
    def validate(armature_data):
        settings = armature_data.expykit_retarget
        for group in ('spine', 'left_arm', 'left_arm_ik', 'right_arm', 'right_arm_ik',
                      'right_leg', 'right_leg_ik', 'left_leg', 'left_leg_ik', 'face'):

            trg_setting = getattr(settings, group)
            for k, v in trg_setting.items():
                try:
                    if v not in armature_data.bones:
                        setattr(trg_setting, k, "")
                except TypeError:
                    continue

        finger_bones = 'a', 'b', 'c'
        for trg_grp in settings.left_fingers, settings.right_fingers:
            for k, trg_finger in trg_grp.items():
                if k == 'name':  # skip Property Group name
                    continue

                for slot in finger_bones:
                    bone_name = trg_finger.get(slot)
                    if bone_name not in armature_data.bones:
                        trg_finger[slot] = ""


    def execute(self, context):
        from os.path import basename, splitext
        filepath = self.filepath

        # change the menu title to the most recently chosen option
        preset_class = DATA_MT_retarget_presets
        preset_class.bl_label = bpy.path.display_name(basename(filepath), title_case=False)

        ext = splitext(filepath)[1].lower()

        if ext not in {".py", ".xml"}:
            self.report({'ERROR'}, "Unknown file type: %r" % ext)
            return {'CANCELLED'}

        if hasattr(preset_class, "reset_cb"):
            preset_class.reset_cb(context)

        if ext == ".py":
            try:
                bpy.utils.execfile(filepath)
            except Exception as ex:
                self.report({'ERROR'}, "Failed to execute the preset: " + repr(ex))

        elif ext == ".xml":
            import rna_xml
            rna_xml.xml_file_run(context,
                                 filepath,
                                 preset_class.preset_xml_map)

        if hasattr(preset_class, "post_cb"):
            preset_class.post_cb(context)

        self.validate(context.object.data)

        return {'FINISHED'}


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
        "skeleton.face",

        "skeleton.spine",
        "skeleton.right_arm",
        "skeleton.left_arm",
        "skeleton.right_leg",
        "skeleton.left_leg",

        "skeleton.left_fingers",
        "skeleton.right_fingers",

        "skeleton.right_arm_ik",
        "skeleton.left_arm_ik",

        "skeleton.right_leg_ik",
        "skeleton.left_leg_ik",

        "skeleton.deform_preset"
    ]

    # where to store the preset
    preset_subdir = preset_handler.PRESETS_SUBDIR


class ClearArmatureRetarget(Operator):
    bl_idname = "object.expy_kit_armature_clear"
    bl_label = "Clear Retarget Settings"

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        skeleton = context.object.data.expykit_retarget
        for setting in (skeleton.right_arm, skeleton.left_arm, skeleton.spine, skeleton.right_leg,
                        skeleton.left_leg, skeleton.right_arm_ik, skeleton.left_arm_ik,
                        skeleton.right_leg_ik, skeleton.left_leg_ik,
                        skeleton.face,
                        ):
            for k in setting.keys():
                try:
                    setattr(setting, k, '')
                except TypeError:
                    continue

        for settings in (skeleton.right_fingers, skeleton.left_fingers):
            for setting in [getattr(settings, k) for k in settings.keys()]:
                try:
                    for k in setting.keys():
                        setattr(setting, k, '')
                except AttributeError:
                    continue

        skeleton.root = ''
        skeleton.deform_preset = '--'

        return {'FINISHED'}


class DATA_MT_retarget_presets(Menu):
    bl_label = "Retarget Presets"
    preset_subdir = AddPresetArmatureRetarget.preset_subdir
    preset_operator = ExecutePresetArmatureRetarget.bl_idname
    draw = Menu.draw_preset


class DATA_PT_expy_retarget(bpy.types.Panel):
    bl_label = "Expy Retargeting"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Expy'

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

        split = layout.split(factor=0.75)
        split.menu(DATA_MT_retarget_presets.__name__, text=DATA_MT_retarget_presets.bl_label)
        row = split.row(align=True)
        row.operator(AddPresetArmatureRetarget.bl_idname, text="+")
        row.operator(AddPresetArmatureRetarget.bl_idname, text="-").remove_active = True

        skeleton = ob.data.expykit_retarget

        row = layout.row(align=True)
        row.prop(skeleton, "face_on", text="Face", toggle=True)
        row.prop(skeleton, "twist_on", text="Twist", toggle=True)
        row.prop(skeleton, "fingers_on", text="Fingers", toggle=True)
        row.prop(skeleton, "ik_on", text="IK", toggle=True)

        if skeleton.face_on:
            row = layout.row()
            row.prop_search(skeleton.face, "jaw", ob.data, "bones", text="Jaw")

            split = layout.split()
            col = split.column()
            col.label(text="Right")
            col.prop_search(skeleton.face, "right_eye", ob.data, "bones", text="")
            col.prop_search(skeleton.face, "right_upLid", ob.data, "bones", text="")

            col = split.column()
            col.label(text="")
            col.label(text="Eye")
            col.label(text="Up Lid")

            col = split.column()
            col.label(text="Left")
            col.prop_search(skeleton.face, "left_eye", ob.data, "bones", text="")
            col.prop_search(skeleton.face, "left_upLid", ob.data, "bones", text="")

            row = layout.row()
            row.prop(skeleton.face, "super_copy", text="As Rigify Super Copy")
            layout.separator()

        if skeleton.fingers_on:
            sides = "right", "left"
            split = layout.split()
            finger_bones = ('a', 'b', 'c')
            fingers = ('thumb', 'index', 'middle', 'ring', 'pinky')
            for side, group in zip(sides, [skeleton.right_fingers, skeleton.left_fingers]):
                col = split.column()

                for k in fingers:
                    if k == 'name':  # skip Property Group name
                        continue
                    row = col.row()
                    row.label(text=" ".join((side, k)).title())
                    finger = getattr(group, k)
                    for slot in finger_bones:
                        row = col.row()
                        row.prop_search(finger, slot, ob.data, "bones", text="")
            layout.separator()

        if skeleton.twist_on:
            arm_bones = ('shoulder', 'arm', 'arm_twist', 'forearm', 'forearm_twist', 'hand')
        else:
            arm_bones = ('shoulder', 'arm', 'forearm', 'hand')
        if skeleton.ik_on:
            self.sided_rows(ob, (skeleton.right_arm_ik, skeleton.left_arm_ik), arm_bones, suffix=" IK")
        self.sided_rows(ob, (skeleton.right_arm, skeleton.left_arm), arm_bones)

        layout.separator()
        for slot in ('head', 'neck', 'spine2', 'spine1', 'spine', 'hips'):
            row = layout.row()
            row.prop_search(skeleton.spine, slot, ob.data, "bones", text=slot.title())

        layout.separator()
        if skeleton.twist_on:
            leg_bones = ('upleg', 'upleg_twist', 'leg', 'leg_twist', 'foot', 'toe')
        else:
            leg_bones = ('upleg', 'leg', 'foot', 'toe')
        if skeleton.ik_on:
            self.sided_rows(ob, (skeleton.right_leg_ik, skeleton.left_leg_ik), leg_bones, suffix=" IK")
        self.sided_rows(ob, (skeleton.right_leg, skeleton.left_leg), leg_bones)

        layout.separator()
        row = layout.row()
        row.prop_search(skeleton, 'root', ob.data, "bones", text="Root")

        layout.separator()
        row = layout.row()
        row.prop(skeleton, 'deform_preset')

        row = layout.row()
        row.operator(ClearArmatureRetarget.bl_idname, text="Clear All")


def register_classes():
    bpy.utils.register_class(ClearArmatureRetarget)
    bpy.utils.register_class(DATA_MT_retarget_presets)
    bpy.utils.register_class(ExecutePresetArmatureRetarget)
    bpy.utils.register_class(AddPresetArmatureRetarget)

    bpy.utils.register_class(BindingsMenu)
    bpy.utils.register_class(ConvertMenu)
    bpy.utils.register_class(AnimMenu)
    bpy.utils.register_class(ActionRenameSimple)
    bpy.utils.register_class(DATA_PT_expy_buttons)
    bpy.utils.register_class(DATA_PT_expy_retarget)

    bpy.types.VIEW3D_MT_pose_context_menu.append(pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.append(armature_context_options)
    bpy.types.DOPESHEET_HT_header.append(action_header_buttons)


def unregister_classes():
    bpy.utils.unregister_class(DATA_MT_retarget_presets)
    bpy.utils.unregister_class(AddPresetArmatureRetarget)
    bpy.utils.unregister_class(ExecutePresetArmatureRetarget)
    bpy.utils.unregister_class(ClearArmatureRetarget)

    bpy.types.VIEW3D_MT_pose_context_menu.remove(pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.remove(armature_context_options)
    bpy.types.DOPESHEET_HT_header.remove(action_header_buttons)

    bpy.utils.unregister_class(BindingsMenu)
    bpy.utils.unregister_class(ConvertMenu)
    bpy.utils.unregister_class(AnimMenu)
    bpy.utils.unregister_class(ActionRenameSimple)
    bpy.utils.unregister_class(DATA_PT_expy_buttons)
    bpy.utils.unregister_class(DATA_PT_expy_retarget)
