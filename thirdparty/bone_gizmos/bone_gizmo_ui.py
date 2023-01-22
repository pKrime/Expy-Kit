from bpy.types import Panel, VIEW3D_PT_gizmo_display

class BONEGIZMO_PT_bone_gizmo_settings(Panel):
	"""Panel to draw gizmo settings for the active bone."""
	bl_label = "Custom Gizmo"
	bl_idname = "BONE_PT_CustomGizmo"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_parent_id = "BONE_PT_display"

	@classmethod
	def poll(cls, context):
		ob = context.object
		pb = context.active_pose_bone
		return ob.type == 'ARMATURE' and pb

	def draw_header(self, context):
		pb = context.active_pose_bone
		layout = self.layout
		layout.prop(pb, 'enable_bone_gizmo', text="")

	def draw(self, context):
		overlay_enabled = context.scene.bone_gizmos_enabled
		pb = context.active_pose_bone
		props = pb.bone_gizmo
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False
		layout = layout.column(align=True)

		if not overlay_enabled:
			layout.alert = True
			layout.label(text="Bone Gizmos are disabled in the Viewport Gizmos settings in the 3D View header.")
			return
		layout.enabled = pb.enable_bone_gizmo and overlay_enabled

		bg = pb.bone_group
		usable_bg_col = bg and bg.color_set != 'DEFAULT'
		if usable_bg_col:
			layout.row().prop(props, 'gizmo_color_source', icon='GROUP_BONE', expand=True)
		color_col = layout.column()
		# sub_row = color_col.row(align=True)
		if usable_bg_col and props.gizmo_color_source == 'GROUP':
			color_col.row().prop(bg.colors, 'normal', text="Group Color")
			color_col.row().prop(bg.colors, 'select', text="Group Highlight Color")
		else:
			color_col.row().prop(props, 'color', text="Gizmo Color")
			color_col.row().prop(props, 'color_highlight', text="Gizmo Highlight Color")

		layout.separator()

		layout.row().prop(props, 'operator', expand=True)
		if props.operator == 'transform.rotate':
			layout.row().prop(props, 'rotation_mode', expand=True)
		elif props.operator in ['transform.translate', 'transform.resize']:
			row = layout.row(align=True, heading="Axis")
			row.prop(props, 'transform_axes', index=0, toggle=True, text="X")
			row.prop(props, 'transform_axes', index=1, toggle=True, text="Y")
			row.prop(props, 'transform_axes', index=2, toggle=True, text="Z")

		layout.separator()

		layout.prop(props, 'shape_object')
		if props.shape_object:
			row = layout.row(align=True)
			if props.use_face_map:
				row.prop_search(props, 'face_map_name', props.shape_object, 'face_maps', icon='FACE_MAPS')
				icon = 'FACE_MAPS'
			else:
				row.prop_search(props, 'vertex_group_name', props.shape_object, 'vertex_groups')
				icon = 'GROUP_VERTEX'
			row.prop(props, 'use_face_map', text="", emboss=False, icon=icon)

def VIEW3D_MT_bone_gizmo_global_enable(self, context):
	col = self.layout.column()
	col.label(text="Bone Gizmos")
	col.prop(context.scene, 'bone_gizmos_enabled')

registry = [
	BONEGIZMO_PT_bone_gizmo_settings,
]

def register():
	VIEW3D_PT_gizmo_display.prepend(VIEW3D_MT_bone_gizmo_global_enable)

def unregister():
	VIEW3D_PT_gizmo_display.remove(VIEW3D_MT_bone_gizmo_global_enable)
