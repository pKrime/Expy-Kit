import bpy
skeleton = bpy.context.object.data.expykit_retarget

skeleton.face.super_copy = False

skeleton.spine.head = 'DEF-head'
skeleton.spine.neck = 'DEF-neck'
skeleton.spine.spine2 = 'DEF-chest'
skeleton.spine.spine = 'DEF-spine'
skeleton.spine.hips = 'DEF-hips'

skeleton.right_arm.shoulder = 'DEF-shoulder.R'
skeleton.right_arm.arm = 'DEF-upper_arm.01.R'
skeleton.right_arm.arm_twist = 'DEF-upper_arm.02.R'
skeleton.right_arm.forearm = 'DEF-forearm.01.R'
skeleton.right_arm.forearm_twist = 'DEF-forearm.02.R'
skeleton.right_arm.hand = 'DEF-hand.R'

skeleton.left_arm.shoulder = 'DEF-shoulder.L'
skeleton.left_arm.arm = 'DEF-upper_arm.01.L'
skeleton.left_arm.arm_twist = 'DEF-upper_arm.02.L'
skeleton.left_arm.forearm = 'DEF-forearm.01.L'
skeleton.left_arm.forearm_twist = 'DEF-forearm.02.L'
skeleton.left_arm.hand = 'DEF-hand.L'

skeleton.right_leg.upleg = 'DEF-thigh.01.R'
skeleton.right_leg.upleg_twist = 'DEF-thigh.02.R'
skeleton.right_leg.leg = 'DEF-shin.01.R'
skeleton.right_leg.leg_twist = 'DEF-shin.02.R'
skeleton.right_leg.foot = 'DEF-foot.R'
skeleton.right_leg.toe = 'DEF-toe.R'

skeleton.left_leg.upleg = 'DEF-thigh.01.L'
skeleton.left_leg.upleg_twist = 'DEF-thigh.02.L'
skeleton.left_leg.leg = 'DEF-shin.01.L'
skeleton.left_leg.leg_twist = 'DEF-shin.02.L'
skeleton.left_leg.foot = 'DEF-foot.L'
skeleton.left_leg.toe = 'DEF-toe.L'

skeleton.left_fingers.thumb.a = 'DEF-thumb.01.L.01'
skeleton.left_fingers.thumb.b = 'DEF-thumb.02.L'
skeleton.left_fingers.thumb.c = 'DEF-thumb.03.L'

skeleton.left_fingers.index.meta = 'DEF-palm.01.L'
skeleton.left_fingers.index.a = 'DEF-f_index.01.L.01'
skeleton.left_fingers.index.b = 'DEF-f_index.02.L'
skeleton.left_fingers.index.c = 'DEF-f_index.03.L'

skeleton.left_fingers.middle.meta = 'DEF-palm.02.L'
skeleton.left_fingers.middle.a = 'DEF-f_middle.01.L.01'
skeleton.left_fingers.middle.b = 'DEF-f_middle.02.L'
skeleton.left_fingers.middle.c = 'DEF-f_middle.03.L'

skeleton.left_fingers.ring.meta = 'DEF-palm.03.L'
skeleton.left_fingers.ring.a = 'DEF-f_ring.01.L.01'
skeleton.left_fingers.ring.b = 'DEF-f_ring.02.L'
skeleton.left_fingers.ring.c = 'DEF-f_ring.03.L'

skeleton.left_fingers.pinky.meta = 'DEF-palm.04.L'
skeleton.left_fingers.pinky.a = 'DEF-f_pinky.01.L.01'
skeleton.left_fingers.pinky.b = 'DEF-f_pinky.02.L'
skeleton.left_fingers.pinky.c = 'DEF-f_pinky.03.L'

skeleton.right_fingers.thumb.a = 'DEF-thumb.01.R.01'
skeleton.right_fingers.thumb.b = 'DEF-thumb.02.R'
skeleton.right_fingers.thumb.c = 'DEF-thumb.03.R'

skeleton.right_fingers.index.meta = 'DEF-palm.01.R'
skeleton.right_fingers.index.a = 'DEF-f_index.01.R.01'
skeleton.right_fingers.index.b = 'DEF-f_index.02.R'
skeleton.right_fingers.index.c = 'DEF-f_index.03.R'

skeleton.right_fingers.middle.meta = 'DEF-palm.02.R'
skeleton.right_fingers.middle.a = 'DEF-f_middle.01.R.01'
skeleton.right_fingers.middle.b = 'DEF-f_middle.02.R'
skeleton.right_fingers.middle.c = 'DEF-f_middle.03.R'

skeleton.right_fingers.ring.meta = 'DEF-palm.03.R'
skeleton.right_fingers.ring.a = 'DEF-f_ring.01.R.01'
skeleton.right_fingers.ring.b = 'DEF-f_ring.02.R'
skeleton.right_fingers.ring.c = 'DEF-f_ring.03.R'

skeleton.right_fingers.pinky.meta = 'DEF-palm.04.R'
skeleton.right_fingers.pinky.a = 'DEF-f_pinky.01.R.01'
skeleton.right_fingers.pinky.b = 'DEF-f_pinky.02.R'
skeleton.right_fingers.pinky.c = 'DEF-f_pinky.03.R'

skeleton.right_arm_ik.shoulder = 'DEF-shoulder.R'
skeleton.right_arm_ik.arm = 'DEF-upper_arm.01.R'
skeleton.right_arm_ik.forearm = 'DEF-forearm.01.R'
skeleton.right_arm_ik.hand = 'DEF-hand.R'

skeleton.left_arm_ik.shoulder = 'DEF-shoulder.L'
skeleton.left_arm_ik.arm = 'DEF-upper_arm.01.L'
skeleton.left_arm_ik.forearm = 'DEF-forearm.01.L'
skeleton.left_arm_ik.hand = 'DEF-hand.L'

skeleton.right_leg_ik.upleg = 'DEF-thigh.01.R'
skeleton.right_leg_ik.leg = 'DEF-shin.01.R'
skeleton.right_leg_ik.foot = 'DEF-foot.R'
skeleton.right_leg_ik.toe = 'DEF-toe.R'

skeleton.left_leg_ik.upleg = 'DEF-thigh.01.L'
skeleton.left_leg_ik.leg = 'DEF-shin.01.L'
skeleton.left_leg_ik.foot = 'DEF-foot.L'
skeleton.left_leg_ik.toe = 'DEF-toe.L'

skeleton.deform_preset = '--'
