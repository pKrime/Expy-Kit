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
    "version": (0, 5, 2),
    "author": "Paolo Acampora (Balls & Ninjas)",
    "blender": (2, 90, 0),
    "description": "Tools for Character Rig Conversion",
    "category": "Rigging",
}


from . import operators
from . import ui
from . import preferences
from . import preset_handler
from . import properties
from . import _extra_

from . import __refresh__
__refresh__.reload_modules()


def register():
    properties.register_classes()
    preferences.register_classes()
    operators.register_classes()
    ui.register_classes()
    _extra_.register_classes()

    preset_handler.install_presets()


def unregister():
    _extra_.unregister_classes()
    ui.unregister_classes()
    operators.unregister_classes()
    preferences.unregister_classes()
    properties.unregister_classes()
