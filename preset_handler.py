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


def iterate_presets_with_current(scene, context):
    """CallBack for Enum Property. Must take scene, context arguments"""

    yield '--', "--", "None"  # first menu entry, doesn't do anything
    yield "--Current--", "-- Current Settings --", "Use Bones set in Expy Retarget Panel"

    _dir = get_retarget_dir()
    if os.path.isdir(_dir):
        for f in os.listdir(_dir):
            if not f.endswith('.py'):
                continue
            yield f, os.path.splitext(f)[0].title(), ""


def iterate_presets(scene, context):
    """CallBack for Enum Property. Must take scene, context arguments"""

    yield '--', "--", "None"  # first menu entry, doesn't do anything

    _dir = get_retarget_dir()
    if os.path.isdir(_dir):
        for f in os.listdir(_dir):
            if not f.endswith('.py'):
                continue
            yield f, os.path.splitext(f)[0].title(), ""


def get_settings_skel(settings):
    mapping = HumanSkeleton(preset=settings)
    return mapping

# absent bones substitutions (left to right)
# for fingers it would be 'fingers.thumb' : ((xL,), (xR,),)
bone_name_synonyms = {
    'face.left_eye' : (('eye_master.L', 'master_eye.L'),
                       ('DEF-eye.L', 'eye.L'),
                    ),

    'face.right_eye' : (('eye_master.R', 'master_eye.R'),
                        ('DEF-eye.R', 'eye.R'),
                    ),

    'right_leg.toe' : (('toe.R', 'toe_fk.R'),),
    'left_leg.toe' : (('toe.L', 'toe_fk.L'),),

    'right_leg_ik.toe' : (('toe.R', 'toe_ik.R'),),
    'left_leg_ik.toe' : (('toe.L', 'toe_ik.L'),),
    }

def validate_preset(armature_data, separator=':'):
    settings = armature_data.expykit_retarget
    a_name = armature_data.bones[0].name

    prefix = ""
    if separator in a_name:
        prefix = a_name.rsplit(separator, 1)[0]
        prefix += separator

    def find_possible(name, group, attr):
        """returns existing bone name looking with prefix, and within synonyms, or empty string"""
        if not name:
            return name

        if name in armature_data.bones:
            return name

        else:
            if prefix and prefix + name in armature_data.bones:
                return prefix + name

            synonyms = bone_name_synonyms.get("%s.%s" % (group, attr))
            if synonyms:
                for syn_grp in synonyms:
                    if name in syn_grp:
                        for syn in syn_grp:
                            if syn != name:
                                if syn in armature_data.bones:
                                    return syn

                                if prefix and prefix + syn in armature_data.bones:
                                    return prefix + syn

        return ""

    for group in ('spine', 'left_arm', 'left_arm_ik', 'right_arm', 'right_arm_ik',
                    'right_leg', 'right_leg_ik', 'left_leg', 'left_leg_ik', 'face'):

        trg_setting = getattr(settings, group)
        for k, v in trg_setting.items():
            if k == "name" or type(v) is not str or not v:
                continue
            try:
                v1 = find_possible(v, group, k)
                if v1 != v:
                    setattr(trg_setting, k, v1)
            except TypeError:
                continue

    finger_bones = 'meta', 'a', 'b', 'c'
    for trg_grp in settings.left_fingers, settings.right_fingers:
        for k, trg_finger in trg_grp.items():
            if k == 'name':  # skip Property Group name
                continue

            for slot in finger_bones:
                bone_name = trg_finger.get(slot)
                if bone_name and bone_name not in armature_data.bones:
                    bone_name1 = find_possible(bone_name, trg_grp.name, k)
                    if bone_name1 != bone_name:
                        trg_finger[slot] = bone_name1


def set_preset_skel(preset, validate=True):
    """reads given preset into the active armature's settings"""
    if not preset:
        return
    if not preset.endswith(".py"):
        return

    preset_path = os.path.join(get_retarget_dir(), preset)
    if not os.path.isfile(preset_path):
        return

    settings = bpy.context.active_object.data.expykit_retarget

    if hasattr(importlib.util, "module_from_spec"):
        spec = importlib.util.spec_from_file_location("sel_preset", preset_path)
        preset_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preset_mod)

        if validate:
            validate_preset(settings.id_data)

        mapping = get_settings_skel(preset_mod.skeleton)
    else:
        # python <3.5. using a crutch
        mapping = get_preset_skel(preset, settings=settings, validate=False)

        if validate:
            validate_preset(settings.id_data)

    return mapping


def get_preset_skel(preset, settings=None, validate=True):
    """reads given preset into the given settings"""
    if not preset:
        return
    if not preset.endswith(".py"):
        return

    preset_path = os.path.join(get_retarget_dir(), preset)
    if not os.path.isfile(preset_path):
        return

    # run preset on current settings if there are any, otherwise create Preset settings
    # the attributes of 'skeleton' are set in the preset
    _new_skeleton = settings is None
    skeleton = settings if settings else PresetSkeleton()

    # HACKISH: executing the preset would apply it to the current armature (target).
    # We don't want that if this is runnning on the source armature. Using ast instead
    code = ast.parse(open(preset_path).read())

    # remove skeleton
    code.body.pop(0)  # remove line 'import bpy' from preset
    code.body.pop(0)  # remove line 'skeleton = bpy.context.object.data.expykit_retarget' from preset
    eval(compile(code, '', 'exec'))

    if settings and validate:
        validate_preset(settings.id_data)

    mapping = HumanSkeleton(preset=skeleton)
    if _new_skeleton:
        del skeleton

    return mapping


def reset_skeleton(skeleton):
    """Reset skeleton values to their defaults"""
    for setting in (skeleton.right_arm, skeleton.left_arm, skeleton.spine, skeleton.right_leg,
                    skeleton.left_leg, skeleton.right_arm_ik, skeleton.left_arm_ik,
                    skeleton.right_leg_ik, skeleton.left_leg_ik,
                    skeleton.face,
                    ):
        for k in setting.keys():
            if k == 'name':
                continue
            try:
                setattr(setting, k, '')
            except TypeError:
                continue

    for settings in (skeleton.right_fingers, skeleton.left_fingers):
        for setting in [getattr(settings, k) for k in settings.keys()]:
            try:
                for k in setting.keys():
                    if k == 'name':
                        continue
                    setattr(setting, k, '')
            except AttributeError:
                continue

    skeleton.root = ''
    skeleton.deform_preset = '--'


def iterate_filled_props(value, prefix="skeleton"):
    """yields only filled non-default skeleton's properties with their paths (path, value)"""
    if isinstance(value, bpy.types.PropertyGroup):
        if hasattr(value, "_order"):
            _items = ((k, value.bl_rna.properties[k]) for k in value._order)
        else:
            _items = value.bl_rna.properties.items()
        for sub_value_attr, sub_prop in _items:
            if (sub_value_attr in ("rna_type", "name") or sub_prop.is_hidden):
                continue
            sub_value = getattr(value, sub_value_attr)
            if hasattr(sub_prop, "default") and sub_prop.default == sub_value:
                continue
            yield from iterate_filled_props(sub_value, prefix="%s.%s" % (prefix, sub_value_attr))
    else:
        # convert thin wrapped sequences
        # to simple lists to repr()
        try:
            value = value[:]
        except BaseException:
            pass

        yield (prefix, value)


class PresetFinger:
    def __init__(self):
        self.a = ""
        self.b = ""
        self.c = ""
        self.meta = ""


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
        """self <- settings"""
        for group in ('spine', 'left_arm', 'left_arm_ik', 'right_arm', 'right_arm_ik',
                      'right_leg', 'right_leg_ik', 'left_leg', 'left_leg_ik', 'face'):
            setting = getattr(self, group)
            trg_setting = getattr(settings, group)
            for k in setting.keys():
                setattr(setting, k, getattr(trg_setting, k))

        finger_bones = 'a', 'b', 'c', 'meta'
        for group, trg_grp in zip((self.left_fingers, self.right_fingers),
                                  (settings.left_fingers, settings.right_fingers)):
            for k in group.keys():
                if k == 'name':  # skip Property Group name
                    continue

                finger = getattr(group, k)
                trg_finger = getattr(trg_grp, k)

                for i, slot in enumerate(finger_bones):
                    # preset/settings compatibility: a,b,c against [0], [1], [2]
                    try:
                        setattr(finger, slot, getattr(trg_finger, slot))
                    except AttributeError:
                        setattr(finger, slot, trg_finger[i])
