import importlib
from bpy.utils import register_class, unregister_class
from . import bone_gizmo_properties
from . import bone_gizmo
from . import bone_gizmo_ui
from . import bone_gizmo_group
from . import operators

from importlib import reload
reload(bone_gizmo)

from bpy.props import FloatProperty, IntProperty
from bpy.types import AddonPreferences

bl_info = {
	'name' : "Bone Gizmos"
	,'author': "Demeter Dzadik"
	,'version' : (0, 0, 1)
	,'blender' : (3, 0, 0)
	,'description' : "Bone Gizmos for better armature interaction"
	,'location': "Properties->Bone->Viewport Display->Custom Gizmo"
	,'category': 'Rigging'
	# ,'doc_url' : "https://gitlab.com/blender/CloudRig/"
}

modules = (
	bone_gizmo_properties,
	bone_gizmo,
	bone_gizmo_ui,
	bone_gizmo_group,
	operators,
)

class BoneGizmoPreferences(AddonPreferences):
	bl_idname = __package__.split('.', 1)[0]

	mesh_alpha: FloatProperty(
		name = "Mesh Gizmo Opacity"
		,description = "Opacity of unselected gizmos when they are defined by a vertex group or face map"
		,min = 0.0
		,max = 1.0
		,default = 0.0
		,subtype = 'FACTOR'
	)
	widget_alpha: FloatProperty(
		name = "Widget Gizmo Opacity"
		,description = "Opacity of unselected gizmos when they are NOT defined by a vertex group or face map"
		,min = 0.1
		,max = 1.0
		,default = 0.5
		,subtype = 'FACTOR'
	)
	delta_alpha_select: FloatProperty(
		name = "Gizmo Selected Opacity Delta"
		,description = "Added Mesh Gizmo opacity when selected"
		,min = 0.0
		,max = 0.5
		,default = 0.2
		,subtype = 'FACTOR'
	)
	delta_alpha_highlight: FloatProperty(
		name = "Gizmo Highlighted Opacity Delta"
		,description = "Added Mesh Gizmo opacity when highlighted"
		,min = 0.0
		,max = 0.5
		,default = 0.1
		,subtype = 'FACTOR'
	)

	line_width: IntProperty(
		name		 = "Line Width"
		,description = "Thickness of the drawn lines in pixels"
		,min		 = 1
		,max		 = 10
		,default	 = 1
	)

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True

		layout = layout.column(align=True)
		layout.prop(self, 'line_width', slider=True)
		layout.label(text="Gizmo Opacity")
		layout.prop(self, 'mesh_alpha', text="Mesh")
		layout.prop(self, 'widget_alpha', text="Widget")
		layout.prop(self, 'delta_alpha_select', text="Delta Selected")
		layout.prop(self, 'delta_alpha_highlight', text="Delta Highlighted")

def register():
	register_class(BoneGizmoPreferences)
	for m in modules:
		importlib.reload(m)
		if hasattr(m, 'registry'):
			for c in m.registry:
				register_class(c)
		if hasattr(m, 'register'):
			m.register()

def unregister():
	unregister_class(BoneGizmoPreferences)
	for m in reversed(modules):
		if hasattr(m, 'unregister'):
			m.unregister()
		if hasattr(m, 'registry'):
			for c in m.registry:
				unregister_class(c)