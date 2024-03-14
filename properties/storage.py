import bpy

from bpy.types import PropertyGroup
from bpy.props import FloatVectorProperty
from bpy.props import StringProperty
from bpy.props import PointerProperty
# from bpy.props import BoolProperty
# from bpy.props import EnumProperty

# from . import preset_handler

class LimbStorageBase(PropertyGroup):
    def has_settings(self):
        for k, v in self.items():
            if k == 'name':
                continue
            if v:
                return True
        return False


class VecStorage(PropertyGroup):
    look_at: FloatVectorProperty(name="look_at")


class StoreSpine(LimbStorageBase):
    head: PointerProperty(name="head", type=VecStorage)
    neck: PointerProperty(name="neck", type=VecStorage)
    spine2: PointerProperty(name="spine2", type=VecStorage)
    spine1: PointerProperty(name="spine1", type=VecStorage)
    spine: PointerProperty(name="spine", type=VecStorage)
    hips: PointerProperty(name="hips", type=VecStorage)


class StoreArm(LimbStorageBase):
    shoulder: PointerProperty(name="shoulder", type=VecStorage)
    arm: PointerProperty(name="arm", type=VecStorage)
    # arm_twist: FloatVectorProperty(name="arm_twist", type=VecStorage)
    forearm: PointerProperty(name="forearm", type=VecStorage)
    # forearm_twist: FloatVectorProperty(name="forearm_twist", type=VecStorage)
    hand: PointerProperty(name="hand", type=VecStorage)

    name: StringProperty(default='arm')


class StoreLeg(LimbStorageBase):
    upleg: PointerProperty(name="upleg", type=VecStorage)
    upleg_twist: PointerProperty(name="upleg_twist", type=VecStorage)
    leg: PointerProperty(name="leg", type=VecStorage)
    leg_twist: PointerProperty(name="leg_twist", type=VecStorage)
    foot: PointerProperty(name="foot", type=VecStorage)
    toe: PointerProperty(name="toe", type=VecStorage)

    name: StringProperty(default='leg')


class StoreFinger(LimbStorageBase):
    a: PointerProperty(name="A", type=VecStorage)
    b: PointerProperty(name="B", type=VecStorage)
    c: PointerProperty(name="C", type=VecStorage)


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
    jaw: PointerProperty(name="jaw", type=VecStorage)
    left_eye: PointerProperty(name="left_eye", type=VecStorage)
    right_eye: PointerProperty(name="right_eye", type=VecStorage)

    left_upLid: PointerProperty(name="left_upLid", type=VecStorage)
    right_upLid: PointerProperty(name="right_upLid", type=VecStorage)

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
    bpy.utils.register_class(VecStorage)
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
    bpy.utils.unregister_class(VecStorage)
