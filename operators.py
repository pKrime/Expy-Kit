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
from . import bone_utils
from . import fbx_helper

from importlib import reload
reload(bone_mapping)
reload(bone_utils)
reload(fbx_helper)

from mathutils import Vector
from mathutils import Matrix
from math import pi
import os
import typing


status_types = (
    ('enable', "Enable", "Enable All Constraints"),
    ('disable', "Disable", "Disable All Constraints"),
    ('remove', "Remove", "Remove All Constraints")
)


skeleton_types = (
    ('unreal', "Unreal", "UE4 Skeleton"),
    ('rigify', "Rigify", "Rigify Skeleton"),
    ('rigify_meta', "Rigify Metarig", "Rigify Metarig"),
    ('rigify_ctrls', "Rigify Controls", "Rigify CTRLS"),
    ('mixamo', "Mixamo", "Mixamo Skeleton"),
    ('daz-gen8', "Daz Genesis 8", "Daz Genesis 8 Skeleton"),
    ('--', "--", "None")
)


class ConstraintStatus(bpy.types.Operator):
    """Disable/Enable bone constraints."""
    bl_idname = "object.expykit_set_constraints_status"
    bl_label = "Enable/disable constraints"
    bl_options = {'REGISTER', 'UNDO'}

    set_status: EnumProperty(items=status_types,
                              name="Status",
                              default='enable')

    selected_only: BoolProperty(name="Only Selected",
                                default=False)

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
                    bone.constraints.remove(constr)
        else:
            for bone in bones:
                for constr in bone.constraints:
                    constr.mute = self.set_status == 'disable'
        return {'FINISHED'}


class SelectConstrainedControls(bpy.types.Operator):
    bl_idname = "armature.expykit_select_constrained_ctrls"
    bl_label = "Select constrained controls"
    bl_description = "Select bone controls with constraints or animations"
    bl_options = {'REGISTER', 'UNDO'}

    select_type: EnumProperty(items=[
        ('constr', "Constrained", "Select constrained controls"),
        ('anim', "Animated", "Select animated controls"),
    ],
        name="Select if",
        default='constr')

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
            for bone in ob.data.bones:
                if bone.use_deform:  # FIXME: ik controls might have use_deform just to be exported for games
                    bone.select = False
                    continue
                pbone = ob.pose.bones[bone.name]
                if len(pbone.constraints) == 0:
                    bone.select = False
                    continue

                bone.select = bool(pbone.custom_shape)
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


class RevertDotBoneNames(bpy.types.Operator):
    """Reverts dots in bones that have renamed by Unreal Engine"""
    bl_idname = "object.expykit_dot_bone_names"
    bl_label = "Revert dots in Names (from UE4 renaming)"
    bl_options = {'REGISTER', 'UNDO'}

    sideletters_only: BoolProperty(name="Only Side Letters",
                                   description="i.e. '_L' to '.L'",
                                   default=True)

    selected_only: BoolProperty(name="Only Selected",
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


class ConvertBoneNaming(bpy.types.Operator):
    """Convert Bone Names between Naming Convention"""
    bl_idname = "object.expykit_convert_bone_names"
    bl_label = "Convert Bone Names"
    bl_options = {'REGISTER', 'UNDO'}

    source: EnumProperty(items=skeleton_types,
                         name="Source Type",
                         default='--')

    target: EnumProperty(items=skeleton_types,
                         name="Target Type",
                         default='--')

    strip_prefix: BoolProperty(
        name="Strip Prefix",
        description="Remove prefix when found",
        default=True
    )

    anim_tracks: BoolProperty(
        name="Convert Animations",
        description="Convert Animation Tracks",
        default=True
    )

    # TODO: separator as a string property
    _separator = ":"

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
        src_skeleton = skeleton_from_type(self.source)
        trg_skeleton = skeleton_from_type(self.target)

        if all((src_skeleton, trg_skeleton, src_skeleton != trg_skeleton)):
            if self.anim_tracks:
                actions = [action for action in bpy.data.actions if validate_actions(action, context.object.path_resolve)]
            else:
                actions = []

            bone_names_map = src_skeleton.conversion_map(trg_skeleton)

            if self.strip_prefix:
                for bone in context.object.data.bones:
                    if self._separator not in bone.name:
                        continue

                    bone.name = bone.name.rsplit(self._separator, 1)[1]

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
                src_bone.name = trg_name

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

                    try:
                        trg_name = bone_names_map[track_bone]
                    except KeyError:
                        continue

                    fc.data_path = fc.data_path.replace('bones["{0}"'.format(track_bone),
                                                        'bones["{0}"'.format(trg_name))

        return {'FINISHED'}


class CreateTransformOffset(bpy.types.Operator):
    """Scale the Character and setup an Empty to preserve final transform"""
    bl_idname = "object.expykit_create_offset"
    bl_label = "Create Scale Offset"
    bl_options = {'REGISTER', 'UNDO'}

    container_name: StringProperty(name="Name", description="Name of the transform container", default="EMP-Offset")
    container_scale: FloatProperty(name="Scale", description="Scale of the transform container", default=0.01)
    fix_animations: BoolProperty(name="Fix Animations", description="Apply Offset to character animations", default=True)
    do_parent: BoolProperty(name="Execute and Exit", description="Parent to the new offset and exit",
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

        # fix constraints rest lenghts
        for pbone in arm_ob.pose.bones:
            for constr in pbone.constraints:
                if constr.type == 'STRETCH_TO':
                    constr.rest_length /= self.container_scale

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


def skeleton_from_type(skeleton_type):
    # TODO: this would be better handled by EnumTypes
    if skeleton_type == 'mixamo':
        return bone_mapping.MixamoSkeleton()
    if skeleton_type == 'rigify':
        return bone_mapping.RigifySkeleton()
    if skeleton_type == 'rigify_meta':
        return bone_mapping.RigifyMeta()
    if skeleton_type == 'rigify_ctrls':
        return bone_mapping.RigifyCtrls()
    if skeleton_type == 'unreal':
        return bone_mapping.UnrealSkeleton()
    if skeleton_type == 'daz-gen8':
        return bone_mapping.DazGenesis8()


def align_to_closer_axis(src_bone, trg_bone):
    src_rot = src_bone.matrix_local.to_3x3().inverted()
    src_x_axis = src_rot[0]
    src_y_axis = src_rot[1]
    src_z_axis = src_rot[2]

    bone_direction = trg_bone.parent.vector.normalized()
    dot_x = abs(bone_direction.dot(src_x_axis))
    dot_y = abs(bone_direction.dot(src_y_axis))
    dot_z = abs(bone_direction.dot(src_z_axis))

    matching_dot = max(dot_x, dot_y, dot_z)
    if matching_dot == dot_x:
        closer_axis = src_x_axis
    elif matching_dot == dot_y:
        closer_axis = src_y_axis
    else:
        closer_axis = src_z_axis

    offset = closer_axis * src_bone.length
    if closer_axis.dot(bone_direction) < 0:
        offset *= -1

    trg_bone.tail = trg_bone.head + offset


class ExtractMetarig(bpy.types.Operator):
    """Create Metarig from current object"""
    bl_idname = "object.expykit_extract_metarig"
    bl_label = "Extract Metarig"
    bl_description = "Create Metarig from current object"
    bl_options = {'REGISTER', 'UNDO'}

    skeleton_type: EnumProperty(items=skeleton_types,
                                name="Source Type",
                                default='--')

    offset_knee: FloatProperty(name='Offset Knee',
                               default=0.0)

    offset_elbow: FloatProperty(name='Offset Elbow',
                                default=0.0)

    offset_fingers: FloatVectorProperty(name='Offset Fingers')

    no_face: BoolProperty(name='No face bones',
                          default=True)

    rigify_names: BoolProperty(name='Use rifify names',
                               default=True)

    assign_metarig: BoolProperty(name='Assign metarig',
                                 default=True,
                                 description='Rigify will generate to the active object')

    forward_spine_roll: BoolProperty(name='Align spine frontally', default=False,
                                     description='Spine Z will face the Y axis')

    apply_transforms: BoolProperty(name='Apply Transform', default=True,
                                   description='Apply current transforms before extraction')

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
        src_object = context.object
        src_armature = context.object.data
        src_skeleton = skeleton_from_type(self.skeleton_type)

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

        if self.skeleton_type != 'rigify' and self.rigify_names:
            bpy.ops.object.expykit_convert_bone_names(source=self.skeleton_type, target='rigify')
            src_skeleton = skeleton_from_type('rigify')

        try:
            metarig = next(ob for ob in bpy.data.objects if ob.type == 'ARMATURE' and ob.data.rigify_target_rig == src_object)
            met_armature = metarig.data
            create_metarig = False
        except StopIteration:
            create_metarig = True
            met_armature = bpy.data.armatures.new('metarig')
            metarig = bpy.data.objects.new("metarig", met_armature)
            metarig.data.rigify_rig_basename = src_object.name

            context.collection.objects.link(metarig)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        metarig.select_set(True)
        bpy.context.view_layer.objects.active = metarig
        bpy.ops.object.mode_set(mode='EDIT')

        if create_metarig:
            from rigify.metarigs import human
            human.create(metarig)

        met_skeleton = bone_mapping.RigifyMeta()

        def match_meta_bone(met_bone_group, src_bone_group, bone_attr, axis=None):
            met_bone = met_armature.edit_bones[getattr(met_bone_group, bone_attr)]
            src_bone = src_armature.bones.get(getattr(src_bone_group, bone_attr), None)

            if not src_bone:
                print(bone_attr, "not found in", src_armature)
                return

            met_bone.head = src_bone.head_local
            met_bone.tail = src_bone.tail_local

            if met_bone.parent and met_bone.use_connect:
                bone_dir = met_bone.vector.normalized()
                parent_dir = met_bone.parent.vector.normalized()

                if bone_dir.dot(parent_dir) < -0.6:
                    print(met_bone.name, "non aligned")
                    # TODO

            if axis:
                met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, axis)
            else:
                src_x_axis = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.inverted().to_3x3()
                src_x_axis.normalize()
                met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, src_x_axis)

        for bone_attr in ['hips', 'spine', 'spine1', 'spine2', 'neck', 'head']:
            if self.forward_spine_roll:
                align = Vector((0.0, -1.0, 0.0))
            else:
                align = None
            match_meta_bone(met_skeleton.spine, src_skeleton.spine, bone_attr, axis=align)

        for bone_attr in ['shoulder', 'arm', 'forearm', 'hand']:
            match_meta_bone(met_skeleton.right_arm, src_skeleton.right_arm, bone_attr)
            match_meta_bone(met_skeleton.left_arm, src_skeleton.left_arm, bone_attr)

        for bone_attr in ['upleg', 'leg', 'foot', 'toe']:
            match_meta_bone(met_skeleton.right_leg, src_skeleton.right_leg, bone_attr)
            match_meta_bone(met_skeleton.left_leg, src_skeleton.left_leg, bone_attr)

        right_leg = met_armature.edit_bones[met_skeleton.right_leg.leg]
        left_leg = met_armature.edit_bones[met_skeleton.left_leg.leg]

        offset = Vector((0.0, self.offset_knee, 0.0))
        for bone in right_leg, left_leg:
            bone.head += offset

        right_knee = met_armature.edit_bones[met_skeleton.right_arm.forearm]
        left_knee = met_armature.edit_bones[met_skeleton.left_arm.forearm]
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

            if 'thumb' not in bone_attr:
                met_bone = met_armature.edit_bones[met_bone_names[0]]
                src_bone = src_armature.bones.get(src_bone_names[0], None)
                if src_bone:
                    palm_bone = met_bone.parent

                    palm_bone.tail = src_bone.head_local
                    hand_bone = palm_bone.parent
                    palm_bone.head = hand_bone.head * 0.75 + src_bone.head_local * 0.25
                    palm_bone.roll = 0

            for met_bone_name, src_bone_name in zip(met_bone_names, src_bone_names):
                met_bone = met_armature.edit_bones[met_bone_name]
                try:
                    src_bone = src_armature.bones[src_bone_name]
                except KeyError:
                    print("source bone not found", src_bone_name)
                    continue

                met_bone.head = src_bone.head_local
                try:
                    met_bone.tail = src_bone.children[0].head_local
                except IndexError:
                    align_to_closer_axis(src_bone, met_bone)

                met_bone.roll = 0.0

                src_z_axis = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.to_3x3()

                inv_rot = met_bone.matrix.to_3x3().inverted()
                trg_z_axis = src_z_axis @ inv_rot
                dot_z = (met_bone.z_axis @ met_bone.matrix.inverted()).dot(trg_z_axis)
                met_bone.roll = dot_z * pi

                offset_fingers = Vector(self.offset_fingers) @ src_bone.matrix_local.to_3x3()
                if met_bone.head.x < 0:  # Right side
                    offset_fingers /= -100
                else:
                    offset_fingers /= 100

                if met_bone.parent.name in met_bone_names and met_bone.children:
                    met_bone.head += offset_fingers
                    met_bone.tail += offset_fingers
                    # met_bone.head += offset/100
                    # met_bone.tail += offset/100

        for bone_attr in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            match_meta_fingers(met_skeleton.right_fingers, src_skeleton.right_fingers, bone_attr)
            match_meta_fingers(met_skeleton.left_fingers, src_skeleton.left_fingers, bone_attr)

        met_armature.edit_bones['spine.003'].tail = met_armature.edit_bones['spine.004'].head
        met_armature.edit_bones['spine.005'].head = (met_armature.edit_bones['spine.004'].head + met_armature.edit_bones['spine.006'].head) / 2

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

            for side in "L", "R":
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

                spine_bone = met_armature.edit_bones['spine']
                pelvis_bone = met_armature.edit_bones['pelvis.' + side]
                pelvis_bone.head = spine_bone.head
                pelvis_bone.tail.z = spine_bone.tail.z

                spine_bone = met_armature.edit_bones['spine.003']
                breast_bone = met_armature.edit_bones['breast.' + side]
                breast_bone.head.z = spine_bone.head.z
                breast_bone.tail.z = spine_bone.head.z

        if self.no_face:
            for bone_name in bone_mapping.rigify_face_bones:
                try:
                    face_bone = met_armature.edit_bones[bone_name]
                except KeyError:
                    continue

                met_armature.edit_bones.remove(face_bone)

        bpy.ops.object.mode_set(mode='POSE')
        if self.assign_metarig:
            met_armature.rigify_target_rig = src_object

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
        scn.frame_start = action_range[0]
        scn.frame_end = action_range[1]

        try:
            bpy.ops.action.view_all()
        except RuntimeError:
            # we are not in the timeline context, we won't set the timeline view
            pass
        return {'FINISHED'}


class MergeHeadTails(bpy.types.Operator):
    """Convert Rigify (0.5) rigs to a Game Friendly hierarchy"""
    bl_idname = "armature.expykit_merge_head_tails"
    bl_label = "Merge Head/Tails"
    bl_description = "Connect head/tails when closer than given max distance"
    bl_options = {'REGISTER', 'UNDO'}

    at_child_head: BoolProperty(
        name="Match at child head",
        description="Bring parent's tail to match child head when possible",
        default=True
    )

    min_distance: FloatProperty(
        name="Distance",
        description="Max Distance for merging",
        default=0.0
    )

    selected_only: BoolProperty(name="Only Selected",
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


class MakeRestPose(bpy.types.Operator):
    """Apply current pose to model and rig"""
    # TODO


class ConvertGameFriendly(bpy.types.Operator):
    """Convert Rigify (0.5) rigs to a Game Friendly hierarchy"""
    bl_idname = "armature.expykit_convert_gamefriendly"
    bl_label = "Rigify Game Friendly"
    bl_description = "Make the rigify deformation bones a one root rig"
    bl_options = {'REGISTER', 'UNDO'}

    keep_backup: BoolProperty(
        name="Backup",
        description="Keep copy of datablock",
        default=True
    )
    rename: StringProperty(
        name="Rename",
        description="Rename rig to 'Armature'",
        default="Armature"
    )
    eye_bones: BoolProperty(
        name="Keep eye bones",
        description="Activate 'deform' for eye bones",
        default=True
    )
    limit_scale: BoolProperty(
        name="Limit Spine Scale",
        description="Limit scale on the spine deform bones",
        default=True
    )
    disable_bendy: BoolProperty(
        name="Disable B-Bones",
        description="Disable Bendy-Bones",
        default=True
    )
    fix_tail: BoolProperty(
        name="Invert Tail",
        description="Reverse the tail direction so that it spawns from hip",
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
                metarig.data.rigify_rig_basename = self.rename
                print("Metarig Base Name", metarig.data.rigify_rig_basename)

        if self.eye_bones:
            # Oddly, changes to use_deform are not kept
            try:
                ob.pose.bones["MCH-eye.L"].bone.use_deform = True
                ob.pose.bones["MCH-eye.R"].bone.use_deform = True
            except KeyError:
                pass

        bpy.ops.object.mode_set(mode='EDIT')
        num_reparents = bone_utils.gamefriendly_hierarchy(ob, fix_tail=self.fix_tail, limit_scale=self.limit_scale)
        bpy.ops.object.mode_set(mode='POSE')

        if self.disable_bendy:
            for bone in ob.data.bones:
                bone.bbone_segments = 1

        self.report({'INFO'}, f'{num_reparents} bones were re-parented')
        return {'FINISHED'}


class ConstrainToArmature(bpy.types.Operator):
    bl_idname = "armature.expykit_constrain_to_armature"
    bl_label = "Bind to Active Armature"
    bl_description = "Constrain bones of selected armatures to active armature"
    bl_options = {'REGISTER', 'UNDO'}

    source: EnumProperty(items=skeleton_types,
                         name="To Bind",
                         default='--')

    skeleton_type: EnumProperty(items=skeleton_types,
                                name="Bind Target",
                                default='--')

    ret_bones_layer: IntProperty(name="Binding-Bones layer",
                                 min=0, max=29, default=24,
                                 description="Armature Layer to use for connection bones")

    match_transform: EnumProperty(items=[
        ('None', "No Matching", "Don't match any transform"),
        ('Bone', "Match Bone Transform", "Match target bones at rest"),
        ('Object', "Match Object Transform", "Match target object transform")
    ],
        name="Match Transform",
        default='None')

    math_look_at: BoolProperty(name="Chain Look At",
                               description="Correct chain direction based on mid limb (Useful for IK)",
                               default=False)

    constrain_root: EnumProperty(items=[
        ('None', "No Root", "Don't constrain root bone"),
        ('Bone', "Bone", "Constrain root to bone"),
        ('Object', "Object", "Constrain root to object")
    ],
        name="Constrain Root",
        default='Bone')

    root_motion_bone: StringProperty(name="Root Motion",
                                     description="Constrain Root bone to Hip motion",
                                     default="")

    root_cp_loc_x: BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=False)
    root_cp_loc_y: BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z: BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x: BoolProperty(name="Use Root Min X", description="Minimum Root X", default=False)
    root_use_loc_min_y: BoolProperty(name="Use Root Min Y", description="Minimum Root Y", default=False)
    root_use_loc_min_z: BoolProperty(name="Use Root Min Z", description="Minimum Root Z", default=True)

    root_loc_min_x: FloatProperty(name="Root Min X", description="Minimum Root X", default=0.0)
    root_loc_min_y: FloatProperty(name="Root Min Y", description="Minimum Root Y", default=0.0)
    root_loc_min_z: FloatProperty(name="Root Min Z", description="Minimum Root Z", default=0.0)

    root_use_loc_max_x: BoolProperty(name="Use Root Max X", description="Maximum Root X", default=False)
    root_use_loc_max_y: BoolProperty(name="Use Root Max Y", description="Maximum Root Y", default=False)
    root_use_loc_max_z: BoolProperty(name="Use Root Max Z", description="Maximum Root Z", default=False)

    root_loc_max_x: FloatProperty(name="Root Max X", description="Maximum Root X", default=0.0)
    root_loc_max_y: FloatProperty(name="Root Max Y", description="Maximum Root Y", default=0.0)
    root_loc_max_z: FloatProperty(name="Root Max Z", description="Maximum Root Z", default=0.0)

    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    check_prefix = BoolProperty(default=False, name="Check Prefix")

    _separator = ":"  # TODO: StringProperty
    _autovars_unset = True
    _constrained_root = None

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

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.split(factor=0.25, align=True)
        row.label(text="To Bind")
        row.prop(self, 'source', text="")

        row = column.split(factor=0.25, align=True)
        row.label(text="Bind Target")
        row.prop(self, 'skeleton_type', text="")

        row = column.split(factor=0.25, align=True)
        row.separator()
        row.prop(self, 'ret_bones_layer')

        row = column.split(factor=0.25, align=True)
        row.label(text="Match Transform")
        row.prop(self, 'match_transform', text='')

        row = column.split(factor=0.25, align=True)
        row.separator()
        row.prop(self, 'math_look_at')

        row = column.split(factor=0.25, align=True)
        row.label(text="Root Animation")
        row.prop(self, 'constrain_root', text="")

        if self.constrain_root != 'None':
            row = column.split(factor=0.25, align=True)
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

    def execute(self, context):
        src_skeleton = skeleton_from_type(self.source)
        trg_skeleton = skeleton_from_type(self.skeleton_type)

        if not src_skeleton:
            return {'FINISHED'}
        if not trg_skeleton:
            return {'FINISHED'}

        bone_names_map = src_skeleton.conversion_map(trg_skeleton)
        deformation_map = src_skeleton.deformation_bone_map

        trg_ob = context.active_object
        # if self._autovars_unset:
        #     # try automatic settings on first executions
        #     if trg_skeleton.root:
        #         self.root_motion_bone = trg_skeleton.root
        #     if src_skeleton.root in trg_ob.data.bones:
        #         self.root_motion_bone = src_skeleton.root
        #
        #     self._autovars_unset = False

        cp_suffix = 'RET'

        prefix = ""
        if self.check_prefix:
            first_bone = trg_ob.data.bones[0]
            if self._separator in first_bone.name:
                prefix = first_bone.name.rsplit(self._separator, 1)[0]
                prefix += self._separator

        for ob in context.selected_objects:
            if ob == trg_ob:
                continue

            look_ats = {}

            if self.constrain_root == 'None':
                try:
                    del bone_names_map[src_skeleton.root]
                except KeyError:
                    pass
                self._constrained_root = None
            elif self.constrain_root == 'Bone':
                bone_names_map[src_skeleton.root] = self.root_motion_bone

            if f'{next(iter(bone_names_map))}_{cp_suffix}' not in trg_ob.data.bones:
                # create Retarget bones
                bpy.ops.object.mode_set(mode='EDIT')
                for src_name, trg_name in bone_names_map.items():
                    if not src_name:
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
                            self.report({'WARNING'}, f"{trg_name} not found in target")
                            continue

                    new_bone = trg_ob.data.edit_bones[new_bone_name]
                    new_bone.parent = new_parent

                    if self.match_transform == 'Bone' and deformation_map:
                        # counter deformation bone transform
                        try:
                            def_bone = ob.data.edit_bones[deformation_map[src_name]]
                        except KeyError:
                            continue
                        try:
                            trg_ed_bone = trg_ob.data.edit_bones[trg_name]
                        except KeyError:
                            continue

                        new_bone.transform(def_bone.matrix.inverted())

                        # even transform
                        new_bone.transform(ob.matrix_world)
                        # counter target transform
                        new_bone.transform(trg_ob.matrix_world.inverted())
                        # bring under trg_bone
                        new_bone.transform(trg_ed_bone.matrix)

                        # orient to TARGET bone
                        trg_bone = trg_ob.data.bones[trg_name]
                        src_x_axis = Vector((0.0, 0.0, 1.0)) @ trg_bone.matrix_local.inverted().to_3x3()

                        # ctrl may have a different orient, in that case we roll them back
                        src_bone = ob.data.edit_bones[src_name]
                        ctrl_offset = src_bone.matrix @ def_bone.matrix.inverted()
                        src_x_axis = ctrl_offset @ src_x_axis
                        src_x_axis.normalize()

                        new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_x_axis)
                    else:
                        src_bone = ob.data.bones[src_name]
                        src_x_axis = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.inverted().to_3x3()
                        src_x_axis.normalize()

                        new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_x_axis)

                        if self.match_transform == 'Object':
                            new_bone.transform(ob.matrix_world)
                            new_bone.transform(trg_ob.matrix_world.inverted())

                    new_bone.layers[self.ret_bones_layer] = True
                    for i, L in enumerate(new_bone.layers):
                        if i == self.ret_bones_layer:
                            continue
                        new_bone.layers[i] = False

                    if self.math_look_at:
                        if src_name == src_skeleton.right_arm_IK.arm:
                            start_bone_name = trg_skeleton.right_arm_IK.forearm
                        elif src_name == src_skeleton.left_arm_IK.arm:
                            start_bone_name = trg_skeleton.left_arm_IK.forearm
                        elif src_name == src_skeleton.right_leg_IK.upleg:
                            start_bone_name = trg_skeleton.right_leg_IK.leg
                        elif src_name == src_skeleton.left_leg_IK.upleg:
                            start_bone_name = trg_skeleton.left_leg_IK.leg
                        else:
                            start_bone_name = ""

                        if start_bone_name:
                            start_bone = trg_ob.data.edit_bones[start_bone_name]

                            look_bone = trg_ob.data.edit_bones.new(start_bone_name + '_LOOK')
                            look_bone.head = start_bone.head
                            look_bone.tail = 2 * start_bone.head - start_bone.tail
                            look_bone.parent = start_bone

                            look_ats[src_name] = look_bone.name

                            look_bone.layers[self.ret_bones_layer] = True
                            for i, L in enumerate(look_bone.layers):
                                if i == self.ret_bones_layer:
                                    continue
                                look_bone.layers[i] = False

            bpy.ops.object.mode_set(mode='POSE')

            for src_name, trg_name in look_ats.items():
                ret_bone = trg_ob.pose.bones[f'{src_name}_{cp_suffix}']
                constr = ret_bone.constraints.new(type='LOCKED_TRACK')

                constr.head_tail = 1.0
                constr.target = trg_ob
                constr.subtarget = trg_name
                constr.lock_axis = 'LOCK_Y'
                constr.track_axis = 'TRACK_NEGATIVE_Z'

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

                if not src_pbone.constraints:
                    for constr_type in 'COPY_ROTATION', 'COPY_LOCATION':
                        constr = src_pbone.constraints.new(type=constr_type)
                        constr.target = trg_ob

                        subtarget_name = f'{src_name}_{cp_suffix}'
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


def validate_actions(act, path_resolve):
    for fc in act.fcurves:
        data_path = fc.data_path
        if fc.array_index:
            data_path = data_path + "[%d]" % fc.array_index
        try:
            path_resolve(data_path)
        except ValueError:
            return False  # Invalid.
    return True  # Valid.


class BakeConstrainedActions(bpy.types.Operator):
    bl_idname = "armature.expykit_bake_constrained_actions"
    bl_label = "Bake Constrained Actions"
    bl_description = "Bake Actions constrained from another Armature"
    bl_options = {'REGISTER', 'UNDO'}

    skeleton_type: EnumProperty(items=skeleton_types,
                                name="Skeleton Type to Bake",
                                default='--')

    clear_users_old: BoolProperty(name="Clear original Action Users",
                                  default=True)

    fake_user_new: BoolProperty(name="Save New Action User",
                                default=True)

    do_bake: BoolProperty(name="Bake and Exit", description="Constrain to the new offset and exit",
                          default=False, options={'SKIP_SAVE'})

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

    def execute(self, context):
        if not self.do_bake:
            return {'FINISHED'}

        src_skeleton = skeleton_from_type(self.skeleton_type)
        if not src_skeleton:
            return {'FINISHED'}

        bone_names = list(bn for bn in src_skeleton.bone_names() if bn)
        trg_ob = context.active_object
        trg_ob.select_set(False)
        path_resolve = trg_ob.path_resolve

        for ob in context.selected_objects:
            if ob == trg_ob:
                # should not happen, but anyway
                continue

            for bone in ob.data.bones:
                bone.select = bone.name in bone_names

            for action in bpy.data.actions:
                if not validate_actions(action, path_resolve):
                    continue

                trg_ob.animation_data.action = action
                fr_start, fr_end = action.frame_range
                bpy.ops.nla.bake(frame_start=fr_start, frame_end=fr_end,
                                 bake_types={'POSE'}, only_selected=True,
                                 visual_keying=True, clear_constraints=False)

                ob.animation_data.action.use_fake_user = self.fake_user_new

                if self.clear_users_old:
                    action.user_clear()

            # delete Constraints
            for bone_name in bone_names:
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


def add_loc_rot_key(bone, frame, options):
    add_loc_key(bone, frame, options)

    bone.keyframe_insert('rotation_quaternion', index=0, frame=frame, options=options)
    bone.keyframe_insert('rotation_quaternion', index=1, frame=frame, options=options)
    bone.keyframe_insert('rotation_quaternion', index=2, frame=frame, options=options)
    bone.keyframe_insert('rotation_quaternion', index=3, frame=frame, options=options)


class AddRootMotion(bpy.types.Operator):
    bl_idname = "armature.expykit_add_rootmotion"
    bl_label = "Hips to Root Motion"
    bl_description = "Bring Hips Motion to Root Bone"
    bl_options = {'REGISTER', 'UNDO'}

    rig_type: EnumProperty(items=skeleton_types,
                           name="Rig Type",
                           default='--')

    new_anim_suffix: StringProperty(name="Suffix",
                                    default="_RM",
                                    description="Suffix of the duplicate animation, leave empty to overwrite")

    keep_offset: BoolProperty(name="Keep Offset", default=True)
    offset_type: EnumProperty(items=[
        ('start', "Action Start", "Offset to Start Pose"),
        ('end', "Action End", "Offset to Match End Pose"),
        ('rest', "Rest Pose", "Offset to Match Rest Pose")],
                              name="Offset",
                              default='start')

    # TODO: offset_type start/end: matches first frame at start, last frame at end, weighted average inbetween

    root_cp_loc_x: BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=False)
    root_cp_loc_y: BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z: BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x: BoolProperty(name="Use Root Min X", description="Minimum Root X", default=False)
    root_use_loc_min_y: BoolProperty(name="Use Root Min Y", description="Minimum Root Y", default=False)
    root_use_loc_min_z: BoolProperty(name="Use Root Min Z", description="Minimum Root Z", default=True)

    root_loc_min_x: FloatProperty(name="Root Min X", description="Minimum Root X", default=0.0)
    root_loc_min_y: FloatProperty(name="Root Min Y", description="Minimum Root Y", default=0.0)
    root_loc_min_z: FloatProperty(name="Root Min Z", description="Minimum Root Z", default=0.0)

    root_use_loc_max_x: BoolProperty(name="Use Root Max X", description="Maximum Root X", default=False)
    root_use_loc_max_y: BoolProperty(name="Use Root Max Y", description="Maximum Root Y", default=False)
    root_use_loc_max_z: BoolProperty(name="Use Root Max Z", description="Maximum Root Z", default=False)

    root_loc_max_x: FloatProperty(name="Root Max X", description="Maximum Root X", default=0.0)
    root_loc_max_y: FloatProperty(name="Root Max Y", description="Maximum Root Y", default=0.0)
    root_loc_max_z: FloatProperty(name="Root Max Z", description="Maximum Root Z", default=0.0)

    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=True)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=True)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    _armature = None

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

        row = column.split(factor=0.25, align=True)
        row.label(text="Rig Type")
        row.prop(self, 'rig_type', text="")

        row = column.split(factor=0.25, align=True)
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

    def execute(self, context):
        if not self.rig_type:
            return {'FINISHED'}

        if self.rig_type == '--':
            return {'FINISHED'}

        self._armature = context.active_object
        if self.new_anim_suffix:
            action_dupli = self._armature.animation_data.action.copy()

            action_name = self._armature.animation_data.action.name
            action_dupli.name = f'{action_name}{self.new_anim_suffix}'
            action_dupli.use_fake_user = self._armature.animation_data.action.use_fake_user
            self._armature.animation_data.action = action_dupli

        rig_map = skeleton_from_type(self.rig_type)
        self.action_offs(rig_map.root, rig_map.spine.hips)

        return {'FINISHED'}

    def action_offs(self, root_bone_name, hips_bone_name):
        action = self._armature.animation_data.action
        start, end = action.frame_range
        start = int(start)
        end = int(end)
        current = bpy.context.scene.frame_current

        hip_bone = self._armature.pose.bones[hips_bone_name]

        if self.keep_offset and self.offset_type == 'end':
            bpy.context.scene.frame_set(end)
            end_mat = hip_bone.matrix.copy()
        else:
            end_mat = Matrix()

        bpy.context.scene.frame_set(start)
        start_mat = hip_bone.matrix.copy()
        start_mat_inverse = start_mat.inverted()
        if self.keep_offset:
            if self.offset_type == 'rest':
                offset_mat = self._armature.data.bones[hip_bone.name].matrix_local.inverted()
            elif self.offset_type == 'start':
                offset_mat = start_mat_inverse
            elif self.offset_type == 'end':
                offset_mat = end_mat.inverted()
        else:
            offset_mat = Matrix()

        try:
            root_bone = self._armature.pose.bones[root_bone_name]
        except (TypeError, KeyError):
            self.report({'WARNING'}, f"{root_bone_name} not found in target")
            return

        skeleton = skeleton_from_type(self.rig_type)

        # TODO: check controls with animation curves instead

        rig_bones = [self._armature.pose.bones[b_name] for b_name in skeleton.bone_names() if b_name and b_name != root_bone_name]
        floating_bones = list([bone for bone in rig_bones if is_bone_floating(bone, hips_bone_name)])

        rootmo_transfs = []
        hip_bone_transfs = []
        all_floating_mats = []
        for frame_num in range(start, end + 1):
            bpy.context.scene.frame_set(frame_num)

            all_floating_mats.append(list([b.matrix.copy() for b in floating_bones]))
            hip_bone_transfs.append(hip_bone.matrix.copy())
            rootmo_transfs.append(hip_bone.matrix @ start_mat_inverse)

        bpy.context.scene.frame_set(start)
        keyframe_options = {'INSERTKEY_VISUAL', 'INSERTKEY_CYCLE_AWARE'}
        add_loc_rot_key(root_bone, start, keyframe_options)

        for i, frame_num in enumerate(range(start, end + 1)):
            bpy.context.scene.frame_set(frame_num)

            rootmo_transf = hip_bone_transfs[i] @ offset_mat
            if self.root_cp_loc_x:
                if self.root_use_loc_min_x:
                    rootmo_transf[0][3] = max(rootmo_transf[0][3], self.root_loc_min_x)
                if self.root_use_loc_max_x:
                    rootmo_transf[0][3] = min(rootmo_transf[0][3], self.root_loc_max_x)
            else:
                rootmo_transf[0][3] = root_bone.matrix[0][3]
            if self.root_cp_loc_y:
                if self.root_use_loc_min_y:
                    rootmo_transf[1][3] = max(rootmo_transf[1][3], self.root_loc_min_y)
                if self.root_use_loc_max_y:
                    rootmo_transf[1][3] = min(rootmo_transf[1][3], self.root_loc_max_y)
            else:
                rootmo_transf[1][3] = root_bone.matrix[1][3]
            if self.root_cp_loc_z:
                if self.root_use_loc_min_z:
                    rootmo_transf[2][3] = max(rootmo_transf[2][3], self.root_loc_min_z)
                if self.root_use_loc_max_z:
                    rootmo_transf[2][3] = min(rootmo_transf[2][3], self.root_loc_max_z)
            else:
                rootmo_transf[2][3] = root_bone.matrix[2][3]

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
                    root_transp = root_bone.matrix.transposed()

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

            root_bone.matrix = rootmo_transf
            add_loc_rot_key(root_bone, frame_num, keyframe_options)

        for i, frame_num in enumerate(range(start, end + 1)):
            bpy.context.scene.frame_set(frame_num)

            floating_mats = all_floating_mats[i]
            for bone, mat in zip(floating_bones, floating_mats):
                bone.matrix = mat

                add_loc_rot_key(bone, frame_num, set())

        bpy.context.scene.frame_set(current)


class ActionNameCandidates(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name Candidate", default="")


class RenameActionsFromFbxFiles(bpy.types.Operator, ImportHelper):
    bl_idname = "armature.expykit_rename_actions_fbx"
    bl_label = "Rename Actions from fbx data..."
    bl_description = "Rename Actions from candidate fbx files"
    bl_options = {'PRESET', 'UNDO'}

    directory: StringProperty()

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    starts_with: StringProperty(default="Action", name="Starts With")

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
            if self.starts_with and not action.name.startswith(self.starts_with):
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
            if isinstance(fbx_match, typing.List):
                for name in fbx_match:
                    entry = action.expykit_name_candidates.add()
                    entry.name = name
                continue

            action.name = fbx_match

        return {'FINISHED'}
