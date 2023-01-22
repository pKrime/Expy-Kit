import bpy
from bpy.utils import flip_name
from bpy.props import BoolProperty

def copy_gizmo_properties(from_pb, to_pb):
    to_pb.enable_bone_gizmo = from_pb.enable_bone_gizmo
    gizmo_properties_class = bpy.types.PropertyGroup.bl_rna_get_subclass_py('BoneGizmoProperties')
    for key in gizmo_properties_class.__annotations__.keys():
        value = getattr(from_pb.bone_gizmo, key)
        setattr(to_pb.bone_gizmo, key, value)

class POSE_OT_Symmetrize_Bone_Gizmos(bpy.types.Operator):
    """Symmetrize bone gizmo settings of selected bones"""
    bl_idname = "pose.symmetrize_bone_gizmos"
    bl_label = "Symmetrize Bone Gizmos"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_pose_bones

    def execute(self, context):
        pbs = context.selected_pose_bones
        
        skipped = 0
        symmetrized = 0
        for pb in pbs:
            flip_pb = context.object.pose.bones.get(flip_name(pb.name))
            if flip_pb in context.selected_pose_bones:
                skipped += 1
                continue

            copy_gizmo_properties(pb, flip_pb)
            flip_pb.bone_gizmo.vertex_group_name = flip_name(flip_pb.bone_gizmo.vertex_group_name)
            flip_pb.bone_gizmo.face_map_name = flip_name(flip_pb.bone_gizmo.face_map_name)
            symmetrized += 1
        
        if skipped:
            self.report({'INFO'}, f"Symmetrized {symmetrized} gizmos. {skipped} were skipped due to being selected on both sides.")
        else:
            self.report({'INFO'}, f"Symmetrized {symmetrized} gizmos.")

        return {'FINISHED'}

class POSE_OT_Edit_Gizmo_Mask(bpy.types.Operator):
    """Enter edit mode to edit the mask of the active bone's gizmo"""
    bl_idname = "pose.edit_gizmo_mask"
    bl_label = "Edit Gizmo Mask"
    bl_options = {'REGISTER', 'UNDO'}

    create_new: BoolProperty(
        name = "Create New Mask"
        ,description = "Whether to create and assign a brand new vertex group or face map when entering edit mode"
        ,default = False
    )

    @classmethod
    def poll(cls, context):
        pb = context.active_pose_bone
        if not pb:
            return
        bg = pb.bone_gizmo
        return bg.shape_object

    def execute(self, context):
        pb = context.active_pose_bone
        bg = pb.bone_gizmo
        shape_object = pb.bone_gizmo.shape_object

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = shape_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='DESELECT')

        if bg.use_face_map:
            if self.create_new:
                fm = shape_object.face_maps.new(name="FM_"+pb.name)
                bg.face_map_name = fm.name
            else:
                shape_object.face_maps.active_index = shape_object.face_maps.find(bg.face_map_name)
            bpy.ops.object.face_map_select()
        else:
            if self.create_new:
                fm = shape_object.vertex_groups.new(name="FM_"+pb.name)
                bg.vertex_group_name = fm.name
            else:
                shape_object.vertex_groups.active_index = shape_object.vertex_groups.find(bg.vertex_group_name)
            bpy.ops.object.vertex_group_select()

        return {'FINISHED'}

class VIEW3D_MT_bone_gizmos(bpy.types.Menu):
    bl_label = "Bone Gizmos"
    bl_idname = "VIEW3D_MT_bone_gizmos"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.operator('pose.restart_gizmos', icon='FILE_REFRESH')
        layout.separator()
        layout.operator(POSE_OT_Symmetrize_Bone_Gizmos.bl_idname, icon='MOD_MIRROR')
        layout.separator()
        row = layout.row()
        bg = context.active_pose_bone.bone_gizmo
        row.active = bool((bg.use_face_map and bg.face_map_name) or bg.vertex_group_name)
        row.operator(POSE_OT_Edit_Gizmo_Mask.bl_idname, icon='FACE_MAPS').create_new=False
        layout.operator(POSE_OT_Edit_Gizmo_Mask.bl_idname, text="Create Gizmo Mask", icon='MOD_SOLIDIFY').create_new=True

def draw_gizmo_menu(self, context):
    if context.active_pose_bone and context.active_pose_bone.enable_bone_gizmo:
        self.layout.menu("VIEW3D_MT_bone_gizmos", text="Gizmo")

registry = [
    POSE_OT_Symmetrize_Bone_Gizmos,
    POSE_OT_Edit_Gizmo_Mask,
    VIEW3D_MT_bone_gizmos,
]

def register():
    bpy.types.VIEW3D_MT_editor_menus.append(draw_gizmo_menu)

def unregister():
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_gizmo_menu)
