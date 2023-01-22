# What are Bone Gizmos?
This add-on is a prototype for a potential future Mesh Gizmos feature in Blender. See [this](https://developer.blender.org/T92218) task for more details.

# Using Bone Gizmos
The UI for Bone Gizmos can be found under Properties Editor->Bone->Viewport Display->Custom Gimzo. You need to be in pose mode and have an active bone. You just need to select a mesh and optionally, a vertex group or face map that the gizmo should be bound to.

### Rigger UX
- Enable Custom Gizmo on the bone. Gizmos are not mutually exclusive with Custom Shapes. You should either assign an empty object as the Custom Shape, or simply disable the Bones overlay.
- Select an object. Until a vertex group or face map is selected, the whole object will be used. In this case, the Custom Shape Offset values will affect the gizmo. If you do select a face map or vertex group, the offset will not be used.
- Assign default interaction behaviour for when the animator click&drags the gizmo: None, Translate, Rotate, Scale.
    The purpose of this setting is to make the most common way of interacting with an individual bone as fast as possible, but it is NOT to restrict the bone to only that method of interaction. This is different from bone transformation locks. This can actually be used **instead of** transformation locks, because they give the animator a **suggestion** without restricting them.
    - None: Just select the gizmo when clicked. Dragging will do nothing.
    - Translate & Scale: Optionally locked to one or two axes (Until you press G,R,S or X,Y,Z).
    - Rotate: Along View, Trackball, or along the bone's local X, Y, or Z

- **Colors**: By default, the gizmo's color is determined by the bone group "normal/selected" colors. Although, mesh gizmos are invisible until hovered or selected, unless the default opacity is changed in the add-on preferences, since by default it is 0.  
- Custom operators can be hooked up to each gizmo: The provided operator will be executed when the gizmo is clicked. This allows automatic IK/FK switching and snapping to happen when certain gizmos are interacted with. There's no UI for providing the operator's name and arguments. Instead, you have to feed all that data into a custom property, stored on the rig data. See [this](https://developer.blender.org/F12799095) example file.

### Animator UX

- Gizmos are only visible for armatures which you are in pose mode on.
- Clicking the gizmo always selects the bone, and starts the default transformation, if one is assigned in the rig. 
- Shift+Clicking toggles the selection.
