# ====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, version 3.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ======================= END GPL LICENSE BLOCK ========================


bl_info = {
    "name": "Expy Kit",
    "version": (0, 2, 1),
    "author": "Paolo Acampora",
    "blender": (2, 90, 0),
    "description": "Tools for Character Rig Conversion",
    "category": "Rigging",
}


import bpy
from . import operators
from . import ui
from . import preferences
from . import properties
from .preferences import ExpyPrefs, ExpyToClipboard

from importlib import reload
reload(operators)
reload(properties)
reload(ui)


def register():
    bpy.utils.register_class(ExpyPrefs)
    bpy.utils.register_class(ExpyToClipboard)
    bpy.utils.register_class(operators.ActionRangeToScene)
    bpy.utils.register_class(operators.ConstraintStatus)
    bpy.utils.register_class(operators.SelectConstrainedControls)
    bpy.utils.register_class(operators.ConvertBoneNaming)
    bpy.utils.register_class(operators.ConvertGameFriendly)
    bpy.utils.register_class(operators.ExtractMetarig)
    bpy.utils.register_class(operators.MergeHeadTails)
    bpy.utils.register_class(operators.RevertDotBoneNames)
    bpy.utils.register_class(operators.ConstrainToArmature)
    bpy.utils.register_class(operators.BakeConstrainedActions)
    bpy.utils.register_class(operators.RenameActionsFromFbxFiles)
    bpy.utils.register_class(operators.CreateTransformOffset)
    bpy.utils.register_class(operators.AddRootMotion)

    bpy.utils.register_class(operators.ActionNameCandidates)
    bpy.utils.register_class(ui.BindingsMenu)
    bpy.utils.register_class(ui.ConvertMenu)
    bpy.utils.register_class(ui.AnimMenu)
    bpy.utils.register_class(ui.ActionRenameSimple)
    bpy.utils.register_class(ui.DATA_PT_expy_buttons)
    bpy.utils.register_class(ui.DATA_PT_expy_retarget)

    bpy.types.VIEW3D_MT_pose_context_menu.append(ui.pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.append(ui.armature_context_options)
    bpy.types.DOPESHEET_HT_header.append(ui.action_header_buttons)

    properties.register_properties()
    bpy.types.Action.expykit_name_candidates = bpy.props.CollectionProperty(type=operators.ActionNameCandidates)


def unregister():
    del bpy.types.Action.expykit_name_candidates

    bpy.types.VIEW3D_MT_pose_context_menu.remove(ui.pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.remove(ui.armature_context_options)
    bpy.types.DOPESHEET_HT_header.remove(ui.action_header_buttons)

    bpy.utils.unregister_class(ui.DATA_PT_expy_buttons)
    bpy.utils.unregister_class(ui.DATA_PT_expy_retarget)
    bpy.utils.unregister_class(ui.ActionRenameSimple)
    bpy.utils.unregister_class(ui.BindingsMenu)
    bpy.utils.unregister_class(ui.ConvertMenu)
    bpy.utils.unregister_class(ui.AnimMenu)
    bpy.utils.unregister_class(operators.ActionNameCandidates)
    bpy.utils.unregister_class(operators.ActionRangeToScene)
    bpy.utils.unregister_class(operators.ConstraintStatus)
    bpy.utils.unregister_class(operators.SelectConstrainedControls)
    bpy.utils.unregister_class(operators.ConvertBoneNaming)
    bpy.utils.unregister_class(operators.ConvertGameFriendly)
    bpy.utils.unregister_class(operators.ExtractMetarig)
    bpy.utils.unregister_class(operators.MergeHeadTails)
    bpy.utils.unregister_class(operators.RevertDotBoneNames)
    bpy.utils.unregister_class(operators.ConstrainToArmature)
    bpy.utils.unregister_class(operators.BakeConstrainedActions)
    bpy.utils.unregister_class(operators.RenameActionsFromFbxFiles)
    bpy.utils.unregister_class(operators.CreateTransformOffset)
    bpy.utils.unregister_class(operators.AddRootMotion)
    bpy.utils.unregister_class(ExpyToClipboard)
    bpy.utils.unregister_class(ExpyPrefs)

    properties.unregister_properties()
