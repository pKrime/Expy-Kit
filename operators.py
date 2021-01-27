import bpy
from bpy.props import BoolProperty
from bpy.props import EnumProperty

status_types = (
    ('enable', "Enable", "Enable All Constraints"),
    ('disable', "Disable", "Disable All Constraints"),
    ('remove', "Remove", "Remove All Constraints")
)


skeleton_types = (
    ('unreal', "Unreal", "UE4 Skeleton"),
    ('rigify', "Rigify", "Rigify Skeleton"),
    ('mixamo', "Mixamo", "Mixamo Skeleton"),
    ('--', "--", "None")
)


class ConstraintStatus(bpy.types.Operator):
    """Disable/Enable bone constraints."""
    bl_idname = "object.charetee_set_constraints_status"
    bl_label = "Enable or disable all constraints"
    bl_options = {'REGISTER', 'UNDO'}

    set_status: EnumProperty(items=status_types,
                              name="Set Status",
                              default='enable')

    selected_only: BoolProperty(name="Only Selected",
                                default=False)

    @classmethod
    def poll(cls, context):
        return all((context.object, context.mode == 'POSE', context.object.type == 'ARMATURE'))

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


class RevertDotBoneNames(bpy.types.Operator):
    """Reverts dots in bones that have renamed by Unreal Engine"""
    bl_idname = "object.charetee_dot_bone_names"
    bl_label = "revert dot naming (from UE4 renaming)"
    bl_options = {'REGISTER', 'UNDO'}

    sideletters_only: BoolProperty(name="Only Side Letters",
                                   description="i.e. '_L' to '.L'",
                                   default=True)

    selected_only: BoolProperty(name="Only Selected",
                                default=False)

    @classmethod
    def poll(cls, context):
        return all((context.object, context.mode == 'POSE', context.object.type == 'ARMATURE'))

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
    bl_idname = "object.charetee_dot_bone_names"
    bl_label = "Convert Rig Naming between different standards"
    bl_options = {'REGISTER', 'UNDO'}

    source: EnumProperty(items=skeleton_types,
                         name="Source Skeleton Type",
                         default='--')

    target: EnumProperty(items=skeleton_types,
                         name="Target Skeleton Type",
                         default='--')

    @classmethod
    def poll(cls, context):
        return all((context.object, context.mode == 'POSE', context.object.type == 'ARMATURE'))

    def execute(self, context):
        # TODO
        return {'FINISHED'}


class UpdateMetarig(bpy.types.Operator):
    """Match current rig pose to metarig"""
    # TODO


class ActionToRange(bpy.types.Operator):
    """Set Playback range to current action Start/End"""
    # TODO
