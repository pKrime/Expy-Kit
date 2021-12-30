import bpy
from bpy.types import PropertyGroup
from bpy.props import CollectionProperty
from bpy.props import StringProperty
from bpy.props import PointerProperty


class RetargetSpine(PropertyGroup):
    head: StringProperty(name="head")
    neck: StringProperty(name="neck")
    spine2: StringProperty(name="spine2")
    spine1: StringProperty(name="spine1")
    spine: StringProperty(name="spine")
    hips: StringProperty(name="hips")


class RetargetArm(PropertyGroup):
    shoulder: StringProperty(name="shoulder")
    arm: StringProperty(name="arm")
    arm_twist: StringProperty(name="arm_twist")
    forearm: StringProperty(name="forearm")
    forearm_twist: StringProperty(name="forearm_twist")
    hand: StringProperty(name="hand")


class RetargetLeg(PropertyGroup):
    upleg: StringProperty(name="upleg")
    upleg_twist: StringProperty(name="upleg_twist")
    leg: StringProperty(name="leg")
    leg_twist: StringProperty(name="leg_twist")
    foot: StringProperty(name="foot")
    toe: StringProperty(name="toe")


class RetargetSettings(PropertyGroup):
    spine: PointerProperty(type=RetargetSpine)
    left_arm: PointerProperty(type=RetargetArm)
    right_arm: PointerProperty(type=RetargetArm)


def register_properties():
    bpy.utils.register_class(RetargetSpine)
    bpy.utils.register_class(RetargetArm)

    bpy.utils.register_class(RetargetSettings)
    bpy.types.Armature.expykit_retarget = bpy.props.PointerProperty(type=RetargetSettings)


def unregister_properties():
    del bpy.types.Armature.expykit_retarget
    bpy.utils.unregister_class(RetargetSpine)
    bpy.utils.unregister_class(RetargetArm)

    bpy.utils.unregister_class(RetargetSettings)
