from math import pi
import os

import bpy
from bpy.props import BoolProperty
from bpy.props import EnumProperty
from bpy.props import FloatProperty
from bpy.props import IntProperty
from bpy.props import StringProperty
from bpy.props import CollectionProperty
from bpy.props import FloatVectorProperty

from bpy_extras.io_utils import ImportHelper

from itertools import chain

from .rig_mapping import bone_mapping
from . import preset_handler
from . import bone_utils
from . import fbx_helper
from .version_compatibility import make_annotations, matmul, get_preferences, layout_split

from mathutils import Vector
from mathutils import Matrix

CONSTR_STATUS = (
    ('enable', "Enable", "Enable All Constraints"),
    ('disable', "Disable", "Disable All Constraints"),
    ('remove', "Remove", "Remove All Constraints")
)


CONSTR_TYPES = bpy.types.PoseBoneConstraints.bl_rna.functions['new'].parameters['type'].enum_items.keys()
CONSTR_TYPES.append('ALL_TYPES')


@make_annotations
class ConstraintStatus(bpy.types.Operator):
    """Disable/Enable bone constraints."""
    bl_idname = "object.expykit_set_constraints_status"
    bl_label = "Enable/disable constraints"
    bl_options = {'REGISTER', 'UNDO'}

    set_status = EnumProperty(items=CONSTR_STATUS,
                             name="Status",
                             default='enable')

    selected_only = BoolProperty(name="Only Selected",
                                default=False)

    constr_type = EnumProperty(items=[(ct, ct.replace('_', ' ').title(), ct) for ct in CONSTR_TYPES],
                              name="Constraint Type",
                              default='ALL_TYPES')

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.mode != 'POSE':
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        bones = context.selected_pose_bones if self.selected_only else context.object.pose.bones
        if self.set_status == 'remove':
            for bone in bones:
                for constr in reversed(bone.constraints):
                    if self.constr_type != 'ALL_TYPES' and constr.type != self.constr_type:
                        continue

                    bone.constraints.remove(constr)
        else:
            for bone in bones:
                for constr in bone.constraints:
                    if self.constr_type != 'ALL_TYPES' and constr.type != self.constr_type:
                        continue

                    constr.mute = self.set_status == 'disable'

        return {'FINISHED'}


@make_annotations
class SelectConstrainedControls(bpy.types.Operator):
    bl_idname = "armature.expykit_select_constrained_ctrls"
    bl_label = "Select constrained controls"
    bl_description = "Select bone controls with constraints or animations"
    bl_options = {'REGISTER', 'UNDO'}

    select_type = EnumProperty(items=[
        ('constr', "Constrained", "Select constrained controls"),
        ('anim', "Animated", "Select animated controls"),
    ],
        name="Select if",
        default='constr')

    skip_deform = BoolProperty(name="Skip Deform Bones", default=True)
    has_shape = BoolProperty(name="Only Control shapes", default=True)

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.mode != 'POSE':
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        ob = context.object

        if self.select_type == 'constr':
            for pb in bone_utils.get_constrained_controls(ob, unselect=True, use_deform=not self.skip_deform):
                pb.bone.select = bool(pb.custom_shape) if self.has_shape else True

        elif self.select_type == 'anim':
            if not ob.animation_data:
                return {'FINISHED'}
            if not ob.animation_data.action:
                return {'FINISHED'}

            for fc in ob.animation_data.action.fcurves:
                bone_name = crv_bone_name(fc)
                if not bone_name:
                    continue
                try:
                    bone = ob.data.bones[bone_name]
                except KeyError:
                    continue
                bone.select = True

        return {'FINISHED'}


@make_annotations
class RevertDotBoneNames(bpy.types.Operator):
    """Reverts dots in bones that have renamed by Unreal Engine"""
    bl_idname = "object.expykit_dot_bone_names"
    bl_label = "Revert dots in Names (from UE4 renaming)"
    bl_options = {'REGISTER', 'UNDO'}

    sideletters_only = BoolProperty(name="Only Side Letters",
                                   description="i.e. '_L' to '.L'",
                                   default=True)

    selected_only = BoolProperty(name="Only Selected",
                                default=False)

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.mode != 'POSE':
            return False
        return context.object.type == 'ARMATURE'

    def execute(self, context):
        bones = context.selected_pose_bones if self.selected_only else context.object.pose.bones

        if self.sideletters_only:
            for bone in bones:
                for side in ("L", "R"):
                    if bone.name[:-1].endswith("_{0}_00".format(side)):
                        bone.name = bone.name.replace("_{0}_00".format(side), ".{0}.00".format(side))
                    elif bone.name.endswith("_{0}".format(side)):
                        bone.name = bone.name[:-2] + ".{0}".format(side)
        else:
            for bone in bones:
                bone.name = bone.name.replace('_', '.')

        return {'FINISHED'}


@make_annotations
class ConvertBoneNaming(bpy.types.Operator):
    """Convert Bone Names between Naming Convention"""
    bl_idname = "object.expykit_convert_bone_names"
    bl_label = "Convert Bone Names"
    bl_options = {'REGISTER', 'UNDO'}

    src_preset = EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Source Preset",
                             )

    trg_preset = EnumProperty(items=preset_handler.iterate_presets,
                             name="Target Preset",
                             )

    strip_prefix = BoolProperty(
        name="Strip Prefix",
        description="Remove prefix when found",
        default=True
    )

    anim_tracks = BoolProperty(
        name="Convert Animations",
        description="Convert Animation Tracks",
        default=True
    )

    replace_existing = BoolProperty(
        name="Take Over Existing Names",
        description='Bones already named after Target Preset will get ".001" suffix',
        default=True
    )

    prefix_separator = StringProperty(
        name="Prefix Separator",
        description="Separator between prefix and name, i.e: MyCharacter:head",
        default=":"
    )

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.mode != 'POSE':
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    @staticmethod
    def convert_presets(src_settings, target_settings):
        src_skeleton = preset_handler.get_preset_skel(src_settings)
        trg_skeleton = preset_handler.get_preset_skel(target_settings)

        return src_skeleton, trg_skeleton

    @staticmethod
    def convert_settings(current_settings, target_settings, validate=True):
        src_settings = preset_handler.PresetSkeleton()
        src_settings.copy(current_settings)

        src_skeleton = preset_handler.get_settings_skel(src_settings)
        trg_skeleton = preset_handler.set_preset_skel(target_settings, validate)

        return src_skeleton, trg_skeleton

    @staticmethod
    def rename_bones(context, src_skeleton, trg_skeleton, separator="", replace_existing=False, skip_ik=False):
        # FIXME: separator should not be necessary anymore, as it is handled at preset validation
        bone_names_map = src_skeleton.conversion_map(trg_skeleton, skip_ik=skip_ik)

        if separator:
            for bone in context.object.data.bones:
                if separator not in bone.name:
                    continue

                bone.name = bone.name.rsplit(separator, 1)[1]

        additional_bones = {}
        for src_name, trg_name in bone_names_map.items():
            if not trg_name:
                continue
            if not src_name:
                continue
            try:
                src_bone = context.object.data.bones.get(src_name, None)
            except SystemError:
                continue

            if not src_bone:
                continue

            if replace_existing:
                pre_existing_bone = context.object.data.bones.get(trg_name, None)
                if pre_existing_bone:
                    pre_existing_name = pre_existing_bone.name
                    pre_existing_bone.name = "{}.001".format(trg_name)
                    additional_bones[pre_existing_name] = pre_existing_bone.name

            src_bone.name = trg_name

        bone_names_map.update(additional_bones)
        return bone_names_map

    def execute(self, context):
        if self.src_preset == "--Current--":
            current_settings = context.object.data.expykit_retarget
            trg_settings = preset_handler.PresetSkeleton()
            trg_settings.copy(current_settings)
            src_skeleton, trg_skeleton = self.convert_settings(trg_settings, self.trg_preset, validate=False)

            set_preset = False
        else:
            src_skeleton, trg_skeleton = self.convert_presets(self.src_preset, self.trg_preset)

            set_preset = True

        if all((src_skeleton, trg_skeleton, src_skeleton != trg_skeleton)):
            if self.anim_tracks:
                actions = [action for action in bpy.data.actions if validate_actions(action, context.object.path_resolve)]
            else:
                actions = []

            bone_names_map = self.rename_bones(context, src_skeleton, trg_skeleton,
                                               self.prefix_separator if self.strip_prefix else "",
                                               self.replace_existing)

            if context.object.animation_data and context.object.data.animation_data:
                for driver in chain(context.object.animation_data.drivers, context.object.data.animation_data.drivers):
                    try:
                        driver_bone = driver.data_path.split('"')[1]
                    except IndexError:
                        continue

                    try:
                        trg_name = bone_names_map[driver_bone]
                    except KeyError:
                        continue

                    driver.data_path = driver.data_path.replace('bones["{0}"'.format(driver_bone),
                                                                'bones["{0}"'.format(trg_name))

            for action in actions:
                for fc in action.fcurves:
                    try:
                        track_bone = fc.data_path.split('"')[1]
                    except IndexError:
                        continue

                    if self.strip_prefix and self.prefix_separator in track_bone:
                        stripped_bone = track_bone.rsplit(self.prefix_separator, 1)[1]
                    else:
                        stripped_bone = track_bone

                    try:
                        trg_name = bone_names_map[stripped_bone]
                    except KeyError:
                        continue

                    fc.data_path = fc.data_path.replace('bones["{0}"'.format(track_bone),
                                                        'bones["{0}"'.format(trg_name))

            if set_preset:
                preset_handler.set_preset_skel(self.trg_preset)
            else:
                preset_handler.validate_preset(bpy.context.active_object.data, separator=self.prefix_separator)

        if bpy.app.version[0] > 2:
            # blender 3.0 objects do not immediately update renamed vertex groups
            for ob in bone_utils.iterate_rigged_obs(context.object):
                ob.data.update()

        return {'FINISHED'}


@make_annotations
class CreateTransformOffset(bpy.types.Operator):
    """Scale the Character and setup an Empty to preserve final transform"""
    bl_idname = "object.expykit_create_offset"
    bl_label = "Create Scale Offset"
    bl_options = {'REGISTER', 'UNDO'}

    container_name = StringProperty(name="Name", description="Name of the transform container", default="EMP-Offset")
    container_scale = FloatProperty(name="Scale", description="Scale of the transform container", default=0.01)
    fix_animations = BoolProperty(name="Fix Animations", description="Apply Offset to character animations", default=True)
    fix_constraints = BoolProperty(name="Fix Constraints", description="Apply Offset to character constraints", default=True)
    do_parent = BoolProperty(name="Execute and Exit", description="Parent to the new offset and exit",
                            default=False, options={'SKIP_SAVE'})

    _allowed_modes = ['OBJECT', 'POSE']

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.parent:
            return False
        if context.object.type != 'ARMATURE':
            return False
        if context.mode not in cls._allowed_modes:
            return False

        return True

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = layout_split(column, factor=0.2, align=True)
        row.label(text="Name")
        row.prop(self, 'container_name', text="")

        row = layout_split(column, factor=0.2, align=True)
        row.label(text="Scale")
        row.prop(self, "container_scale", text="")

        row = layout_split(column, factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_animations")

        row = layout_split(column, factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_constraints")

        row = layout_split(column, factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "do_parent", toggle=True)

    def execute(self, context):
        arm_ob = context.object
        emp_ob = bpy.data.objects.new(self.container_name, None)
        context.collection.objects.link(emp_ob)

        transform = Matrix().to_3x3() * self.container_scale
        emp_ob.matrix_world = transform.to_4x4()
        if self.do_parent:
            arm_ob.parent = emp_ob

        inverted = emp_ob.matrix_world.inverted()
        arm_ob.data.transform(inverted)
        arm_ob.update_tag()

        # bring in metarig if found
        try:
            metarig = next(ob for ob in bpy.data.objects if ob.type == 'ARMATURE' and ob.data.rigify_target_rig == arm_ob)
        except (StopIteration, AttributeError):  # Attribute Error if Rigify is not loaded
            pass
        else:
            if self.do_parent:
                metarig.parent = emp_ob
            metarig.data.transform(inverted)
            metarig.update_tag()

        if self.fix_constraints:
            # fix constraints rest lenghts
            for pbone in arm_ob.pose.bones:
                for constr in pbone.constraints:
                    if constr.type == 'STRETCH_TO':
                        constr.rest_length /= self.container_scale
                    elif constr.type == 'LIMIT_DISTANCE':
                        constr.distance /= self.container_scale
                    elif constr.type == 'ACTION':
                        if constr.target == arm_ob and constr.transform_channel.startswith('LOCATION'):
                            if constr.target_space != 'WORLD':
                                constr.min /= self.container_scale
                                constr.max /= self.container_scale
                    elif constr.type == 'LIMIT_LOCATION' and constr.owner_space != 'WORLD':
                        constr.min_x /= self.container_scale
                        constr.min_y /= self.container_scale
                        constr.min_z /= self.container_scale

                        constr.max_x /= self.container_scale
                        constr.max_y /= self.container_scale
                        constr.max_z /= self.container_scale

        # scale rigged meshes as well
        rigged = (ob for ob in bpy.data.objects if
                  next((mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object == context.object),
                           None))

        for ob in rigged:
            if ob.data.shape_keys:
                # cannot transform objects with shape keys
                ob.scale /= self.container_scale
            else:
                ob.data.transform(inverted)
            # fix scale dependent attrs in modifiers
            for mod in ob.modifiers:
                if mod.type == 'DISPLACE':
                    mod.strength /= self.container_scale
                elif mod.type == 'SOLIDIFY':
                    mod.thickness /= self.container_scale

        if self.fix_animations:
            path_resolve = arm_ob.path_resolve

            for action in bpy.data.actions:
                if not validate_actions(action, path_resolve):
                    continue

                for fc in action.fcurves:
                    data_path = fc.data_path

                    if not data_path.endswith('location'):
                        continue

                    for kf in fc.keyframe_points:
                        kf.co[1] /= self.container_scale

        return {'FINISHED'}


@make_annotations
class ExtractMetarig(bpy.types.Operator):
    """Create Metarig from current object"""
    bl_idname = "object.expykit_extract_metarig"
    bl_label = "Extract Metarig"
    bl_description = "Create Metarig from current object"
    bl_options = {'REGISTER', 'UNDO'}

    rig_preset = EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Rig Type",
                             )

    offset_knee = FloatProperty(name='Offset Knee',
                               default=0.0)

    offset_elbow = FloatProperty(name='Offset Elbow',
                                default=0.0)

    offset_fingers = FloatVectorProperty(name='Offset Fingers')

    no_face = BoolProperty(name='No face bones',
                          default=True)

    rigify_names = BoolProperty(name='Use rigify names',
                               default=True,
                               description="Rename source rig bones to match Rigify Deform preset")

    assign_metarig = BoolProperty(name='Assign metarig',
                                 default=True,
                                 description='Rigify will generate to the active object')

    forward_spine_roll = BoolProperty(name='Align spine frontally', default=True,
                                     description='Spine Z will face the Y axis')

    apply_transforms = BoolProperty(name='Apply Transform', default=True,
                                   description='Apply current source transforms before extraction')

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        # if not context.active_object.data.expykit_retarget.has_settings():
        row = column.row()
        row.prop(self, 'rig_preset', text="Rig Type")

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Offset Knee")
        row.prop(self, 'offset_knee', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Offset Elbow")
        row.prop(self, 'offset_elbow', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Offset Fingers")
        row.prop(self, 'offset_fingers', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="No Face Bones")
        row.prop(self, 'no_face', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Use Rigify Names")
        row.prop(self, 'rigify_names', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Assign Metarig")
        row.prop(self, 'assign_metarig', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Align spine frontally")
        row.prop(self, 'forward_spine_roll', text='')

        row = layout_split(column, factor=0.5, align=True)
        row.label(text="Apply Transform")
        row.prop(self, 'apply_transforms', text='')

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if 'rigify' not in get_preferences(context).addons:
            return False
        if context.mode != 'POSE':
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        src_object = context.object
        src_armature = context.object.data

        if not bone_mapping.get_rigify_version():
            self.report({'WARNING'}, 'Cannot detect Rigify version')
            return {'CANCELLED'}

        if self.rig_preset == "--Current--":
            current_settings = context.object.data.expykit_retarget

            if current_settings.deform_preset and current_settings.deform_preset != '--':
                deform_preset = current_settings.deform_preset

                src_skeleton = preset_handler.set_preset_skel(deform_preset)
                current_settings = src_skeleton
            else:
                src_settings = preset_handler.PresetSkeleton()
                src_settings.copy(current_settings)
                src_skeleton = preset_handler.get_settings_skel(src_settings)
        elif self.rig_preset == "--":
            src_skeleton = None
        else:
            src_skeleton = preset_handler.set_preset_skel(self.rig_preset)
            current_settings = context.object.data.expykit_retarget

        if not src_skeleton:
            return {'FINISHED'}

        # TODO: remove action, bring to rest pose
        if self.apply_transforms:
            rigged = (ob for ob in bpy.data.objects if
                      next((mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object == src_object),
                           None))
            for ob in rigged:
                ob.data.transform(src_object.matrix_local)

            src_armature.transform(src_object.matrix_local)
            src_object.matrix_local = Matrix()

        met_skeleton = bone_mapping.RigifyMeta()

        if self.rigify_names:
            # check if doesn't contain rigify deform bones already
            bones_needed = met_skeleton.spine.hips, met_skeleton.spine.spine, met_skeleton.spine.spine1
            if not [b for b in bones_needed if b in src_armature.bones]:
                # Converted settings should not be validated yet, as bones have not been renamed
                if bone_mapping.rigify_version < (0, 5):
                    _preset_name = 'Rigify_Deform_0_4.py'
                else:
                    _preset_name = 'Rigify_Deform.py'
                src_skeleton, trg_skeleton = ConvertBoneNaming.convert_settings(current_settings, _preset_name, validate=False)
                ConvertBoneNaming.rename_bones(context, src_skeleton, trg_skeleton, skip_ik=True)
                src_skeleton = bone_mapping.RigifySkeleton()

                for name_attr in ('left_eye', 'right_eye'):
                    bone_name = getattr(src_skeleton.face, name_attr)

                    if bone_name not in src_armature.bones and bone_name[4:] in src_armature.bones:
                        # fix eye bones lacking "DEF-" prefix on b3.2
                        setattr(src_skeleton.face, name_attr, bone_name[4:])

                    if src_skeleton.face.super_copy:
                        # supercopy def bones start with DEF-
                        bone_name = getattr(src_skeleton.face, name_attr)

                        if bone_name and not bone_name.startswith('DEF-'):
                            new_name = "DEF-{}".format(bone_name)
                            try:
                                context.object.data.bones[bone_name].name = new_name
                            except KeyError:
                                pass
                            else:
                                setattr(src_skeleton.face, name_attr, new_name)

        src_to_met_map = src_skeleton.conversion_map(met_skeleton)

        # bones that have rigify attr will be copied when the metarig is in edit mode
        additional_bones = [(b.name, b.rigify_type) for b in src_object.pose.bones if b.rigify_type]

        # look if there is a metarig for this rig already
        metarig = None
        for ob in bpy.data.objects:
            if ob.type == 'ARMATURE':
                # rigify from (0, 6, 1) has it as object ref
                if hasattr(ob.data, "rigify_target_rig") and ob.data.rigify_target_rig:
                    if ob.data.rigify_target_rig == src_object:
                        metarig = ob
                        break
                    continue

                # some versions from 0.6.1 have it
                if hasattr(ob.data, "rigify_rig_basename") and ob.data.rigify_rig_basename:
                    if ob.data.rigify_rig_basename == src_object.name:
                        metarig = ob
                        break
                    continue

                # in rigify 0.4, 0.5 it's partially implemented, but we set it ourselves (rigify only reads it, never writes)
                if ob.get("rig_object_name") and ob["rig_object_name"] == src_object.name:
                    metarig = ob
                    break

        if not metarig:
            create_metarig = True
            met_armature = bpy.data.armatures.new('metarig')
            metarig = bpy.data.objects.new("metarig", met_armature)

            if bpy.app.version < (2, 80):
                context.scene.objects.link(metarig)
            else:
                context.collection.objects.link(metarig)
        else:
            met_armature = metarig.data
            create_metarig = False

        # getting real z_axes for src rest pose
        src_z_axes = bone_utils.get_rest_z_axes(src_object, context)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        if bpy.app.version < (2, 80):
            metarig.select = True
            context.scene.objects.active = metarig
        else:
            metarig.select_set(True)
            context.view_layer.objects.active = metarig

        # in local view it will fail prior 2.80 but in 2.80 it won't add it to the view as well
        if context.space_data.local_view is not None:
            if bpy.app.version < (2, 80):
                met_obj_base = next((base for base in context.scene.object_bases if base.object == metarig))
                if met_obj_base:
                    met_obj_base.layers_from_view(context.space_data)
            else:
                bpy.ops.view3d.localview(frame_selected=False)
                src_object.select_set(True)
                bpy.ops.view3d.localview(frame_selected=False)
                src_object.select_set(False)

        bpy.ops.object.mode_set(mode='EDIT')

        if create_metarig:
            from rigify.metarigs import human
            human.create(metarig)

        # measure some original meta proportions for later use
        def get_body_proportions():
            props = {}
            bone_pairs = []
            for attr in ("hips", "head", "neck", "spine2"):
                try:
                    met_bone = met_armature.edit_bones[getattr(met_skeleton.spine, attr)]
                    src_bone = src_armature.bones[getattr(src_skeleton.spine, attr)]
                except:
                    continue
                if met_bone and src_bone:
                    bone_pairs.append((attr, met_bone, src_bone))
                    if len(bone_pairs) > 1:
                        break
            if len(bone_pairs) < 2 or bone_pairs[0][0] != "hips":
                return None

            met_body_vector = bone_pairs[1][1].head - bone_pairs[0][1].head
            src_body_vector = bone_pairs[1][2].head_local - bone_pairs[0][2].head_local

            props["body_scale"] = src_body_vector.length / met_body_vector.length
            props["hips_head"] = bone_pairs[0][1].head.copy()
            return props

        body_proportions = get_body_proportions()

        def match_meta_spine(met_bone_group, src_bone_group, bone_attrs, axis=None):
            # find existing bones
            ms_bones = []
            for bone_attr in bone_attrs:
                met_bone_name = getattr(met_bone_group, bone_attr, None)
                met_bone = met_armature.edit_bones.get(met_bone_name, None) if met_bone_name else None
                src_bone_name = getattr(src_bone_group, bone_attr, None)
                src_bone = src_armature.bones.get(src_bone_name, None) if src_bone_name else None
                ms_bones.append((met_bone, src_bone))
            # terminators must exist anyway
            if not (ms_bones[0][0] and ms_bones[0][1] and ms_bones[-1][0] and ms_bones[-1][1]):
                self.report({'ERROR'}, "First and last bone in the chain ({}..{}) must exist".format(bone_attrs[0], bone_attrs[-1]))
                return

            met_bones_to_kill = {ms[0] for ms in ms_bones if ms[0] and not ms[1]}

            # place matched bones and set their rolls
            for met_bone, src_bone in ((ms[0], ms[1]) for ms in ms_bones if ms[0] and ms[1]):

                met_bone.head = src_bone.head_local
                met_bone.tail = src_bone.tail_local

                if axis:
                    met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, axis)
                else:
                    src_z_axis = src_z_axes[src_bone.name]
                    met_bone.align_roll(src_z_axis)

            for met_bone in met_bones_to_kill:
                met_bone.length = 0.0

        def match_meta_bone(met_bone_group, src_bone_group, bone_attr, axis=None):
            try:
                met_bone = met_armature.edit_bones[getattr(met_bone_group, bone_attr)]
                src_bone_name = getattr(src_bone_group, bone_attr)
                src_bone = src_armature.bones.get(src_bone_name, None)
            except KeyError:
                return

            if not src_bone:
                self.report({'WARNING'}, "{}, {} not found in {}".format(bone_attr, src_bone_name, src_armature))
                return

            met_bone.head = src_bone.head_local
            met_bone.tail = src_bone.tail_local

            if met_bone.parent and met_bone.use_connect:
                bone_dir = met_bone.vector.normalized()
                parent_dir = met_bone.parent.vector.normalized()

                if bone_dir.dot(parent_dir) < -0.6:
                    self.report({'WARNING'}, "{} is not aligned with its parent".format(met_bone.name))
                    # TODO

            if axis:
                met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, axis)
            else:
                src_z_axis = src_z_axes[src_bone.name]
                met_bone.align_roll(src_z_axis)

            return met_bone

        if self.forward_spine_roll:
            align = Vector((0.0, -1.0, 0.0))
        else:
            align = None
        match_meta_spine(met_skeleton.spine, src_skeleton.spine,
                         ('hips', 'spine', 'spine1', 'spine2', 'neck', 'head'),
                         axis=align)

        for bone_attr in ['shoulder', 'arm', 'forearm', 'hand']:
            match_meta_bone(met_skeleton.right_arm, src_skeleton.right_arm, bone_attr)
            match_meta_bone(met_skeleton.left_arm, src_skeleton.left_arm, bone_attr)

        for bone_attr in ['upleg', 'leg', 'foot', 'toe']:
            match_meta_bone(met_skeleton.right_leg, src_skeleton.right_leg, bone_attr)
            match_meta_bone(met_skeleton.left_leg, src_skeleton.left_leg, bone_attr)

        rigify_face_bones = set(bone_mapping.rigify_face_bones)
        for bone_attr in ['left_eye', 'right_eye', 'jaw']:
            met_bone = match_meta_bone(met_skeleton.face, src_skeleton.face, bone_attr)
            if met_bone:
                try:
                    rigify_face_bones.remove(met_skeleton.face[bone_attr])
                except:
                    pass

                if src_skeleton.face.super_copy:
                    metarig.pose.bones[met_bone.name].rigify_type = "basic.super_copy"
                    # FIXME: sometimes eye bone group is not renamed accordingly
                    # TODO: then maybe change jaw shape to box

        try:
            right_leg = met_armature.edit_bones[met_skeleton.right_leg.leg]
            left_leg = met_armature.edit_bones[met_skeleton.left_leg.leg]
        except KeyError:
            pass
        else:
            offset = Vector((0.0, self.offset_knee, 0.0))
            for bone in right_leg, left_leg:
                bone.head += offset

            try:
                right_knee = met_armature.edit_bones[met_skeleton.right_arm.forearm]
                left_knee = met_armature.edit_bones[met_skeleton.left_arm.forearm]
            except KeyError:
                pass
            else:
                offset = Vector((0.0, self.offset_elbow, 0.0))

                for bone in right_knee, left_knee:
                    bone.head += offset

        def match_meta_fingers(met_bone_group, src_bone_group, bone_attr):
            met_bone_names = getattr(met_bone_group, bone_attr)
            src_bone_names = getattr(src_bone_group, bone_attr)

            if not src_bone_names:
                print(bone_attr, "not found in", src_armature)
                return
            if not met_bone_names:
                print(bone_attr, "not found in", src_armature)
                return

            # handle palm bones
            if 'thumb' not in bone_attr:
                # check if it's already mapped in 'meta' limb
                try:
                    met_bone = met_armature.edit_bones[met_bone_names[3]]
                    src_bone = src_armature.bones.get(src_bone_names[3])
                except Exception:
                    pass
                if not met_bone or not src_bone:
                    try:
                        met_bone = met_armature.edit_bones[met_bone_names[0]]
                        src_bone = src_armature.bones.get(src_bone_names[0], None)
                    except KeyError:
                        pass
                    else:
                        if src_bone:
                            palm_bone = met_bone.parent
                            palm_bone.tail = src_bone.head_local
                            hand_bone = palm_bone.parent
                            palm_bone.head = hand_bone.head * 0.75 + src_bone.head_local * 0.25
                            # not a big deal to match palm's roll with the proximal's
                            src_z_axis = src_z_axes[src_bone.name]
                            palm_bone.align_roll(src_z_axis)

            for i, (met_bone_name, src_bone_name) in enumerate(zip(met_bone_names, src_bone_names)):
                if not src_bone_name:
                    continue
                try:
                    met_bone = met_armature.edit_bones[met_bone_name]
                    src_bone = src_armature.bones[src_bone_name]
                except KeyError:
                    print("source bone not found", src_bone_name)
                    continue

                met_bone.head = src_bone.head_local
                try:
                    met_bone.tail = src_bone.children[0].head_local
                except IndexError:
                    try:
                        if i < 2:
                            src_bone_next = src_armature.bones[src_bone_names[i + 1]]
                        elif i == 3: # palm
                            src_bone_next = src_armature.bones[src_bone_names[0]]
                        else:
                            raise KeyError()
                    except KeyError:
                        bone_utils.align_to_closer_axis(src_bone, met_bone)
                    else:
                        met_bone.tail = src_bone_next.head_local

                src_z_axis = src_z_axes[src_bone.name]
                met_bone.align_roll(src_z_axis)

                offset_fingers = matmul(Vector(self.offset_fingers), src_bone.matrix_local.to_3x3())
                if met_bone.head.x < 0:  # Right side
                    offset_fingers /= -100
                else:
                    offset_fingers /= 100

                if met_bone.parent.name in met_bone_names and met_bone.children:
                    met_bone.translate(offset_fingers)

        for bone_attr in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            match_meta_fingers(met_skeleton.right_fingers, src_skeleton.right_fingers, bone_attr)
            match_meta_fingers(met_skeleton.left_fingers, src_skeleton.left_fingers, bone_attr)

        try:
            met_armature.edit_bones['spine.003'].tail = met_armature.edit_bones['spine.004'].head
            met_armature.edit_bones['spine.005'].head = (met_armature.edit_bones['spine.004'].head + met_armature.edit_bones['spine.006'].head) / 2
        except KeyError:
            pass

        # find foot vertices
        foot_verts = {}
        foot_ob = None
        # pick object with most foot verts
        for ob in bone_utils.iterate_rigged_obs(src_object):
            if src_skeleton.left_leg.foot not in ob.vertex_groups:
                continue
            grouped_verts = bone_utils.get_group_verts(ob, src_skeleton.left_leg.foot, threshold=0.8)
            if len(grouped_verts) > len(foot_verts):
                foot_verts = grouped_verts
                foot_ob = ob

        if foot_verts:
            # find rear verts (heel)
            rearest_y = max([foot_ob.data.vertices[v].co[1] for v in foot_verts])
            leftmost_x = max([foot_ob.data.vertices[v].co[0] for v in foot_verts])  # FIXME: we should counter rotate verts for more accuracy
            rightmost_x = min([foot_ob.data.vertices[v].co[0] for v in foot_verts])

            for side in 'L', 'R':
                # invert left/right vertices when we switch sides
                leftmost_x, rightmost_x = rightmost_x, leftmost_x

                heel_bone = met_armature.edit_bones['heel.02.' + side]

                heel_bone.head.y = rearest_y
                heel_bone.tail.y = rearest_y

                if heel_bone.head.x > 0:
                    heel_head = leftmost_x
                    heel_tail = rightmost_x
                else:
                    heel_head = rightmost_x * -1
                    heel_tail = leftmost_x * -1
                heel_bone.head.x = heel_head
                heel_bone.tail.x = heel_tail

                try:
                    spine_bone = met_armature.edit_bones[met_skeleton.spine.hips]
                    pelvis_bone = met_armature.edit_bones['pelvis.' + side]
                except KeyError:
                    pass
                else:
                    offset = spine_bone.head - pelvis_bone.head
                    pelvis_bone.translate(offset)
                    if body_proportions:
                        pelvis_bone.length *= body_proportions["body_scale"]

                try:
                    if body_proportions:
                        spine_bone = met_armature.edit_bones[met_skeleton.spine.hips]
                    else:
                        spine_bone = met_armature.edit_bones[met_skeleton.spine.spine2]
                    breast_bone = met_armature.edit_bones['breast.' + side]
                except KeyError:
                    pass
                else:
                    if body_proportions:
                        offset0 = (breast_bone.head - body_proportions["hips_head"])
                        offset = (offset0 * body_proportions["body_scale"] - offset0 +
                                  (spine_bone.head - body_proportions["hips_head"]))
                    else:
                        offset = spine_bone.head - breast_bone.head
                        offset.x = 0.0
                    breast_bone.translate(offset)

        if self.no_face:
            for bone_name in rigify_face_bones:
                try:
                    face_bone = met_armature.edit_bones[bone_name]
                except KeyError:
                    continue

                met_armature.edit_bones.remove(face_bone)
        else:
            #TODO: position face bones with body_proportions
            pass

        for src_name, src_attr in additional_bones:
            # find target bone name by src_name
            met_bone_name = src_to_met_map.get(src_name)
            if not met_bone_name:
                continue

            new_bone_name = bone_utils.copy_bone_to_arm(src_object, metarig, src_name, trg_bone_name=met_bone_name, suffix="")

            if 'chain' in src_attr:  # TODO: also fingers
                # working around weird bug: sometimes src_armature.bones causes KeyError even if the bone is there
                bone = next((b for b in src_armature.bones if b.name == src_name), None)

                new_parent_name = new_bone_name
                while bone:
                    # optional: use connect
                    try:
                        bone = bone.children[0]
                    except IndexError:
                        break

                    child_bone_name = bone_utils.copy_bone_to_arm(src_object, metarig, bone.name, trg_bone_name=src_to_met_map.get(bone.name), suffix="")
                    child_bone = met_armature.edit_bones[child_bone_name]
                    child_bone.parent = met_armature.edit_bones[new_parent_name]
                    child_bone.use_connect = True

                    bone.name = "DEF-{}".format(bone.name)
                    new_parent_name = child_bone_name

            try:
                bone = next((b for b in src_armature.bones if b.name == src_name), None)

                if bone:
                    if bone.parent:
                        # DONE: should use mapping to get parent bone name
                        parent_name = bone.parent.name.replace('DEF-', '')
                        met_parent_name = src_to_met_map.get(parent_name)
                        if met_parent_name:
                            met_armature.edit_bones[new_bone_name].parent = met_armature.edit_bones[met_parent_name]
                    if ".raw_" in src_attr:
                        met_armature.edit_bones[new_bone_name].use_deform = bone.use_deform
                    elif bone.name.startswith('DEF-'):
                        # already a DEF, need to strip that from metarig bone instead
                        met_armature.edit_bones[new_bone_name].name = new_bone_name.replace("DEF-", '')
                    else:
                        bone.name = "DEF-{}".format(bone.name)
            except KeyError:
                self.report({'WARNING'}, "parent bone [{}] not found in target, perhaps wrong preset?".format(parent_name))
                continue

        bpy.ops.object.mode_set(mode='POSE')
        # now we can copy the stored rigify attrs
        for src_name, src_attr in additional_bones:
            src_meta = src_name[4:] if src_name.startswith('DEF-') else src_name
            src_meta = src_to_met_map.get(src_meta)
            if src_meta:
                metarig.pose.bones[src_meta].rigify_type = src_attr
                # TODO: should copy rigify options of specific types as well

        if current_settings.left_leg.upleg_twist_02 or current_settings.left_leg.leg_twist_02:
            metarig.pose.bones['thigh.L']['rigify_parameters']['segments'] = 3

        if current_settings.right_leg.upleg_twist_02 or current_settings.right_leg.leg_twist_02:
            metarig.pose.bones['thigh.R']['rigify_parameters']['segments'] = 3

        if current_settings.left_arm.arm_twist_02 or current_settings.left_arm.forearm_twist_02:
            metarig.pose.bones['upper_arm.L']['rigify_parameters']['segments'] = 3

        if current_settings.right_arm.arm_twist_02 or current_settings.right_arm.forearm_twist_02:
            metarig.pose.bones['upper_arm.R']['rigify_parameters']['segments'] = 3

        if self.assign_metarig:
            # register target rig according to rigify version
            # rigify_target_rig begins in 0.6.1
            if hasattr(metarig.data, "rigify_target_rig"):
                metarig.data.rigify_target_rig = src_object

            # rigify_rig_basename begins in 0.6.1, dies in 0.6.4, and resurrects in 0.6.6
            elif hasattr(metarig.data, "rigify_rig_basename"):
                metarig.data.rigify_rig_basename = src_object.name

            else:
                # in rigify 0.4, 0.5 it's partially implemented, but we set it ourselves as custom prop
                metarig["rig_object_name"] = src_object.name
        else:
            if create_metarig:
                if bone_mapping.rigify_version <= (0, 5):
                    # help older rigify to avoid using hardcoded name 'rig'
                    _name = metarig.name.replace("meta","")
                    _name = _name.replace("Meta","")
                    _name = _name.replace("META","")
                    if _name != metarig.name:
                        metarig["rig_object_name"] = _name

        metarig.parent = src_object.parent

        return {'FINISHED'}


class ActionRangeToScene(bpy.types.Operator):
    """Set Playback range to current action Start/End"""
    bl_idname = "object.expykit_action_to_range"
    bl_label = "Action Range to Scene"
    bl_description = "Match scene range with current action range"
    bl_options = {'REGISTER', 'UNDO'}

    _allowed_modes_ = ['POSE', 'OBJECT']

    @classmethod
    def poll(cls, context):
        obj = context.object

        if not obj:
            return False
        if obj.mode not in cls._allowed_modes_:
            return False
        if not obj.animation_data:
            return False
        if not obj.animation_data.action:
            return False

        return True

    def execute(self, context):
        action_range = context.object.animation_data.action.frame_range

        scn = context.scene
        scn.frame_start = int(action_range[0])
        scn.frame_end = int(action_range[1])

        try:
            bpy.ops.action.view_all()
        except RuntimeError:
            # we are not in a timeline context, let's look for one in the screen
            for window in context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == 'DOPESHEET_EDITOR':
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                _ovr = {"window" : window,
                                        "area" : area,
                                        "region" : region
                                        }
                                if bpy.app.version < (3, 2):
                                    bpy.ops.action.view_all(_ovr)
                                else:
                                    with context.temp_override(**_ovr):
                                        bpy.ops.action.view_all()
                                break
                        break
        return {'FINISHED'}


@make_annotations
class MergeHeadTails(bpy.types.Operator):
    """Connect head/tails when closer than given max distance"""
    bl_idname = "armature.expykit_merge_head_tails"
    bl_label = "Merge Head/Tails"
    bl_description = "Connect head/tails when closer than given max distance"
    bl_options = {'REGISTER', 'UNDO'}

    at_child_head = BoolProperty(
        name="Match at child head",
        description="Bring parent's tail to match child head when possible",
        default=True
    )

    min_distance = FloatProperty(
        name="Distance",
        description="Max Distance for merging",
        default=0.0
    )

    selected_only = BoolProperty(name="Only Selected",
                                default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
        if obj.mode != 'EDIT':
            return False
        if obj.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        if self.selected_only:
            selected_names = [bone.name for bone in context.selected_bones]
            bones = [bone for bone in context.object.data.edit_bones if bone.name in selected_names]
        else:
            bones = context.object.data.edit_bones

        for bone in bones:
            if bone.use_connect:
                continue
            if not bone.parent:
                continue

            distance = (bone.parent.tail - bone.head).length
            if distance <= self.min_distance:
                if self.at_child_head and len(bone.parent.children) == 1:
                    bone.parent.tail = bone.head

                bone.use_connect = True

        context.object.update_from_editmode()

        return {'FINISHED'}


def mute_fcurves(obj, channel_name): # :Object, :str
    action = obj.animation_data.action
    if not action:
        return

    for fc in action.fcurves:
        if fc.data_path == channel_name:
            fc.mute = True

def limit_scale(obj):
    constr = obj.constraints.new('LIMIT_SCALE')

    constr.owner_space = 'LOCAL'
    constr.min_x = obj.scale[0]
    constr.min_y = obj.scale[1]
    constr.min_z = obj.scale[2]

    constr.max_x = obj.scale[0]
    constr.max_y = obj.scale[1]
    constr.max_z = obj.scale[2]

    constr.use_min_x = True
    constr.use_min_y = True
    constr.use_min_z = True

    constr.use_max_x = True
    constr.use_max_y = True
    constr.use_max_z = True


@make_annotations
class ConvertGameFriendly(bpy.types.Operator):
    """Convert Rigify (0.5) rigs to a Game Friendly hierarchy"""
    bl_idname = "armature.expykit_convert_gamefriendly"
    bl_label = "Rigify Game Friendly"
    bl_description = "Make the rigify deformation bones a one root rig"
    bl_options = {'REGISTER', 'UNDO'}

    keep_backup = BoolProperty(
        name="Backup",
        description="Keep copy of datablock",
        default=True
    )
    rename = StringProperty(
        name="Rename",
        description="Rename rig to 'Armature'",
        default="Armature"
    )
    eye_bones = BoolProperty(
        name="Keep eye bones",
        description="Activate 'deform' for eye bones",
        default=True
    )
    limit_scale = BoolProperty(
        name="Limit Spine Scale",
        description="Limit scale on the spine deform bones",
        default=True
    )
    disable_bendy = BoolProperty(
        name="Disable B-Bones",
        description="Disable Bendy-Bones",
        default=True
    )
    fix_tail = BoolProperty(
        name="Invert Tail",
        description="Reverse the tail direction so that it spawns from hip",
        default=True
    )
    reparent_twist = BoolProperty(
        name="Dispossess Twist Bones",
        description="Rearrange Twist Hierarchy in limbs for in game IK",
        default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
        if obj.mode != 'POSE':
            return False
        if obj.type != 'ARMATURE':
            return False
        return bool(context.active_object.data.get("rig_id"))

    def execute(self, context):
        ob = context.active_object
        if self.keep_backup:
            backup_data = ob.data.copy()
            backup_data.name = ob.name + "_GameUnfriendly_backup"
            backup_data.use_fake_user = True

        if self.rename:
            ob.name = self.rename
            ob.data.name = self.rename

            try:
                metarig = next(
                    obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and obj.data.rigify_target_rig == ob)
            except (StopIteration, AttributeError):  # Attribute Error if Rigify is not loaded
                pass
            else:
                try:
                    metarig.data.rigify_rig_basename = self.rename
                except AttributeError:
                    # Removed in rigify 0.6.4
                    pass

        if self.eye_bones and 'DEF-eye.L' not in ob.pose.bones:
            # Old rigify face: eyes deform is disabled
            # FIXME: the 'DEF-eye.L' condition should be checked on invoke
            try:
                # Oddly, changes to use_deform are not kept
                ob.pose.bones["MCH-eye.L"].bone.use_deform = True
                ob.pose.bones["MCH-eye.R"].bone.use_deform = True
            except KeyError:
                pass

        bpy.ops.object.mode_set(mode='EDIT')
        num_reparents = bone_utils.gamefriendly_hierarchy(ob, fix_tail=self.fix_tail, limit_scale=self.limit_scale)

        if self.reparent_twist:
            arm_bones = ("DEF-upper_arm", "DEF-forearm", "DEF-hand")
            leg_bones = ("DEF-thigh", "DEF-shin", "DEF-foot")
            for side in ".L", ".R":
                for bone_names in list(arm_bones), list(leg_bones):
                    parent_bone = ob.data.edit_bones[bone_names.pop(0) + side]
                    for bone in bone_names:
                        e_bone = ob.data.edit_bones[bone + side]
                        e_bone.use_connect = False

                        e_bone.parent = parent_bone
                        parent_bone = e_bone

                        num_reparents += 1

        bpy.ops.object.mode_set(mode='POSE')

        if self.disable_bendy:
            for bone in ob.data.bones:
                bone.bbone_segments = 1
                # TODO: disable bbone drivers

        self.report({'INFO'}, "{} bones were re-parented".format(num_reparents))
        return {'FINISHED'}


@make_annotations
class ConstrainToArmature(bpy.types.Operator):
    bl_idname = "armature.expykit_constrain_to_armature"
    bl_label = "Bind to Active Armature"
    bl_description = "Constrain bones of selected armatures to active armature"
    bl_options = {'REGISTER', 'UNDO'}

    src_preset = EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="To Bind",
                             options={'SKIP_SAVE'}
                             )

    trg_preset = EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Bind To",
                             options={'SKIP_SAVE'}
                             )

    only_selected = BoolProperty(name="Only Selected", default=False, description="Bind only selected bones")

    bind_by_name = BoolProperty(name="Bind bones by name", default=True)
    name_prefix = StringProperty(name="Add prefix to name", default="")
    name_replace = StringProperty(name="Replace in name", default="")
    name_replace_with = StringProperty(name="Replace in name with", default="")
    name_suffix = StringProperty(name="Add suffix to name", default="")

    if bpy.app.version[0] < 4:
        ret_bones_layer = IntProperty(name="Layer",
                                    min=0, max=29, default=24,
                                    description="Armature Layer to use for connection bones")
        use_legacy_index = True
    else:
        ret_bones_collection = StringProperty(name="Layer",
                                             default="Retarget Bones",
                                             description="Armature collection to use for connection bones")
        use_legacy_index = False

    match_transform = EnumProperty(items=[
        ('None', "- None -", "Don't match any transform"),
        ('Bone', "Bones Offset", "Account for difference between control and deform rest pose (Requires similar proportions and Y bone-axis)"),
        ('Pose', "Current Pose is target Rest Pose", "Armature was posed manually to match rest pose of target"),
        ('World', "Follow target Pose in world space", "Just copy target world positions (Same bone orient, different rest pose)"),
    ],
        name="Match Transform",
        default='None')

    match_object_transform = BoolProperty(name="Match Object Transform", default=True)

    math_look_at = BoolProperty(name="Fix direction",
                               description="Correct chain direction based on mid limb (Useful for IK)",
                               default=False)

    copy_IK_roll_hands = BoolProperty(name="Hands IK Roll",
                            description="USe IK target roll from source armature (Useful for IK)",
                            default=False)

    copy_IK_roll_feet = BoolProperty(name="Feet IK Roll",
                            description="USe IK target roll from source armature (Useful for IK)",
                            default=False)

    fit_target_scale = EnumProperty(name="Fit height",
                                   items=(('--', '- None -', 'None'),
                                          ('head', 'head', 'head'),
                                          ('neck', 'neck', 'neck'),
                                          ('spine2', 'chest', 'spine2'),
                                          ('spine1', 'spine1', 'spine1'),
                                          ('spine', 'spine', 'spine'),
                                          ('hips', 'hips', 'hips'),
                                          ),
                                    default='--',
                                    description="Fit height of the target Armature at selected bone")
    adjust_location = BoolProperty(default=True, name="Adjust location to new scale")

    constrain_root = EnumProperty(items=[
        ('None', "No Root", "Don't constrain root bone"),
        ('Bone', "Bone", "Constrain root to bone"),
        ('Object', "Object", "Constrain root to object")
    ],
        name="Constrain Root",
        default='None')

    loc_constraints = BoolProperty(name="Copy Location",
                                  description="Use Location Constraint when binding",
                                  default=False)

    rot_constraints = BoolProperty(name="Copy Rotation",
                                  description="Use Rotation Constraint when binding",
                                  default=True)

    constraint_policy = EnumProperty(items=[
        ('skip', "Skip Existing Constraints", "Skip Bones that are constrained already"),
        ('disable', "Disable Existing Constraints", "Disable existing binding constraints and add new ones"),
        ('remove', "Delete Existing Constraints", "Delete existing binding constraints")
        ],
        name="Policy",
        description="Action to take with existing constraints",
        default='skip'
        )

    bind_floating = BoolProperty(name="Bind Floating",
                                description="Always bind unparented bones Location and Rotation",
                                default=True)

    root_motion_bone = StringProperty(name="Root Motion",
                                     description="Constrain Root bone to Hip motion",
                                     default="")

    root_cp_loc_x = BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=False)
    root_cp_loc_y = BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z = BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x = BoolProperty(name="Use Root Min X", description="Minimum Root X", default=False)
    root_use_loc_min_y = BoolProperty(name="Use Root Min Y", description="Minimum Root Y", default=False)
    root_use_loc_min_z = BoolProperty(name="Use Root Min Z", description="Minimum Root Z", default=True)

    root_loc_min_x = FloatProperty(name="Root Min X", description="Minimum Root X", default=0.0)
    root_loc_min_y = FloatProperty(name="Root Min Y", description="Minimum Root Y", default=0.0)
    root_loc_min_z = FloatProperty(name="Root Min Z", description="Minimum Root Z", default=0.0)

    root_use_loc_max_x = BoolProperty(name="Use Root Max X", description="Maximum Root X", default=False)
    root_use_loc_max_y = BoolProperty(name="Use Root Max Y", description="Maximum Root Y", default=False)
    root_use_loc_max_z = BoolProperty(name="Use Root Max Z", description="Maximum Root Z", default=False)

    root_loc_max_x = FloatProperty(name="Root Max X", description="Maximum Root X", default=0.0)
    root_loc_max_y = FloatProperty(name="Root Max Y", description="Maximum Root Y", default=0.0)
    root_loc_max_z = FloatProperty(name="Root Max Z", description="Maximum Root Z", default=0.0)

    root_cp_rot_x = BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y = BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z = BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    no_finger_loc = BoolProperty(default=False, name="No Finger Location")

    prefix_separator = StringProperty(
        name="Prefix Separator",
        description="Separator between prefix and name, i.e: MyCharacter:head",
        default=":"
    )

    force_dialog = BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    _autovars_unset = True
    _constrained_root = None

    _prop_indent = 0.15

    @property
    def _bind_constraints(self):
        constrs = []
        if self.loc_constraints:
            constrs.append('COPY_LOCATION')
        if self.rot_constraints:
            constrs.append('COPY_ROTATION')

        return constrs

    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) != 2:
            return False
        if context.mode != 'POSE':
            return False
        for ob in context.selected_objects:
            if ob.type != 'ARMATURE':
                return False

        return True

    def invoke(self, context, event):
        # Set to use current Expy Kit settings if found
        to_bind = next(ob for ob in context.selected_objects if ob != context.active_object)

        if to_bind.data.expykit_retarget.has_settings():
            self.src_preset = '--Current--'
        if context.active_object.data.expykit_retarget.has_settings():
            self.trg_preset = '--Current--'

        if self.force_dialog:
            return context.window_manager.invoke_props_dialog(self)

        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.row()
        row.prop(self, 'src_preset', text="To Bind")

        row = column.row()
        row.prop(self, 'trg_preset', text="Bind To")

        if self.force_dialog:
            return

        column.separator()
        row = column.row()
        row.label(text='Conversion')

        row = layout_split(column, factor=self._prop_indent, align=True)
        row.separator()
        col = row.column()
        col.prop(self, 'match_transform', text='')
        col.prop(self, 'match_object_transform')
        col.prop(self, 'fit_target_scale')
        if self.fit_target_scale != "--":
            col.prop(self, 'adjust_location')

        if not self.loc_constraints and self.match_transform == 'Bone':
            col.label(text="'Copy Location' might be required", icon='ERROR')
        elif self.fit_target_scale == '--' and self.match_transform == 'Pose':
            col.label(text="'Fit height' might improve results", icon='ERROR')
        else:
            col.separator()

        column.separator()
        row = column.row()
        row.label(text='Constraints')

        row = column.row()
        row = layout_split(column, factor=self._prop_indent, align=True)
        row.separator()

        constr_col = row.column()

        copy_loc_row = constr_col.row()
        copy_loc_row.prop(self, 'loc_constraints')
        if self.loc_constraints:
            copy_loc_row.prop(self, 'no_finger_loc', text="Except Fingers")
        else:
            copy_loc_row.prop(self, 'bind_floating', text="Only Floating")

        copy_rot_row = constr_col.row()
        copy_rot_row.prop(self, 'rot_constraints')
        copy_rot_row.prop(self, 'math_look_at')

        ik_aim_row = constr_col.row()
        ik_aim_row.prop(self, 'copy_IK_roll_hands')
        ik_aim_row.prop(self, 'copy_IK_roll_feet')

        row = layout_split(column, factor=self._prop_indent, align=True)
        constr_col.prop(self, 'constraint_policy', text='')

        column.separator()
        row = column.row()
        row.label(text="Affect Bones")

        row = column.row()
        row = layout_split(column, factor=self._prop_indent, align=True)
        row.separator()
        col = row.column()
        col.prop(self, 'only_selected')
        row.prop(self, 'bind_by_name', text="Also by Name")
        if self.bind_by_name:
            row = column.row()
            col = row.column()
            col.label(text="Prefix")
            col.prop(self, 'name_prefix', text="")

            col = row.column()
            col.label(text="Replace:")
            col.prop(self, 'name_replace', text="")

            col = row.column()
            col.label(text="With:")
            col.prop(self, 'name_replace_with', text="")

            col = row.column()
            col.label(text="Suffix:")
            col.prop(self, 'name_suffix', text="")

        column.separator()
        row = column.row()
        row.label(text="Root Animation")
        row = layout_split(column, factor=self._prop_indent, align=True)
        row.separator()
        row.prop(self, 'constrain_root', text="")

        if self.constrain_root != 'None':
            row = layout_split(column, factor=self._prop_indent, align=True)
            row.label(text="")
            row.prop_search(self, 'root_motion_bone',
                            context.active_object.data,
                            "bones", text="")

        if self.constrain_root != 'None':
            row = column.row(align=True)
            row.label(text="Location")
            row.prop(self, "root_cp_loc_x", text="X", toggle=True)
            row.prop(self, "root_cp_loc_y", text="Y", toggle=True)
            row.prop(self, "root_cp_loc_z", text="Z", toggle=True)

            if any((self.root_cp_loc_x, self.root_cp_loc_y, self.root_cp_loc_z)):
                column.separator()

                # Min/Max X
                if self.root_cp_loc_x:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_x", text="Min X")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_x", text="")
                    subcol.enabled = self.root_use_loc_min_x

                    row.separator()
                    row.prop(self, "root_use_loc_max_x", text="Max X")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_x", text="")
                    subcol.enabled = self.root_use_loc_max_x
                    row.enabled = self.root_cp_loc_x

                # Min/Max Y
                if self.root_cp_loc_y:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_y", text="Min Y")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_y", text="")
                    subcol.enabled = self.root_use_loc_min_y

                    row.separator()
                    row.prop(self, "root_use_loc_max_y", text="Max Y")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_y", text="")
                    subcol.enabled = self.root_use_loc_max_y
                    row.enabled = self.root_cp_loc_y

                # Min/Max Z
                if self.root_cp_loc_z:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_z", text="Min Z")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_z", text="")
                    subcol.enabled = self.root_use_loc_min_z

                    row.separator()
                    row.prop(self, "root_use_loc_max_z", text="Max Z")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_z", text="")
                    subcol.enabled = self.root_use_loc_max_z
                    row.enabled = self.root_cp_loc_z

                column.separator()

            row = column.row(align=True)
            row.label(text="Rotation")
            row.prop(self, "root_cp_rot_x", text="X", toggle=True)
            row.prop(self, "root_cp_rot_y", text="Y", toggle=True)
            row.prop(self, "root_cp_rot_z", text="Z", toggle=True)

        column.separator()
        if self.use_legacy_index:
            row = layout_split(column, factor=self._prop_indent, align=True)
            row.separator()
            row.prop(self, 'ret_bones_layer')
        else:
            row = column.row()
            row.prop(self, 'ret_bones_collection', text="Layer")

    def _bone_bound_already(self, bone):
        for constr in bone.constraints:
            if constr.type in self._bind_constraints:
                return True

        return False

    def _add_limit_constraintss(self, ob, rot=True, loc=True, scale=False):
        limit_constraints = []
        if self.match_transform == 'Pose':
            return limit_constraints

        if rot:
            limit_rot = ob.constraints.new('LIMIT_ROTATION')
            limit_rot.use_limit_x = True
            limit_rot.use_limit_y = True
            limit_rot.use_limit_z = True

            limit_constraints.append(limit_rot)

        def limit_all(constr):
            constr.use_min_x = True
            constr.use_min_y = True
            constr.use_min_z = True
            constr.use_max_x = True
            constr.use_max_y = True
            constr.use_max_z = True

        if loc:
            limit_loc = ob.constraints.new('LIMIT_LOCATION')
            limit_all(limit_loc)
            limit_constraints.append(limit_loc)

        if scale:
            limit_scale = ob.constraints.new('LIMIT_SCALE')
            limit_scale.min_x = 1.0
            limit_scale.min_y = 1.0
            limit_scale.min_z = 1.0

            limit_scale.max_x = 1.0
            limit_scale.max_y = 1.0
            limit_scale.max_z = 1.0

            limit_all(limit_scale)
            limit_constraints.append(limit_scale)

        return limit_constraints

    def execute(self, context):
        # force_dialog limits drawn properties and is no longer required
        self.force_dialog = False

        trg_ob = context.active_object

        _ad = trg_ob.animation_data
        if _ad and _ad.action:
            bpy.ops.object.expykit_action_to_range()

        if self.trg_preset == '--':
            return {'FINISHED'}
        if self.src_preset == '--':
            return {'FINISHED'}

        if self.trg_preset == '--Current--' and trg_ob.data.expykit_retarget.has_settings():
            trg_settings = trg_ob.data.expykit_retarget
            trg_skeleton = preset_handler.get_settings_skel(trg_settings)
        else:
            trg_skeleton = preset_handler.set_preset_skel(self.trg_preset)

            if not trg_skeleton:
                return {'FINISHED'}

        cp_suffix = 'RET'
        prefix = ""

        fit_scale = False
        if self.fit_target_scale != '--':
            try:
                trg_bone = trg_ob.pose.bones[getattr(trg_skeleton.spine, self.fit_target_scale)]
            except KeyError:
                pass
            else:
                fit_scale = True
                trg_height = matmul(trg_ob.matrix_world, trg_bone.bone.head_local)

        for ob in context.selected_objects:
            if ob == trg_ob:
                continue

            src_settings = ob.data.expykit_retarget
            if self.src_preset == '--Current--' and ob.data.expykit_retarget.has_settings():
                if not src_settings.has_settings():
                    return {'FINISHED'}
                src_skeleton = preset_handler.get_settings_skel(src_settings)
            else:
                src_skeleton = preset_handler.get_preset_skel(self.src_preset, src_settings)
                if not src_skeleton:
                    return {'FINISHED'}

            if fit_scale:
                ob_height = matmul(ob.matrix_world, ob.pose.bones[getattr(src_skeleton.spine, self.fit_target_scale)].bone.head_local)
                height_ratio = ob_height[2] / trg_height[2]

                mute_fcurves(trg_ob, 'scale')
                trg_ob.scale *= height_ratio
                limit_scale(trg_ob)

                if self.adjust_location:
                    # scale location animation to avoid offset
                    if trg_ob.animation_data and trg_ob.animation_data.action:
                        for fc in trg_ob.animation_data.action.fcurves:
                            data_path = fc.data_path

                            if not data_path.endswith('location'):
                                continue

                            for kf in fc.keyframe_points:
                                kf.co[1] /= height_ratio

            bone_names_map = src_skeleton.conversion_map(trg_skeleton)
            def_skeleton = preset_handler.get_preset_skel(src_settings.deform_preset)
            if def_skeleton:
                deformation_map = src_skeleton.conversion_map(def_skeleton)
            else:
                deformation_map = None

            if self.bind_by_name:
                # Look for bones present in both
                for bone in ob.pose.bones:
                    bone_name = bone.name
                    bone_look_up = self.name_prefix + bone_name.replace(self.name_replace, self.name_replace_with) + self.name_suffix
                    if bone_look_up in bone_names_map:
                        continue
                    if bone_utils.is_pose_bone_all_locked(bone):
                        continue
                    if bone_look_up in trg_ob.pose.bones:
                        bone_names_map[bone_name] = bone_look_up

            look_ats = {}

            if self.constrain_root == 'None':
                try:
                    del bone_names_map[src_skeleton.root]
                except KeyError:
                    pass
                self._constrained_root = None
            elif self.constrain_root == 'Bone':
                bone_names_map[src_skeleton.root] = self.root_motion_bone

            if self.only_selected:
                b_names = list(bone_names_map.keys())
                for b_name in b_names:
                    if not b_name:
                        continue
                    try:
                        bone = ob.data.bones[b_name]
                    except KeyError:
                        continue

                    if not bone.select:
                        del bone_names_map[b_name]

            # hacky, but will do it: keep target armature in place during binding
            limit_constraints = self._add_limit_constraintss(trg_ob)

            if not self.use_legacy_index:
                try:
                    ret_collection = trg_ob.data.collections[self.ret_bones_collection]
                except KeyError:
                    ret_collection = trg_ob.data.collections.new(self.ret_bones_collection)
                    ret_collection.is_visible = False

            # create Retarget bones
            bpy.ops.object.mode_set(mode='EDIT')
            for src_name, trg_name in bone_names_map.items():
                if not src_name:
                    continue

                if self.constraint_policy == 'skip':
                    try:
                        pb = ob.pose.bones[src_name]
                    except KeyError:
                        pass
                    else:
                        if self._bone_bound_already(pb):
                            continue

                is_object_root = src_name == src_skeleton.root and self.constrain_root == 'Object'
                if not trg_name and not is_object_root:
                    continue

                trg_name = str(prefix) + str(trg_name)

                new_bone_name = bone_utils.copy_bone_to_arm(ob, trg_ob, src_name, suffix=cp_suffix)
                if not new_bone_name:
                    continue
                try:
                    new_parent = trg_ob.data.edit_bones[trg_name]
                except KeyError:
                    if is_object_root:
                        new_parent = None
                    else:
                        self.report({'WARNING'}, "{} not found in target".format(trg_name))
                        continue

                new_bone = trg_ob.data.edit_bones[new_bone_name]
                new_bone.parent = new_parent

                if self.match_transform == 'Bone':
                    # counter deformation bone transform

                    if deformation_map:
                        try:
                            def_bone = ob.data.edit_bones[deformation_map[src_name]]
                        except KeyError:
                            def_bone = ob.data.edit_bones[src_name]
                    else:
                        def_bone = ob.data.edit_bones[src_name]

                    try:
                        trg_ed_bone = trg_ob.data.edit_bones[trg_name]
                    except KeyError:
                        continue

                    new_bone.transform(def_bone.matrix.inverted())

                    # even transform
                    if self.match_object_transform:
                        new_bone.transform(ob.matrix_world)
                    # counter target transform
                    new_bone.transform(trg_ob.matrix_world.inverted())

                    # align target temporarily
                    trg_roll = trg_ed_bone.roll
                    trg_ed_bone.roll = bone_utils.ebone_roll_to_vector(trg_ed_bone, def_bone.z_axis)

                    # bring under trg_bone
                    new_bone.transform(trg_ed_bone.matrix)

                    # restore target orient
                    trg_ed_bone.roll = trg_roll

                    new_bone.roll = bone_utils.ebone_roll_to_vector(trg_ed_bone, def_bone.z_axis)
                elif self.match_transform == 'Pose':
                    new_bone.matrix = ob.pose.bones[src_name].matrix
                    if self.match_object_transform:
                        new_bone.transform(ob.matrix_world)
                    new_bone.transform(trg_ob.matrix_world.inverted_safe())
                elif self.match_transform == 'World':
                    new_bone.head = new_bone.parent.head
                    new_bone.tail = new_bone.parent.tail
                    new_bone.roll = new_bone.parent.roll
                    if self.match_object_transform:
                        new_bone.transform(ob.matrix_world)
                else:
                    src_bone = ob.data.bones[src_name]
                    src_z_axis_neg = matmul(Vector((0.0, 0.0, 1.0)), src_bone.matrix_local.inverted().to_3x3())
                    src_z_axis_neg.normalize()

                    new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_z_axis_neg)

                    if self.match_object_transform:
                        new_bone.transform(ob.matrix_world)
                        new_bone.transform(trg_ob.matrix_world.inverted())

                if self.copy_IK_roll_hands:
                    if src_name in (src_skeleton.right_arm_ik.hand,
                                    src_skeleton.left_arm_ik.hand):

                        src_ik = ob.data.bones[src_name]
                        new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_ik.z_axis)
                if self.copy_IK_roll_feet:
                    if src_name in (src_skeleton.left_leg_ik.foot,
                                    src_skeleton.right_leg_ik.foot):

                        src_ik = ob.data.bones[src_name]
                        new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_ik.z_axis)

                if self.use_legacy_index:
                    new_bone.layers[self.ret_bones_layer] = True
                    for i, L in enumerate(new_bone.layers):
                        # FIXME: should be util function
                        if i == self.ret_bones_layer:
                            continue
                        new_bone.layers[i] = False
                else:
                    for coll in new_bone.collections:
                        coll.unassign(new_bone)
                    ret_collection.assign(new_bone)

                if self.math_look_at:
                    if src_name == src_skeleton.right_arm_ik.arm:
                        start_bone_name = trg_skeleton.right_arm_ik.forearm
                    elif src_name == src_skeleton.left_arm_ik.arm:
                        start_bone_name = trg_skeleton.left_arm_ik.forearm
                    elif src_name == src_skeleton.right_leg_ik.upleg:
                        start_bone_name = trg_skeleton.right_leg_ik.leg
                    elif src_name == src_skeleton.left_leg_ik.upleg:
                        start_bone_name = trg_skeleton.left_leg_ik.leg
                    else:
                        start_bone_name = ""

                    if start_bone_name:
                        start_bone = trg_ob.data.edit_bones[prefix + start_bone_name]

                        look_bone = trg_ob.data.edit_bones.new(start_bone_name + '_LOOK')
                        look_bone.head = start_bone.head
                        look_bone.tail = 2 * start_bone.head - start_bone.tail
                        look_bone.parent = start_bone

                        look_ats[src_name] = look_bone.name

                        if self.use_legacy_index:
                            look_bone.layers[self.ret_bones_layer] = True
                            for i, L in enumerate(look_bone.layers):
                                # FIXME: should be util function
                                if i == self.ret_bones_layer:
                                    continue
                                look_bone.layers[i] = False
                        else:
                            for coll in look_bone.collections:
                                coll.unissign(look_bone)
                            ret_collection.assign(look_bone)

            for constr in limit_constraints:
                trg_ob.constraints.remove(constr)

            bpy.ops.object.mode_set(mode='POSE')

            for src_name, trg_name in look_ats.items():
                ret_bone = trg_ob.pose.bones["{}_{}".format(src_name, cp_suffix)]
                constr = ret_bone.constraints.new(type='LOCKED_TRACK')

                constr.head_tail = 1.0
                constr.target = trg_ob
                constr.subtarget = trg_name
                constr.lock_axis = 'LOCK_Y'
                constr.track_axis = 'TRACK_NEGATIVE_Z'

            left_finger_bones = list(chain(*src_skeleton.left_fingers.values()))
            right_finger_bones = list(chain(*src_skeleton.right_fingers.values()))

            for src_name in bone_names_map.keys():
                if not src_name:
                    continue
                if src_name == src_skeleton.root:
                    if self.constrain_root == "None":
                        continue
                    if self.constrain_root == "Bone" and not self.root_motion_bone:
                        continue
                try:
                    src_pbone = ob.pose.bones[src_name]
                except KeyError:
                    continue

                if self._bone_bound_already(src_pbone):
                    if self.constraint_policy == 'skip':
                        continue

                    if self.constraint_policy == 'disable':
                        for constr in src_pbone.constraints:
                            if constr.type in self._bind_constraints:
                                constr.mute = True
                    elif self.constraint_policy == 'remove':
                        for constr in reversed(src_pbone.constraints):
                            if constr.type in self._bind_constraints:
                                src_pbone.constraints.remove(constr)
                    # TODO: should unconstrain mid bones to!

                if not self.loc_constraints and self.bind_floating and is_bone_floating(src_pbone, src_skeleton.spine.hips):
                    constr_types = ['COPY_LOCATION', 'COPY_ROTATION']
                elif self.no_finger_loc and (src_name in left_finger_bones or src_name in right_finger_bones):
                    constr_types = ['COPY_ROTATION']
                else:
                    constr_types = self._bind_constraints

                for constr_type in constr_types:
                    constr = src_pbone.constraints.new(type=constr_type)
                    constr.target = trg_ob

                    subtarget_name = "{}_{}".format(src_name, cp_suffix)
                    if subtarget_name in trg_ob.data.bones:
                        constr.subtarget = subtarget_name

                if self.constrain_root == 'Bone' and src_name == src_skeleton.root:
                    self._constrained_root = src_pbone

            if self.constrain_root == 'Object' and self.root_motion_bone:
                constr_types = ['COPY_LOCATION']
                if any([self.root_cp_rot_x, self.root_cp_rot_y, self.root_cp_rot_z]):
                    constr_types.append('COPY_ROTATION')
                for constr_type in constr_types:
                    constr = ob.constraints.new(type=constr_type)
                    constr.target = trg_ob

                    constr.subtarget = self.root_motion_bone

                self._constrained_root = ob

            if self._constrained_root:
                if any((self.root_use_loc_min_x, self.root_use_loc_min_y, self.root_use_loc_min_z,
                        self.root_use_loc_max_x, self.root_use_loc_max_y, self.root_use_loc_max_z))\
                        or not all((self.root_cp_loc_x, self.root_cp_loc_y, self.root_cp_loc_z)):

                    constr = self._constrained_root.constraints.new('LIMIT_LOCATION')

                    constr.use_min_x = self.root_use_loc_min_x or not self.root_cp_loc_x
                    constr.use_min_y = self.root_use_loc_min_y or not self.root_cp_loc_y
                    constr.use_min_z = self.root_use_loc_min_z or not self.root_cp_loc_z

                    constr.use_max_x = self.root_use_loc_max_x or not self.root_cp_loc_x
                    constr.use_max_y = self.root_use_loc_max_y or not self.root_cp_loc_y
                    constr.use_max_z = self.root_use_loc_max_z or not self.root_cp_loc_z

                    constr.min_x = self.root_loc_min_x if self.root_cp_loc_x and self.root_use_loc_min_x else 0.0
                    constr.min_y = self.root_loc_min_y if self.root_cp_loc_y and self.root_use_loc_min_y else 0.0
                    constr.min_z = self.root_loc_min_z if self.root_cp_loc_z and self.root_use_loc_min_z else 0.0

                    constr.max_x = self.root_loc_max_x if self.root_cp_loc_x and self.root_use_loc_max_x else 0.0
                    constr.max_y = self.root_loc_max_y if self.root_cp_loc_y and self.root_use_loc_max_y else 0.0
                    constr.max_z = self.root_loc_max_z if self.root_cp_loc_z and self.root_use_loc_max_z else 0.0

            if self._constrained_root and not all((self.root_cp_rot_x, self.root_cp_rot_y, self.root_cp_rot_z)):
                constr = self._constrained_root.constraints.new('LIMIT_ROTATION')

                constr.use_limit_x = not self.root_cp_rot_x
                constr.use_limit_y = not self.root_cp_rot_y
                constr.use_limit_z = not self.root_cp_rot_z

        return {'FINISHED'}


def validate_actions(action, path_resolve): # :Action, :callable
    for fc in action.fcurves:
        data_path = fc.data_path
        if fc.array_index:
            data_path = data_path + "[%d]" % fc.array_index
        try:
            path_resolve(data_path)
        except ValueError:
            return False  # Invalid.
    return True  # Valid.


if bpy.app.version < (2, 79):
    @make_annotations
    class ConstrainActiveToSelected(bpy.types.Operator):
        bl_idname = "armature.expykit_constrain_active"
        bl_label = "Bind Active to Selected"
        bl_description = "The same as above, but swaps the two first"
        bl_options = {'REGISTER', 'UNDO'}

        @classmethod
        def poll(cls, context):
            return (
                len(context.selected_objects) == 2
                and context.mode == 'POSE'
                and all(map(lambda ob: ob.type == 'ARMATURE', context.selected_objects))
                )

        def execute(self, context):
            trg_obj = next((ob for ob in context.selected_objects if ob != context.object))
            if bpy.app.version >= (2, 80):
                context.view_layer.objects.active = trg_obj
            else:
                context.scene.objects.active = trg_obj

            bpy.ops.object.mode_set(mode='POSE')

            bpy.ops.armature.expykit_constrain_to_armature('INVOKE_DEFAULT', force_dialog=True)

            return {'FINISHED'}


@make_annotations
class BakeConstrainedActions(bpy.types.Operator):
    bl_idname = "armature.expykit_bake_constrained_actions"
    bl_label = "Bake Constrained Actions"
    bl_description = "Bake Actions constrained from another Armature. No need to select two armatures"
    bl_options = {'REGISTER', 'UNDO'}

    clear_users_old = BoolProperty(name="Clear original Action Users",
                                  default=True)

    fake_user_new = BoolProperty(name="Save New Action User",
                                default=True)

    exclude_deform = BoolProperty(name="Exclude deform bones", default=True)

    do_bake = BoolProperty(name="Bake and Exit", description="Bake driven motion and exit",
                          default=False, options={'SKIP_SAVE'})

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        for to_bake in context.selected_objects:
            trg_ob = self.get_trg_ob(to_bake)
            if not trg_ob:
                continue

            column.label(text="Baking from {} to {}".format(trg_ob.name, to_bake.name))

        if len(context.selected_objects) > 1:
            column.label(text="No need to select two Armatures anymore", icon='ERROR')

        row = layout_split(column, factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "clear_users_old")

        row = layout_split(column, factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "fake_user_new")

        row = layout_split(column, factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "exclude_deform")

        row = layout_split(column, factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "do_bake", toggle=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def get_trg_ob(self, ob): # -> bpy.types.Object:
        for pb in bone_utils.get_constrained_controls(armature_object=ob, use_deform=not self.exclude_deform):
            for constr in pb.constraints:
                try:
                    subtarget = constr.subtarget
                except AttributeError:
                    continue

                if subtarget.endswith("_RET"):
                    return(constr.target)

    def execute(self, context):
        if not self.do_bake:
            return {'FINISHED'}

        sel_obs = list(context.selected_objects)
        for ob in sel_obs:
            if bpy.app.version < (2, 80):
                ob.select = False
            else:
                ob.select_set(False)

            trg_ob = self.get_trg_ob(ob)
            if not trg_ob:
                continue

            constr_bone_names = []
            for pb in bone_utils.get_constrained_controls(ob, unselect=True, use_deform=not self.exclude_deform):

                if pb.name + "_RET" in trg_ob.data.bones:
                    pb.bone.select = True
                    constr_bone_names.append(pb.name)

            for action in list(bpy.data.actions):  # convert to list beforehand to avoid picking new actions
                if not validate_actions(action, trg_ob.path_resolve):
                    continue

                trg_ob.animation_data.action = action
                fr_start, fr_end = action.frame_range
                bpy.ops.nla.bake(frame_start=int(fr_start), frame_end=int(fr_end),
                                 bake_types={'POSE'}, only_selected=True,
                                 visual_keying=True, clear_constraints=False)

                if not ob.animation_data:
                    self.report({'WARNING'}, "failed to bake {}".format(action.name))
                    continue

                ob.animation_data.action.use_fake_user = self.fake_user_new

                if trg_ob.name in action.name:
                    new_name = action.name.replace(trg_ob.name, ob.name)
                else:
                    new_name = "{}|{}".format(ob.name, action.name)

                ob.animation_data.action.name = new_name

                if self.clear_users_old:
                    action.user_clear()

            # delete Constraints
            for bone_name in constr_bone_names:
                try:
                    pbone = ob.pose.bones[bone_name]
                except KeyError:
                    continue
                for constr in reversed(pbone.constraints):
                    pbone.constraints.remove(constr)

        return {'FINISHED'}


def crv_bone_name(fcurve):
    p_bone_prefix = 'pose.bones['
    if not fcurve.data_path.startswith(p_bone_prefix):
        return
    data_path = fcurve.data_path
    return data_path[len(p_bone_prefix):].rsplit('"]', 1)[0].strip('"[')


def is_bone_floating(bone, hips_bone_name):
    binding_constrs = ['COPY_LOCATION', 'COPY_ROTATION', 'COPY_TRANSFORMS']
    while bone.parent:
        if bone.parent.name == hips_bone_name:
            return False
        for constr in bone.constraints:
            if constr.type in binding_constrs:
                return False
        bone = bone.parent

    return True


def add_loc_key(bone, frame, options):
    bone.keyframe_insert('location', index=0, frame=frame, options=options)
    bone.keyframe_insert('location', index=1, frame=frame, options=options)
    bone.keyframe_insert('location', index=2, frame=frame, options=options)


def get_rot_ani_path(to_animate):
    if to_animate.rotation_mode == 'QUATERNION':
        return 'rotation_quaternion', 4
    if to_animate.rotation_mode == 'AXIS_ANGLE':
        return 'rotation_axis_angle', 4

    return 'rotation_euler', 3


def add_loc_rot_key(bone, frame, options):
    add_loc_key(bone, frame, options)

    mode, channels = get_rot_ani_path(bone)
    for i in range(channels):
        bone.keyframe_insert(mode, index=i, frame=frame, options=options)


@make_annotations
class AddRootMotion(bpy.types.Operator):
    bl_idname = "armature.expykit_add_rootmotion"
    bl_label = "Transfer Root Motion"
    bl_description = "Bring Motion to Root Bone"
    bl_options = {'REGISTER', 'UNDO'}

    rig_preset = EnumProperty(items=preset_handler.iterate_presets,
                             name="Target Preset")

    motion_bone = StringProperty(name="Motion",
                                description="Constrain Root bone to Hip motion",
                                default="")

    root_motion_bone = StringProperty(name="Root Motion",
                                     description="Constrain Root bone to Hip motion",
                                     default="")

    new_anim_suffix = StringProperty(name="Suffix",
                                    default="_RM",
                                    description="Suffix of the duplicate animation, leave empty to overwrite")

    obj_or_bone = EnumProperty(items=[
        ('object', "Object", "Transfer Root Motion To Object"),
        ('bone', "Bone", "Transfer Root Motion To Bone")],
                              name="Object/Bone", default='bone')

    keep_offset = BoolProperty(name="Keep Offset", default=True)
    offset_type = EnumProperty(items=[
        ('start', "Action Start", "Offset to Start Pose"),
        ('end', "Action End", "Offset to Match End Pose"),
        ('rest', "Rest Pose", "Offset to Match Rest Pose")],
                              name="Offset",
                              default='rest')

    root_cp_loc_x = BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=False)
    root_cp_loc_y = BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z = BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x = BoolProperty(name="Use Root Min X", description="Minimum Root X", default=False)
    root_use_loc_min_y = BoolProperty(name="Use Root Min Y", description="Minimum Root Y", default=False)
    root_use_loc_min_z = BoolProperty(name="Use Root Min Z", description="Minimum Root Z", default=True)

    root_loc_min_x = FloatProperty(name="Root Min X", description="Minimum Root X", default=0.0)
    root_loc_min_y = FloatProperty(name="Root Min Y", description="Minimum Root Y", default=0.0)
    root_loc_min_z = FloatProperty(name="Root Min Z", description="Minimum Root Z", default=0.0)

    root_use_loc_max_x = BoolProperty(name="Use Root Max X", description="Maximum Root X", default=False)
    root_use_loc_max_y = BoolProperty(name="Use Root Max Y", description="Maximum Root Y", default=False)
    root_use_loc_max_z = BoolProperty(name="Use Root Max Z", description="Maximum Root Z", default=False)

    root_loc_max_x = FloatProperty(name="Root Max X", description="Maximum Root X", default=0.0)
    root_loc_max_y = FloatProperty(name="Root Max Y", description="Maximum Root Y", default=0.0)
    root_loc_max_z = FloatProperty(name="Root Max Z", description="Maximum Root Z", default=0.0)

    root_cp_rot_x = BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=True)
    root_cp_rot_y = BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=True)
    root_cp_rot_z = BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    _armature = None
    _prop_indent = 0.15

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.mode != 'POSE':
            return False
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.animation_data:
            return False
        if not context.object.animation_data.action:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        if not context.object.data.expykit_retarget.has_settings():
            row = column.row()
            row.prop(self, 'rig_preset', text="Rig Type:")

        row = layout_split(column, factor=self._prop_indent, align=True)
        row.label(text="From")
        row.prop_search(self, 'motion_bone',
                        context.active_object.data,
                        "bones", text="")

        split = layout_split(column, factor=self._prop_indent, align=True)
        split.label(text="To")

        col = split.column()
        col.prop(self, 'obj_or_bone', expand=True)

        col.prop_search(self, 'root_motion_bone',
                        context.active_object.data,
                        "bones", text="")

        row = layout_split(column, factor=self._prop_indent, align=True)
        row.label(text="Suffix:")
        row.prop(self, 'new_anim_suffix', text="")

        column.separator()

        row = column.row(align=False)
        row.prop(self, "keep_offset")
        subcol = row.column()
        subcol.prop(self, "offset_type", text="Match ")
        subcol.enabled = self.keep_offset

        row = column.row(align=True)
        row.label(text="Location")
        row.prop(self, "root_cp_loc_x", text="X", toggle=True)
        row.prop(self, "root_cp_loc_y", text="Y", toggle=True)
        row.prop(self, "root_cp_loc_z", text="Z", toggle=True)

        row = column.row(align=True)
        row.label(text="Rotation Plane")
        row.prop(self, "root_cp_rot_x", text="X", toggle=True)
        row.prop(self, "root_cp_rot_y", text="Y", toggle=True)
        row.prop(self, "root_cp_rot_z", text="Z", toggle=True)

        column.separator()

        # Min/Max X
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_x", text="Min X")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_x", text="")
        subcol.enabled = self.root_use_loc_min_x

        row.separator()
        row.prop(self, "root_use_loc_max_x", text="Max X")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_x", text="")
        subcol.enabled = self.root_use_loc_max_x
        row.enabled = self.root_cp_loc_x

        # Min/Max Y
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_y", text="Min Y")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_y", text="")
        subcol.enabled = self.root_use_loc_min_y

        row.separator()
        row.prop(self, "root_use_loc_max_y", text="Max Y")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_y", text="")
        subcol.enabled = self.root_use_loc_max_y
        row.enabled = self.root_cp_loc_y

        # Min/Max Z
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_z", text="Min Z")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_z", text="")
        subcol.enabled = self.root_use_loc_min_z

        row.separator()
        row.prop(self, "root_use_loc_max_z", text="Max Z")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_z", text="")
        subcol.enabled = self.root_use_loc_max_z
        row.enabled = self.root_cp_loc_z

    def _set_defaults(self, rig_settings):
        if not rig_settings:
            return False

        if not self.root_motion_bone:
            self.root_motion_bone = rig_settings.root

        if not self.motion_bone:
            self.motion_bone = rig_settings.spine.hips

        return(bool(self.motion_bone))

    def invoke(self, context, event):
        """Fill root and hips field according to character settings"""
        self._rootmo_transfs = []
        self._rootbo_transfs = []
        self._hip_bone_transfs = []
        self._all_floating_mats = []

        self._stored_motion_bone = ""
        self._stored_motion_type = self.obj_or_bone
        self._transforms_stored = False

        rig_settings = context.object.data.expykit_retarget
        if self._set_defaults(rig_settings):
            self._store_transforms(context)

        return self.execute(context)

    def _get_floating_bones(self, context):
        arm_ob = context.active_object
        skeleton = preset_handler.get_settings_skel(arm_ob.data.expykit_retarget)

        # TODO: check controls with animation curves instead
        def consider_bone(b_name):
            if b_name == self.root_motion_bone:
                return False
            return b_name in arm_ob.pose.bones

        rig_bones = [arm_ob.pose.bones[b_name] for b_name in skeleton.bone_names() if b_name and consider_bone(b_name)]
        return list([bone for bone in rig_bones if is_bone_floating(bone, self.motion_bone)])

    def _clear_cache(self):
        self._all_floating_mats.clear()
        self._hip_bone_transfs.clear()
        self._rootmo_transfs.clear()

        self._rootbo_transfs.clear()

    def _store_transforms(self, context):
        self._clear_cache()
        arm_ob = context.active_object

        root_bone = arm_ob.pose.bones[self.root_motion_bone]
        hip_bone = arm_ob.pose.bones[self.motion_bone]
        floating_bones = self._get_floating_bones(context)

        start, end = self._get_start_end(context)

        current_position = arm_ob.data.pose_position

        if self.offset_type == 'start':
            context.scene.frame_set(start)
        elif self.offset_type == 'end':
            context.scene.frame_set(end)
        else:
            arm_ob.data.pose_position = 'REST'

        start_mat_inverse = hip_bone.matrix.inverted()

        context.scene.frame_set(start)
        arm_ob.data.pose_position = current_position

        for frame_num in range(start, end + 1):
            context.scene.frame_set(frame_num)

            self._all_floating_mats.append(list([b.matrix.copy() for b in floating_bones]))
            self._hip_bone_transfs.append(hip_bone.matrix.copy())
            self._rootmo_transfs.append(matmul(hip_bone.matrix, start_mat_inverse))

            if self.obj_or_bone == 'object' and root_bone:
                self._rootbo_transfs.append(root_bone.matrix.copy())

        self._stored_motion_bone = self.motion_bone
        self._stored_motion_type = self.obj_or_bone
        self._transforms_stored = True

    def _cache_dirty(self):
        if self._stored_motion_bone != self.motion_bone:
            return True
        if self._stored_motion_type != self.obj_or_bone:
            return True

        return False

    def execute(self, context):
        rig_settings = context.object.data.expykit_retarget
        if not rig_settings.has_settings():
            rig_settings = preset_handler.set_preset_skel(self.rig_preset)
            self._set_defaults(rig_settings)
        if not self.root_motion_bone:
            return {'FINISHED'}
        if not self.motion_bone:
            return {'FINISHED'}

        armature = context.active_object
        if self.new_anim_suffix:
            action_dupli = armature.animation_data.action.copy()

            action_name = armature.animation_data.action.name
            action_dupli.name = "{}{}".format(action_name, self.new_anim_suffix)
            action_dupli.use_fake_user = armature.animation_data.action.use_fake_user
            armature.animation_data.action = action_dupli

        if self._cache_dirty():
            self._store_transforms(context)

        if not self._transforms_stored:
            self.report({'WARNING'}, "No transforms stored")

        self.action_offs(context)
        return {'FINISHED'}

    @staticmethod
    def _get_start_end(context):
        action = context.active_object.animation_data.action
        start, end = action.frame_range

        return int(start), int(end)

    def action_offs(self, context):
        start, end = self._get_start_end(context)
        current = context.scene.frame_current

        hips_bone_name = self.motion_bone
        hip_bone = context.active_object.pose.bones[hips_bone_name]

        if self.keep_offset and self.offset_type == 'end':
            context.scene.frame_set(end)
            end_mat = hip_bone.matrix.copy()
        else:
            end_mat = Matrix()

        context.scene.frame_set(start)
        start_mat = hip_bone.matrix.copy()
        start_mat_inverse = start_mat.inverted()

        if self.keep_offset:
            if self.offset_type == 'rest':
                offset_mat = context.active_object.data.bones[hip_bone.name].matrix_local.inverted()
            elif self.offset_type == 'start':
                offset_mat = start_mat_inverse
            elif self.offset_type == 'end':
                offset_mat = end_mat.inverted()
        else:
            offset_mat = Matrix()

        root_bone_name = self.root_motion_bone

        if self.obj_or_bone == 'object':
            root_bone = context.active_object
        else:
            try:
                root_bone = context.active_object.pose.bones[root_bone_name]
            except (TypeError, KeyError):
                self.report({'WARNING'}, "{} not found in target".format(root_bone_name))
                return {'FINISHED'}

        bpy.context.scene.frame_set(start)
        keyframe_options = {'INSERTKEY_VISUAL', 'INSERTKEY_CYCLE_AWARE'}
        add_loc_rot_key(root_bone, start, keyframe_options)

        root_matrix = root_bone.matrix if self.obj_or_bone == 'bone' else context.active_object.matrix_world
        for i, frame_num in enumerate(range(start, end + 1)):
            bpy.context.scene.frame_set(frame_num)

            rootmo_transf = matmul(self._hip_bone_transfs[i], offset_mat)
            if self.root_cp_loc_x:
                if self.root_use_loc_min_x:
                    rootmo_transf[0][3] = max(rootmo_transf[0][3], self.root_loc_min_x)
                if self.root_use_loc_max_x:
                    rootmo_transf[0][3] = min(rootmo_transf[0][3], self.root_loc_max_x)
            else:
                rootmo_transf[0][3] = root_matrix[0][3]
            if self.root_cp_loc_y:
                if self.root_use_loc_min_y:
                    rootmo_transf[1][3] = max(rootmo_transf[1][3], self.root_loc_min_y)
                if self.root_use_loc_max_y:
                    rootmo_transf[1][3] = min(rootmo_transf[1][3], self.root_loc_max_y)
            else:
                rootmo_transf[1][3] = root_matrix[1][3]
            if self.root_cp_loc_z:
                if self.root_use_loc_min_z:
                    rootmo_transf[2][3] = max(rootmo_transf[2][3], self.root_loc_min_z)
                if self.root_use_loc_max_z:
                    rootmo_transf[2][3] = min(rootmo_transf[2][3], self.root_loc_max_z)
            else:
                rootmo_transf[2][3] = root_matrix[2][3]

            if not all((self.root_cp_rot_x, self.root_cp_rot_y, self.root_cp_rot_z)):
                if self.root_cp_rot_x + self.root_cp_rot_y + self.root_cp_rot_z < 2:
                    # need at least two axis to make this work, don't use rotation
                    no_rot = Matrix()
                    no_rot[0][3] = rootmo_transf[0][3]
                    no_rot[1][3] = rootmo_transf[1][3]
                    no_rot[2][3] = rootmo_transf[2][3]

                    rootmo_transf = no_rot
                else:
                    rootmo_transf.transpose()
                    root_transp = root_matrix.transposed()

                    if not self.root_cp_rot_z:
                        # XY plane
                        rootmo_transf[1][2] = root_transp[1][2]
                        rootmo_transf[0][2] = root_transp[0][2]

                        y_axis = rootmo_transf[1].to_3d()
                        y_axis.normalize()

                        x_axis = y_axis.cross(root_transp[2].to_3d())
                        x_axis.normalize()

                        z_axis = x_axis.cross(y_axis)
                        z_axis.normalize()
                    elif not self.root_cp_rot_x:
                        # ZY plane
                        rootmo_transf[1][0] = root_transp[1][0]
                        rootmo_transf[2][0] = root_transp[2][0]

                        z_axis = rootmo_transf[2].to_3d().normalized()
                        up = root_transp[1].to_3d()
                        x_axis = up.cross(z_axis).normalized()
                        y_axis = z_axis.cross(x_axis)
                        y_axis.normalize()
                    else:
                        # XZ plane
                        rootmo_transf[2][1] = root_transp[2][1]
                        rootmo_transf[0][1] = root_transp[0][1]

                        z_axis = rootmo_transf[2].to_3d().normalized()
                        up = root_transp[1].to_3d()
                        x_axis = up.cross(z_axis).normalized()
                        y_axis = z_axis.cross(x_axis)

                    rootmo_transf[0] = x_axis.to_4d()
                    rootmo_transf[1] = y_axis.to_4d()
                    rootmo_transf[2] = z_axis.to_4d()

                    rootmo_transf.transpose()

            if self.obj_or_bone == 'object':
                root_bone.matrix_world = rootmo_transf
            else:
                root_bone.matrix = rootmo_transf
            add_loc_rot_key(root_bone, frame_num, keyframe_options)

        floating_bones = self._get_floating_bones(context)
        for i, frame_num in enumerate(range(start, end + 1)):
            bpy.context.scene.frame_set(frame_num)

            if self.obj_or_bone == 'object' and self.root_motion_bone:
                context.active_object.pose.bones[self.root_motion_bone].matrix = matmul(root_bone.matrix_world.inverted(), context.active_object.pose.bones[self.root_motion_bone].matrix)

            floating_mats = self._all_floating_mats[i]
            for bone, mat in zip(floating_bones, floating_mats):
                if self.obj_or_bone == 'object':
                    # TODO: should get matrix at frame 0
                    mat = matmul(root_bone.matrix_world.inverted(), mat)

                bone.matrix = mat
                add_loc_rot_key(bone, frame_num, set())

        bpy.context.scene.frame_set(current)


@make_annotations
class ActionNameCandidates(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="Name Candidate", default="")


@make_annotations
class RenameActionsFromFbxFiles(bpy.types.Operator, ImportHelper):
    bl_idname = "armature.expykit_rename_actions_fbx"
    bl_label = "Rename Actions from fbx data..."
    bl_description = "Rename Actions from candidate fbx files"
    bl_options = {'PRESET', 'UNDO'}

    directory = StringProperty()

    filename_ext = ".fbx"
    filter_glob = StringProperty(default="*.fbx", options={'HIDDEN'})

    files = CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    contains = StringProperty(name="Containing", default="|")
    starts_with = StringProperty(name="Starting with", default="Action")

    def execute(self, context):
        fbx_durations = dict()
        for f in self.files:
            fbx_path = os.path.join(self.directory, f.name)
            local_time = fbx_helper.get_fbx_local_time(fbx_path)
            if not local_time:
                continue

            duration = fbx_helper.convert_from_fbx_duration(*local_time)
            duration = round(duration, 5)
            duration = str(duration)
            action_name = os.path.splitext(f.name[:-3])[0]

            try:
                fbx_durations[duration].append(action_name)
            except KeyError:  # entry doesn'exist yet
                fbx_durations[duration] = action_name
            except AttributeError:  # existing entry is not a list
                current = fbx_durations[duration]
                fbx_durations[duration] = [current, action_name]

        path_resolve = context.object.path_resolve
        for action in bpy.data.actions:
            skip_action = True

            if self.contains and self.contains in action.name:
                skip_action = False
            if skip_action and self.starts_with and action.name.startswith(self.starts_with):
                skip_action = False

            if skip_action:
                continue

            if not validate_actions(action, path_resolve):
                continue

            start, end = action.frame_range
            ac_duration = end - start
            ac_duration /= context.scene.render.fps
            ac_duration = round(ac_duration, 5)
            ac_duration = str(ac_duration)

            try:
                fbx_match = fbx_durations[ac_duration]
            except KeyError:
                continue

            if not fbx_match:
                continue
            if isinstance(fbx_match, list):
                for name in fbx_match:
                    entry = action.expykit_name_candidates.add()
                    entry.name = name
                continue

            action.name = fbx_match

        return {'FINISHED'}


def register_classes():
    bpy.utils.register_class(ActionRangeToScene)
    bpy.utils.register_class(ConstraintStatus)
    bpy.utils.register_class(SelectConstrainedControls)
    bpy.utils.register_class(ConvertBoneNaming)
    bpy.utils.register_class(ConvertGameFriendly)
    bpy.utils.register_class(ExtractMetarig)
    bpy.utils.register_class(MergeHeadTails)
    bpy.utils.register_class(RevertDotBoneNames)
    bpy.utils.register_class(ConstrainToArmature)
    if bpy.app.version < (2, 79):
        bpy.utils.register_class(ConstrainActiveToSelected)
    bpy.utils.register_class(BakeConstrainedActions)
    bpy.utils.register_class(RenameActionsFromFbxFiles)
    bpy.utils.register_class(CreateTransformOffset)
    bpy.utils.register_class(AddRootMotion)
    bpy.utils.register_class(ActionNameCandidates)

    bpy.types.Action.expykit_name_candidates = bpy.props.CollectionProperty(type=ActionNameCandidates)


def unregister_classes():
    del bpy.types.Action.expykit_name_candidates

    bpy.utils.unregister_class(ActionRangeToScene)
    bpy.utils.unregister_class(ConstraintStatus)
    bpy.utils.unregister_class(SelectConstrainedControls)
    bpy.utils.unregister_class(ConvertBoneNaming)
    bpy.utils.unregister_class(ConvertGameFriendly)
    bpy.utils.unregister_class(ExtractMetarig)
    bpy.utils.unregister_class(MergeHeadTails)
    bpy.utils.unregister_class(RevertDotBoneNames)
    if bpy.app.version < (2, 79):
        bpy.utils.unregister_class(ConstrainActiveToSelected)
    bpy.utils.unregister_class(ConstrainToArmature)
    bpy.utils.unregister_class(BakeConstrainedActions)
    bpy.utils.unregister_class(RenameActionsFromFbxFiles)
    bpy.utils.unregister_class(CreateTransformOffset)
    bpy.utils.unregister_class(AddRootMotion)
    bpy.utils.unregister_class(ActionNameCandidates)
