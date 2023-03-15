import bpy
from typing import Dict, Tuple, List
from bpy.types import GizmoGroup, Gizmo, Object, PoseBone, Operator
from bpy.app.handlers import persistent

### MSGBUS FUNCTIONS ###
# The Gizmo API doesn't provide the necessary callbacks to do careful partial
# updates of gizmo data based on what properties are modified.
# However, the msgbus system allows us to create our own connections between
# Blender properties and the functions that should be called when those properties
# change.

# msgbus system needs an arbitrary python object as storage, so here it is.
gizmo_msgbus = object()

def mb_ensure_gizmos_on_active_armature(gizmo_group):
	"""Ensure gizmos exist for all PoseBones that need them.""" 
	context = bpy.context
	obj = context.object

	for pose_bone in obj.pose.bones:
		try:
			if pose_bone.enable_bone_gizmo and pose_bone.name not in gizmo_group.widgets:
				gizmo = gizmo_group.create_gizmo(context, pose_bone)
			elif not pose_bone.bone_gizmo.shape_object:
				for bone_name, gizmo in gizmo_group.widgets.items():
					if bone_name == pose_bone.name:
						gizmo.custom_shape = None

		except ReferenceError:
			# StructRNA of type BoneGizmoGroup has been removed.
			# TODO: Not sure when this happens.
			pass

def mb_refresh_all_gizmo_colors(gizmo_group):
	"""Keep Gizmo colors in sync with addon preferences."""
	context = bpy.context
	addon_prefs = context.preferences.addons[__package__.split('.', 1)[0]].preferences

	try:
		for bone_name, gizmo in gizmo_group.widgets.items():
			gizmo.refresh_colors(context)
	except ReferenceError:
		# StructRNA of type BoneGizmoGroup has been removed.
		# TODO: Not sure when this happens.
		pass

def mb_refresh_single_gizmo(gizmo_group, bone_name):
	"""Refresh Gizmo behaviour settings. This should be called when the user changes
	the Gizmo settings in the Properties editor.
	"""
	if not gizmo_group:
		return
	context = bpy.context
	pose_bone = context.object.pose.bones.get(bone_name)
	gizmo_props = pose_bone.bone_gizmo
	try:
		gizmo = gizmo_group.widgets[bone_name]
	except:
		return
	
	if gizmo_props.operator != 'None':
		op_name = gizmo_props.operator
		if op_name == 'transform.rotate' and gizmo_props.rotation_mode == 'TRACKBALL':
			op_name = 'transform.trackball'

		op = gizmo.target_set_operator(op_name)

		if op_name == 'transform.rotate' and gizmo_props.rotation_mode in 'XYZ':
			op.orient_type = 'LOCAL'
			op.constraint_axis = [axis == gizmo_props.rotation_mode for axis in 'XYZ']

		if op_name in ['transform.translate', 'transform.resize']:
			op.constraint_axis = gizmo_props.transform_axes

	gizmo.init_properties(context)

def mb_refresh_single_gizmo_shape(gizmo_group, bone_name):
	"""Re-calculate a gizmo's vertex indicies. This is expensive, so it should
	be called sparingly."""
	context = bpy.context

	if not context.object or context.object.type != 'ARMATURE' or context.object.mode != 'POSE':
		return
	try:
		gizmo = gizmo_group.widgets[bone_name]
		gizmo.init_shape(context)
	except:
		pass

class BoneGizmoGroup(GizmoGroup):
	"""This single GizmoGroup manages all bone gizmos for all rigs."""	# TODO: Currently this will have issues when there are two rigs with similar bone names. Rig object names should be included when identifying widgets.
	bl_idname = "OBJECT_GGT_bone_gizmo"
	bl_label = "Bone Gizmos"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'WINDOW'
	bl_options = {
		'3D'				# Lets Gizmos use the 'draw_select' function to draw into a selection pass.
		,'PERSISTENT'
		,'SHOW_MODAL_ALL'	# TODO what is this
		,'DEPTH_3D'			# Provides occlusion but results in Z-fighting when gizmo geometry isn't offset from the source mesh.
		,'SELECT'			# I thought this would make Gizmo.select do something but doesn't seem that way
		,'SCALE'			# This makes all gizmos' scale relative to the world rather than the camera, so we don't need to set use_draw_scale on each Gizmo. (And that option does nothing because of this one)
	}

	@classmethod
	def poll(cls, context):
		return context.scene.bone_gizmos_enabled and context.object \
			and context.object.type == 'ARMATURE' and context.object.mode=='POSE'

	def setup(self, context):
		"""Runs when this GizmoGroup is created, I think.
		Executed by Blender on launch, and for some reason
		also when changing bone group colors. WHAT!?"""
		self.widgets = {}
		mb_ensure_gizmos_on_active_armature(self)

		# Hook up the addon preferences to color refresh function
		# using msgbus system.
		addon_prefs = context.preferences.addons[__package__.split('.', 1)[0]]
		global gizmo_msgbus
		bpy.msgbus.subscribe_rna(
			key		= addon_prefs.path_resolve('preferences', False)
			,owner	= gizmo_msgbus
			,args	= (self,)
			,notify	= mb_refresh_all_gizmo_colors
		)

		# Hook up Custom Gizmo checkbox to a function that will ensure that 
		# a Gizmo instance actually exists for each bone that needs one.
		bpy.msgbus.subscribe_rna(
			key		= (bpy.types.PoseBone, "enable_bone_gizmo")
			,owner	= gizmo_msgbus
			,args	= (self,)
			,notify	= mb_ensure_gizmos_on_active_armature
		)

	def create_gizmo(self, context, pose_bone) -> Gizmo:
		"""Add a gizmo to this GizmoGroup based on user-defined properties."""
		gizmo_props = pose_bone.bone_gizmo

		if not pose_bone.enable_bone_gizmo:
			return

		gizmo = self.gizmos.new('GIZMO_GT_bone_gizmo')
		gizmo.bone_name = pose_bone.name

		# Hook up gizmo properties (the ones that can be customized by user)
		# to the gizmo refresh functions, using msgbus system.
		global gizmo_msgbus
		bpy.msgbus.subscribe_rna(
			key		= gizmo_props
			,owner	= gizmo_msgbus
			,args	= (self, gizmo.bone_name)
			,notify	= mb_refresh_single_gizmo
		)

		for prop_name in ['shape_object', 'vertex_group_name', 'face_map_name', 'use_face_map']:
			bpy.msgbus.subscribe_rna(
				key		= gizmo_props.path_resolve(prop_name, False)
				,owner	= gizmo_msgbus
				,args	= (self, gizmo.bone_name)
				,notify	= mb_refresh_single_gizmo_shape
			)

		self.widgets[pose_bone.name] = gizmo
		mb_refresh_single_gizmo(self, pose_bone.name)
		mb_refresh_single_gizmo_shape(self, pose_bone.name)

		return gizmo

	def refresh(self, context):
		"""This is a Gizmo API function, called by Blender on what seems to be
		depsgraph updates and frame changes.
		Refresh all visible gizmos that use vertex group masking.
		This should be done whenever a bone position changes.
		This should be kept performant!
		"""
		dg = context.evaluated_depsgraph_get()
		eval_meshes = {}

		for bonename, gizmo in self.widgets.items():
			pb = gizmo.get_pose_bone(context)

			if not gizmo or not gizmo.is_using_vgroup(context) or not gizmo.poll(context):
				continue

			obj = pb.bone_gizmo.shape_object
			if obj.name in eval_meshes:
				eval_mesh = eval_meshes[obj.name]
			else:
				eval_meshes[obj.name] = eval_mesh = obj.evaluated_get(dg).to_mesh()
				eval_mesh.calc_loop_triangles()
			try:
				gizmo.refresh_shape_vgroup(context, eval_mesh)
			except ReferenceError:
				# For some reason sometimes it complains that StructRNA of the Mesh has been removed. I don't get why.
				pass

class BONEGIZMO_OT_RestartGizmoGroup(Operator):
	"""Re-initialize all gizmos. Needed when the gizmo shape objects are modified, since there's no dependency between gizmos and their target shapes"""

	bl_idname = "pose.restart_gizmos"
	bl_label = "Refresh Gizmos"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		bpy.utils.unregister_class(BoneGizmoGroup)
		bpy.utils.register_class(BoneGizmoGroup)

		return {'FINISHED'}

registry = [
	BoneGizmoGroup,
	BONEGIZMO_OT_RestartGizmoGroup
]

def unregister():
	# Unhook everything from msgbus system
	global gizmo_msgbus
	bpy.msgbus.clear_by_owner(gizmo_msgbus)