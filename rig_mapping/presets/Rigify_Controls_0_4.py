import bpy
skeleton = bpy.context.object.data.expykit_retarget

skeleton.spine.head = 'head'
skeleton.spine.neck = 'neck'
skeleton.spine.spine2 = 'chest'
skeleton.spine.spine1 = 'spine'
skeleton.spine.spine = 'hips'
skeleton.spine.hips = 'torso'

skeleton.right_arm.shoulder = 'shoulder.R'
skeleton.right_arm.arm = 'upper_arm.fk.R'
skeleton.right_arm.arm_twist = 'upper_arm_hose.R'
skeleton.right_arm.forearm = 'forearm.fk.R'
skeleton.right_arm.forearm_twist = 'forearm_hose.R'
skeleton.right_arm.hand = 'hand.fk.R'

skeleton.left_arm.shoulder = 'shoulder.L'
skeleton.left_arm.arm = 'upper_arm.fk.L'
skeleton.left_arm.arm_twist = 'upper_arm_hose.L'
skeleton.left_arm.forearm = 'forearm.fk.L'
skeleton.left_arm.forearm_twist = 'forearm_hose.L'
skeleton.left_arm.hand = 'hand.fk.L'

skeleton.right_leg.upleg = 'thigh.fk.R'
skeleton.right_leg.upleg_twist = 'thigh_hose.R'
skeleton.right_leg.leg = 'shin.fk.R'
skeleton.right_leg.leg_twist = 'shin_hose.R'
skeleton.right_leg.foot = 'foot.fk.R'
skeleton.right_leg.toe = 'toe.R'

skeleton.left_leg.upleg = 'thigh.fk.L'
skeleton.left_leg.upleg_twist = 'thigh_hose.L'
skeleton.left_leg.leg = 'shin.fk.L'
skeleton.left_leg.leg_twist = 'shin_hose.L'
skeleton.left_leg.foot = 'foot.fk.L'
skeleton.left_leg.toe = 'toe.L'

skeleton.right_fingers.thumb.a = 'thumb.01.R'
skeleton.right_fingers.thumb.b = 'thumb.02.R'
skeleton.right_fingers.thumb.c = 'thumb.03.R'
skeleton.right_fingers.index.a = 'f_index.01.R'
skeleton.right_fingers.index.b = 'f_index.02.R'
skeleton.right_fingers.index.c = 'f_index.03.R'
skeleton.right_fingers.middle.a = 'f_middle.01.R'
skeleton.right_fingers.middle.b = 'f_middle.02.R'
skeleton.right_fingers.middle.c = 'f_middle.03.R'
skeleton.right_fingers.ring.a = 'f_ring.01.R'
skeleton.right_fingers.ring.b = 'f_ring.02.R'
skeleton.right_fingers.ring.c = 'f_ring.03.R'
skeleton.right_fingers.pinky.a = 'f_pinky.01.R'
skeleton.right_fingers.pinky.b = 'f_pinky.02.R'
skeleton.right_fingers.pinky.c = 'f_pinky.03.R'

skeleton.left_fingers.thumb.a = 'thumb.01.L'
skeleton.left_fingers.thumb.b = 'thumb.02.L'
skeleton.left_fingers.thumb.c = 'thumb.03.L'
skeleton.left_fingers.index.a = 'f_index.01.L'
skeleton.left_fingers.index.b = 'f_index.02.L'
skeleton.left_fingers.index.c = 'f_index.03.L'
skeleton.left_fingers.middle.a = 'f_middle.01.L'
skeleton.left_fingers.middle.b = 'f_middle.02.L'
skeleton.left_fingers.middle.c = 'f_middle.03.L'
skeleton.left_fingers.ring.a = 'f_ring.01.L'
skeleton.left_fingers.ring.b = 'f_ring.02.L'
skeleton.left_fingers.ring.c = 'f_ring.03.L'
skeleton.left_fingers.pinky.a = 'f_pinky.01.L'
skeleton.left_fingers.pinky.b = 'f_pinky.02.L'
skeleton.left_fingers.pinky.c = 'f_pinky.03.L'

skeleton.right_arm_ik.shoulder = 'shoulder.R'
skeleton.right_arm_ik.arm = 'elbow_target.ik.R'
skeleton.right_arm_ik.hand = 'hand.ik.R'

skeleton.left_arm_ik.shoulder = 'shoulder.L'
skeleton.left_arm_ik.arm = 'elbow_target.ik.L'
skeleton.left_arm_ik.hand = 'hand.ik.L'

skeleton.right_leg_ik.upleg = 'knee_target.ik.R'
skeleton.right_leg_ik.foot = 'foot.ik.R'
skeleton.right_leg_ik.toe = 'toe.R'

skeleton.left_leg_ik.upleg = 'knee_target.ik.L'
skeleton.left_leg_ik.foot = 'foot.ik.L'
skeleton.left_leg_ik.toe = 'toe.L'

skeleton.root = 'root'
skeleton.deform_preset = 'Rigify_Deform_0_4.py'
