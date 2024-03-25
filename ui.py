import bpy
from bpy.props import StringProperty
from bpy.props import FloatProperty
from bpy.props import PointerProperty
from bpy.props import EnumProperty
from bpy.types import Context, Operator, Menu
from bl_operators.presets import AddPresetBase

from . import operators
from . import preset_handler
from . import properties
from .utils import make_annotations, layout_split


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
        op = row.operator(operators.SelectConstrainedControls.bl_idname)
        op.select_type = 'constr'


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


class ActionRemoveRenameData(bpy.types.Operator):
    """Remove action rename data"""
    bl_idname = "object.expykit_remove_action_rename_data"
    bl_label = "Expy remove rename data"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        for action in bpy.data.actions:
            action.expykit_name_candidates.clear()

        return {'FINISHED'}


class ActionMakeActive(bpy.types.Operator):
    """Apply next action and adjust timeline"""
    bl_idname = "object.expykit_make_action_active"
    bl_label = "Expy apply action"

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context: Context):
        ob = context.object
        to_rename = [a for a in bpy.data.actions if len(a.expykit_name_candidates) > 1 and operators.validate_actions(a, ob.path_resolve)]

        if len(to_rename) == 0:
            return {'CANCELLED'}

        if not ob.animation_data.action:
            action = to_rename.pop()
        else:
            try:
                idx = to_rename.index(ob.animation_data.action)
            except ValueError:
                action = to_rename.pop()
            else:
                action = to_rename[idx - 1]

        bpy.context.object.animation_data.action = action
        bpy.ops.object.expykit_action_to_range()

        return {'FINISHED'}


@make_annotations
class ActionRenameSimple(bpy.types.Operator):
    """Rename Current Action"""
    bl_idname = "object.expykit_rename_action_simple"
    bl_label = "Expy Action Rename"
    bl_options = {'REGISTER', 'UNDO'}

    new_name = StringProperty(default="", name="Renamed to")

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


class VIEW3D_PT_expy_rename_candidates(bpy.types.Panel):
    bl_label = "Action Name Candidates"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Expy"
    bl_idname = "VIEW3D_PT_expy_rename_candidates"

    @classmethod
    def poll(cls, context):
        if not context.mode == 'POSE':
            return False

        try:
            next(a for a in bpy.data.actions if len(a.expykit_name_candidates) > 1)
        except StopIteration:
            return False

        return True

    def draw(self, context):
        layout = self.layout

        to_rename = [a for a in bpy.data.actions if len(a.expykit_name_candidates) > 1 and operators.validate_actions(a, context.object.path_resolve)]

        row = layout.row()
        row.operator(ActionMakeActive.bl_idname, text="Next of {} actions to rename".format(len(to_rename)))

        action = context.object.animation_data.action
        if not action:
            return

        row = layout.row()
        row.label(text=action.name)

        for candidate in action.expykit_name_candidates:
            if candidate.name in bpy.data.actions:
                # that name has been taken
                continue

            row = layout.row()
            op = row.operator(ActionRenameSimple.bl_idname, text=candidate.name)
            op.new_name = candidate.name


class VIEW3D_PT_expy_rename_advanced(bpy.types.Panel):
    bl_label = "Advanced Options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Expy"

    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = VIEW3D_PT_expy_rename_candidates.bl_idname

    @classmethod
    def poll(cls, context):
        if not context.mode == 'POSE':
            return False

        to_rename = [a for a in bpy.data.actions if len(a.expykit_name_candidates) > 1]
        return len(to_rename) > 0

    def draw(self, context):
        row = self.layout.row()
        row.operator(ActionRemoveRenameData.bl_idname, text="Remove Rename Data")


@make_annotations
class ExecutePresetArmatureRetarget(Operator):
    """Apply a Bone Retarget Preset"""
    bl_idname = "object.expy_kit_armature_preset_apply"
    bl_label = "Apply Bone Retarget Preset"

    filepath = StringProperty(
        subtype='FILE_PATH',
        options={'SKIP_SAVE'},
    )
    menu_idname = StringProperty(
        name="Menu ID Name",
        description="ID name of the menu this was called from",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        from os.path import basename, splitext
        filepath = self.filepath

        # change the menu title to the most recently chosen option
        preset_class = VIEW3D_MT_retarget_presets
        if bpy.app.version < (2, 93, 0):
            preset_class.bl_label = bpy.path.display_name(basename(filepath))
        else:
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

        preset_handler.validate_preset(context.object.data)

        settings = context.object.data.expykit_retarget
        preset_handler.reset_preset_names(settings)

        return {'FINISHED'}


class AddPresetArmatureRetarget(AddPresetBase, Operator):
    """Add a Bone Retarget Preset"""
    bl_idname = "object.expy_kit_armature_preset_add"
    bl_label = "Add Bone Retarget Preset"
    preset_menu = "VIEW3D_MT_retarget_presets"

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
                if k == 'name':
                    continue
                try:
                    setattr(setting, k, '')
                except TypeError:
                    continue

        for settings in (skeleton.right_fingers, skeleton.left_fingers):
            for setting in [getattr(settings, k) for k in settings.keys()]:
                try:
                    for k in setting.keys():
                        if k == 'name':
                            continue
                        setattr(setting, k, '')
                except AttributeError:
                    continue

        skeleton.root = ''
        skeleton.deform_preset = '--'

        return {'FINISHED'}


@make_annotations
class SetToActiveBone(Operator):
    """Set adjacent UI entry to active bone"""
    bl_idname = "object.expy_kit_set_to_active_bone"
    bl_label = "Set Expy Kit value to active bone"

    attr_name = StringProperty(default="", options={'SKIP_SAVE'})
    sub_attr_name = StringProperty(default="", options={'SKIP_SAVE'})
    slot_name = StringProperty(default="", options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        if not context.active_pose_bone:
            return False

        return True

    def execute(self, context):
        if not self.attr_name:
            return {'FINISHED'}

        skeleton = context.object.data.expykit_retarget

        if not self.slot_name:
            if self.attr_name == 'root':
                setattr(skeleton, 'root', context.active_pose_bone.name)

            return {'FINISHED'}

        try:
            rig_grp = getattr(skeleton, self.attr_name)
        except AttributeError:
            # TODO: warning
            return {'FINISHED'}
        else:
            if self.sub_attr_name:
                rig_grp = getattr(rig_grp, self.sub_attr_name)

            setattr(rig_grp, self.slot_name, context.active_pose_bone.name)

        return {'FINISHED'}


@make_annotations
class MirrorSettings(Operator):
    """Mirror Settings to the other side"""
    bl_idname = "object.expy_kit_settings_mirror"
    bl_label = "Mirror Skeleton Mapping"
    bl_options = {'REGISTER', 'UNDO'}

    src_setting = StringProperty(default="", options={'SKIP_SAVE'})
    trg_setting = StringProperty(default="", options={'SKIP_SAVE'})

    tolerance = FloatProperty(default=0.001)

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if not context.active_pose_bone:
            return False
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.data.expykit_retarget:
            return False

        return True

    def _is_mirrored_vec(self, trg_head, src_head):
        epsilon = self.tolerance
        if abs(trg_head.x + src_head.x) > epsilon:
            return False
        if abs(trg_head.y - src_head.y) > epsilon:
            return False
        return abs(trg_head.z - src_head.z) < epsilon

    def _is_mirrored(self, src_bone, trg_bone):
        if not self._is_mirrored_vec(src_bone.head_local, trg_bone.head_local):
            return False
        if not self._is_mirrored_vec(src_bone.tail_local, trg_bone.tail_local):
            return False

        return True

    def find_mirrored(self, arm_data, bone):
        # TODO: should be in bone_utils
        # TODO: should select best among mirror candidates
        return next((b for b in arm_data.bones if self._is_mirrored(bone, b)), None)

    def execute(self, context):
        if not self.src_setting:
            return {'FINISHED'}
        if not self.trg_setting:
            return {'FINISHED'}

        skeleton = context.object.data.expykit_retarget

        try:
            src_grp = getattr(skeleton, self.src_setting)
        except AttributeError:
            # TODO: warning
            return {'FINISHED'}

        try:
            trg_grp = getattr(skeleton, self.trg_setting)
        except AttributeError:
            # TODO: warning
            return {'FINISHED'}

        arm_data = context.object.data
        if 'fingers' in self.trg_setting:
            for finger_name in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                for attr_name in ('a', 'b', 'c'):
                    bone_name = getattr(getattr(src_grp, finger_name), attr_name)
                    if not bone_name:
                        continue
                    m_bone = self.find_mirrored(arm_data,
                                                arm_data.bones[bone_name])
                    if not m_bone:
                        continue

                    setattr(getattr(trg_grp, finger_name), attr_name, m_bone.name)

            return {'FINISHED'}

        for k, v in src_grp.items():
            if not v:
                continue

            try:
                bone = arm_data.bones[v]
            except KeyError:
                continue

            m_bone = self.find_mirrored(arm_data, bone)
            if m_bone:
                setattr(trg_grp, k, m_bone.name)

        return {'FINISHED'}


class VIEW3D_MT_retarget_presets(Menu):
    bl_label = "Retarget Presets"
    preset_subdir = AddPresetArmatureRetarget.preset_subdir
    preset_operator = ExecutePresetArmatureRetarget.bl_idname
    draw = Menu.draw_preset


# for blender < 2.79 we use the binding command in the pose mode specials menu instead
if bpy.app.version >= (2, 79, 0):
    class BindFromPanelSelection(bpy.types.Operator):
        """Constrain to armature selected in panel"""
        bl_idname = "object.expy_kit_bind_from_panel"
        bl_label = "Bind Armatures"
        bl_options = {'REGISTER', 'UNDO'}

        @classmethod
        def poll(cls, context):
            return context.mode == 'POSE' and context.scene.expykit_bind_to and context.object != context.scene.expykit_bind_to

        def execute(self, context: Context):
            for ob in context.selected_objects:
                ob.select_set(ob == context.object)

            context.scene.expykit_bind_to.select_set(True)
            context.view_layer.objects.active = context.scene.expykit_bind_to
            bpy.ops.object.mode_set(mode='POSE')

            _ad = context.scene.expykit_bind_to.animation_data
            if _ad and _ad.action:
                # TODO: this should be in the constrain operator
                bpy.ops.object.expykit_action_to_range()

            bpy.ops.armature.expykit_constrain_to_armature('INVOKE_DEFAULT', force_dialog=True)

            return {'FINISHED'}


    class VIEW3D_PT_BindPanel(bpy.types.Panel):
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "Expy"
        bl_label = "Bind To"

        @classmethod
        def poll(cls, context):
            return context.mode == 'POSE'

        def draw(self, context):
            layout = self.layout
            layout.prop(context.scene, 'expykit_bind_to', text="")

            layout.operator(BindFromPanelSelection.bl_idname)


class RetargetBasePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Expy"

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def sided_rows(self, ob, limbs, bone_names, suffix=""):
        split = layout_split(self.layout)

        labels = None
        side = 'right'
        for group in limbs:
            attr_tokens = [side, group.name]
            attr_suffix = suffix.strip(' ').lower()
            if attr_suffix:
                attr_tokens.append(attr_suffix)

            attr_name = '_'.join(attr_tokens)

            col = split.column()
            row = col.row()
            if not labels:
                row.label(text=side.title())
                labels = split.column()
                row = labels.row()

                mirror_props = row.operator(MirrorSettings.bl_idname, text="<--")
                mirror_props.trg_setting = attr_name

                mirror_props_2 = row.operator(MirrorSettings.bl_idname, text="-->")
                mirror_props_2.src_setting = attr_name
                side = 'left'
            else:
                mirror_props.src_setting = attr_name
                mirror_props_2.trg_setting = attr_name
                row.label(text=side.title())

            for k in bone_names:
                bsplit = layout_split(col, factor=0.85)
                bsplit.prop_search(group, k, ob.data, "bones", text="")

                props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
                props.attr_name = attr_name
                props.slot_name = k

        for k in bone_names:
            row = labels.row()
            row.label(text=(k + suffix).title())


class VIEW3D_PT_expy_retarget(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Expy Mapping"

    def draw(self, context):
        layout = self.layout

        split = layout_split(layout, factor=0.75)
        split.menu(VIEW3D_MT_retarget_presets.__name__, text=VIEW3D_MT_retarget_presets.bl_label)
        row = split.row(align=True)
        row.operator(AddPresetArmatureRetarget.bl_idname, text="+")
        row.operator(AddPresetArmatureRetarget.bl_idname, text="-").remove_active = True


class VIEW3D_PT_expy_retarget_face(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Face"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget

        bsplit = layout_split(layout, factor=0.85)
        bsplit.prop_search(skeleton.face, "jaw", ob.data, "bones", text="Jaw")
        props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
        props.attr_name = 'face'
        props.slot_name = 'jaw'

        split = layout_split(layout)
        col = split.column()
        col.label(text="Right")

        bsplit = layout_split(col, factor=0.85)
        col = bsplit.column()
        col.prop_search(skeleton.face, "right_eye", ob.data, "bones", text="")
        col.prop_search(skeleton.face, "right_upLid", ob.data, "bones", text="")

        col = bsplit.column()
        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'right_eye'

        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'right_upLid'

        col = split.column()
        col.label(text="")
        col.label(text="Eye")
        col.label(text="Up Lid")

        col = split.column()
        col.label(text="Left")

        bsplit = layout_split(col, factor=0.85)
        col = bsplit.column()
        col.prop_search(skeleton.face, "left_eye", ob.data, "bones", text="")
        col.prop_search(skeleton.face, "left_upLid", ob.data, "bones", text="")

        col = bsplit.column()
        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'left_eye'

        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'left_upLid'

        row = layout.row()
        row.prop(skeleton.face, "super_copy", text="As Rigify Super Copy")


class VIEW3D_PT_expy_retarget_fingers(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Fingers"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget

        sides = "right", "left"
        split = layout_split(layout)
        finger_bones = ('a', 'b', 'c')
        fingers = ('thumb', 'index', 'middle', 'ring', 'pinky')
        m_props = []
        for side, group in zip(sides, [skeleton.right_fingers, skeleton.left_fingers]):
            col = split.column()
            m_props.append(col.operator(MirrorSettings.bl_idname, text="<--" if side == 'right' else "-->"))

            for k in fingers:
                if k == 'name':  # skip Property Group name
                    continue
                row = col.row()
                row.label(text=" ".join((side, k)).title())
                finger = getattr(group, k)
                for slot in finger_bones:
                    bsplit = layout_split(col, factor=0.85)
                    bsplit.prop_search(finger, slot, ob.data, "bones", text="")

                    f_props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
                    f_props.attr_name = '_'.join([side, group.name])
                    f_props.sub_attr_name = k
                    f_props.slot_name = slot

        m_props[0].trg_setting = "right_fingers"
        m_props[0].src_setting = "left_fingers"

        m_props[1].trg_setting = "left_fingers"
        m_props[1].src_setting = "right_fingers"


class VIEW3D_PT_expy_retarget_arms_IK(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Arms IK"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget
        arm_bones = ('shoulder', 'arm', 'forearm', 'hand')

        self.sided_rows(ob, (skeleton.right_arm_ik, skeleton.left_arm_ik), arm_bones, suffix=" IK")


class VIEW3D_PT_expy_retarget_arms(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Arms"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget

        row = layout.row()
        row.prop(ob.data, "expykit_twist_on", text="Display Twist Bones")

        if ob.data.expykit_twist_on:
            arm_bones = ('shoulder', 'arm', 'arm_twist', 'arm_twist_02', 'forearm', 'forearm_twist', 'forearm_twist_02', 'hand')
        else:
            arm_bones = ('shoulder', 'arm', 'forearm', 'hand')

        self.sided_rows(ob, (skeleton.right_arm, skeleton.left_arm), arm_bones)


class VIEW3D_PT_expy_retarget_spine(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Spine"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget

        for slot in ('head', 'neck', 'spine2', 'spine1', 'spine', 'hips'):
            split = layout_split(layout, factor=0.85)
            split.prop_search(skeleton.spine, slot, ob.data, "bones", text="Chest" if slot == 'spine2' else slot.title())
            props = split.operator(SetToActiveBone.bl_idname, text="<-")
            props.attr_name = 'spine'
            props.slot_name = slot


class VIEW3D_PT_expy_retarget_leg_IK(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Legs IK"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object

        skeleton = ob.data.expykit_retarget

        leg_bones = ('upleg', 'leg', 'foot', 'toe')
        self.sided_rows(ob, (skeleton.right_leg_ik, skeleton.left_leg_ik), leg_bones, suffix=" IK")


class VIEW3D_PT_expy_retarget_leg(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Legs"

    def draw(self, context):
        ob = context.object

        skeleton = ob.data.expykit_retarget

        row = self.layout.row(align=True)
        row.prop(ob.data, "expykit_twist_on", text="Display Twist Bones")

        if ob.data.expykit_twist_on:
            leg_bones = ('upleg', 'upleg_twist', 'upleg_twist_02', 'leg', 'leg_twist', 'leg_twist_02', 'foot', 'toe')
        else:
            leg_bones = ('upleg', 'leg', 'foot', 'toe')

        self.sided_rows(ob, (skeleton.right_leg, skeleton.left_leg), leg_bones)


class VIEW3D_PT_expy_retarget_root(RetargetBasePanel, bpy.types.Panel):
    bl_label = "Root"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        skeleton = ob.data.expykit_retarget

        split = layout_split(layout, factor=0.85)
        split.prop_search(skeleton, 'root', ob.data, "bones", text="Root")
        s_props = split.operator(SetToActiveBone.bl_idname, text="<-")
        s_props.attr_name = 'root'
        s_props.sub_attr_name = ''

        layout.separator()
        row = layout.row()
        row.prop(skeleton, 'deform_preset')

        row = layout.row()
        row.operator(ClearArmatureRetarget.bl_idname, text="Clear All")


def poll_armature_bind_to(self, obj):
    return obj != bpy.context.object and obj.type == 'ARMATURE'


def register_classes():
    if bpy.app.version >= (2, 79, 0):
        bpy.types.Scene.expykit_bind_to = PointerProperty(type=bpy.types.Object,
                                                          name="Bind To",
                                                          poll=poll_armature_bind_to,
                                                          description="This armature will drive another one.")

    bpy.utils.register_class(ClearArmatureRetarget)
    bpy.utils.register_class(VIEW3D_MT_retarget_presets)
    bpy.utils.register_class(ExecutePresetArmatureRetarget)
    bpy.utils.register_class(AddPresetArmatureRetarget)

    bpy.utils.register_class(SetToActiveBone)
    bpy.utils.register_class(MirrorSettings)

    bpy.utils.register_class(BindingsMenu)
    bpy.utils.register_class(ConvertMenu)
    bpy.utils.register_class(AnimMenu)

    bpy.utils.register_class(ActionRenameSimple)
    bpy.utils.register_class(ActionMakeActive)
    bpy.utils.register_class(ActionRemoveRenameData)
    bpy.utils.register_class(VIEW3D_PT_expy_rename_candidates)
    bpy.utils.register_class(VIEW3D_PT_expy_rename_advanced)

    if bpy.app.version >= (2, 79, 0):
        bpy.utils.register_class(BindFromPanelSelection)
        bpy.utils.register_class(VIEW3D_PT_BindPanel)

    bpy.utils.register_class(VIEW3D_PT_expy_retarget)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_face)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_fingers)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_arms_IK)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_arms)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_spine)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_leg_IK)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_leg)
    bpy.utils.register_class(VIEW3D_PT_expy_retarget_root)

    bpy.types.VIEW3D_MT_pose_context_menu.append(pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.append(armature_context_options)
    bpy.types.DOPESHEET_HT_header.append(action_header_buttons)


def unregister_classes():
    bpy.utils.unregister_class(VIEW3D_MT_retarget_presets)
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
    bpy.utils.unregister_class(ActionMakeActive)
    bpy.utils.unregister_class(ActionRemoveRenameData)
    bpy.utils.unregister_class(VIEW3D_PT_expy_rename_candidates)
    bpy.utils.unregister_class(VIEW3D_PT_expy_rename_advanced)

    if bpy.app.version >= (2, 79, 0):
        bpy.utils.unregister_class(BindFromPanelSelection)
        bpy.utils.unregister_class(VIEW3D_PT_BindPanel)

    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_root)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_leg_IK)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_leg)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_spine)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_arms_IK)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_arms)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_fingers)
    bpy.utils.unregister_class(VIEW3D_PT_expy_retarget_face)

    bpy.utils.unregister_class(SetToActiveBone)
    bpy.utils.unregister_class(MirrorSettings)

    if bpy.app.version >= (2, 79, 0):
        del bpy.types.Scene.expykit_bind_to
