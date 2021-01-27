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
    "name": "Charigtee Scripts",
    "version": (0, 0, 1),
    "author": "Paolo Acampora",
    "blender": (2, 90, 0),
    "description": "Tools for Character Rigging",
    "category": "Rigging",
}


import bpy
from . import operators
from . import ui

from importlib import reload
reload(operators)
reload(ui)


def register():
    bpy.utils.register_class(operators.ConstraintStatus)
    bpy.utils.register_class(operators.RevertDotBoneNames)

    bpy.types.VIEW3D_MT_pose_context_menu.append(ui.pose_context_options)


def unregister():
    bpy.utils.unregister_class(operators.ConstraintStatus)
    bpy.utils.unregister_class(operators.RevertDotBoneNames)

    bpy.types.VIEW3D_MT_pose_context_menu.remove(ui.pose_context_options)
