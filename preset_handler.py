import ast
import importlib.util
import os
import shutil

import bpy
from .rig_mapping.bone_mapping import HumanFingers, HumanSpine, HumanLeg, HumanArm, HumanSkeleton, SimpleFace


PRESETS_SUBDIR = os.path.join("armature", "retarget")


def get_retarget_dir():
    presets_dir = bpy.utils.user_resource('SCRIPTS', path="presets")
    retarget_dir = os.path.join(presets_dir, PRESETS_SUBDIR)

    return retarget_dir


def install_presets():
    retarget_dir = get_retarget_dir()
    bundled_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rig_mapping", "presets")

    os.makedirs(retarget_dir, exist_ok=True)
    for f in os.listdir(bundled_dir):
        shutil.copy2(os.path.join(bundled_dir, f), retarget_dir)


def iterate_presets(scene, context):
    """CallBack for Enum Property. Must take scene, context arguments"""

    yield '--', "--", "None"  # first menu entry, doesn't do anything
    for f in os.listdir(get_retarget_dir()):
        if not f.endswith('.py'):
            continue
        yield f, os.path.splitext(f)[0].title(), ""


def get_settings_skel(settings):
    mapping = HumanSkeleton(preset=settings)
    return mapping


def set_preset_skel(preset):
    if not preset:
        return
    if not preset.endswith(".py"):
        return

    preset_path = os.path.join(get_retarget_dir(), preset)
    if not os.path.isfile(preset_path):
        return

    spec = importlib.util.spec_from_file_location("sel_preset", preset_path)
    preset_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preset_mod)

    mapping = get_settings_skel(preset_mod.skeleton)
    return mapping


def get_preset_skel(preset, settings=None):
    if not preset:
        return
    if not preset.endswith(".py"):
        return

    preset_path = os.path.join(get_retarget_dir(), preset)
    if not os.path.isfile(preset_path):
        return

    # HACKISH: executing the preset would apply it to the current armature. Use ast instead
    code = ast.parse(open(preset_path).read())
    code.body.pop(0)
    code.body.pop(0)

    skeleton = settings if settings else PresetSkeleton()
    eval(compile(code, '', 'exec'))

    mapping = HumanSkeleton(preset=skeleton)
    del skeleton
    return mapping


class PresetFinger:
    def __init__(self):
        self.a = ""
        self.b = ""
        self.c = ""


class PresetSkeleton:
    def __init__(self):
        self.face = SimpleFace()
        self.spine = HumanSpine()

        self.left_arm = HumanArm()
        self.left_arm_ik = HumanArm()
        self.right_arm = HumanArm()
        self.right_arm_ik = HumanArm()

        self.right_leg = HumanLeg()
        self.right_leg_ik = HumanLeg()
        self.left_leg = HumanLeg()
        self.left_leg_ik = HumanLeg()

        self.left_fingers = HumanFingers(thumb=PresetFinger(), index=PresetFinger(), middle=PresetFinger(), ring=PresetFinger(), pinky=PresetFinger())
        self.right_fingers = HumanFingers(thumb=PresetFinger(), index=PresetFinger(), middle=PresetFinger(), ring=PresetFinger(), pinky=PresetFinger())
        self.root = ""

    def copy(self, settings):
        for group in ('spine', 'left_arm', 'left_arm_ik', 'right_arm', 'right_arm_ik',
                      'right_leg', 'right_leg_ik', 'left_leg', 'left_leg_ik', 'face'):
            setting = getattr(self, group)
            trg_setting = getattr(settings, group)
            for k in setting.keys():
                setattr(setting, k, getattr(trg_setting, k))

        finger_bones = 'a', 'b', 'c'
        for group, trg_grp in zip((self.left_fingers, self.right_fingers),
                                  (settings.left_fingers, settings.right_fingers)):
            for k in group.keys():
                if k == 'name':  # skip Property Group name
                    continue

                finger = getattr(group, k)
                trg_finger = getattr(trg_grp, k)

                for i, slot in enumerate(finger_bones):
                    setattr(finger, slot, getattr(trg_finger, slot))
