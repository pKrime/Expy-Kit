import bpy
from bpy.types import Object, Scene, PropertyGroup
from bpy.props import (
	IntProperty, PointerProperty, BoolProperty,
	FloatVectorProperty, StringProperty, EnumProperty,
	BoolVectorProperty
)

def mesh_contains_vg(ob, vg):
	if ob.type != 'MESH':
		return False
	
	if not vg:
		return True
	
	return vg in ob.vertex_groups


def bone_items(self, context):
	arma = context.object
	if arma is None:
		return
	
	items = [("", "", "")]
	items.extend([(bone.name, bone.name, "") for bone in context.active_bone.children])
	return items


def gizmo_items(self, context):
	arma = context.object
	if arma is None:
		return
	
	items = [("--", "None", "")]
	items.extend([(pb.name, pb.name, "") for pb in context.object.pose.bones if pb.enable_bone_gizmo])
	return items


class BoneGizmoProperties(PropertyGroup):
	operator: EnumProperty(
		name		 = "Operator"
		,description = "Operator to use when click and dragging on the gizmo"
		,items		 = [
			('None', "None", "Only select the bone on click & drag, ignoring the dragging")
			,('transform.translate', "Translate", "Translate the bone on click & drag")
			,('transform.rotate', "Rotate", "Rotate the bone on click & drag")
			,('transform.resize', "Scale", "Scale the bone on click & drag")
		]
		,default	 = 'transform.translate'
	)
	rotation_mode: EnumProperty(
		name		 = "Rotation Mode"
		,description = "How the bone should rotate on initial click & drag interaction"
		,items		 = [
			('VIEW', "View", "Viewing angle dependent rotation,  same as pressing R or using the outer white ring of the rotation gizmo")
			,('TRACKBALL', "Trackball", "Trackball-type rotation, could be useful for eyes")
			,('X', "X", "Rotate along local X axis")
			,('Y', "Y", "Rotate along local Y axis")
			,('Z', "Z", "Rotate along local Z axis")
		]
		,default	 = 'VIEW'
	)
	transform_axes: BoolVectorProperty(
		name		 = "On Axis"
		,description = "Lock transformation along one or more axes on initial click & drag interaction"
		,size		 = 3
	)

	shape_object: PointerProperty(
		name		 = "Shape"
		,type		 = Object
		,description = "Object to use as shape for this gizmo"
		,poll		 = lambda self, object: mesh_contains_vg(object, self.vertex_group_name)
	)
	face_map_name: StringProperty(
		name		 = "Face Map"
		,description = "Face Map to use as shape for this gizmo"
	)
	vertex_group_name: StringProperty(
		name		 = "Vertex Group"
		,description = "Vertex Group to use as shape for this gizmo"
	)
	use_face_map: BoolProperty(
		name		 = "Mesh Mask Type"
		,description = "Toggle between using Face Maps or Vertex Groups as the mesh masking data"	# Currently it seems face maps are just worse vertex groups, but maybe they are faster, or maybe it's good to have them separated.
	)

	associate_action: EnumProperty(
		name="Associated action",
		description="React to Action of associated widget",
		items = [
			('SELECT_ALONG', 'Select', 'Select along associated widget bone'),
			('SELECT_DRAG', 'Drag to Transform', 'Affect Transform with Mouse Drag'),
			('--', 'None', "No associated action")
		],
		default='--'
	)
	associate_transform: EnumProperty(
		name="Associated transform",
		description="Transform from associated widget",
		items = [
			('SCALE', 'Scale', 'Convert Drag to Scale'),
			('ROTATE', 'Rotate', 'Convert Drag to Rotation'),
			('TRANSLATE', 'Translate', 'Convert Drag to Translation'),
			('--', 'None', "No associated transform")
		],
		default='--'
	)
	associate_axis: EnumProperty(
		name="Associate axis",
		items=[
			('X', "X", "X axis"),
			('Y', "Y", "Y axis"),
			('Z', "Z", "Z axis"),
			('W', "W", "W axis (only quat, angle/axis rotation)"),
		],
		default='X'
	)
	modifier_action: EnumProperty(
		name="Modifier Action",
		description="Trigger event with keyboard",
		items=[
			('TOGGLE_LOCK', "Lock/Unlock", "Stop/Reprise moving this bone"),
			('--', 'None', '')
		],
		default='--'
	)
	modifier_key: EnumProperty(
		name="Modifier Key",
		description="Key for triggering action",
		items=[
			("TAB", "Tab", ""),
			("CTRL", "Ctrl", ""),
			("ALT", "alt", ""),
			("--", "None", "")
		],
		default='--'
	)
	modifier_type: EnumProperty(
		name="Modifier Trigger Type",
		description="Modifier Event Type",
		items=[
			("PRESS", "Press", ""),
			("RELEASE", "Release", ""),
			("ANY", "Any", ""),
		],
		default='ANY'
	)

	associate_with: EnumProperty(items=gizmo_items)

	gizmo_color_source: EnumProperty(
		name		 = "Color Source"
		,description = "Where to take Gizmo Color information from"
		,items		 = [
			('GROUP', 'Bone Group', 'Color this Gizmo based on the bone group colors'),
			('UNIQUE', 'Unique', 'Give this gizmo its own individual color')
		]
	)
	color: FloatVectorProperty(
		name		 = "Color"
		,description = "Color of the gizmo when not mouse hovered"
		,subtype	 = 'COLOR'
		,size		 = 3
		,min		 = 0.0
		,max		 = 1.0
		,default	 = (1.0, 0.05, 0.38)
	)

	color_highlight: FloatVectorProperty(
		name		 = "Highlight Color"
		,description = "Color of the gizmo when mouse hovered or selected"
		,subtype	 = 'COLOR'
		,size		 = 3
		,min		 = 0.0
		,max		 = 1.0
		,default	 = (1.0, 0.5, 1.0)
	)

	# This is made redundant by the ability to set the color to fully transparent.
	use_draw_hover: BoolProperty(
		name		 = "Hover Only"
		,description = "Draw the gizmo only when it is being mouse hovered"
		,default	 = False
	)

	# These functionalities sadly don't work when the gizmo uses target_set_operator,
	# which we absolutely need.
	use_draw_modal: BoolProperty(
		name		 = "Draw During Interact"
		,description = "Draw the gizmo during interaction"
		,default	 = True
	)

	use_draw_value: BoolProperty(
		name		 = "Draw Interact Value"
		,description = "Draw values in the top-left corner of the viewport during interaction"
		,default	 = True
	)

	use_draw_cursor: BoolProperty(
		name		 = "Draw Interact Mouse"
		,description = "Draw the mouse cursor during interaction"
		,default	 = True
	)

classes = (
	BoneGizmoProperties,
)
register_cls, unregister_cls = bpy.utils.register_classes_factory(classes)


def register():
	register_cls()

	# This cannot be a part of the PropertyGroup because we need it to be drivable. See T48975.
	bpy.types.PoseBone.enable_bone_gizmo = BoolProperty(
		name		 = "Enable Bone Gizmo"
		,description = "Attach a custom gizmo to this bone"
		,default	 = False
	)
	bpy.types.PoseBone.bone_gizmo = PointerProperty(type=BoneGizmoProperties)

	Scene.bone_gizmos_enabled = BoolProperty(
		name		 = "Bone Gizmos"
		,description = "Globally toggle bone gizmos"
		,default	 = True
	)


def unregister():
	unregister_cls()

	del bpy.types.PoseBone.bone_gizmo
	del Scene.bone_gizmos_enabled
