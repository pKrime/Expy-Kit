import bpy
from mathutils import Matrix, Vector, Euler
from bpy.types import Gizmo, Object
import numpy as np
import gpu

from .shapes import MeshShape3D

# Let's fucking do it.
is_interacting = False

class MoveBoneGizmo(Gizmo):
	"""In order to avoid re-implementing logic for transforming bones with 
	mouse movements, this gizmo instead binds its offset value to the
	bpy.ops.transform.translate operator, giving us all that behaviour for free.
	(Important behaviours like auto-keying, precision, snapping, axis locking, etc)
	The downside of this is that we can't customize that behaviour very well,
	for example we can't get the gizmo to draw during mouse interaction,
	we can't hide the mouse cursor, etc. Minor sacrifices.
	"""

	bl_idname = "GIZMO_GT_bone_gizmo"
	# The id must be "offset"
	bl_target_properties = (
		{"id": "offset", "type": 'FLOAT', "array_length": 3},
	)

	__slots__ = (
		# This __slots__ thing allows us to use arbitrary Python variable 
		# assignments on instances of this gizmo.
		"bone_name"			# Name of the bone that owns this gizmo.

		,"custom_shape"		# Currently drawn shape, being passed into self.new_custom_shape().
		,"meshshape"		# Cache of vertex indicies. Can fall out of sync if the mesh is modified; Only re-calculated when gizmo properties are changed by user.

		# Gizmos, like bones, have 3 states.
		,"color_selected"
		,"color_unselected"
		,"alpha_selected"
		,"alpha_unselected"
		# The 3rd one is "highlighted". 
		# color_highlight and alpha_highlight are already provided by the API.
		# We currently don't visually distinguish between selected and active gizmos.
	)

	def setup(self):
		"""Called by Blender when the Gizmo is created."""
		self.meshshape = None
		self.custom_shape = None

	def init_shape(self, context):
		"""Should be called by the GizmoGroup, after it assigns the neccessary 
		__slots__ properties to properly initialize this Gizmo."""
		if not self.poll(context):
			return

		props = self.get_props(context)

		if self.is_using_vgroup(context):
			self.load_shape_vertex_group(self.get_shape_object(context), props.vertex_group_name)

			dg = context.evaluated_depsgraph_get()
			ob = self.get_shape_object(context)
			self.refresh_shape_vgroup(context, ob.evaluated_get(dg).to_mesh())

		elif self.is_using_facemap(context):
			# We use the built-in function to draw face maps, so we don't need to do any extra processing.
			pass
		else:
			self.load_shape_entire_object(context)

	def init_properties(self, context):
		props = self.get_props(context)
		self.refresh_colors(context)

	def refresh_colors(self, context):
		prefs = context.preferences.addons[__package__.split('.', 1)[0]].preferences

		self.line_width = prefs.line_width

		props = self.get_props(context)
		if self.is_using_bone_group_colors(context):
			pb = self.get_pose_bone(context)
			self.color_unselected = pb.bone_group.colors.normal[:]
			self.color_selected = pb.bone_group.colors.select[:]
			self.color_highlight = pb.bone_group.colors.select[:]
		else:
			self.color_unselected = props.color[:]
			self.color_selected = props.color_highlight[:]
			self.color_highlight = props.color_highlight[:]

		if self.is_using_facemap(context) or self.is_using_vgroup(context):
			self.alpha_unselected = prefs.mesh_alpha
			self.alpha_selected = prefs.mesh_alpha + prefs.delta_alpha_select
			self.alpha_highlight = min(0.999, self.alpha_selected + prefs.delta_alpha_highlight)
		else:
			self.alpha_unselected = prefs.widget_alpha
			self.alpha_selected = prefs.widget_alpha + prefs.delta_alpha_select
			self.alpha_highlight = min(0.999, self.alpha_selected + prefs.delta_alpha_highlight)

	def poll(self, context):
		"""Whether any gizmo logic should be executed or not. This function is not
		from the API! Call this manually for early exists.
		"""

		global is_interacting
		if is_interacting:
			return False

		pb = self.get_pose_bone(context)
		if not pb or pb.bone.hide: return False
		any_visible_layer = any(bl and al for bl, al in zip(pb.bone.layers[:], pb.id_data.data.layers[:]))
		bone_visible = not pb.bone.hide and any_visible_layer

		ret = self.get_shape_object(context) and bone_visible and pb.enable_bone_gizmo
		return ret

	def load_shape_vertex_group(self, obj, v_grp: str, weight_threshold=0.2):
		"""Update the vertex indicies that the gizmo shape corresponds to when using
		vertex group masking.
		This is very expensive, should only be called on initial Gizmo creation, 
		manual updates, and changing of	gizmo display object or mask group.
		"""
		self.meshshape = MeshShape3D(obj, vertex_groups=[v_grp], weight_threshold=weight_threshold)

	def refresh_shape_vgroup(self, context, eval_mesh):
		"""Update the custom shape based on the stored vertex indices."""
		if not self.meshshape:
			self.init_shape(context)
		draw_style = 'TRIS'
		if len(self.meshshape._indices) < 3:
			draw_style = 'LINES'
		if len(self.meshshape._indices) < 2:
			return
		self.custom_shape = self.new_custom_shape(draw_style, self.meshshape.get_vertices(eval_mesh))
		return True

	def load_shape_entire_object(self, context):
		"""Update the custom shape to an entire object. This is somewhat expensive,
		should only be called when Gizmo display object is changed or mask
		facemap/vgroup is cleared.
		"""
		mesh = self.get_shape_object(context).data
		vertices = np.zeros((len(mesh.vertices), 3), 'f')
		mesh.vertices.foreach_get("co", vertices.ravel())

		if len(mesh.polygons) > 0:
			draw_style = 'TRIS'
			mesh.calc_loop_triangles()
			tris = np.zeros((len(mesh.loop_triangles), 3), 'i')
			mesh.loop_triangles.foreach_get("vertices", tris.ravel())
			custom_shape_verts = vertices[tris].reshape(-1,3)
		else:
			draw_style = 'LINES'
			edges = np.zeros((len(mesh.edges), 2), 'i')
			mesh.edges.foreach_get("vertices", edges.ravel())
			custom_shape_verts = vertices[edges].reshape(-1,3)

		self.custom_shape = self.new_custom_shape(draw_style, custom_shape_verts)

	def draw_shape(self, context, select_id=None):
		"""Shared drawing logic for selection and color.
		We do not pass color here; The C functions read the 
		colors from self.color and self.color_highlight.
		"""

		ob = self.get_shape_object(context)
		props = self.get_props(context)

		face_map = ob.face_maps.get(props.face_map_name)
		if face_map and props.use_face_map:
			self.draw_preset_facemap(ob, face_map.index, select_id=select_id or 0)
		elif self.custom_shape:
			self.draw_custom_shape(self.custom_shape, select_id=select_id)
		else:
			# This can happen if the specified vertex group is empty.
			return

	def draw_shared(self, context, select_id=None):
		if not self.poll(context):
			return
		if not self.get_shape_object(context):
			return
		self.update_basis_and_offset_matrix(context)

		gpu.state.line_width_set(self.line_width)
		gpu.state.blend_set('MULTIPLY')
		self.draw_shape(context, select_id)
		gpu.state.blend_set('NONE')
		gpu.state.line_width_set(1)

	def get_opacity(self, context):
		"""Based factors of whether the bone corresponding to this gizmo 
		is currently selected, and whether the gizmo is being mouse hovered,
		return the opacity value that is expected to be used for drawing this gizmo.
		"""

		prefs = context.preferences.addons[__package__.split('.', 1)[0]].preferences
		is_selected = self.get_pose_bone(context).bone.select
		opacity = prefs.widget_alpha
		if self.is_using_facemap(context) or self.is_using_vgroup(context):
			opacity = prefs.mesh_alpha
		
		if self.is_highlight:
			opacity += prefs.delta_alpha_highlight
		elif is_selected:
			opacity += prefs.delta_alpha_select

		return opacity

	def draw(self, context):
		"""Called by Blender on every viewport update (including mouse moves).
		Drawing functions called at this time will draw into the color pass.
		"""
		if not self.poll(context):
			return
		if self.use_draw_hover and not self.is_highlight:
			return
		if self.get_opacity(context) == 0:
			return

		pb = self.get_pose_bone(context)
		if pb.bone.select:
			self.color = self.color_selected
			self.alpha = min(0.999, self.alpha_selected)	# An alpha value of 1.0 or greater results in glitched drawing.
		else:
			self.color = self.color_unselected
			self.alpha = min(0.999, self.alpha_unselected)

		self.draw_shared(context)

	def draw_select(self, context, select_id):
		"""Called by Blender on every viewport update (including mouse moves).
		Drawing functions called at this time will draw into an invisible pass
		that is used for mouse interaction.
		"""
		if not self.poll(context):
			return
		self.draw_shared(context, select_id)

	def is_using_vgroup(self, context):
		ob = self.get_shape_object(context)
		if not ob: return False
		props = self.get_pose_bone(context).bone_gizmo
		vgroup_exists = props.vertex_group_name in ob.vertex_groups
		ret = ob and not props.use_face_map and vgroup_exists
		return ret

	def is_using_facemap(self, context):
		props = self.get_props(context)
		ob = self.get_shape_object(context)
		if not ob: return False
		return props.use_face_map and props.face_map_name in ob.face_maps

	def is_using_bone_group_colors(self, context):
		pb = self.get_pose_bone(context)
		props = self.get_props(context)
		return pb and pb.bone_group and pb.bone_group.color_set != 'DEFAULT' and props.gizmo_color_source == 'GROUP'

	def get_pose_bone(self, context):
		arm_ob = context.object
		if not arm_ob or arm_ob.type != 'ARMATURE':
			return
		ret = arm_ob.pose.bones.get(self.bone_name)
		return ret

	def get_shape_object(self, context):
		"""Get the shape object selected by the user in the Custom Gizmo panel.
		"""
		pb = self.get_pose_bone(context)
		if not pb: return
		ob = pb.bone_gizmo.shape_object
		if not ob:
			ob = pb.custom_shape 
		return ob

	def get_props(self, context):
		"""Use this context-based getter rather than any direct mean of referencing
		the gizmo properties, because that would result in a crash on undo.
		"""
		pb = self.get_pose_bone(context)
		return pb.bone_gizmo

	def update_basis_and_offset_matrix(self, context):
		"""Set the gizmo matrices self.matrix_basis and self.matrix_offset,
		to position the gizmo correctly."""

		pb = self.get_pose_bone(context)
		armature = context.object

		if self.is_using_facemap(context) or self.is_using_vgroup(context):
			# If there is a face map or vertex group specified:
			# The gizmo should stick strictly to the vertex group or face map of the shape object.
			self.matrix_basis = self.get_shape_object(context).matrix_world.copy()
			self.matrix_offset = Matrix.Identity(4)
		else:
			# If there is NO face map or vertex group specified:
			# The gizmo should function as a replacement for the bone's Custom Shape
			# properties. That means applying the custom shape transformation offsets
			# and using the custom shape transform bone, if there is one specified.
			self.matrix_basis = armature.matrix_world.copy()

			display_bone = pb
			if pb.custom_shape_transform:
				display_bone = pb.custom_shape_transform

			bone_mat = display_bone.matrix.copy()

			trans_mat = Matrix.Translation(pb.custom_shape_translation)

			rot = Euler((pb.custom_shape_rotation_euler.x, pb.custom_shape_rotation_euler.y, pb.custom_shape_rotation_euler.z), 'XYZ')
			rot_mat = rot.to_matrix().to_4x4()

			display_scale = pb.custom_shape_scale_xyz.copy()
			if pb.use_custom_shape_bone_size:
				display_scale *= pb.bone.length

			scale_mat_x = Matrix.Scale(display_scale.x, 4, (1, 0, 0))
			scale_mat_y = Matrix.Scale(display_scale.y, 4, (0, 1, 0))
			scale_mat_z = Matrix.Scale(display_scale.z, 4, (0, 0, 1))
			scale_mat = scale_mat_x @ scale_mat_y @ scale_mat_z

			final_mat = bone_mat @ trans_mat @ rot_mat @ scale_mat

			self.matrix_offset = final_mat

	def invoke(self, context, event):
		armature = context.object
		if not event.shift:
			for pb in armature.pose.bones:
				pb.bone.select = False
		pb = self.get_pose_bone(context)

		if event.shift and pb.bone.select:
			pb.bone.select = False
			return {'FINISHED'}
		if event.shift and not pb.bone.select:
			pb.bone.select = True
			armature.data.bones.active = pb.bone
			return {'FINISHED'}

		global is_interacting
		is_interacting = True

		pb.bone.select = True
		armature.data.bones.active = pb.bone

		# Allow executing an operator on bone interaction,
		# based on data stored in the armatures 'gizmo_interaction' custom property.
		# 	This should be a dictionary structured:
		# 		op_bl_idname : [ ( [list of bone names], {op_kwargs} ) ]
		# Whenever any of the bones from one list of bone names is interacted, 
		# the operator with op_bl_idname is executed, with op_kwargs passed in to it.
		if 'gizmo_interactions' in armature.data:
			interaction_data = armature.data['gizmo_interactions'].to_dict()
			for op_name, op_datas in interaction_data.items():
				op_category, op_name = op_name.split(".")
				op_callable = getattr(getattr(bpy.ops, op_category), op_name)
				for op_data in op_datas:
					bone_names, op_kwargs = op_data
					if pb.name in bone_names:
						op_callable(**op_kwargs)

		return {'RUNNING_MODAL'}

	def exit(self, context, cancel):
		global is_interacting
		is_interacting = False
		return

	def modal(self, context, event, tweak):
		if event.alt:
			pb = self.get_pose_bone(context)
			if event.ctrl:
				spin_name = self.bone_name.replace('_ik', '_spin_ik')
				try:
					spin = context.object.pose.bones[spin_name]
				except KeyError:
					pass
				else:
					mat = pb.matrix.copy()
					eu = spin.rotation_quaternion.to_euler()
					eu[2] += (event.mouse_x - event. mouse_prev_x)/10
					spin.rotation_quaternion = eu.to_quaternion()
					pb.matrix = mat
			else:
				heel_name = self.bone_name.replace('_ik', '_heel_ik')
				try:
					heel = context.object.pose.bones[heel_name]
				except KeyError:
					pass
				else:
					mat = pb.matrix.copy()
					heel.rotation_euler[0] += (event.mouse_x - event. mouse_prev_x)/10
					pb.matrix = mat
		return {'RUNNING_MODAL'}

classes = (
	MoveBoneGizmo,
)

register, unregister = bpy.utils.register_classes_factory(classes)
