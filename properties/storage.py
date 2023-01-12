import bpy

from bpy.types import PropertyGroup
from bpy.props import FloatVectorProperty
from bpy.props import StringProperty
from bpy.props import PointerProperty
# from bpy.props import BoolProperty
# from bpy.props import EnumProperty

# from . import preset_handler

class VecStorageBase(PropertyGroup):
    def has_settings(self):
        for k, v in self.items():
            if k == 'name':
                continue
            if v:
                return True
        return False


class StoreSpine(VecStorageBase):
    head: FloatVectorProperty(name="head")
    neck: FloatVectorProperty(name="neck")
    spine2: FloatVectorProperty(name="spine2")
    spine1: FloatVectorProperty(name="spine1")
    spine: FloatVectorProperty(name="spine")
    hips: FloatVectorProperty(name="hips")


class StoreArm(VecStorageBase):
    shoulder: FloatVectorProperty(name="shoulder")
    arm: FloatVectorProperty(name="arm")
    # arm_twist: FloatVectorProperty(name="arm_twist")
    forearm: FloatVectorProperty(name="forearm")
    # forearm_twist: FloatVectorProperty(name="forearm_twist")
    hand: FloatVectorProperty(name="hand")

    name: StringProperty(default='arm')


class StoreLeg(VecStorageBase):
    upleg: FloatVectorProperty(name="upleg")
    upleg_twist: FloatVectorProperty(name="upleg_twist")
    leg: FloatVectorProperty(name="leg")
    leg_twist: FloatVectorProperty(name="leg_twist")
    foot: FloatVectorProperty(name="foot")
    toe: FloatVectorProperty(name="toe")

    name: StringProperty(default='leg')


class StoreFinger(VecStorageBase):
    a: FloatVectorProperty(name="A")
    b: FloatVectorProperty(name="B")
    c: FloatVectorProperty(name="C")


class StoreFingers(PropertyGroup):
    thumb: PointerProperty(type=StoreFinger)
    index: PointerProperty(type=StoreFinger)
    middle: PointerProperty(type=StoreFinger)
    ring: PointerProperty(type=StoreFinger)
    pinky: PointerProperty(type=StoreFinger)

    name: StringProperty(default='fingers')

    def has_settings(self):
        for setting in (self.thumb, self.index, self.middle, self.ring, self.pinky):
            if setting.has_settings():
                return True

        return False


class StoreFaceSimple(PropertyGroup):
    jaw: FloatVectorProperty(name="jaw")
    left_eye: FloatVectorProperty(name="left_eye")
    right_eye: FloatVectorProperty(name="right_eye")

    left_upLid: FloatVectorProperty(name="left_upLid")
    right_upLid: FloatVectorProperty(name="right_upLid")

    # super_copy: BoolProperty(default=True)


class StoreSettings(PropertyGroup):
    face: PointerProperty(type=StoreFaceSimple)
    spine: PointerProperty(type=StoreSpine)

    left_arm: PointerProperty(type=StoreArm)
    left_arm_ik: PointerProperty(type=StoreArm)
    left_fingers: PointerProperty(type=StoreFingers)

    right_arm: PointerProperty(type=StoreArm)
    right_arm_ik: PointerProperty(type=StoreArm)
    right_fingers: PointerProperty(type=StoreFingers)

    left_leg: PointerProperty(type=StoreLeg)
    left_leg_ik: PointerProperty(type=StoreLeg)
    right_leg: PointerProperty(type=StoreLeg)
    right_leg_ik: PointerProperty(type=StoreLeg)

    root: StringProperty(name="root")

    def has_settings(self):
        for setting in (self.spine, self.left_arm, self.left_arm_ik, self.left_fingers,
                        self.right_arm, self.right_arm_ik, self.right_fingers,
                        self.left_leg, self.left_leg_ik, self.right_leg, self.right_leg_ik):
            if setting.has_settings():
                return True

        return False


def register_classes():
    bpy.utils.register_class(StoreSpine)
    bpy.utils.register_class(StoreArm)
    bpy.utils.register_class(StoreLeg)
    bpy.utils.register_class(StoreFinger)
    bpy.utils.register_class(StoreFingers)
    bpy.utils.register_class(StoreFaceSimple)

    bpy.utils.register_class(StoreSettings)

    bpy.types.WindowManager.expykit_storage = bpy.props.PointerProperty(type=StoreSettings)


def unregister_classes():
    del bpy.types.WindowManager.expykit_storage
    bpy.utils.unregister_class(StoreSettings)

    bpy.utils.unregister_class(StoreFaceSimple)
    bpy.utils.unregister_class(StoreFinger)
    bpy.utils.unregister_class(StoreFingers)
    bpy.utils.unregister_class(StoreSpine)

    bpy.utils.unregister_class(StoreArm)
    bpy.utils.unregister_class(StoreLeg)
