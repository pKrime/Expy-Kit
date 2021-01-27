
# Charigty Scripts
## tools that come handy when rigging

* Enable/Disable/Remove all constraints
* Convert rigify armatures to a deform hierarchy for game engines
* Restore rigify ".L"/".R" naming on skeletons reimported from Unreal Engine
* Convert Bone Names to export rigify character to mixamo


### How to use

Click the **Code** button and choose **Download Zip**, then install via the blender **Add-ons** preferences.

Or clone to your `Scripts/addons` path if u're a gangsta

Once enabled, the script will add the following actions to the pose menu (mouse right click in **pose mode**)


* Enable/disable constraints
    
    options:
    * Status: enabled/disabled/remove (careful with the last one)
    * Only Selected: affect only selected bones if checked

* Revert dots in Names: Unreal Engine doesn't like dots in name and will convert "bone.L" to "bone_L".
                        Bring 'em dots back using this fine operator

    options:
    * Only Side Letters: will only revert side identifiers, like "_L" to ".R", but will leave
                         the rest of the name untouched, i.e. "bone_name" won't become "bone.name".
                         This is better left on, but hey, it's your rig after all.
    * Only Selected: as you certainly guess, only selected bones get to be renamed
    
* Convert Bone Names: Renames a standard hierarchy to another, i.e. Rigify skeleton to Mixamo skeleton
    options:
    * Source Type
    * Target Type 