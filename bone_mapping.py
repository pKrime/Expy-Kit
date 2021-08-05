

rigify_face_bones = [
    'face', 'nose', 'nose.001', 'nose.002', 'nose.003', 'nose.004',
    'lip.T.L', 'lip.T.L.001', 'lip.B.L', 'lip.B.L.001',
    'jaw', 'chin', 'chin.001',
    'ear.L', 'ear.L.001', 'ear.L.002', 'ear.L.003', 'ear.L.004', 'ear.R', 'ear.R.001', 'ear.R.002', 'ear.R.003', 'ear.R.004',
    'lip.T.R', 'lip.T.R.001', 'lip.B.R', 'lip.B.R.001',
    'brow.B.L', 'brow.B.L.001', 'brow.B.L.002', 'brow.B.L.003',
    'lid.T.L', 'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'lid.B.L', 'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003',
    'brow.B.R', 'brow.B.R.001', 'brow.B.R.002', 'brow.B.R.003',
    'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 'lid.T.R.003',
    'lid.B.R', 'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003',
    'forehead.L', 'forehead.L.001', 'forehead.L.002',  'temple.L',
    'jaw.L', 'jaw.L.001', 'chin.L', 'cheek.B.L', 'cheek.B.L.001',
    'brow.T.L', 'brow.T.L.001', 'brow.T.L.002', 'brow.T.L.003',
    'forehead.R', 'forehead.R.001', 'forehead.R.002', 'temple.R',
    'jaw.R', 'jaw.R.001', 'chin.R', 'cheek.B.R', 'cheek.B.R.001',
    'brow.T.R', 'brow.T.R.001', 'brow.T.R.002', 'brow.T.R.003',
    'eye.L', 'eye.R',
    'cheek.T.L', 'cheek.T.L.001', 'cheek.T.R', 'cheek.T.R.001',
    'nose.L', 'nose.L.001', 'nose.R', 'nose.R.001',
    'teeth.T', 'teeth.B', 'tongue', 'tongue.001', 'tongue.002',
]


class HumanLimb:
    def __str__(self):
        return self.__class__.__name__ + ' ' + ', '.join(["{0}: {1}".format(k, v) for k, v in self.__dict__.items()])

    def __getitem__(self, item):
        return getattr(self, item, None)

    def items(self):
        return self.__dict__.items()


class HumanSpine(HumanLimb):
    def __init__(self, head='', neck='', spine2='', spine1='', spine='', hips=''):
        self.head = head
        self.neck = neck
        self.spine2 = spine2
        self.spine1 = spine1
        self.spine = spine
        self.hips = hips


class HumanArm(HumanLimb):
    def __init__(self, shoulder='', arm='', forearm='', hand=''):
        self.shoulder = shoulder
        self.arm = arm
        self.arm_twist = None
        self.forearm = forearm
        self.forearm_twist = None
        self.hand = hand


class HumanLeg(HumanLimb):
    def __init__(self, upleg='', leg='', foot='', toe=''):
        self.upleg = upleg
        self.upleg_twist = None
        self.leg = leg
        self.leg_twist = None
        self.foot = foot
        self.toe = toe


class HumanFingers(HumanLimb):
    def __init__(self, thumb=[''] * 3, index=[''] * 3, middle=[''] * 3, ring=[''] * 3, pinky=[''] * 3):
        self.thumb = thumb
        self.index = index
        self.middle = middle
        self.ring = ring
        self.pinky = pinky


class HumanSkeleton:
    spine = None

    left_arm = None
    right_arm = None
    left_leg = None
    right_leg = None

    left_fingers = None
    right_fingers = None

    def conversion_map(self, target_skeleton):
        """Return a dictionary that maps skeleton bone names to target bone names
        >>> rigify = RigifySkeleton()
        >>> rigify.conversion_map(MixamoSkeleton())
        {'DEF-spine.006': 'Head', 'DEF-spine.004': 'Neck', 'DEF-spine.003'...
        """
        bone_map = dict()

        def bone_mapping(attr, limb, bone_name):
            target_limbs = getattr(target_skeleton, attr, None)
            if not target_limbs:
                return

            trg_name = target_limbs[limb]

            if trg_name:
                bone_map[bone_name] = trg_name

        for limb_name, bone_name in self.spine.items():
            bone_mapping('spine', limb_name, bone_name)

        for limb_name, bone_name in self.left_arm.items():
            bone_mapping('left_arm', limb_name, bone_name)

        for limb_name, bone_name in self.right_arm.items():
            bone_mapping('right_arm', limb_name, bone_name)

        for limb_name, bone_name in self.left_leg.items():
            bone_mapping('left_leg', limb_name, bone_name)

        for limb_name, bone_name in self.right_leg.items():
            bone_mapping('right_leg', limb_name, bone_name)

        def fingers_mapping(src_fingers, trg_fingers):
            for finger, bone_names in src_fingers.items():
                trg_bone_names = trg_fingers[finger]

                assert len(bone_names) == len(trg_bone_names)
                for bone, trg_bone in zip(bone_names, trg_bone_names):
                    bone_map[bone] = trg_bone

        trg_fingers = target_skeleton.left_fingers
        fingers_mapping(self.left_fingers, trg_fingers)

        trg_fingers = target_skeleton.right_fingers
        fingers_mapping(self.right_fingers, trg_fingers)

        return bone_map


class MixamoSkeleton(HumanSkeleton):
    def __init__(self):
        self.spine = HumanSpine(
            head='Head',
            neck='Neck',
            spine2='Spine2',
            spine1='Spine1',
            spine='Spine',
            hips='Hips'
        )

        side = 'Left'
        self.left_arm = HumanArm(shoulder=side + "Shoulder",
                                 arm=side + "Arm",
                                 forearm=side + "ForeArm",
                                 hand=side + "Hand")

        self.left_fingers = HumanFingers(
                    thumb=["{0}HandThumb{1}".format(side, i) for i in range(1, 4)],
                    index=["{0}HandIndex{1}".format(side, i) for i in range(1, 4)],
                    middle=["{0}HandMiddle{1}".format(side, i) for i in range(1, 4)],
                    ring=["{0}HandRing{1}".format(side, i) for i in range(1, 4)],
                    pinky=["{0}HandPinky{1}".format(side, i) for i in range(1, 4)],
                )

        self.left_leg = HumanLeg(upleg="{0}UpLeg".format(side),
                                  leg="{0}Leg".format(side),
                                  foot="{0}Foot".format(side),
                                  toe="{0}ToeBase".format(side))

        side = 'Right'
        self.right_arm = HumanArm(shoulder=side + "Shoulder",
                                 arm=side + "Arm",
                                 forearm=side + "ForeArm",
                                 hand=side + "Hand")

        self.right_fingers = HumanFingers(
            thumb=["{0}HandThumb{1}".format(side, i) for i in range(1, 4)],
            index=["{0}HandIndex{1}".format(side, i) for i in range(1, 4)],
            middle=["{0}HandMiddle{1}".format(side, i) for i in range(1, 4)],
            ring=["{0}HandRing{1}".format(side, i) for i in range(1, 4)],
            pinky=["{0}HandPinky{1}".format(side, i) for i in range(1, 4)],
        )

        self.right_leg = HumanLeg(upleg="{0}UpLeg".format(side),
                                  leg="{0}Leg".format(side),
                                  foot="{0}Foot".format(side),
                                  toe="{0}ToeBase".format(side))


class RigifySkeleton(HumanSkeleton):
    def __init__(self):
        self.spine = HumanSpine(
            head='DEF-spine.006',
            neck='DEF-spine.004',
            spine2='DEF-spine.003',
            spine1='DEF-spine.002',
            spine='DEF-spine.001',
            hips='DEF-spine'
        )

        for side, side_letter in zip(('left', 'right'), ('L', 'R')):
            arm = HumanArm(shoulder="DEF-shoulder.{0}".format(side_letter),
                           arm="DEF-upper_arm.{0}".format(side_letter),
                           forearm="DEF-forearm.{0}".format(side_letter),
                           hand="DEF-hand.{0}".format(side_letter))

            arm.arm_twist = arm.arm + ".001"
            arm.forearm_twist = arm.forearm + ".001"
            setattr(self, side + "_arm", arm)

            fingers = HumanFingers(
                thumb=["DEF-thumb.{1:02d}.{0}".format(side_letter, i) for i in range(1, 4)],
                index=["DEF-f_index.{1:02d}.{0}".format(side_letter, i) for i in range(1, 4)],
                middle=["DEF-f_middle.{1:02d}.{0}".format(side_letter, i) for i in range(1, 4)],
                ring=["DEF-f_ring.{1:02d}.{0}".format(side_letter, i) for i in range(1, 4)],
                pinky=["DEF-f_pinky.{1:02d}.{0}".format(side_letter, i) for i in range(1, 4)],
            )
            setattr(self, side + "_fingers", fingers)

            leg = HumanLeg(upleg="DEF-thigh.{0}".format(side_letter),
                           leg="DEF-shin.{0}".format(side_letter),
                           foot="DEF-foot.{0}".format(side_letter),
                           toe="DEF-toe.{0}".format(side_letter))

            leg.upleg_twist = leg.upleg + ".001"
            leg.leg_twist = leg.leg + ".001"
            setattr(self, side + "_leg", leg)


class RigifyMeta(HumanSkeleton):
    def __init__(self):
        self.spine = HumanSpine(
            head='spine.006',
            neck='spine.004',
            spine2='spine.003',
            spine1='spine.002',
            spine='spine.001',
            hips='spine'
        )

        side = 'L'
        self.left_arm = HumanArm(shoulder="shoulder.{0}".format(side),
                                 arm="upper_arm.{0}".format(side),
                                 forearm="forearm.{0}".format(side),
                                 hand="hand.{0}".format(side))

        self.left_fingers = HumanFingers(
            thumb=["thumb.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            index=["f_index.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            middle=["f_middle.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            ring=["f_ring.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            pinky=["f_pinky.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
        )

        self.left_leg = HumanLeg(upleg="thigh.{0}".format(side),
                                 leg="shin.{0}".format(side),
                                 foot="foot.{0}".format(side),
                                 toe="toe.{0}".format(side))

        side = 'R'
        self.right_arm = HumanArm(shoulder="shoulder.{0}".format(side),
                                  arm="upper_arm.{0}".format(side),
                                  forearm="forearm.{0}".format(side),
                                  hand="hand.{0}".format(side))

        self.right_fingers = HumanFingers(
            thumb=["thumb.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            index=["f_index.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            middle=["f_middle.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            ring=["f_ring.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
            pinky=["f_pinky.{1:02d}.{0}".format(side, i) for i in range(1, 4)],
        )

        self.right_leg = HumanLeg(upleg="thigh.{0}".format(side),
                                  leg="shin.{0}".format(side),
                                  foot="foot.{0}".format(side),
                                  toe="toe.{0}".format(side))


class UnrealSkeleton(HumanSkeleton):
    def __init__(self):
        self.spine = HumanSpine(
            head='head',
            neck='neck_01',
            spine2='spine_03',
            spine1='spine_02',
            spine='spine_01',
            hips='pelvis'
        )

        for side, side_letter in zip(('left', 'right'), ('_l', '_r')):
            arm = HumanArm(shoulder="clavicle" + side_letter,
                           arm="upperarm" + side_letter,
                           forearm="lowerarm" + side_letter,
                           hand="hand" + side_letter)

            arm.arm_twist = "upperarm_twist_01" + side_letter
            arm.forearm_twist = "lowerarm_twist_01" + side_letter
            setattr(self, side + "_arm", arm)

            fingers = HumanFingers(
                    thumb=["thumb_{0:02d}{1}".format(i, side_letter) for i in range(1, 4)],
                    index=["index_{0:02d}{1}".format(i, side_letter) for i in range(1, 4)],
                    middle=["middle_{0:02d}{1}".format(i, side_letter) for i in range(1, 4)],
                    ring=["ring_{0:02d}{1}".format(i, side_letter) for i in range(1, 4)],
                    pinky=["pinky_{0:02d}{1}".format(i, side_letter) for i in range(1, 4)],
                )
            setattr(self, side + "_fingers", fingers)

            leg = HumanLeg(upleg="thigh{0}".format(side_letter),
                           leg="calf{0}".format(side_letter),
                           foot="foot{0}".format(side_letter),
                           toe="ball{0}".format(side_letter))

            leg.upleg_twist = "thigh_twist_01" + side_letter
            leg.leg_twist = "calf_twist_01" + side_letter
            setattr(self, side + "_leg", leg)


# test
if __name__ == "__main__":
    rigify = RigifySkeleton()
    bone_map = rigify.conversion_map(MixamoSkeleton())

    print("Bone Map:")
    for k, v in bone_map.items():
        print('\t', k, v)
