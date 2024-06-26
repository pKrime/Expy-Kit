import bpy
skeleton = bpy.context.object.data.expykit_retarget

skeleton.face.jaw = 'jaw'
skeleton.face.right_eye = 'eye_r'
skeleton.face.left_eye = 'eye_l'
skeleton.face.right_upLid = 'eyelid_r'
skeleton.face.left_upLid = 'eyelid_l'

skeleton.spine.head = 'head'
skeleton.spine.neck = 'neck'
skeleton.spine.spine2 = 'spine_03'
skeleton.spine.spine1 = 'spine_02'
skeleton.spine.spine = 'spine_01'
skeleton.spine.hips = 'hip'

skeleton.right_arm.shoulder = 'shoulder_r'
skeleton.right_arm.arm = 'upperarm_r'
skeleton.right_arm.arm_twist = 'upperarm_twist_r'
skeleton.right_arm.forearm = 'lowerarm_r'
skeleton.right_arm.forearm_twist = 'lowerarm_twist_r'
skeleton.right_arm.hand = 'hand_r'

skeleton.left_arm.shoulder = 'shoulder_l'
skeleton.left_arm.arm = 'upperarm_l'
skeleton.left_arm.arm_twist = 'upperarm_twist_l'
skeleton.left_arm.forearm = 'lowerarm_l'
skeleton.left_arm.forearm_twist = 'lowerarm_twist_l'
skeleton.left_arm.hand = 'hand_l'

skeleton.right_leg.upleg = 'upperleg_r'
skeleton.right_leg.upleg_twist = 'upperleg_twist_r'
skeleton.right_leg.leg = 'lowerleg_r'
skeleton.right_leg.leg_twist = 'lowerleg_twist_r'
skeleton.right_leg.foot = 'foot_r'
skeleton.right_leg.toe = 'ball_r'

skeleton.left_leg.upleg = 'upperleg_l'
skeleton.left_leg.upleg_twist = 'upperleg_twist_l'
skeleton.left_leg.leg = 'lowerleg_l'
skeleton.left_leg.leg_twist = 'lowerleg_twist_l'
skeleton.left_leg.foot = 'foot_l'
skeleton.left_leg.toe = 'ball_l'

skeleton.right_fingers.thumb.a = 'thumb_01_r'
skeleton.right_fingers.thumb.b = 'thumb_02_r'
skeleton.right_fingers.thumb.c = 'thumb_03_r'
skeleton.right_fingers.index.a = 'index_01_r'
skeleton.right_fingers.index.b = 'index_02_r'
skeleton.right_fingers.index.c = 'index_03_r'
skeleton.right_fingers.middle.a = 'middle_01_r'
skeleton.right_fingers.middle.b = 'middle_02_r'
skeleton.right_fingers.middle.c = 'middle_03_r'
skeleton.right_fingers.ring.a = 'ring_01_r'
skeleton.right_fingers.ring.b = 'ring_02_r'
skeleton.right_fingers.ring.c = 'ring_03_r'
skeleton.right_fingers.pinky.a = 'pinky_01_r'
skeleton.right_fingers.pinky.b = 'pinky_02_r'
skeleton.right_fingers.pinky.c = 'pinky_03_r'

skeleton.left_fingers.thumb.a = 'thumb_01_l'
skeleton.left_fingers.thumb.b = 'thumb_02_l'
skeleton.left_fingers.thumb.c = 'thumb_03_l'
skeleton.left_fingers.index.a = 'index_01_l'
skeleton.left_fingers.index.b = 'index_02_l'
skeleton.left_fingers.index.c = 'index_03_l'
skeleton.left_fingers.middle.a = 'middle_01_l'
skeleton.left_fingers.middle.b = 'middle_02_l'
skeleton.left_fingers.middle.c = 'middle_03_l'
skeleton.left_fingers.ring.a = 'ring_01_l'
skeleton.left_fingers.ring.b = 'ring_02_l'
skeleton.left_fingers.ring.c = 'ring_03_l'
skeleton.left_fingers.pinky.a = 'pinky_01_l'
skeleton.left_fingers.pinky.b = 'pinky_02_l'
skeleton.left_fingers.pinky.c = 'pinky_03_l'
