import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty
from bpy.props import PointerProperty
from bpy.props import BoolProperty
from bpy.props import EnumProperty

from .. import preset_handler


class RetargetBase(PropertyGroup):
    def has_settings(self):
        for k, v in self.items():
            if k == 'name':
                continue
            if v:
                return True
        return False


class RetargetSpine(RetargetBase):
    head: StringProperty(name="head")
    neck: StringProperty(name="neck")
    spine2: StringProperty(name="spine2")
    spine1: StringProperty(name="spine1")
    spine: StringProperty(name="spine")
    hips: StringProperty(name="hips")


class RetargetArm(RetargetBase):
    shoulder: StringProperty(name="shoulder")
    arm: StringProperty(name="arm")
    arm_twist: StringProperty(name="arm_twist")
    arm_twist_02: StringProperty(name="arm_twist_02")
    forearm: StringProperty(name="forearm")
    forearm_twist: StringProperty(name="forearm_twist")
    forearm_twist_02: StringProperty(name="forearm_twist_02")
    hand: StringProperty(name="hand")

    name: StringProperty(default='arm')


class RetargetLeg(RetargetBase):
    upleg: StringProperty(name="upleg")
    upleg_twist: StringProperty(name="upleg_twist")
    upleg_twist_02: StringProperty(name="upleg_twist_02")
    leg: StringProperty(name="leg")
    leg_twist: StringProperty(name="leg_twist")
    leg_twist_02: StringProperty(name="leg_twist_02")
    foot: StringProperty(name="foot")
    toe: StringProperty(name="toe")

    name: StringProperty(default='leg')


class RetargetFinger(RetargetBase):
    meta: StringProperty(name="meta")
    a: StringProperty(name="A")
    b: StringProperty(name="B")
    c: StringProperty(name="C")


class RetargetFingers(PropertyGroup):
    thumb: PointerProperty(type=RetargetFinger)
    index: PointerProperty(type=RetargetFinger)
    middle: PointerProperty(type=RetargetFinger)
    ring: PointerProperty(type=RetargetFinger)
    pinky: PointerProperty(type=RetargetFinger)

    name: StringProperty(default='fingers')

    def has_settings(self):
        for setting in (self.thumb, self.index, self.middle, self.ring, self.pinky):
            if setting.has_settings():
                return True

        return False


class RetargetFaceSimple(PropertyGroup):
    jaw: StringProperty(name="jaw")
    left_eye: StringProperty(name="left_eye")
    right_eye: StringProperty(name="right_eye")

    left_upLid: StringProperty(name="left_upLid")
    right_upLid: StringProperty(name="right_upLid")

    super_copy: BoolProperty(default=True)


class RetargetSettings(PropertyGroup):
    face: PointerProperty(type=RetargetFaceSimple)
    spine: PointerProperty(type=RetargetSpine)

    left_arm: PointerProperty(type=RetargetArm)
    left_arm_ik: PointerProperty(type=RetargetArm)
    left_fingers: PointerProperty(type=RetargetFingers)

    right_arm: PointerProperty(type=RetargetArm)
    right_arm_ik: PointerProperty(type=RetargetArm)
    right_fingers: PointerProperty(type=RetargetFingers)

    left_leg: PointerProperty(type=RetargetLeg)
    left_leg_ik: PointerProperty(type=RetargetLeg)
    right_leg: PointerProperty(type=RetargetLeg)
    right_leg_ik: PointerProperty(type=RetargetLeg)

    root: StringProperty(name="root")

    def has_settings(self):
        for setting in (self.spine, self.left_arm, self.left_arm_ik, self.left_fingers,
                        self.right_arm, self.right_arm_ik, self.right_fingers,
                        self.left_leg, self.left_leg_ik, self.right_leg, self.right_leg_ik):
            if setting.has_settings():
                return True

        return False

    deform_preset: EnumProperty(items=preset_handler.iterate_presets, name="Deformation Bones")


def register_classes():
    bpy.utils.register_class(RetargetBase)
    bpy.utils.register_class(RetargetSpine)
    bpy.utils.register_class(RetargetArm)
    bpy.utils.register_class(RetargetLeg)
    bpy.utils.register_class(RetargetFinger)
    bpy.utils.register_class(RetargetFingers)
    bpy.utils.register_class(RetargetFaceSimple)

    bpy.utils.register_class(RetargetSettings)
    bpy.types.Armature.expykit_retarget = PointerProperty(type=RetargetSettings)
    bpy.types.Armature.expykit_twist_on = BoolProperty(default=False)


def unregister_classes():
    del bpy.types.Armature.expykit_retarget
    del bpy.types.Armature.expykit_twist_on

    bpy.utils.unregister_class(RetargetSettings)

    bpy.utils.unregister_class(RetargetFaceSimple)
    bpy.utils.unregister_class(RetargetFingers)
    bpy.utils.unregister_class(RetargetFinger)
    bpy.utils.unregister_class(RetargetSpine)

    bpy.utils.unregister_class(RetargetArm)
    bpy.utils.unregister_class(RetargetLeg)
    bpy.utils.unregister_class(RetargetBase)
